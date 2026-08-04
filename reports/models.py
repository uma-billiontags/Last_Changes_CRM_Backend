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