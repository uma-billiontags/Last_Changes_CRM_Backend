# Added by charu

import os

import firebase_admin

from firebase_admin import credentials 

from django.conf import settings

# Fire base json file path
firebase_cred_path = os.path.join(

    settings.BASE_DIR,

    "crm-notification-system-b1fbf-firebase-adminsdk-fbsvc-e2c98885a3.json"

)

cred = credentials.Certificate(

    firebase_cred_path

)

if not firebase_admin._apps:

    firebase_admin.initialize_app(

        cred

    )

print(

    "Firebase Initialized Successfully"

)