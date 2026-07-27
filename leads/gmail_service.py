# import os
# import pickle
# from google.auth.transport.requests import Request
# from googleapiclient.discovery import build
# from django.conf import settings

# SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
# TOKEN_PATH = os.path.join(settings.BASE_DIR, 'token.pickle')
# CREDENTIALS_PATH = os.path.join(settings.BASE_DIR, 'credentials.json')

# def get_gmail_service():
#     creds = None
#     if os.path.exists(TOKEN_PATH):
#         with open(TOKEN_PATH, 'rb') as f:
#             creds = pickle.load(f)

#     # auto-refresh expired token
#     if creds and creds.expired and creds.refresh_token:
#         creds.refresh(Request())
#         with open(TOKEN_PATH, 'wb') as f:
#             pickle.dump(creds, f)

#     if not creds or not creds.valid:
#         raise Exception("No valid credentials found. Run gmail_auth.py first.")

#     return build('gmail', 'v1', credentials=creds)


# gmail_service.py decides which Gmail account to connect to and manages the saved login token.
import os
import pickle
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from django.conf import settings

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
CREDENTIALS_PATH = os.path.join(settings.BASE_DIR, 'credentials.json')

GMAIL_ACCOUNTS = {
    'charulatha': os.path.join(settings.BASE_DIR, 'token_charulatha.pickle'),
    'charulatham312': os.path.join(settings.BASE_DIR, 'token_charulatham312.pickle'),
    'uma': os.path.join(settings.BASE_DIR, 'token_uma.pickle'),
}

def get_gmail_service(account_key):
    token_path = GMAIL_ACCOUNTS.get(account_key)
    if not token_path:
        raise Exception(f"Unknown Gmail account key: {account_key}")

    creds = None
    if os.path.exists(token_path):
        with open(token_path, 'rb') as f:
            creds = pickle.load(f)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, 'wb') as f:
            pickle.dump(creds, f)

    if not creds or not creds.valid:
        raise Exception(f"No valid credentials for '{account_key}'. Run: python gmail_auth.py {account_key}")

    return build('gmail', 'v1', credentials=creds)


'''
gmail_service.py — Connects to the correct Gmail account 
This file maintains your configured Gmail accounts:

GMAIL_ACCOUNTS = {
    'charulatha': os.path.join(settings.BASE_DIR, 'token_charulatha.pickle'),
    'charulatham312': os.path.join(settings.BASE_DIR, 'token_charulatham312.pickle'),
}

gmail_service.py decides which Gmail account to connect to and manages the saved login token.
'''