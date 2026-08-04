# # Added by charu
# from firebase_admin import messaging
# from .models import FCMToken

# def send_notification_to_user(user, title, body):
#     """
#     Sends a push notification to every device/browser this internal user
#     has registered an FCM token for. Auto-deletes stale/invalid tokens.
#     """
#     tokens = list(
#         FCMToken.objects.filter(user=user).values_list("token", flat=True).distinct()
#     )
#     if not tokens:
#         print(f"No FCM token found for user: {user}")
#         return

#     for token in tokens:
#         try:
#             message = messaging.Message(
#                 notification=messaging.Notification(title=title, body=body),
#                 token=token,
#             )
#             response = messaging.send(message)
#             print(f"Notification sent to {user}: {response}")
#         except Exception as e:
#             print(f"FCM Error for {user}: {e}")
#             if "NotRegistered" in str(e) or "invalid-registration-token" in str(e):
#                 FCMToken.objects.filter(token=token).delete()
#                 print(f"Deleted stale token for {user}")






# Added by charu
from firebase_admin import messaging
from .models import FCMToken

def send_notification_to_user(user, title, body):
    """
    Sends a push notification to every device/browser this internal user
    has registered an FCM token for. Auto-deletes stale/invalid tokens.
    """
    tokens = list(
        FCMToken.objects.filter(user=user).values_list("token", flat=True).distinct()
    )
    if not tokens:
        print(f"No FCM token found for user: {user}")
        return

    for token in tokens:
        try:
            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                token=token,
            )
            response = messaging.send(message)
            print(f"Notification sent to {user}: {response}")
        except messaging.UnregisteredError:
            # Token is dead (device unregistered / app uninstalled / token rotated).
            # This is the exception type Firebase actually raises for "Device unregistered."
            FCMToken.objects.filter(token=token).delete()
            print(f"Deleted stale token for {user}")
        except Exception as e:
            print(f"FCM Error for {user}: {e}")