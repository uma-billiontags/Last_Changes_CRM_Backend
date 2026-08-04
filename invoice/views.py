from datetime import date, timedelta
import calendar

from django.db.models import Sum
from django.core.files.base import ContentFile
from django.http import HttpResponse, Http404, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response

from campaigns.models import Campaign, LineItem
from reports.models import CampaignDailyEntry
from company_details.models import CompanyDetails, CompanyContacts
from .models import Invoice, InvoiceLineItem, PaymentHistory


# ── Parse LineItem.unit_cost text into a number (booked total cost / ceiling) ──
def get_booked_cost(line_item):
    if not line_item.unit_cost:
        return 0
    try:
        return float(''.join(c for c in line_item.unit_cost if c.isdigit() or c == '.'))
    except ValueError:
        return 0


def get_rate(line_item):
    return line_item.unit_value or 0


# ── THE CORE ENGINE — cumulative overspend discount + billing amount ──
def calculate_invoice_amounts(invoice):
    """
    For every line item across every campaign (ticket_id) on this invoice:
      - this month's delivered volume = SUM(impressions or clicks) from CampaignDailyEntry, THIS invoice month
      - previous delivered volume     = SUM(impressions or clicks) from CampaignDailyEntry, BEFORE invoice_from
      - this_month_spend = (volume/1000)*rate [CPM] or volume*rate [CPC]
      - if cumulative spend > booked_cost (from unit_cost) → discount = overage (capped at this month's spend)
      - billing_cost = this_month_spend - discount
    Rolls up into invoice.total_amount, total_discount, billing_amount (+ GST/VAT).
    """
    total_amount = 0
    total_discount = 0
    total_billing_amount = 0

    line_items = LineItem.objects.filter(campaign__in=invoice.campaigns.all()).distinct()

    InvoiceLineItem.objects.filter(invoice=invoice).exclude(line_item__in=line_items).delete()

    for li in line_items:
        booked_cost = get_booked_cost(li)
        rate = get_rate(li)
        is_cpc = (li.units or "").strip().upper() == "CPC"

        this_month_qs = CampaignDailyEntry.objects.filter(
            line_item=li,
            entry_date__year=invoice.invoice_from.year,
            entry_date__month=invoice.invoice_from.month,
        )
        previous_qs = CampaignDailyEntry.objects.filter(
            line_item=li,
            entry_date__lt=invoice.invoice_from,
        )

        if is_cpc:
            this_month_volume = this_month_qs.aggregate(total=Sum('clicks'))['total'] or 0
            previous_volume = previous_qs.aggregate(total=Sum('clicks'))['total'] or 0
            this_month_spend = round(this_month_volume * rate, 2)
            previous_spend = round(previous_volume * rate, 2)
        else:  # CPM (default)
            this_month_volume = this_month_qs.aggregate(total=Sum('impressions'))['total'] or 0
            previous_volume = previous_qs.aggregate(total=Sum('impressions'))['total'] or 0
            this_month_spend = round((this_month_volume / 1000) * rate, 2)
            previous_spend = round((previous_volume / 1000) * rate, 2)

        overall_spent = round(this_month_spend + previous_spend, 2)

        discount = 0
        if overall_spent > round(booked_cost, 2):
            discount = round(overall_spent - booked_cost, 2)
        if this_month_spend < discount:
            discount = this_month_spend

        billing_cost = round(this_month_spend - discount, 2)

        InvoiceLineItem.objects.update_or_create(
            invoice=invoice,
            line_item=li,
            defaults=dict(
                description=li.line_item_name,
                net_cost=this_month_spend,
                booked_cost=booked_cost,
                discount=round(discount, 2),
                billing_cost=billing_cost,
            )
        )

        total_amount += this_month_spend
        total_discount += discount
        total_billing_amount += billing_cost

    invoice.total_amount = round(total_amount, 2)
    invoice.total_discount = round(total_discount, 2)
    invoice.gst_amount = round((total_billing_amount / 100) * invoice.gst, 2) if invoice.gst else 0
    invoice.vat_tax_amount = round((total_billing_amount / 100) * invoice.vat_tax, 2) if invoice.vat_tax else 0
    invoice.billing_amount = round(
        invoice.gst_amount + invoice.vat_tax_amount + total_billing_amount, 2
    )
    invoice.save()
    return invoice


def apply_manual_discount(invoice, discount_input):
    discount_input = (discount_input or "").strip()
    billing_amount = invoice.billing_amount or 0
    final_discount = 0

    if discount_input:
        if discount_input.endswith("%"):
            try:
                pct = float(discount_input.rstrip("%").strip())
                final_discount = round((billing_amount * pct) / 100, 2) if billing_amount > 0 else 0
            except ValueError:
                raise ValueError("Invalid percentage value. e.g. 10%")
        else:
            try:
                final_discount = round(float(discount_input), 2)
            except ValueError:
                raise ValueError("Invalid discount value. Enter amount (e.g. 100) or % (e.g. 10%)")

    if billing_amount > 0 and final_discount > billing_amount:
        raise ValueError(f"Discount ({final_discount}) cannot exceed billing amount ({billing_amount}).")

    invoice.additional_discount = final_discount
    invoice.save(update_fields=["additional_discount"])
    return final_discount


# ── Shared eligibility helper — keyed on ticket_id instead of campaign_id/approval_status ──
def get_eligible_campaigns(client, month_start, month_end):
    """
    A campaign is eligible for invoice month [month_start, month_end] if:
      1. It has a ticket_id assigned (equivalent to being a "real"/active campaign)
      2. It has at least one LINE ITEM whose date range overlaps the month
      3. The month has FULLY CLOSED — month_end must be before today.
    """
    today = date.today()
    if month_end >= today:
        return Campaign.objects.none()

    return Campaign.objects.filter(
        client=client,
    ).exclude(
        ticket_id__isnull=True
    ).exclude(
        ticket_id=""
    ).filter(
        line_items__start_date__lte=month_end,
        line_items__end_date__gte=month_start,
    ).distinct().order_by("-created_at")


@api_view(['POST'])
def generate_monthly_invoice(request):
    """
    Body: {
        "client_id": "CL0001",
        "invoice_month": "2026-07-01",
        "campaign_ids": [12, 15, 20],       # internal PK of Campaign (not ticket_id)
        "contact_person_id": 4,             # optional
        "gst": 18,
        "vat_tax": null,
        "additional_discount": "10%",
        "existing_invoice_id": "BTU000001"  # optional — regenerate/overwrite
    }
    """
    client_id = request.data.get("client_id")
    invoice_month_str = request.data.get("invoice_month")
    campaign_ids = request.data.get("campaign_ids") or []
    contact_person_id = request.data.get("contact_person_id")
    gst_input = request.data.get("gst")
    vat_input = request.data.get("vat_tax")
    discount_input = request.data.get("additional_discount")
    existing_invoice_id = request.data.get("existing_invoice_id")

    if not client_id or not invoice_month_str:
        return Response({"error": "client_id and invoice_month are required"}, status=400)
    if not campaign_ids:
        return Response({"error": "Select at least one campaign"}, status=400)

    def parse_pct(value, label):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid {label} value")

    try:
        gst_val = parse_pct(gst_input, "GST")
        vat_val = parse_pct(vat_input, "VAT")
    except ValueError as e:
        return Response({"error": str(e)}, status=400)

    try:
        client = CompanyDetails.objects.get(client_id=client_id)
        invoice_month = date.fromisoformat(invoice_month_str)
    except CompanyDetails.DoesNotExist:
        return Response({"error": "Client not found"}, status=404)
    except ValueError:
        return Response({"error": "Invalid invoice_month format, use YYYY-MM-DD"}, status=400)

    client_invoice_type = client.invoice_type or "single"

    month_start = invoice_month.replace(day=1)
    last_day = calendar.monthrange(invoice_month.year, invoice_month.month)[1]
    month_end = invoice_month.replace(day=last_day)

    if month_end >= date.today():
        return Response(
            {"error": "This month hasn't ended yet. You can only invoice fully completed months."},
            status=400,
        )

    eligible_ids = set(
        get_eligible_campaigns(client, month_start, month_end).values_list("id", flat=True)
    )
    campaigns = Campaign.objects.filter(client=client, id__in=campaign_ids)
    invalid_ids = [c.id for c in campaigns if c.id not in eligible_ids]
    campaigns = campaigns.filter(id__in=eligible_ids)

    if not campaigns.exists():
        return Response({"error": "None of the selected campaigns are valid for this client/month"}, status=400)
    if invalid_ids:
        return Response(
            {"error": f"Campaign(s) {invalid_ids} have no line items running in this month and were excluded."},
            status=400,
        )

    contact_person = None
    if contact_person_id:
        contact_person = CompanyContacts.objects.filter(id=contact_person_id, company=client).first()
    else:
        contact_person = client.default_contact_person

    created_invoices = []

    if client_invoice_type == "single":
        if existing_invoice_id:
            invoice = Invoice.objects.filter(invoice_id=existing_invoice_id, client=client).first()
        else:
            invoice = Invoice.objects.filter(client=client, invoice_month=month_start, invoice_type="single").first()
        invoice = invoice or Invoice.objects.create(client=client)

        invoice.invoice_month = month_start
        invoice.invoice_from = month_start
        invoice.invoice_to = month_end
        invoice.due_date = month_end + timedelta(days=7)
        invoice.invoice_type = "single"
        invoice.contact_person = contact_person
        if gst_val is not None:
            invoice.gst = gst_val
        if vat_val is not None:
            invoice.vat_tax = vat_val
        invoice.save()
        invoice.campaigns.set(campaigns)
        calculate_invoice_amounts(invoice)
        if discount_input:
            try:
                apply_manual_discount(invoice, discount_input)
            except ValueError as e:
                return Response({"error": str(e)}, status=400)
        created_invoices.append(invoice)

    else:  # "multiple" — one invoice per campaign
        for campaign in campaigns:
            if existing_invoice_id:
                invoice = Invoice.objects.filter(invoice_id=existing_invoice_id, client=client, campaigns=campaign).first()
            else:
                invoice = Invoice.objects.filter(
                    client=client, invoice_month=month_start, invoice_type="multiple", campaigns=campaign
                ).first()
            invoice = invoice or Invoice.objects.create(client=client)

            invoice.invoice_month = month_start
            invoice.invoice_from = month_start
            invoice.invoice_to = month_end
            invoice.due_date = month_end + timedelta(days=7)
            invoice.invoice_type = "multiple"
            invoice.contact_person = contact_person
            if gst_val is not None:
                invoice.gst = gst_val
            if vat_val is not None:
                invoice.vat_tax = vat_val
            invoice.save()
            invoice.campaigns.set([campaign])
            calculate_invoice_amounts(invoice)
            if discount_input:
                try:
                    apply_manual_discount(invoice, discount_input)
                except ValueError as e:
                    return Response({"error": str(e)}, status=400)
            created_invoices.append(invoice)

    return Response({
        "message": f"{len(created_invoices)} invoice(s) generated/updated",
        "invoices": [
            {
                "invoice_id": inv.invoice_id,
                "billing_amount": inv.billing_amount,
                "total_pay_amount": inv.total_pay_amount(),
                "gst": inv.gst,
                "vat_tax": inv.vat_tax,
                "campaigns": [c.ticket_id for c in inv.campaigns.all()],   # ← ticket_id, not campaign_id
            } for inv in created_invoices
        ],
    }, status=200)


@api_view(['POST'])
def set_invoice_discount(request, invoice_id):
    try:
        invoice = Invoice.objects.get(invoice_id=invoice_id)
    except Invoice.DoesNotExist:
        return Response({"error": "Invoice not found"}, status=404)

    try:
        final_discount = apply_manual_discount(invoice, request.data.get("additional_discount"))
    except ValueError as e:
        return Response({"error": str(e)}, status=400)

    return Response({
        "message": "Discount applied",
        "additional_discount": final_discount,
        "total_pay_amount": invoice.total_pay_amount(),
    }, status=200)


@api_view(['POST'])
def set_invoice_tax(request, invoice_id):
    try:
        invoice = Invoice.objects.get(invoice_id=invoice_id)
    except Invoice.DoesNotExist:
        return Response({"error": "Invoice not found"}, status=404)

    def parse_pct(value, label):
        if value in (None, ""):
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid {label} value")

    try:
        if "gst" in request.data:
            invoice.gst = parse_pct(request.data.get("gst"), "GST")
        if "vat_tax" in request.data:
            invoice.vat_tax = parse_pct(request.data.get("vat_tax"), "VAT")
    except ValueError as e:
        return Response({"error": str(e)}, status=400)

    invoice.save(update_fields=["gst", "vat_tax"])
    calculate_invoice_amounts(invoice)

    return Response({
        "message": "Tax applied",
        "gst": invoice.gst,
        "vat_tax": invoice.vat_tax,
        "billing_amount": invoice.billing_amount,
        "total_pay_amount": invoice.total_pay_amount(),
    }, status=200)


@api_view(['POST'])
def record_payment(request, invoice_id):
    try:
        invoice = Invoice.objects.get(invoice_id=invoice_id)
    except Invoice.DoesNotExist:
        return Response({"error": "Invoice not found"}, status=404)

    PaymentHistory.objects.create(
        invoice=invoice,
        mode_of_payment=request.data.get("mode_of_payment"),
        amount=request.data.get("amount"),
        date=request.data.get("date"),
        additional_info=request.data.get("additional_info", ""),
    )

    paid = invoice.total_paid()
    invoice.status = "Paid" if paid >= invoice.total_pay_amount() else "Partial Paid"
    invoice.save(update_fields=["status"])

    return Response({
        "message": "Payment recorded",
        "status": invoice.status,
        "balance_amount": invoice.balance_amount(),
    }, status=200)


@api_view(['GET'])
def get_invoices_by_client(request, client_id):
    try:
        client = CompanyDetails.objects.get(client_id=client_id)
    except CompanyDetails.DoesNotExist:
        return Response({"error": "Client not found"}, status=404)

    invoice_type = client.invoice_type or "single"
    invoices = Invoice.objects.filter(client=client).prefetch_related("campaigns").order_by("-invoice_month")

    data = []
    for inv in invoices:
        data.append({
            "invoice_id": inv.invoice_id,
            "invoice_month": str(inv.invoice_month) if inv.invoice_month else None,
            "invoice_from": str(inv.invoice_from) if inv.invoice_from else None,
            "invoice_to": str(inv.invoice_to) if inv.invoice_to else None,
            "due_date": str(inv.due_date) if inv.due_date else None,
            "invoice_type": inv.invoice_type,
            "campaigns": [
                {"ticket_id": c.ticket_id, "campaign_name": c.campaign_name}
                for c in inv.campaigns.all()
            ],
            "total_amount": inv.total_amount,
            "total_discount": inv.total_discount,
            "additional_discount": inv.additional_discount,
            "billing_amount": inv.billing_amount,
            "total_pay_amount": inv.total_pay_amount(),
            "total_paid": inv.total_paid(),
            "balance_amount": inv.balance_amount(),
            "status": inv.status,
            "is_approved": inv.is_approved,
            "pdf_generated": bool(inv.pdf_file),
            "pdf_url": request.build_absolute_uri(inv.pdf_file.url) if inv.pdf_file else None,
            "gst": inv.gst,
            "vat_tax": inv.vat_tax,
            "gst_amount": inv.gst_amount,
            "vat_tax_amount": inv.vat_tax_amount,
        })

    return Response({
        "client_id": client.client_id,
        "client_name": client.name,
        "invoice_type": invoice_type,
        "invoices": data,
    })


@api_view(['GET'])
def get_all_clients(request):
    clients = CompanyDetails.objects.all().order_by('name')
    data = [
        {"client_id": c.client_id, "name": c.name, "invoice_type": c.invoice_type}
        for c in clients
    ]
    return Response({"clients": data})


@api_view(['GET'])
def get_client_invoice_info(request, client_id):
    try:
        client = CompanyDetails.objects.get(client_id=client_id)
    except CompanyDetails.DoesNotExist:
        return Response({"error": "Client not found"}, status=404)

    contact = client.default_contact_person

    return Response({
        "client_id": client.client_id,
        "client_name": client.name,
        "invoice_type": client.invoice_type or "single",
        "billing_currency": client.billing_currency,
        "contact_person": {
            "id": contact.id,
            "name": contact.name,
            "email": contact.email,
            "phone": contact.phone,
        } if contact else None,
        "default_invoice_address_id": client.default_invoice_address_id,
        "default_invoice_bank_id": client.default_invoice_bank_id,
        "default_authorized_person": {
            "id": client.default_authorized_person.id,
            "name": client.default_authorized_person.name,
        } if client.default_authorized_person else None,
    })


@api_view(['GET'])
def get_available_campaigns(request, client_id):
    """
    GET /get_available_campaigns/<client_id>/?invoice_month=2026-07-01&exclude_invoice_id=BTU000001
    """
    invoice_month_str = request.GET.get("invoice_month")
    exclude_invoice_id = request.GET.get("exclude_invoice_id")

    if not invoice_month_str:
        return Response({"error": "invoice_month is required"}, status=400)

    try:
        client = CompanyDetails.objects.get(client_id=client_id)
        invoice_month = date.fromisoformat(invoice_month_str)
    except CompanyDetails.DoesNotExist:
        return Response({"error": "Client not found"}, status=404)
    except ValueError:
        return Response({"error": "Invalid invoice_month format, use YYYY-MM-DD"}, status=400)

    month_start = invoice_month.replace(day=1)
    last_day = calendar.monthrange(invoice_month.year, invoice_month.month)[1]
    month_end = invoice_month.replace(day=last_day)

    campaigns = get_eligible_campaigns(client, month_start, month_end)

    invoiced_qs = Invoice.objects.filter(client=client, invoice_month=month_start)
    if exclude_invoice_id:
        invoiced_qs = invoiced_qs.exclude(invoice_id=exclude_invoice_id)

    already_invoiced_campaign_ids = invoiced_qs.values_list("campaigns__id", flat=True)
    campaigns = campaigns.exclude(id__in=list(already_invoiced_campaign_ids))

    data = [
        {
            "id": c.id,
            "ticket_id": c.ticket_id,
            "campaign_name": c.campaign_name,
            "start_date": str(c.start_date),
            "end_date": str(c.end_date),
        }
        for c in campaigns
    ]
    return Response({"campaigns": data})


@api_view(['GET'])
def get_invoice_detail(request, invoice_id):
    try:
        invoice = Invoice.objects.select_related('client', 'contact_person').prefetch_related('campaigns').get(invoice_id=invoice_id)
    except Invoice.DoesNotExist:
        return Response({"error": "Invoice not found"}, status=404)

    return Response({
        "invoice_id": invoice.invoice_id,
        "client_id": invoice.client.client_id,
        "client_name": invoice.client.name,
        "invoice_month": str(invoice.invoice_month) if invoice.invoice_month else None,
        "invoice_type": invoice.invoice_type,
        "contact_person_id": invoice.contact_person.id if invoice.contact_person else None,
        "additional_discount": invoice.additional_discount,
        "gst": invoice.gst,
        "vat_tax": invoice.vat_tax,
        "campaign_ids": [c.id for c in invoice.campaigns.all()],
        "campaigns": [
            {"id": c.id, "ticket_id": c.ticket_id, "campaign_name": c.campaign_name}
            for c in invoice.campaigns.all()
        ],
        "billing_amount": invoice.billing_amount,
        "total_pay_amount": invoice.total_pay_amount(),
        "status": invoice.status,
        "pdf_generated": bool(invoice.pdf_file),
    })
    
from weasyprint import HTML as WeasyHTML
from django.core.files.base import ContentFile
from django.http import HttpResponse, Http404
from .pdf_templates import build_invoice_pdf_html


def _render_invoice_pdf(invoice):
    """Renders the invoice to PDF bytes using WeasyPrint and saves it to invoice.pdf_file."""
    html = build_invoice_pdf_html(invoice)
    pdf_bytes = WeasyHTML(string=html).write_pdf()
    invoice.pdf_file.save(f"{invoice.invoice_id}.pdf", ContentFile(pdf_bytes), save=True)
    return pdf_bytes


@api_view(['GET'])
def view_invoice_pdf(request, invoice_id):
    """Renders (or re-renders) the PDF and streams it inline for browser viewing."""
    try:
        invoice = Invoice.objects.select_related('client', 'contact_person').prefetch_related(
            'campaigns', 'line_items__line_item__campaign'
        ).get(invoice_id=invoice_id)
    except Invoice.DoesNotExist:
        raise Http404("Invoice not found")

    try:
        pdf_bytes = _render_invoice_pdf(invoice)
    except Exception as e:
        return Response({"error": f"Failed to generate invoice PDF: {e}"}, status=500)

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{invoice.invoice_id}.pdf"'
    return response


@api_view(['GET'])
def download_invoice_pdf(request, invoice_id):
    """Renders (or re-renders) the PDF and forces a download."""
    try:
        invoice = Invoice.objects.select_related('client', 'contact_person').prefetch_related(
            'campaigns', 'line_items__line_item__campaign'
        ).get(invoice_id=invoice_id)
    except Invoice.DoesNotExist:
        raise Http404("Invoice not found")

    try:
        pdf_bytes = _render_invoice_pdf(invoice)
    except Exception as e:
        return Response({"error": f"Failed to generate invoice PDF: {e}"}, status=500)

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{invoice.invoice_id}.pdf"'
    return response