from django.db import models
from company_details.models import CompanyDetails


# Added by me
import re
from django.db import transaction

# Added by me
def generate_line_item_id(prefix: str) -> str:
    """
    prefix is everything before the trailing digits, e.g. 'LILEAD' from 'LILEAD002'.
    Locks and recomputes the next number atomically — guarantees uniqueness even
    if multiple browser tabs submit near-simultaneously.
    """
    with transaction.atomic():
        last = (
            LineItem.objects
            .select_for_update()
            .filter(line_item_id__startswith=prefix)
            .order_by('-line_item_id')
            .first()
        )
        if last:
            match = re.search(r'(\d+)$', last.line_item_id)
            last_num = int(match.group(1)) if match else 0
            new_num = last_num + 1
        else:
            new_num = 1
        return f"{prefix}{str(new_num).zfill(3)}"



class Campaign(models.Model):
 
    client = models.ForeignKey(CompanyDetails, on_delete=models.CASCADE, related_name="campaigns")  # ← renamed from client_id
    ticket_id = models.CharField(max_length=20, blank=True, null=True, db_index=True)  # ← ADD THIS

    campaign_name = models.CharField(max_length=300)

    client_campaign_ID = models.CharField(max_length=100, blank=True, null=True)
    purchase_order_ID = models.CharField(max_length=100, blank=True, null=True)

    campaign_type = models.CharField(max_length=50)
    buying_type = models.CharField(max_length=60)
    objective = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()

    notes = models.TextField(blank=True, null=True)
    
    report_published = models.BooleanField(default=False)
    # Today date (7/8/2026)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('live', 'Live'),
        ],
        default='pending',
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        db_table = "tbl_campaign"
        verbose_name = "Campaign"
        verbose_name_plural = 'Campaigns'

    def __str__(self):
        return f"{self.campaign_name}"   # ← fixed, was self.campaign_id which doesn't exist
# ==== Add Line Item ====

def generate_line_item_id(prefix="LILEAD"):
    """Sequential, collision-proof: LILEAD001, LILEAD002, ... across ALL campaigns."""
    with transaction.atomic():
        last = (
            LineItem.objects
            .filter(line_item_id__startswith=prefix)
            .exclude(line_item_id__isnull=True).exclude(line_item_id="")
            .select_for_update()
            .order_by("-line_item_id")
            .first()
        )
        try:
            last_num = int(last.line_item_id.replace(prefix, "")) if last else 0
        except ValueError:
            last_num = 0
        new_num = last_num + 1
        return f"{prefix}{str(new_num).zfill(3)}"
    
class LineItem(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='line_items') # One campaign have multiple line items (,null=True, blank=True)

    line_item_id = models.CharField(max_length=50, unique=True)  # ← add unique=True
    line_item_name = models.CharField(max_length=300)

    # Better than comma-separated
    ethnicity = models.JSONField(blank=True, null=True)

    start_date = models.DateField() 
    end_date = models.DateField()

    # multiple formats (image, video)
    ad_format = models.JSONField()

    impressions = models.BigIntegerField(null=True, blank=True)

    
    units = models.CharField(max_length=100,null=True, blank=True)
    ctr = models.FloatField(null=True, blank=True)
    viewability = models.FloatField(null=True, blank=True)
    vcr = models.FloatField(null=True, blank=True)

    # add unit costs and kpi notes
    unit_cost = models.CharField(max_length=100,null=True, blank=True)
    kpi_notes = models.TextField(null=True, blank=True)
    unit_value = models.FloatField(null=True, blank=True)

    # ── NEW targeting fields ──
    age = models.CharField(max_length=200, blank=True, null=True)
    gender = models.CharField(max_length=100, blank=True, null=True)
    geo_targeting = models.TextField(blank=True, null=True)

    dv_id = models.CharField(max_length=100, blank=True, null=True, unique=True)  # ← ADD THIS
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('live', 'Live'),
            ('upcoming', 'Upcoming'),
            ('completed', 'Completed'),
            ('paused', 'Paused'),
        ],
        default='upcoming'
    )
    
    def compute_status(self):
        from datetime import date
        today = date.today()
        
        if self.start_date and self.end_date:
            if today > self.end_date:
                return 'completed'  # end date over → always completed, no override
            elif today >= self.start_date:
                return 'live'       # within date range → live
            else:
                return 'upcoming'   # start date not reached → upcoming
        return 'upcoming'

    def save(self, *args, **kwargs):
        from datetime import date
        today = date.today()
        
        # Only allow 'paused' as manual override — and only if end date is NOT over
        if self.status == 'paused' and self.end_date and today <= self.end_date:
            pass  # keep paused as-is
        else:
            self.status = self.compute_status()  # auto-compute for everything else
        
        super().save(*args, **kwargs)
        
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        db_table = "tbl_line_items"
        verbose_name = "Line item"
        verbose_name_plural = 'Line items'
        unique_together = ("campaign", "line_item_id")   # ← add this

    #  validation
    def clean(self):
        if self.end_date and self.start_date:
            if self.end_date < self.start_date:
                raise ValueError("End date must be greater than start date")

    def __str__(self):
        return f"{self.line_item_name} ({self.campaign.campaign_name})"


class Creative(models.Model):
    line_item = models.ForeignKey(
        LineItem,
        on_delete=models.CASCADE,
        related_name='creatives_detail' 
    )

    creative_name = models.CharField(max_length=300)

    # FILES
    main_asset = models.FileField(upload_to='creatives/main/', blank=True, null=True)
    #backup_image = models.FileField(upload_to='creatives/backup/', blank=True, null=True)

    # AUTO FILE TYPE
    #file_type = models.CharField(max_length=20, blank=True)

    # META DATA
    dimensions = models.CharField(max_length=50, blank=True)
    aspect_ratio = models.CharField(max_length=20, blank=True)
    file_size = models.CharField(max_length=30, blank=True)

    # FILE NAMES
    #main_asset_name = models.CharField(max_length=255, blank=True)
    #backup_image_name = models.CharField(max_length=255, blank=True)

    # EXTRA
    click_through_url = models.URLField(max_length=400, blank=True, null=True)
    appended_html_tag = models.TextField(blank=True)
    integration_code = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    creative_id = models.CharField(max_length=100, blank=True, null=True)  # ← ADD THIS

    class Meta:
        ordering = ['-uploaded_at']
        db_table = "tbl_creatives"
        verbose_name = "Creative"
        verbose_name_plural = 'Creatives'

    def __str__(self):
        return f"{self.creative_name} ({self.line_item.line_item_name})"


# ==============================
# THIRD PARTY CREATIVE
# ==============================

class ThirdPartyCreative(models.Model):

    line_item = models.ForeignKey(LineItem,on_delete=models.CASCADE,related_name='third_party_creatives')
    # ZIP / HTML / TXT / DOCX / XLSX
    input_file = models.FileField(upload_to='thirdparty/files/',blank=True,null=True)

    # Backup image
    backup_image = models.FileField(upload_to='thirdparty/backup/',blank=True,null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    creative_id = models.CharField(max_length=100, blank=True, null=True)  # ← ADD THIS

    class Meta:
        ordering = ['-uploaded_at']
        db_table = "tbl_thirdparty_creative"
        verbose_name = "ThirdParty Creative"
        verbose_name_plural = 'ThirdParty Creatives'

    def __str__(self):
        return f"ThirdPartyCreative ({self.line_item.line_item_name})"

from django.db import transaction

class InsertionOrder(models.Model):
    campaign = models.OneToOneField(Campaign, on_delete=models.CASCADE, related_name="insertion_order")
    io_id = models.CharField(max_length=20, unique=True, editable=False)
    pdf_file = models.FileField(upload_to="insertion_orders/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tbl_insertion_order"

    def __str__(self):
        return f"{self.io_id} — {self.campaign.campaign_name}"


def generate_io_id():
    """Mirrors leads.models.generate_ticket_id — sequential IO0001, IO0002, ..."""
    with transaction.atomic():
        last = (
            InsertionOrder.objects
            .exclude(io_id__isnull=True).exclude(io_id="")
            .select_for_update()
            .order_by("-io_id")
            .first()
        )
        new_num = int(last.io_id.replace("IO", "")) + 1 if last else 1
        return f"IO{str(new_num).zfill(4)}"