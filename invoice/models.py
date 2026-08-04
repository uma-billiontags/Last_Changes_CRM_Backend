from django.db import models
from company_details.models import CompanyDetails, CompanyContacts
from campaigns.models import Campaign, LineItem
from categories.models import InvoiceAuthorizedPerson  # ← reuse existing model, no need to redefine

INVOICE_STATUS = (
    ("Not Paid", "Not Paid"),
    ("Partial Paid", "Partial Paid"),
    ("Paid", "Paid"),
)


class Invoice(models.Model):
    invoice_id = models.CharField(max_length=20, unique=True, editable=False)
    client = models.ForeignKey(CompanyDetails, on_delete=models.CASCADE, related_name='invoices')

    contact_person = models.ForeignKey(
        CompanyContacts,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invoices',
    )

    # ← ONE invoice can cover MULTIPLE campaigns (identified by ticket_id underneath)
    campaigns = models.ManyToManyField(Campaign, related_name='invoices')

    invoice_month = models.DateField(null=True, blank=True, help_text="1st of the invoice month, e.g. 2026-06-01")
    invoice_from = models.DateField(null=True, blank=True)
    invoice_to = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)

    invoice_no = models.CharField(max_length=120, unique=True, null=True, blank=True)
    additional_discount = models.FloatField(default=0.0, verbose_name="Offers or Discount")
    gst = models.PositiveIntegerField(null=True, blank=True, verbose_name="GST %")
    vat_tax = models.PositiveIntegerField(null=True, blank=True, verbose_name="VAT %")
    gst_amount = models.FloatField(default=0.0)
    vat_tax_amount = models.FloatField(default=0.0)
    total_amount = models.FloatField(default=0.0)
    total_discount = models.FloatField(default=0.0)
    billing_amount = models.FloatField(default=0.0)
    status = models.CharField(max_length=20, choices=INVOICE_STATUS, default="Not Paid")
    is_approved = models.BooleanField(default=False)
    invoice_type = models.CharField(
        max_length=20,
        choices=(("single", "Single"), ("multiple", "Multiple")),
        default="single",
    )

    generated_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(upload_to='invoices/', null=True, blank=True)

    class Meta:
        db_table = "tbl_invoice"
        ordering = ['-generated_at']

    def generate_invoice_id(self):
        last = Invoice.objects.order_by('-id').first()
        if last and last.invoice_id:
            try:
                last_num = int(last.invoice_id[3:])
                new_num = last_num + 1
            except ValueError:
                new_num = 1
        else:
            new_num = 1
        return f"BTU{str(new_num).zfill(6)}"

    def save(self, *args, **kwargs):
        if not self.invoice_id:
            self.invoice_id = self.generate_invoice_id()
        if not self.invoice_no:
            self.invoice_no = self.invoice_id
        super().save(*args, **kwargs)

    def additional_discount_per(self):
        try:
            return round((self.additional_discount / self.billing_amount) * 100, 4)
        except (ZeroDivisionError, TypeError):
            return 0

    def total_pay_amount(self):
        result = round(self.billing_amount - self.additional_discount, 2)
        return max(result, 0)

    def total_paid(self):
        amount = self.payment_history.aggregate(amount=models.Sum("amount"))['amount']
        return amount or 0

    def balance_amount(self):
        return round(self.total_pay_amount() - self.total_paid(), 2)

    def __str__(self):
        return f"{self.invoice_id} → {self.client.name if self.client else ''}"


class InvoiceLineItem(models.Model):
    invoice = models.ForeignKey(Invoice, related_name="line_items", on_delete=models.CASCADE)
    line_item = models.ForeignKey(LineItem, on_delete=models.CASCADE)
    description = models.CharField(max_length=300, blank=True)

    net_cost = models.FloatField(default=0.0)      # this month's actual spend (from CampaignDailyEntry)
    booked_cost = models.FloatField(default=0.0)   # booked ceiling — parsed from LineItem.unit_cost
    discount = models.FloatField(default=0.0)      # auto overspend-discount, this line item, this month
    billing_cost = models.FloatField(default=0.0)  # net_cost − discount

    class Meta:
        db_table = "tbl_invoice_line_item"
        unique_together = ("invoice", "line_item")

    def __str__(self):
        return f"{self.description} ({self.invoice.invoice_id})"


class PaymentHistory(models.Model):
    invoice = models.ForeignKey(Invoice, related_name="payment_history", on_delete=models.CASCADE)
    mode_of_payment = models.CharField(max_length=100)
    amount = models.FloatField()
    date = models.DateField()
    additional_info = models.CharField(max_length=200, blank=True, null=True)
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "tbl_payment_history"
        ordering = ["-created_on"]

    def __str__(self):
        return f"{self.invoice.invoice_id} - {self.mode_of_payment} - {self.amount}"