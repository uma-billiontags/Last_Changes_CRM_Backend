# from google_auth_oauthlib.flow import InstalledAppFlow
# import pickle

# SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# def generate_token():
#     flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
#     creds = flow.run_local_server(port=0)  # opens browser for one-time login
#     with open('token.pickle', 'wb') as token_file:
#         pickle.dump(creds, token_file)
#     print("✅ token.pickle created")

# if __name__ == '__main__':
#     generate_token()



# gmail_auth.py logs into Gmail once and saves the authorization token.
import sys
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def generate_token(account_key):
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)  # opens browser for one-time login
    token_filename = f'token_{account_key}.pickle'
    with open(token_filename, 'wb') as token_file:
        pickle.dump(creds, token_file)
    print(f"✅ {token_filename} created")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python gmail_auth.py <account_key>")
        print("Example: python gmail_auth.py uma")
        sys.exit(1)

    account_key = sys.argv[1]
    generate_token(account_key)


'''
gmail_auth.py — One-time Gmail authorization
This file is used to connect a Gmail account to your application for the first time.
When you run: python gmail_auth.py charulatha
Google opens the browser and asks you to authorize the Gmail account.
After successful authorization, it creates:
token_charulatha.pickle

'''