from django.db import models

# Create your models here.
# Added by charu
from django.db import models
from categories.models import UserCredential

class FCMToken(models.Model):
    user = models.ForeignKey(
        UserCredential, on_delete=models.CASCADE, null=True, blank=True
    )
    token = models.CharField(max_length=500, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} — {self.token[:20]}..."