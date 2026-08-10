# campaigns/utils.py
"""
Shared helper for the "Live" status automation.
Called from both tasks/views.py (when Creative Ops marks a task complete)
and reports/views.py (when a campaign report is generated).
"""


def check_and_update_campaign_live_status(ticket_id):
    """
    Flips Campaign.status to 'live' only when ALL 3 conditions are true:
      1. Creative Ops task for this ticket is 'completed'
      2. Every creative (standard + third-party) across all line items has a Creative ID
      3. At least one CampaignExcel report has been generated for this campaign
    Safe to call anywhere — never raises, so it can't break the caller's flow.
    """
    if not ticket_id:
        return

    from campaigns.models import Campaign
    from tasks.models import TaskAssignment
    from reports.models import CampaignExcel

    try:
        campaign = Campaign.objects.get(ticket_id=ticket_id)
    except Campaign.DoesNotExist:
        return

    # already live — nothing to do
    if campaign.status == "live":
        return

    # ── Condition 1: Creative Ops task completed ──
    creative_task = (
        TaskAssignment.objects
        .filter(ticket_id=ticket_id, task_type="creative_ops")
        .order_by("-assigned_at", "-id")
        .first()
    )
    if not creative_task or creative_task.status != "completed":
        return

    # ── Condition 2: every creative has a Creative ID ──
    for li in campaign.line_items.all():
        for c in li.creatives_detail.all():
            if not c.creative_id or not c.creative_id.strip():
                return
        for tp in li.third_party_creatives.all():
            if not tp.creative_id or not tp.creative_id.strip():
                return

    # ── Condition 3: at least one campaign report generated ──
    if not CampaignExcel.objects.filter(campaign=campaign).exists():
        return

    # ── All 3 conditions passed ──
    campaign.status = "live"
    campaign.save(update_fields=["status"])