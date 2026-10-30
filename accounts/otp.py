import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.utils import timezone

from .models import EmailOTP

OTP_VALID_MINUTES = 10
MAX_ATTEMPTS = 5
RESEND_SECONDS = 60


def send_otp(user):
    # cancel any older codes
    EmailOTP.objects.filter(user=user, used=False).update(used=True)

    code = f"{secrets.randbelow(1_000_000):06d}"
    EmailOTP.objects.create(user=user, code_hash=make_password(code))

    send_mail(
        subject="Your FinanceAI verification code",
        message=(
            f"Hi {user.username},\n\n"
            f"Your verification code is: {code}\n\n"
            f"It expires in {OTP_VALID_MINUTES} minutes. "
            "If you didn't sign up, ignore this email."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def resend_wait_seconds(user):
    """0 if the user may request a new code now, otherwise seconds left."""
    last = EmailOTP.objects.filter(user=user).order_by("-created_at").first()
    if not last:
        return 0
    wait = RESEND_SECONDS - (timezone.now() - last.created_at).total_seconds()
    return max(0, int(wait))


def check_otp(user, code):
    """Returns (ok, error_message)."""
    otp = EmailOTP.objects.filter(user=user, used=False).order_by("-created_at").first()
    if not otp:
        return False, "No active code. Please request a new one."

    if timezone.now() - otp.created_at > timedelta(minutes=OTP_VALID_MINUTES):
        otp.used = True
        otp.save()
        return False, "This code has expired. Please request a new one."

    if otp.attempts >= MAX_ATTEMPTS:
        otp.used = True
        otp.save()
        return False, "Too many wrong attempts. Please request a new code."

    otp.attempts += 1
    if not check_password(code, otp.code_hash):
        otp.save()
        left = MAX_ATTEMPTS - otp.attempts
        return False, f"Incorrect code. {left} attempt(s) left."

    otp.used = True
    otp.save()
    user.is_active = True
    user.save()
    return True, ""