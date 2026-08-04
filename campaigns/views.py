from django.http import FileResponse
from django.shortcuts import get_object_or_404
import mimetypes
from rest_framework.response import Response
from rest_framework.decorators import api_view, parser_classes
from .serializers import CampaignSerializer
from django.http import HttpResponse
from datetime import datetime
import json
from django.db import transaction  # imports Django transaction management system.
from django.db.models import Prefetch
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import LineItem, Creative, ThirdPartyCreative, Campaign, generate_line_item_id
from company_details.models import CompanyDetails   # ← add this import
from django.http import JsonResponse
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

# Added by charu
import re
from .models import LineItem, Creative, ThirdPartyCreative, Campaign, generate_line_item_id


# Creates a custom function to convert frontend date string into Python date.
def parse_date(date_str):

    if not date_str:
        return None
    return datetime.fromisoformat(date_str.replace("Z", "")).date()

from tasks.views import auto_assign_campaign_tasks   # ← ADD THIS IMPORT
from .io_utils import generate_io_for_campaign   # ← ADD

@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])  # it allows file upload, formdata. (without this file uploads won't work)
def create_campaign(request):

    client_id = request.data.get(
        "client"
    )  
    if not client_id:
        return Response(
            {"error": "client is required"}, status=400
        )  # if frontend not send throw this error

    client = get_object_or_404(CompanyDetails, client_id=client_id)   # ← added: resolve the actual object

     # =====================================================
    # VALIDATE CAMPAIGN
    # =====================================================

    serializer = CampaignSerializer(
        data=request.data
    )  # Take all data coming from frontend request and give it to serializer.
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)

    try:
        with transaction.atomic():  # save together
            campaign = serializer.save(
                client=client,
                ticket_id=request.data.get("ticket_id") or None
            )  
            if campaign.ticket_id:                          # ← ADD THIS
                auto_assign_campaign_tasks(campaign.ticket_id)   # ← ADD THIS
                
            generate_io_for_campaign(campaign)   # ← ADD — no ticket_id guard needed,
                                                  # every campaign gets an IO regardless
                                                  
            try:
                line_items_data = json.loads(
                    request.data.get("line_items", "[]")
                )  # get the line items from frontend and converts json into python dict
            except Exception:
                return Response({"error": "Invalid line_items JSON"}, status=400)

            # =============================================
            # LOOP LINE ITEMS
            # =============================================
            for i, li in enumerate(
                line_items_data
            ):  # Loop through every line item one by one. (eg: i=0, li=first line item)


                # Added by me
                raw_line_item_id = li.get("line_item_id")
                if not raw_line_item_id:
                    continue

                # Ignore whatever number the frontend guessed — recompute the real
                # next number server-side, inside this transaction, so it's always correct.
                match = re.match(r'^(.*?)(\d+)$', raw_line_item_id)
                prefix = match.group(1) if match else raw_line_item_id
                line_item_id = generate_line_item_id(prefix)


            
                # Added by me
                line_item = LineItem.objects.create(
                    campaign=campaign,
                    line_item_id=line_item_id,
                    line_item_name=li.get("line_item_name"),
                    ethnicity=li.get("ethnicity", []),
                    start_date=parse_date(li.get("start_date")),
                    end_date=parse_date(li.get("end_date")),
                    ad_format=li.get("ad_format", []),
                    impressions=li.get("impressions") or None,
                    units=li.get("units") or None,
                    ctr=li.get("ctr") or None,
                    viewability=li.get("viewability") or None,
                    vcr=li.get("vcr") or None,
                    unit_cost=li.get("unit_cost") or None,
                    kpi_notes=li.get("kpi_notes", ""),
                    unit_value=li.get("unit_value") or None,
                    age=li.get("age", ""),
                    gender=li.get("gender", ""),
                    geo_targeting=li.get("geo_targeting", ""),
                )

            

                # Fix — two separate loops

                # Loop 1: normal creatives
                creatives_meta = li.get("creatives", [])
                for j, meta in enumerate(creatives_meta):
                    if not meta.get("creative_name"):
                        continue

                    main_asset = request.FILES.get(f"line_item_{i}main_asset{j}")
                    Creative.objects.create(
                        line_item=line_item,
                        creative_name=meta.get("creative_name", ""),
                        main_asset=main_asset,
                        dimensions=meta.get("dimensions", ""),
                        aspect_ratio=meta.get("aspect_ratio", ""),
                        file_size=meta.get("file_size", ""),
                        click_through_url=meta.get("click_through_url") or None,
                        appended_html_tag=meta.get("appended_html_tag", ""),
                        integration_code=meta.get("integration_code", ""),
                        notes=meta.get("notes", ""),
                    )

                # Loop 2: third-party creatives — completely separate
                third_party_meta = li.get("third_party_creatives", [])
                for k, _ in enumerate(third_party_meta):
                    input_file = request.FILES.get(f"line_item_{i}thirdparty_file{k}")
                    backup_image = request.FILES.get(
                        f"line_item_{i}thirdparty_backup{k}"
                    )
                    ThirdPartyCreative.objects.create(
                        line_item=line_item,
                        input_file=input_file,
                        backup_image=backup_image,
                    )

    except Exception as e:
        return Response({"error": str(e)}, status=500)

    # =============================================
    # SEND FIREBASE PUSH NOTIFICATION
    # =============================================

    return Response(
        {
            "message": "Campaign + LineItem + Creative + ThirdPartyCreative saved successfully",
            "campaign_id": campaign.id,   # ← fixed, was campaign.campaign_id
        },
        status=201,
    )


# ===========================
# GET ALL CAMPAIGNS
# ==========================


@api_view(["GET"])
def get_campaigns(request):

    campaigns = Campaign.objects.select_related("client").prefetch_related(
        "line_items__creatives_detail", "line_items__third_party_creatives"
    )
    serializer = CampaignSerializer(campaigns, many=True)
    return Response(serializer.data)

@api_view(["GET"])
def download_creative(request, creative_id):

    # Get creative object
    creative = get_object_or_404(Creative, id=creative_id)

    # Get uploaded file path
    file_path = creative.main_asset.path

    mime_type, _ = mimetypes.guess_type(file_path)
    mime_type = mime_type or "application/octet-stream"

    # Return downloadable response
    return FileResponse(
        open(file_path, "rb"), as_attachment=True, content_type=mime_type
    )


# Third party function
@api_view(["GET"])
def download_thirdparty(request, thirdparty_id):

    # Get third-party creative object
    thirdparty = get_object_or_404(ThirdPartyCreative, id=thirdparty_id)

    if not thirdparty.input_file:
        return Response({"error": "No input file uploaded"}, status=404)

    # Get uploaded file path
    file_path = thirdparty.input_file.path

    # Return downloadable response
    return FileResponse(
        open(file_path, "rb"), as_attachment=True, filename=thirdparty.input_file.name
    )


# Backup image function
@api_view(["GET"])
def download_backup_image(request, thirdparty_id):

    thirdparty = get_object_or_404(ThirdPartyCreative, id=thirdparty_id)

    if not thirdparty.backup_image:
        return Response({"error": "No input file uploaded"}, status=404)
    file_path = thirdparty.backup_image.path
    return FileResponse(
        open(file_path, "rb"), as_attachment=True, filename=thirdparty.backup_image.name
    )

# ------------------------IO Function-------------------------------------

from django.http import FileResponse
from .models import InsertionOrder

@api_view(["GET"])
def get_io_list(request):
    campaigns = Campaign.objects.select_related("client", "insertion_order").prefetch_related("line_items")
    data = []
    for c in campaigns:
        io = getattr(c, "insertion_order", None)
        data.append({
            "ticket_id": c.ticket_id,              # ← replaces campaign_id in the response
            "campaign_name": c.campaign_name,
            "client_name": str(c.client) if c.client else "",
            "start_date": str(c.start_date) if c.start_date else "",
            "end_date": str(c.end_date) if c.end_date else "",
            "campaign_type": c.campaign_type or "",
            "line_items_count": c.line_items.count(),
            "io_id": io.io_id if io else None,
            "pdf_generated": bool(io and io.pdf_file),
            "created_at": c.created_at.isoformat() if c.created_at else "",
        })
    return Response(data)


@api_view(["GET"])
def download_io_pdf(request, ticket_id):
    try:
        io_obj = InsertionOrder.objects.get(campaign__ticket_id=ticket_id)
    except InsertionOrder.DoesNotExist:
        return Response({"error": "IO not found"}, status=404)
    if not io_obj.pdf_file:
        return Response({"error": "PDF not generated yet"}, status=404)
    response = FileResponse(io_obj.pdf_file.open("rb"), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{io_obj.io_id}.pdf"'
    return response

@api_view(["POST"])
def generate_io_pdf(request, ticket_id):
    try:
        campaign = Campaign.objects.get(ticket_id=ticket_id)
    except Campaign.DoesNotExist:
        return Response({"error": "Campaign not found"}, status=404)
    io_id = generate_io_for_campaign(campaign)
    return Response({"message": "IO PDF generated", "io_id": io_id}, status=200)

# ------------------------Send Email-------------------------------------

# campaigns/views.py (or wherever your IO views live)

def io_send_email_preview(request, ticket_id):
    campaign = get_object_or_404(Campaign, ticket_id=ticket_id)
    io_obj = getattr(campaign, "insertion_order", None)  # or however IO relates
    if not io_obj:
        return JsonResponse({"status": False, "message": "No Insertion Order found for this campaign."})
    client = campaign.client  # CompanyDetails

    to_emails = [e.strip() for e in (client.default_email_send_to or "").split(",") if e.strip()]
    cc_emails = [e.strip() for e in (client.default_email_send_cc or "").split(",") if e.strip()]

    if not to_emails:
        return JsonResponse({
            "status": False,
            "message": f"No 'Default Email To' configured for {client.name}.",
            "needs_email_setup": True,
            "company_id": client.id,
        })

    subject = f"Insertion Order {io_obj.io_id} - {campaign.campaign_name}"

    return JsonResponse({
        "status": True,
        "io_id": io_obj.io_id,
        "ticket_id": ticket_id,
        "campaign_name": campaign.campaign_name,
        "client_name": client.name,
        "subject": subject,
        "to": to_emails,
        "cc": cc_emails,
        "attachments": [f"{io_obj.io_id}_{ticket_id}.pdf"],
    })


from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def io_send_email(request, ticket_id):
    if request.method != "POST":
        return JsonResponse({"status": False, "message": "Invalid request method."})

    campaign = get_object_or_404(Campaign, ticket_id=ticket_id)
    io_obj = getattr(campaign, "insertion_order", None)
    if not io_obj:
        return JsonResponse({"status": False, "message": "No Insertion Order found for this campaign."})
    client = campaign.client

    to_emails = [e.strip() for e in (client.default_email_send_to or "").split(",") if e.strip()]
    cc_emails = [e.strip() for e in (client.default_email_send_cc or "").split(",") if e.strip()]
    if not to_emails:
        return JsonResponse({"status": False, "message": "No 'Default Email To' configured."})

    subject = request.POST.get("subject") or f"Insertion Order {io_obj.io_id}"
    body_html = request.POST.get("email_body") or f"Please find attached the Insertion Order {io_obj.io_id}."

    email = EmailMultiAlternatives(
        subject=subject, body="", from_email=settings.DEFAULT_FROM_EMAIL,
        to=to_emails, cc=cc_emails if cc_emails else None,
    )
    email.attach_alternative(body_html, "text/html")

    try:
        if not io_obj.pdf_file:
            return JsonResponse({"status": False, "message": "IO PDF not yet generated."})
        email.attach(
            f"{io_obj.io_id}_{ticket_id}.pdf",
            io_obj.pdf_file.read(),
            "application/pdf",
        )
        email.send(fail_silently=False)
    except Exception as e:
        return JsonResponse({"status": False, "message": f"Failed to send email: {e}"})

    return JsonResponse({"status": True, "message": f"Email sent to {', '.join(to_emails)}"})
