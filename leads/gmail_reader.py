# # gmail_reader.py
# import base64
# from datetime import datetime, timezone
# from .gmail_service import get_gmail_service

# def list_recent_message_ids(query="newer_than:2d", max_results=100):
#     service = get_gmail_service()
#     result = service.users().messages().list(
#         userId='me', q=query, maxResults=max_results
#     ).execute()
#     messages = result.get('messages', [])
#     return [m['id'] for m in messages]  # list of message IDs

# def get_message_detail(msg_id):
#     service = get_gmail_service()
#     msg = service.users().messages().get(
#         userId='me', id=msg_id, format='full'
#     ).execute()

#     headers = msg['payload'].get('headers', [])
#     header_map = {h['name']: h['value'] for h in headers}

#     sender = header_map.get('From', '')
#     receiver = header_map.get('To', '')
#     subject = header_map.get('Subject', '(no subject)')
#     thread_id = msg.get('threadId')

#     received_at = datetime.fromtimestamp(
#         int(msg['internalDate']) / 1000, tz=timezone.utc
#     ).replace(tzinfo=None)

#     body = extract_plain_body(msg['payload'])
#     attachments = extract_attachment_parts(msg['payload'])   # NEW

#     return {
#         'message_id': msg_id,
#         'thread_id': thread_id,
#         'sender': sender,
#         'receiver': receiver,
#         'subject': subject,
#         'body': body[:1000],
#         'received_at': received_at,
#         'mail_link': f"https://mail.google.com/mail/u/0/#all/{msg_id}",
#         'attachments': attachments,   # NEW
#     }

# def extract_plain_body(payload):
#     """Recursively find the text/plain part of a message (handles multipart)."""
#     if payload.get('mimeType') == 'text/plain' and 'data' in payload.get('body', {}):
#         return decode_base64(payload['body']['data'])

#     if 'parts' in payload:
#         for part in payload['parts']:
#             if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
#                 return decode_base64(part['body']['data'])
#             if 'parts' in part:
#                 nested = extract_plain_body(part)
#                 if nested:
#                     return nested

#     return ""

# # ── NEW: attachment helpers ──────────────────────────────────────────────
# def extract_attachment_parts(payload):
#     """Recursively collect parts that represent real file attachments."""
#     attachments = []

#     def _walk(part):
#         filename = part.get('filename')
#         body = part.get('body', {})
#         if filename and body.get('attachmentId'):
#             attachments.append({
#                 'filename': filename,
#                 'mime_type': part.get('mimeType', ''),
#                 'attachment_id': body['attachmentId'],
#                 'size': body.get('size', 0),
#             })
#         for sub in part.get('parts', []):
#             _walk(sub)

#     _walk(payload)
#     return attachments


# def download_attachment(service, msg_id, attachment_id):
#     att = service.users().messages().attachments().get(
#         userId='me', messageId=msg_id, id=attachment_id
#     ).execute()
#     return base64.urlsafe_b64decode(att['data'].encode('ASCII'))
# # ──────────────────────────────────────────────────────────────────────────

# def decode_base64(data):
#     decoded_bytes = base64.urlsafe_b64decode(data.encode('ASCII'))
#     return decoded_bytes.decode('utf-8', errors='ignore')







# gmail_reader.py is responsible for reading the email data itself.

import base64
from datetime import datetime, timezone

def list_recent_message_ids(service, query="newer_than:2d", max_results=100):
    result = service.users().messages().list(
        userId='me', q=query, maxResults=max_results
    ).execute()
    messages = result.get('messages', [])
    return [m['id'] for m in messages]

def get_message_detail(service, msg_id):
    msg = service.users().messages().get(
        userId='me', id=msg_id, format='full'
    ).execute()

    headers = msg['payload'].get('headers', [])
    header_map = {h['name']: h['value'] for h in headers}

    sender = header_map.get('From', '')
    receiver = header_map.get('To', '')
    subject = header_map.get('Subject', '(no subject)')
    thread_id = msg.get('threadId')
    received_at = datetime.fromtimestamp(
    int(msg['internalDate']) / 1000, tz=timezone.utc)

    # received_at = datetime.fromtimestamp(
    #     int(msg['internalDate']) / 1000, tz=timezone.utc
    # ).replace(tzinfo=None)

    body = extract_plain_body(msg['payload'])
    attachments = extract_attachment_parts(msg['payload'])

    return {
        'message_id': msg_id,
        'thread_id': thread_id,
        'sender': sender,
        'receiver': receiver,
        'subject': subject,
        'body': body[:1000],
        'received_at': received_at,
        'mail_link': f"https://mail.google.com/mail/u/0/#all/{msg_id}",
        'attachments': attachments,
    }

def extract_plain_body(payload):
    if payload.get('mimeType') == 'text/plain' and 'data' in payload.get('body', {}):
        return decode_base64(payload['body']['data'])

    if 'parts' in payload:
        for part in payload['parts']:
            if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
                return decode_base64(part['body']['data'])
            if 'parts' in part:
                nested = extract_plain_body(part)
                if nested:
                    return nested

    return ""

def extract_attachment_parts(payload):
    attachments = []

    def _walk(part):
        filename = part.get('filename')
        body = part.get('body', {})
        if filename and body.get('attachmentId'):
            attachments.append({
                'filename': filename,
                'mime_type': part.get('mimeType', ''),
                'attachment_id': body['attachmentId'],
                'size': body.get('size', 0),
            })
        for sub in part.get('parts', []):
            _walk(sub)

    _walk(payload)
    return attachments

def download_attachment(service, msg_id, attachment_id):
    att = service.users().messages().attachments().get(
        userId='me', messageId=msg_id, id=attachment_id
    ).execute()
    return base64.urlsafe_b64decode(att['data'].encode('ASCII'))

def decode_base64(data):
    decoded_bytes = base64.urlsafe_b64decode(data.encode('ASCII'))
    return decoded_bytes.decode('utf-8', errors='ignore')

'''
gmail_reader.py — Reads and extracts Gmail data
This file communicates with the Gmail API and gets the actual email information.
gmail_reader.py is responsible for reading the email data itself.


'''