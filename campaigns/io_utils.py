# campaigns/io_utils.py
import json
import base64
import os
from functools import lru_cache
from weasyprint import HTML as WeasyHTML
from django.core.files.base import ContentFile
from .models import InsertionOrder, generate_io_id

LOGO_PATH = os.path.join(os.path.dirname(__file__), 'static', 'campaigns', 'billiontags_logo.webp')

# ── Billiontags' own authorized signature image — lives in the same
# static/campaigns folder as the logo. Update the filename/extension below
# if your actual file is named differently (e.g. 'signature.png'). ──
SIGNATURE_PATH = os.path.join(os.path.dirname(__file__), 'static', 'campaigns', 'Praveen_Signature.png')


@lru_cache(maxsize=1)
def get_logo_data_uri():
    """Load and cache the logo as a base64 data URI. Returns None if missing
    so the PDF still generates (falls back to text logo) instead of crashing."""
    try:
        with open(LOGO_PATH, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        return f"data:image/webp;base64,{encoded}"
    except FileNotFoundError:
        return None


@lru_cache(maxsize=1)
def get_signature_data_uri():
    """Load and cache the Billiontags authorized-signature image as a base64
    data URI. Returns None if missing so the PDF still generates (falls back
    to a blank signature line) instead of crashing."""
    try:
        with open(SIGNATURE_PATH, 'rb') as f:
            encoded = base64.b64encode(f.read()).decode('utf-8')
        return f"data:image/webp;base64,{encoded}"
    except FileNotFoundError:
        return None


def fmt_date(d):
    if not d:
        return "—"
    return d.strftime('%d-%m-%Y')


def parse_geo(geo):
    """Current project's LineItem.geo_targeting is a plain TextField, not
    guaranteed JSON — try to parse as JSON (list of dicts), fall back to
    printing the raw string if it isn't."""
    if not geo:
        return "—"
    try:
        data = json.loads(geo)
        parts = []
        for loc in (data if isinstance(data, list) else [data]):
            seg = ', '.join(filter(None, [
                loc.get('country', ''), loc.get('state', ''), loc.get('city', '')
            ]))
            if seg:
                parts.append(seg)
        return ' | '.join(parts) or "—"
    except (json.JSONDecodeError, TypeError, AttributeError):
        return str(geo)


def build_io_html(campaign, io_id):
    line_items = campaign.line_items.all()
    client = campaign.client  # CompanyDetails instance
    today = __import__('datetime').date.today().strftime('%d %B %Y')

    # ── Fields not confirmed on CompanyDetails — using getattr so this
    # doesn't hard-crash if the real field names differ. Verify these
    # against your actual CompanyDetails model and swap in real names. ──
    client_name = getattr(client, 'name', getattr(client, 'company_name', '—')) if client else "—"
    client_addr1 = getattr(client, 'address_line1', '—') if client else "—"
    client_addr2 = getattr(client, 'address_line2', '—') if client else "—"
    client_phone = getattr(client, 'phone', '—') if client else "—"
    client_email = getattr(client, 'email', '—') if client else "—"

    # advertiser/new_cpm/new_price aren't on your Campaign model — falls
    # back gracefully instead of throwing AttributeError
    advertiser = getattr(campaign, 'advertiser', None) or client_name
    new_cpm = getattr(campaign, 'new_cpm', None)
    new_price = getattr(campaign, 'new_price', None)

    line_rows = ""
    total_impressions = 0
    for i, li in enumerate(line_items):
        bg = "#fff" if i % 2 == 0 else "#f9fafb"
        impressions = li.impressions or 0
        total_impressions += impressions

        # ad_format and ethnicity are JSONFields (lists) on this project's LineItem
        ad_formats = ", ".join(li.ad_format) if isinstance(li.ad_format, list) else (li.ad_format or "—")
        ethnicity = ", ".join(li.ethnicity) if isinstance(li.ethnicity, list) else "—"

        line_rows += f"""
        <tr style="background:{bg};">
          <td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px;
                     font-family:monospace;color:#4f46e5;">
            {io_id}/<br/>{li.line_item_id or "—"}
          </td>
          <td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px;">
            <div style="font-weight:600;color:#111827;">{campaign.campaign_name}</div>
            <div style="color:#6b7280;margin-top:2px;">{li.line_item_name or "—"}</div>
          </td>
          <td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:center;">
            {ad_formats}
          </td>
          <td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:center;">
            {ethnicity}
          </td>
          <td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px;
                     text-align:center;white-space:nowrap;">
            {fmt_date(li.start_date)}
          </td>
          <td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px;
                     text-align:center;white-space:nowrap;">
            {fmt_date(li.end_date)}
          </td>
          <td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:right;">
            {f"{impressions:,}" if impressions else "—"}
          </td>
          <td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:center;">
            {li.units or "—"}
          </td>
          <td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px;text-align:right;">
            {f"${float(li.unit_value):.2f}" if li.unit_value else (li.unit_cost or "—")}
          </td>
          <td style="padding:8px 10px;border:1px solid #e5e7eb;font-size:12px;
                     text-align:right;font-weight:600;">
            {li.unit_cost or "—"}
          </td>
        </tr>"""

    first_li = line_items.first()
    geo = parse_geo(first_li.geo_targeting if first_li else None)

    cpm_row = f"<tr><td>CPM</td><td>${new_cpm}</td></tr>" if new_cpm else ""
    price_row = f"<tr><td>Price</td><td>${new_price}</td></tr>" if new_price else ""
    notes_row = f"<tr><td>Notes</td><td>{campaign.notes}</td></tr>" if campaign.notes else ""

    logo_uri = get_logo_data_uri()
    logo_html = (
        f'<img src="{logo_uri}" style="height:120px;display:block;" alt="Billiontags"/>'
        if logo_uri else
        '<div style="font-size:22px;font-weight:900;color:#111827;letter-spacing:-0.5px;">'
        'Billion<span style="color:#f59e0b;">tags</span></div>'
    )

    # ── Billiontags signature: rendered as an image if available.
    # Advertiser agency signature is intentionally left blank (signed manually). ──
    signature_uri = get_signature_data_uri()
    publisher_sig_html = (
        f'<img src="{signature_uri}" class="sig-img" alt="Signature"/>' if signature_uri else ""
    )
    client_sig_html = ""

    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8"/>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: Arial, sans-serif; color: #111827; background: #fff; }}
    .page {{ width:100%; margin: 0 auto; padding: 32px 36px; }}
    .header-bar {{ margin-bottom: 24px; }}
    .id-row {{ display: flex; justify-content: space-between; align-items: center;
               margin-top: 16px; padding-bottom: 16px; border-bottom: 3px solid #111827;
               font-size: 14px; font-weight: 700; color: #111827; }}
    .id-row span {{ font-family: monospace; }}
    .section-title {{ font-size: 11px; font-weight: 800; color: #374151;
                      text-transform: uppercase; letter-spacing: 0.08em;
                      border-bottom: 2px solid #111827; padding-bottom: 4px; margin: 20px 0 12px; }}
    .info-table {{ width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 6px; }}
    .info-table td {{ padding: 5px 8px; border: 1px solid #e5e7eb; vertical-align: top; }}
    .info-table td:first-child {{ font-weight: 600; color: #374151; background: #f9fafb;
                                   width: 140px; white-space: nowrap; }}
    .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    .booking-table {{ width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }}
    .booking-table th {{ padding: 8px 10px; background: #111827; color: #fff; font-weight: 700;
                         font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em;
                         border: 1px solid #374151; text-align: left; }}
    .booking-table th.right {{ text-align: right; }}
    .booking-table th.center {{ text-align: center; }}
    .total-row td {{ font-weight: 800; font-size: 13px; background: #f9fafb !important;
                     border-top: 2px solid #111827 !important; }}
    .sig-wrapper {{ margin-top: 24px; border: 1px solid #d1d5db; }}
    .sig-header {{ background: #e5e7eb; padding: 8px 14px; font-size: 13px;
                  font-weight: 700; color: #111827; }}
    .sig-cols {{ display: grid; grid-template-columns: 1fr 1fr; }}
    .sig-box {{ padding: 14px; }}
    .sig-box:first-child {{ border-right: 1px solid #d1d5db; }}
    .sig-box-title {{ font-size: 12px; font-weight: 700; color: #111827; margin-bottom: 8px; }}
    .sig-meta-row {{ font-size: 12px; color: #111827; margin-bottom: 6px; }}
    .sig-meta-row b {{ font-weight: 700; }}
    .sig-img {{ max-height: 50px; margin: 6px 0 2px; display: block; }}
    .sig-line {{ border-bottom: 1px solid #111827; margin-top: 30px; }}
    .tc-page {{ width: 100%; padding: 12px 20 40px; }}
    .tc-title {{ font-size: 12px; font-weight: 900; color: #111827;
                 margin-bottom: 6px; letter-spacing: -0.3px; }}
    .tc-subtitle {{ font-size: 12px; color: #374151; margin-bottom: 18px; font-style: italic; }}
    .tc-section-title {{ font-size: 12px; font-weight: 800; color: #111827;
                         margin: 18px 0 8px; text-decoration: underline; }}
    .tc-body {{ font-size: 12px; color: #374151; line-height: 1.75; }}
    .tc-body ol {{ padding-left: 20px; margin: 8px 0; }}
    .tc-body ol li {{ margin-bottom: 8px; }}
    .tc-body p {{ margin-bottom: 10px; }}
    @page {{ margin: 10mm; }}
  </style>
</head>
<body>
<div class="page">
  <div>
    {logo_html}
    <div class="id-row">
      <div>Booking IO ID : <span>{io_id}</span></div>
      <div>Ticket ID : <span>{campaign.ticket_id or "—"}</span></div>
    </div>
  </div>
  <table class="info-table">
    <tr><td>Network / Publisher</td><td>Billiontags Creations Pvt. Ltd.</td></tr>
    <tr><td>Date of IO</td><td>{today}</td></tr>
    <tr><td>Order Taken By</td><td>Praveen Kumar</td></tr>
    <tr><td>Email</td><td>praveenkumar@billiontags.com</td></tr>
    <tr><td>Address</td>
      <td>Sankaran Avenue, Shree Vatsa Towers, No:1/93, Janakpuri 2nd Street,
          2nd Floor, Above Cars 24 Velachery, Chennai, Tamil Nadu 600042.</td></tr>
  </table>

  <div class="section-title">Customer Details</div>
  <div class="two-col">
    <div>
      <div style="font-size:12px;font-weight:700;color:#374151;margin-bottom:8px;">
        Customer Contact Details
      </div>
      <table class="info-table">
        <tr><td>Agency / Advertiser</td><td>{advertiser}</td></tr>
        <tr><td>Phone</td><td>{client_phone}</td></tr>
        <tr><td>E-Mail</td><td>{client_email}</td></tr>
        <tr><td>Address Line – 1</td><td>{client_addr1}</td></tr>
        <tr><td>Address Line – 2</td><td>{client_addr2}</td></tr>
      </table>
    </div>
    <div>
      <div style="font-size:12px;font-weight:700;color:#374151;margin-bottom:8px;">
        Customer Billing Details
      </div>
      <table class="info-table">
        <tr><td>Agency / Advertiser</td><td>{advertiser}</td></tr>
        <tr><td>Phone</td><td>{client_phone}</td></tr>
        <tr><td>E-Mail</td><td>{client_email}</td></tr>
        <tr><td>Address Line – 1</td><td>{client_addr1}</td></tr>
        <tr><td>Address Line – 2</td><td>{client_addr2}</td></tr>
      </table>
    </div>
  </div>

  <div class="section-title">Order Details</div>
  <div class="two-col">
    <div>
      <table class="info-table">
        <tr><td>Advertising Client Name</td><td>{client_name}</td></tr>
        <tr><td>Campaign Name</td><td><strong>{campaign.campaign_name}</strong></td></tr>
        <tr><td>GEO</td><td>{geo}</td></tr>
        <tr><td>Client Campaign ID</td><td>{campaign.client_campaign_ID or "—"}</td></tr>
      </table>
    </div>
    <div>
      <table class="info-table">
        <tr><td>Out Clause</td><td>48 Hours</td></tr>
        <tr><td>Billing On</td><td>Billiontags Numbers</td></tr>
        <tr><td>Campaign Dates</td>
            <td>{fmt_date(campaign.start_date)} to {fmt_date(campaign.end_date)}</td></tr>
        {cpm_row}
        {price_row}
        {notes_row}
      </table>
    </div>
  </div>

  <div class="section-title">Booking Details</div>
  <table class="booking-table">
    <thead>
      <tr>
        <th style="width:110px;">IO ID &amp; Line Item ID</th>
        <th>IO Name &amp; Line Item Name</th>
        <th class="center">Ad Type</th>
        <th class="center">Ethnicity</th>
        <th class="center">Start Date</th>
        <th class="center">End Date</th>
        <th class="right">Volume</th>
        <th class="center">Unit</th>
        <th class="right">Unit Cost</th>
        <th class="right">Net Cost</th>
      </tr>
    </thead>
    <tbody>
      {line_rows or '<tr><td colspan="10" style="padding:16px;text-align:center;color:#9ca3af;">No line items</td></tr>'}
      <tr class="total-row">
        <td colspan="6" style="padding:8px 10px;border:1px solid #e5e7eb;
                                text-align:right;font-weight:800;">Total</td>
        <td style="padding:8px 10px;border:1px solid #e5e7eb;text-align:right;font-weight:800;">
          {total_impressions:,}
        </td>
        <td colspan="3" style="padding:8px 10px;border:1px solid #e5e7eb;"></td>
      </tr>
    </tbody>
  </table>

  <div class="sig-wrapper">
    <div class="sig-header">Signature</div>
    <div class="sig-cols">
      <div class="sig-box">
        <div class="sig-box-title">Duly Authorized on behalf of the Billiontags by:</div>
        <div class="sig-meta-row"><b>Name:</b> Praveen Kumar &nbsp;&nbsp; <b>Date:</b> {today}</div>
        <div class="sig-meta-row"><b>Signature</b></div>
        {publisher_sig_html}
        <div class="sig-line"></div>
      </div>
      <div class="sig-box">
        <div class="sig-box-title">Duly Authorized on behalf of the advertiser agency:</div>
        <div class="sig-meta-row"><b>Name:</b> {client_name} &nbsp;&nbsp; <b>Date:</b> {today}</div>
        <div class="sig-meta-row"><b>Signature</b></div>
        {client_sig_html}
        <div class="sig-line"></div>
      </div>
    </div>
  </div>

<div style="page-break-before:always;"></div>
<div class="tc-page">
  <div class="tc-body">
    <div class="tc-title">BILLIONTAGS Terms and Conditions for Internet Advertising</div>
    <p class="tc-subtitle">
      These BILLIONTAGS, Inc. Terms and Conditions for Internet Advertising (“Standard Terms”) are affiliating
(“BILLIONTAGS”) the Advertiser / Agency identified below (“Advertiser” or “Agency”). The parties acknowledge and agree
the Standard Terms shall be effective as of the date set forth below, and shall govern one or more separate insertion
orders (each an “IO”) executed by the parties.
    </p>
    <div class="tc-section-title">Cancellation and Termination:</div>
    <ol>
      <li>At any time prior to the serving of the first impression of the IO, Agency may cancel the IO with reports must be
updated / sent /given access on a daily basis. Cancellation 48Hours prior written notice, without penalty.</li>
      <li>Upon the serving of the first impression of the IO, Agency may cancel the IO for any reason, without penalty, by
providing BILLIONTAGS written notice of cancellation which will be effective after the later of: (i) 30 days after
serving the first impression of the IO; or (ii) 14 days after providing BILLIONTAGS with such written notice."</li>
      <li>Either party may terminate an IO if the other party is in material breach not cured
          within 10 days after written notice.</li>
        <li>Non-breaching party, except as otherwise stated in this Agreement with regard to specific breaches. Additionally, if
Agency or Advertiser commit a violation of the same Policy (as defined below), where such Policy had been
provided by BILLIONTAGS to Agency, on three separate occasions after having received timely notice of each such
breach, even if such breach has been cured by Agency or Advertiser, then BILLIONTAGS may terminate the IO
associated with such breach upon written notice. If Agency or Advertiser do not cure a violation of a Policy within
the applicable ten-day cure period after written notice, where such Policy had been provided by BILLIONTAGS to
Agency, then BILLIONTAGS may terminate the IO associated with such breach upon written notice."</li>
      <li>Short rates will apply to cancel buys to the degree stated on the IO.</li>
      <li>For Any Creative or tags that is not in accordance with IAB Standard or a non performing creative or tags were
given to BILLIONTAGS then BILLIONTAGS cannot be accounted for non-performance however BILLIONTAGS can be
given another creative tags as an alternative. There will be a minimum deployment charge for all campaigns
irrespective of the completion or not and that will not be borne by BILLIONTAGS for any failure from the Advertiser
side. Deployment cost will be prorated according to the delivery report and is a sole discretion of BILLIONTAGS
However we will ensure that the campaigns is delivered in accordance to the IO.</li>
    </ol>
    <div class="tc-section-title">Refund Policy:</div>
    <p>BILLIONTAGS do not allow Redirects, Malware, Adult Ads and Pop ups. An Advertiser can only have one offer per
campaign. If an Advertiser wish to display two different Landing Pages for the same offer, then Billiontags requires two
tracking URL within the same campaign.</p>
    <p>"You are entitled to request for a refund in the following cases:
First, if there has been an incorrect payment transaction. Second, if you have made a prepayment and you prove that
the actions forming the basis of the pricing model of your Campaign are based on a Publisher’s fraudulent activities (i.e.
the artificial increase of actions). In order to detect and prove Publishers’ fraudulent activities you undertake to send to
Billiontags a weekly detailed report of sources/websites you consider to be fraudulent. In case the Publisher’s fraudulent
activities cannot be clearly identified based on your report, Billiontags is entitled to request additional proof from you. If
you fail to submit a weekly report or additional proof regarding the Publishers’ fraudulent activities, Billiontags may
refuse to give a refund and adjust your balance accordingly. In case you are using post-payment method and you are
able to prove Publishers’ fraudulent activities pursuant to this clause, Billiontags will not invoice you for the agreed
actions based on Publisher’s fraudulent activities. Third, if at the end of the validity of the Contract it appears that you
have spent for Billiontags services less than you have prepaid. In such a case you are entitled to ask for a refund within
30 days after the termination of the Contract, provided that the amount of your unused balance is at least 50 EUR.
Before refunding, Billiontags will have to finalize all not invoiced spending and make necessary adjustments where
needed. After finalizing all current statistics, your unused balance will be refunded to you at your request, minus an
administrative fee of 25% to cover Billiontags costs and fees related with the management of giving a refund, within 30
working days. YOUR REFUND WILL BE CREDITED BACK TO THE SAME PAYMENT METHOD AND SAME PAYMENT ACCOUNT
THAT YOU USED TO MAKE YOUR LAST PAYMENT. You may be required to provide additional information or
documentation in order for Billiontags to confirm your identity, before any refund request is processed. PLEASE BE
AWARE THAT IF YOUR CONTRACT WITH Billiontags IS TERMINATED DUE TO THE VIOLATION OF CONTRACT BY YOU (E.G.
DUE TO YOUR FRAUDULENT ACTIVITY), Billiontags IS ENTITLED TO A CONTRACTUAL PENALTY IN THE AMOUNT OF YOUR
UNUSED BALANCE AND THEREFORE, Billiontags MAY REFUSE TO GIVE YOU A REFUND BY WAY OF SET-OFF OF THE
CLAIMS.”</p>
  </div>
</div>
</body>
</html>"""


# campaigns/io_utils.py (continued)

def generate_io_for_campaign(campaign):
    io_obj, _ = InsertionOrder.objects.get_or_create(
        campaign=campaign,
        defaults={"io_id": generate_io_id()},
    )
    try:
        html_string = build_io_html(campaign, io_obj.io_id)
        pdf_bytes = WeasyHTML(string=html_string).write_pdf()
        filename = f"{io_obj.io_id}_{campaign.ticket_id or campaign.id}.pdf"
        io_obj.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
    except Exception as e:
        print(f"⚠️ IO PDF generation failed for campaign {campaign.id}: {e}")
    return io_obj.io_id