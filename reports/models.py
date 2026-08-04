from django.db import models
from campaigns.models import Campaign, LineItem


class CampaignDailyEntry(models.Model):
    """One row per (line_item, date). Locks the date once submitted."""
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="daily_entries")
    line_item = models.ForeignKey(LineItem, on_delete=models.CASCADE, related_name="daily_entries")
    entry_date = models.DateField()

    impressions = models.BigIntegerField(default=0)
    clicks = models.BigIntegerField(default=0)
    ctr = models.FloatField(default=0)
    viewable_impression = models.BigIntegerField(default=0)
    measurable_impression = models.BigIntegerField(default=0)
    video_start = models.BigIntegerField(default=0)
    video_end = models.BigIntegerField(default=0)
    revenue = models.FloatField(default=0)
    media_cost = models.FloatField(default=0)
    vcr = models.FloatField(default=0)
    viewability = models.FloatField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tbl_campaign_daily_entry"
        unique_together = ("line_item", "entry_date")
        ordering = ["entry_date"]

    def __str__(self):
        return f"{self.line_item.line_item_id} — {self.entry_date} — {self.impressions} imp"


class CampaignDailyReportExcel(models.Model):
    campaign = models.OneToOneField(Campaign, on_delete=models.CASCADE, related_name="daily_report_excel")
    excel_file = models.FileField(upload_to="daily_report_excels/")
    generated_at = models.DateTimeField(auto_now=True)
  
    class Meta:
        db_table = "tbl_campaign_daily_report_excel"
        
        
        
# Added by charu
from campaigns.models import Campaign, LineItem


class CampaignExcel(models.Model):
    REPORT_TYPE_CHOICES = [("cpm", "CPM (Impressions Booked)"), ("cpc", "CPC (Clicks Booked)")]
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="excel_reports")
    report_type = models.CharField(max_length=10, choices=REPORT_TYPE_CHOICES, default="cpm")
    excel_file = models.FileField(upload_to="excel_reports/")
    generated_at = models.DateTimeField(auto_now=True)
    line_item_overrides = models.JSONField(default=dict, blank=True)
    PUBLISH_STATUS_CHOICES = [("published", "Published")]
    publish_status = models.CharField(max_length=20, choices=PUBLISH_STATUS_CHOICES, null=True, blank=True, default=None)
    needs_republish = models.BooleanField(default=False)   # ← ADD THIS

    class Meta:
        unique_together = ("campaign", "report_type")



class CampaignLineItemExcelDetails(models.Model):
    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="line_item_excel_data"
    )
    line_item = models.ForeignKey(
        LineItem, on_delete=models.CASCADE, related_name="excel_data"
    )
    report_type = models.CharField(
        max_length=10, choices=[("cpm", "CPM"), ("cpc", "CPC")], default="cpm"
    )

    # ── Excel-specific fields ──
    impressions = models.BigIntegerField(null=True, blank=True)  # CPM report
    clicks = models.BigIntegerField(null=True, blank=True)  # CPC report only

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    target_cpm = models.FloatField(
        null=True, blank=True
    )  # ← ADD THIS (unit_cost for CPM)
    target_ctr = models.FloatField(null=True, blank=True)  # ctr field from LineItem
    target_cpc = models.FloatField(
        null=True, blank=True
    )  # CPC only, no LineItem source

    booked_budget = models.FloatField(
        null=True, blank=True
    )  # CPC only, no LineItem source

    sitelist = models.TextField(null=True, blank=True)  # only here, not in LineItem

    advertiser_id = models.CharField(max_length=100, blank=True, null=True)
    # Default from campaign.client_campaign_ID, but edits saved here only

    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("line_item", "report_type")

    def __str__(self):
        return f"ExcelData — {self.line_item.line_item_id} ({self.report_type})"

