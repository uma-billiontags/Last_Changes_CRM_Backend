# Added by charu
from rest_framework.decorators import api_view
from rest_framework.response import Response
import json
from categories.models import UserCredential
from .models import FCMToken

@api_view(["POST"])
def save_fcm_token(request):
    try:
        data = json.loads(request.body)
        token = data.get("token")
        user_id = data.get("user_id")

        if not token:
            return Response({"error": "Token missing"}, status=400)
        if not user_id:
            return Response({"error": "user_id missing"}, status=400)

        try:
            user = UserCredential.objects.get(id=user_id)
        except UserCredential.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        FCMToken.objects.update_or_create(token=token, defaults={"user": user})
        return Response({"message": "Token saved successfully"}, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=500)