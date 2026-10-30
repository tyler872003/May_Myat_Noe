from django.conf import settings
from django.db import models
from django.utils import timezone


class EmailOTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="email_otps")
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(default=timezone.now)
    attempts = models.PositiveSmallIntegerField(default=0)
    used = models.BooleanField(default=False)