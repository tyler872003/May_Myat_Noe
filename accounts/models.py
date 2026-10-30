from django.conf import settings
from django.db import models
from django.utils import timezone


class EmailOTP(models.Model):
    PURPOSE_CHOICES = [("verify", "Email verification"), ("reset", "Password reset")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_otps")
    purpose = models.CharField(max_length=10, choices=PURPOSE_CHOICES, default="verify")
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(default=timezone.now)
    attempts = models.PositiveSmallIntegerField(default=0)
    used = models.BooleanField(default=False)