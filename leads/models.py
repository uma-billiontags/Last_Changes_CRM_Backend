from django.db import models
from company_details.models import CompanyDetails
from django.db import transaction

def generate_ticket_id():
    with transaction.atomic():
        last = (
            Lead.objects
            .exclude(ticket_id__isnull=True)
            .exclude(ticket_id="")
            .select_for_update()
            .order_by('-ticket_id') # ← fixed: order by the ticket number itself, not by lead id
            .first()
        )
        if last and last.ticket_id:
            last_num = int(last.ticket_id.replace('TIK', ''))
            new_num = last_num + 1
        else:
            new_num = 1
        return f"TIK{str(new_num).zfill(4)}"   # TIK0001, TIK0002, ...


class ExcludedEmail(models.Model):
    """Sender addresses whose emails should NEVER be saved."""
    email = models.EmailField(unique=True)
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class LeadCategory(models.Model):
    """A category bucket, e.g. 'Creative Team', 'Account Manager Team'."""
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    priority = models.PositiveIntegerField(
        default=0,
        help_text="Lower number = checked first, in case an email matches multiple categories."
    )

    class Meta:
        ordering = ['priority', 'name']

    def __str__(self):
        return self.name


class CategoryKeyword(models.Model):
    """A keyword/phrase that, if found in an email, assigns it to `category`."""
    category = models.ForeignKey(LeadCategory, related_name='keywords', on_delete=models.CASCADE)
    keyword = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.keyword} → {self.category.name}"


class Lead(models.Model):
    CATEGORY_STATUS_CHOICES = (
        ('category', 'Category'),
        ('uncategory', 'Uncategory'),
    )

    sender = models.CharField(max_length=255)
    receiver = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=500)
    body = models.TextField()
    thread_id = models.CharField(max_length=255)
    message_id = models.CharField(max_length=255, unique=True)
    mail_link = models.URLField(blank=True)
    received_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    category_status = models.CharField(
        max_length=20, choices=CATEGORY_STATUS_CHOICES, default='uncategory'
    )
    category_name = models.CharField(max_length=100, blank=True, null=True)
    
    # ── NEW ──
    ticket_id = models.CharField(max_length=20, unique=True, blank=True, null=True, editable=False)
    client = models.ForeignKey(
        CompanyDetails, on_delete=models.SET_NULL, blank=True, null=True,
        related_name="leads", verbose_name="Linked Client"
    )
    
    source_account = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.subject
    

class LeadAttachment(models.Model):
    lead = models.ForeignKey(Lead, related_name='attachments', on_delete=models.CASCADE)
    filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100, blank=True)
    size = models.PositiveIntegerField(default=0)
    file = models.FileField(upload_to='lead_attachments')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.filename} ({self.lead_id})"