# invoices/pdf_templates.py
from campaigns.io_utils import get_logo_data_uri, get_signature_data_uri


def fmt_date(d):
    if not d:
        return "—"
    return d.strftime('%d %b %Y')


def build_invoice_pdf_html(invoice):
    """
    Builds the invoice PDF HTML directly from the Invoice model —
    supports multiple campaigns (M2M, identified by ticket_id) and uses
    the invoice's own already-computed amounts (billing_amount, gst_amount,
    vat_tax_amount, additional_discount) instead of recalculating from scratch.

    CompanyDetails stores billing_currency/gst_number/cin_number/etc directly
    (no separate ClientBilling relation), so we read them straight off client.
    """
    client = invoice.client
    contact = invoice.contact_person or (client.contacts.first() if client and hasattr(client, 'contacts') else None)
    if not contact and client:
        # CompanyDetails → CompanyContacts is a plain FK (related_name defaults to companycontacts_set)
        contact = client.companycontacts_set.first() if hasattr(client, 'companycontacts_set') else None

    invoice_date = invoice.generated_at.strftime('%d %B %Y') if invoice.generated_at else __import__('datetime').date.today().strftime('%d %B %Y')
    due_date_str = fmt_date(invoice.due_date)
    period_start_str = fmt_date(invoice.invoice_from)
    period_end_str = fmt_date(invoice.invoice_to)

    currency_code = client.billing_currency if client else "INR"
    currency_map = {"INR": "₹", "AED": "د.إ", "NZD": "$", "USD": "$"}
    currency_symbol = currency_map.get(currency_code, "₹")

    payment_terms = client.payment_type if client and client.payment_type else "NET 0 Days"

    client_id_display = client.client_id if client else "—"
    contact_name = contact.name if contact else (client.name if client else "—")
    company_name = client.name if client else "—"
    address = client.address_line1 if client else "—"
    city_country = f"{client.city}, {client.country}" if client and client.city else (client.country if client else "—")
    gst_number = client.gst_number if client else "—"
    cin_number = client.cin_number if client else "—"

    # ── ticket_id, not campaign_id — this is the current project's identifier ──
    ticket_ids_str = ", ".join(c.ticket_id or "—" for c in invoice.campaigns.all()) or "—"

    booking_rows = ""
    total_volume = 0
    for i, li in enumerate(invoice.line_items.select_related('line_item', 'line_item__campaign').all()):
        bg = "#f9fafb" if i % 2 == 1 else "#fff"
        campaign = li.line_item.campaign if li.line_item else None
        campaign_name = campaign.campaign_name if campaign else "—"
        ticket_id_disp = campaign.ticket_id if campaign else "—"
        vol = f"{int(li.line_item.impressions):,}" if li.line_item and li.line_item.impressions else "0"
        total_volume += li.line_item.impressions if li.line_item and li.line_item.impressions else 0

        booking_rows += f"""
        <tr style="border-bottom:1px solid #e5e7eb;background:{bg};">
          <td style="padding:10px 12px;font-size:12px;color:#374151;vertical-align:top;line-height:1.6;">
            <div style="font-weight:600;color:#111827;margin-bottom:2px;">
              Campaign: {campaign_name} | Ticket ID: {ticket_id_disp}
            </div>
            <div style="color:#4f46e5;font-weight:500;">
              Line Item: {li.description or "—"}
            </div>
          </td>
          <td style="padding:10px 12px;font-size:12px;text-align:center;white-space:nowrap;">
            <span style="display:inline-block;padding:2px 8px;border-radius:4px;
                         background:#eef2ff;color:#4f46e5;font-weight:700;font-size:11px;">
              {li.line_item.units if li.line_item and li.line_item.units else "—"}
            </span>
          </td>
          <td style="padding:10px 12px;font-size:12px;text-align:right;white-space:nowrap;">
            {vol}
          </td>
          <td style="padding:10px 12px;font-size:12px;text-align:right;white-space:nowrap;
                     color:#dc2626;">
            {currency_symbol}{li.discount:.2f}
          </td>
          <td style="padding:10px 12px;font-size:12px;text-align:right;white-space:nowrap;
                     font-weight:700;color:#111827;">
            {currency_symbol}{li.billing_cost:.2f}
          </td>
        </tr>"""

    discount_pct = invoice.additional_discount_per()

    logo_uri = get_logo_data_uri()
    logo_html = (
        f'<img src="{logo_uri}" style="height:70px;display:block;" alt="Billiontags"/>'
        if logo_uri else
        '<div class="inv-logo-text">Billion<span>tags</span></div>'
    )

    signature_uri = get_signature_data_uri()
    signature_html = (
        f'<img src="{signature_uri}" style="max-height:50px;margin:6px 0 2px;display:block;" alt="Signature"/>'
        if signature_uri else ""
    )

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8"/>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: Arial, sans-serif; color: #111827; background: #fff; font-size: 13px; }}
    .page {{ width: 100%; padding: 16px 20px; }}
    .inv-header {{ display: flex; justify-content: space-between;
                   align-items: flex-start; margin-bottom: 32px; }}
    .inv-logo-text {{ font-size: 26px; font-weight: 900; color: #111827; letter-spacing:-1px; }}
    .inv-logo-text span {{ color: #f59e0b; }}
    .section-label {{ font-size: 11px; font-weight: 800; color: #374151;
                      text-transform: uppercase; letter-spacing: 0.08em;
                      border-bottom: 2px solid #111827; padding-bottom: 4px; margin: 20px 0 10px; }}
    .inv-top-grid {{ display: grid; grid-template-columns: 1fr 1fr;
                     gap: 24px; margin-bottom: 24px; }}
    .bill-to-label {{ font-size: 11px; font-weight: 800; color: #374151;
                      text-transform: uppercase; letter-spacing: 0.08em;
                      margin-bottom: 8px; border-bottom: 2px solid #111827; padding-bottom: 4px; }}
    .inv-detail-row {{ display: flex; justify-content: space-between;
                       padding: 4px 0; font-size: 12px; border-bottom: 1px solid #f3f4f6; }}
    .inv-detail-label {{ color: #6b7280; }}
    .inv-detail-val {{ font-weight: 600; color: #111827; }}
    .amount-due-box {{ background: #0f172a; border-radius: 10px; padding: 16px 20px;
                       margin-bottom: 20px; display: flex; justify-content: space-between;
                       align-items: center; }}
    .summary-box {{ border: 1px solid #e5e7eb; border-radius: 8px;
                    padding: 14px 16px; margin-bottom: 20px; }}
    .summary-row {{ display: flex; justify-content: space-between;
                    font-size: 12px; padding: 3px 0; }}
    .summary-row.total {{ font-weight: 800; font-size: 14px; color: #111827;
                          border-top: 1px solid #e5e7eb; margin-top: 6px; padding-top: 8px; }}
    .bank-table {{ width: 100%; font-size: 12px; border-collapse: collapse; }}
    .bank-table td {{ padding: 4px 8px; }}
    .bank-table td:first-child {{ color: #6b7280; font-weight: 600; width: 140px; }}
    .booking-table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }}
    .booking-table th {{ padding: 9px 12px; background: #111827; color: #fff; font-weight: 700;
                         font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em;
                         border: 1px solid #374151; text-align: left; }}
    .booking-table td {{ border: 1px solid #e5e7eb; word-break: break-word; }}
    .sig-box {{ border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px 24px; width: 320px; }}
    @page {{ margin: 10mm; }}
  </style>
</head>
<body>

<!-- PAGE 1 -->
<div class="page">
  <div class="inv-header">
    <div>{logo_html}</div>
    <div style="text-align:right;">
      <div style="font-size:22px;font-weight:900;color:#111827;">Tax Invoice</div>
      <div style="font-size:13px;color:#6b7280;font-family:monospace;">
        Invoice number: {invoice.invoice_id}
      </div>
    </div>
  </div>

  <div style="display:flex;justify-content:flex-end;margin-bottom:24px;">
    <div style="text-align:right;font-size:12px;color:#6b7280;line-height:1.7;">
      <div style="font-size:13px;font-weight:700;color:#111827;">
        Billiontags Enterprises - FZCO
      </div>
      IFZA Business Park, DDP,<br/>
      Building A2, Premises No: 30485 - 001,<br/>
      Dubai, United Arab Emirates, Pin code: 341041.<br/>
      TRN No: 104101902500003<br/>
      License No: 30485
    </div>
  </div>

  <div class="inv-top-grid">
    <div>
      <div class="bill-to-label">Bill To</div>
      <div class="inv-detail-row"><span class="inv-detail-label">Contact Person</span><span class="inv-detail-val">{contact_name}</span></div>
      <div class="inv-detail-row"><span class="inv-detail-label">Company Name</span><span class="inv-detail-val">{company_name}</span></div>
      <div class="inv-detail-row"><span class="inv-detail-label">Address</span><span class="inv-detail-val">{address}</span></div>
      <div class="inv-detail-row"><span class="inv-detail-label">Location</span><span class="inv-detail-val">{city_country}</span></div>
      <div class="inv-detail-row"><span class="inv-detail-label">Client ID</span><span class="inv-detail-val">{client_id_display}</span></div>
      <div class="inv-detail-row"><span class="inv-detail-label">GST No</span><span class="inv-detail-val">{gst_number}</span></div>
      <div class="inv-detail-row"><span class="inv-detail-label">CIN No</span><span class="inv-detail-val">{cin_number}</span></div>
    </div>
    <div>
      <div class="bill-to-label">Details</div>
      <div class="inv-detail-row"><span class="inv-detail-label">Invoice number</span><span class="inv-detail-val">{invoice.invoice_id}</span></div>
      <div class="inv-detail-row"><span class="inv-detail-label">Invoice date</span><span class="inv-detail-val">{invoice_date}</span></div>
      <div class="inv-detail-row"><span class="inv-detail-label">Payment terms</span><span class="inv-detail-val">{payment_terms}</span></div>
      <div class="inv-detail-row"><span class="inv-detail-label">Due date</span><span class="inv-detail-val">{due_date_str}</span></div>
      <div class="inv-detail-row"><span class="inv-detail-label">Campaigns (Ticket ID)</span><span class="inv-detail-val">{ticket_ids_str}</span></div>
    </div>
  </div>

  <div class="amount-due-box">
    <div>
      <div style="font-size:11px;color:#f59e0b;font-weight:700;letter-spacing:0.08em;">Pay in {currency_code}</div>
      <div style="font-size:12px;color:rgba(255,255,255,0.5);font-weight:600;text-transform:uppercase;letter-spacing:0.08em;">Total amount due</div>
      <div style="font-size:11px;color:rgba(255,255,255,0.4);margin-top:2px;">Due {due_date_str}</div>
    </div>
    <div style="font-size:28px;font-weight:900;color:#fff;letter-spacing:-1px;">
      {currency_symbol}{invoice.total_pay_amount():.2f}
    </div>
  </div>

  <div class="summary-box">
    <div style="font-size:11px;font-weight:800;color:#374151;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:10px;">
      Summary for {period_start_str} - {period_end_str}
    </div>
    <div class="summary-row"><span>Sub Total</span><span>{currency_symbol}{invoice.total_amount:.2f}</span></div>
    <div class="summary-row"><span>Overspend Adjustment</span><span>- {currency_symbol}{invoice.total_discount:.2f}</span></div>
    <div class="summary-row"><span>GST ({invoice.gst or 0}%)</span><span>{currency_symbol}{invoice.gst_amount:.2f}</span></div>
    <div class="summary-row"><span>VAT ({invoice.vat_tax or 0}%)</span><span>{currency_symbol}{invoice.vat_tax_amount:.2f}</span></div>
    <div class="summary-row" style="color:#dc2626;">
      <span>Offers/Discount ({discount_pct}%)</span><span>- {currency_symbol}{invoice.additional_discount:.2f}</span>
    </div>
    <div class="summary-row total">
      <span>Total amount due in {currency_code}</span>
      <span>{currency_symbol}{invoice.total_pay_amount():.2f}</span>
    </div>
  </div>

  <div class="section-label">Bank Account Details</div>
  <table class="bank-table">
    <tr><td>Name</td><td>Billiontags Enterprises FZCO</td></tr>
    <tr><td>Account Number</td><td>1000000000001</td></tr>
    <tr><td>Bank</td><td>Emirates Bank</td></tr>
    <tr><td>Swift Code</td><td>EBUAAEAD</td></tr>
    <tr><td>IBAN No</td><td>AE321021000101500019001</td></tr>
    <tr><td>Bank Address</td><td>Emirates Bank PJSC. P.O. Box: 777, Dubai, UAE</td></tr>
  </table>
</div>

<!-- PAGE 2 — Booking Details -->
<div style="page-break-before:always;"></div>
<div class="page">
  <div class="inv-header" style="margin-bottom:20px;">
    <div>{logo_html}</div>
    <div style="text-align:right;">
      <div style="font-size:22px;font-weight:900;color:#111827;">Tax Invoice</div>
      <div style="font-size:13px;color:#6b7280;font-family:monospace;">Invoice number: {invoice.invoice_id}</div>
    </div>
  </div>

  <div class="section-label">Booking Details</div>
  <table class="booking-table">
    <thead>
      <tr>
        <th style="width:46%;">Description</th>
        <th style="text-align:center;width:12%;">Unit</th>
        <th style="text-align:right;width:14%;">Volume</th>
        <th style="text-align:right;width:14%;">Discount</th>
        <th style="text-align:right;width:14%;">Amount {currency_symbol}</th>
      </tr>
    </thead>
    <tbody>
      {booking_rows or '<tr><td colspan="5" style="padding:20px;text-align:center;color:#9ca3af;">No line items</td></tr>'}
      <tr style="background:#0f172a;">
        <td colspan="4" style="padding:10px 12px;border:1px solid #374151;text-align:right;font-weight:800;color:#fff;">
          Total amount due in {currency_code}
        </td>
        <td style="padding:10px 12px;border:1px solid #374151;text-align:right;font-weight:900;font-size:15px;color:#fff;">
          {currency_symbol}{invoice.total_pay_amount():.2f}
        </td>
      </tr>
    </tbody>
  </table>

  <div style="display:flex;justify-content:flex-end;margin-top:48px;">
    <div class="sig-box">
      <div style="font-size:12px;font-weight:700;color:#374151;margin-bottom:12px;">
        Duly Authorized on behalf of Billiontags Enterprises - FZCO by:
      </div>
      <div style="font-size:13px;color:#111827;margin-bottom:8px;">Name: <strong>Praveen Kumar</strong></div>
      <div style="font-size:12px;color:#6b7280;">Designation: Director</div>
      {signature_html}
      <div style="border-bottom:1px solid #9ca3af;margin:8px 0 8px;"></div>
      <div style="font-size:11px;color:#6b7280;">Signature</div>
    </div>
  </div>
</div>

</body>
</html>"""