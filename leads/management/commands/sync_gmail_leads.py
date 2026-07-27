# from datetime import date, timedelta
# from django.core.management.base import BaseCommand
# from leads.models import Lead, LeadAttachment, generate_ticket_id
# from leads.gmail_reader import list_recent_message_ids, get_message_detail, download_attachment
# from leads.lead_rules import is_excluded_sender, classify_email, extract_email_address, find_matching_client
# from django.core.files.base import ContentFile
# from leads.gmail_service import get_gmail_service


# class Command(BaseCommand):
#     help = "Sync recent Gmail messages into the Lead table"

#     def handle(self, *args, **options):

#         service = get_gmail_service()

#         yesterday_str = (date.today() - timedelta(days=1)).strftime('%Y/%m/%d')
#         query = f"after:{yesterday_str}"

#         msg_ids = list_recent_message_ids(query=query, max_results=100)

#         if not msg_ids:
#             self.stdout.write("No messages found in window.")
#             return

#         existing_ids = set(
#             Lead.objects.filter(message_id__in=msg_ids).values_list('message_id', flat=True)
#         )
#         new_ids = [m for m in msg_ids if m not in existing_ids]

#         if not new_ids:
#             self.stdout.write("No new messages.")
#             return

#         details = [get_message_detail(mid) for mid in new_ids]
#         details.sort(key=lambda d: d['received_at'])

#         saved_count = 0
#         excluded_count = 0
#         linked_count = 0

#         for d in details:
#             if is_excluded_sender(d['sender']):
#                 excluded_count += 1
#                 continue

#             category_status, category_name = classify_email(d['subject'], d['body'])

#             # ── NEW: ticket_id + client link, only for categorized leads ──
#             ticket_id = None
#             client = None
#             if category_status == 'category':
#                 ticket_id = generate_ticket_id()
#                 sender_email = extract_email_address(d['sender'])
#                 client = find_matching_client(sender_email)
#                 if client:
#                     linked_count += 1

#             try:
#                 lead = Lead.objects.create(
#                     sender=d['sender'], receiver=d['receiver'], subject=d['subject'],
#                     body=d['body'], thread_id=d['thread_id'], message_id=d['message_id'],
#                     mail_link=d['mail_link'], received_at=d['received_at'],
#                     category_status=category_status, category_name=category_name,
#                     ticket_id=ticket_id, client=client,   # ← NEW
#                 )
#                 saved_count += 1

#                 for att in d.get('attachments', []):
#                     try:
#                         data = download_attachment(service, d['message_id'], att['attachment_id'])
#                         LeadAttachment.objects.create(
#                             lead=lead,
#                             filename=att['filename'],
#                             mime_type=att['mime_type'],
#                             size=att['size'],
#                             file=ContentFile(data, name=att['filename']),
#                         )
#                     except Exception as e:
#                         self.stderr.write(f"Attachment failed for {d['message_id']}: {e}")

#             except Exception as e:
#                 self.stderr.write(f"Failed to save {d['message_id']}: {e}")

#         self.stdout.write(self.style.SUCCESS(
#             f" Saved {saved_count} lead(s). Excluded {excluded_count} sender(s). "
#             f"Linked {linked_count} to existing client(s)."
#         ))




# =================================================================================

# Django custom management command that reads recent emails from multiple Gmail accounts and saves them as Lead records in your database.

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from leads.models import Lead, LeadAttachment, generate_ticket_id
from leads.gmail_reader import list_recent_message_ids, get_message_detail, download_attachment
from leads.lead_rules import is_excluded_sender, classify_email, extract_email_address, find_matching_client
from django.core.files.base import ContentFile
from leads.gmail_service import get_gmail_service, GMAIL_ACCOUNTS


class Command(BaseCommand):
    help = "Sync Gmail messages (last 2 days) into the Lead table, across all configured accounts"

    def handle(self, *args, **options):
        # ── Pull emails from the last 2 days (today - 2) ──
        # two_days_ago_str = (date.today() - timedelta(days=2)).strftime('%Y/%m/%d')
        # query = f"after:{two_days_ago_str}"
        # ── Pull emails from the previous 2 complete days, excluding today ──
        today = date.today()
        two_days_ago = today - timedelta(days=2)

        query = (
            f"after:{(two_days_ago - timedelta(days=1)).strftime('%Y/%m/%d')} "
            f"before:{today.strftime('%Y/%m/%d')}"
        )

        total_saved = 0
        total_excluded = 0
        total_linked = 0

        for account_key in GMAIL_ACCOUNTS.keys():
            self.stdout.write(f"\n--- Syncing account: {account_key} ---")

            try:
                service = get_gmail_service(account_key)
            except Exception as e:
                self.stderr.write(f"Skipping '{account_key}': {e}")
                continue

            # ── max_results increased from 100 -> 200 to handle higher volume ──
            msg_ids = list_recent_message_ids(service, query=query, max_results=200)
            if not msg_ids:
                self.stdout.write("No messages found in window.")
                continue

            existing_ids = set(
                Lead.objects.filter(message_id__in=msg_ids).values_list('message_id', flat=True)
            )
            new_ids = [m for m in msg_ids if m not in existing_ids]

            if not new_ids:
                self.stdout.write("No new messages.")
                continue

            details = [get_message_detail(service, mid) for mid in new_ids]
            details.sort(key=lambda d: d['received_at'])

            saved_count = 0
            excluded_count = 0
            linked_count = 0

            for d in details:
                if is_excluded_sender(d['sender']):
                    excluded_count += 1
                    continue

                category_status, category_name = classify_email(d['subject'], d['body'])

                ticket_id = None
                client = None
                if category_status == 'category':
                    ticket_id = generate_ticket_id()
                    sender_email = extract_email_address(d['sender'])
                    client = find_matching_client(sender_email)
                    if client:
                        linked_count += 1
                try:
                    lead = Lead.objects.create(
                        sender=d['sender'], receiver=d['receiver'], subject=d['subject'],
                        body=d['body'], thread_id=d['thread_id'], message_id=d['message_id'],
                        mail_link=d['mail_link'], received_at=d['received_at'],
                        category_status=category_status, category_name=category_name,
                        ticket_id=ticket_id, client=client,
                        source_account=account_key,
                    )
                    saved_count += 1

                    for att in d.get('attachments', []):
                        try:
                            data = download_attachment(service, d['message_id'], att['attachment_id'])
                            LeadAttachment.objects.create(
                                lead=lead, 
                                filename=att['filename'],
                                mime_type=att['mime_type'],
                                size=att['size'],
                                file=ContentFile(data, name=att['filename']),
                            )
                        except Exception as e:
                            self.stderr.write(f"Attachment failed for {d['message_id']}: {e}")

                except Exception as e:
                    self.stderr.write(f"Failed to save {d['message_id']}: {e}")

            self.stdout.write(self.style.SUCCESS(
                f"[{account_key}] Saved {saved_count}, excluded {excluded_count}, linked {linked_count}."
            ))
            total_saved += saved_count
            total_excluded += excluded_count
            total_linked += linked_count

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ TOTAL: Saved {total_saved} lead(s). Excluded {total_excluded} sender(s). "
            f"Linked {total_linked} to existing client(s)."
        ))


'''
sync_gmail_leads.py — Main synchronization process
This is the main file that connects everything together.
It performs this process:

1. Calculate date range
2. Connect to charulatha Gmail
3. Read emails
4. Check existing emails
5. Get full email details
6. Exclude unwanted senders
7. Categorize emails
8. Generate ticket IDs
9. Find matching clients
10. Save Lead
11. Download attachments
12. Save attachments
13. Repeat for charulatham312


'''