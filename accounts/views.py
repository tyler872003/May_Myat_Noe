from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from transactions.utils import ensure_default_categories   
from django.http import JsonResponse
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from .forms import RegisterForm

User = get_user_model()

import time

from django.contrib.auth.forms import SetPasswordForm
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from .otp import RESEND_SECONDS, check_otp, resend_wait_seconds, send_otp

def mask_email(email):
    name, _, domain = email.partition("@")
    return f"{name[:2]}***@{domain}"


def welcome(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "accounts/welcome.html")


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            send_otp(user)
            request.session["pending_user_id"] = user.pk
            return redirect("verify_otp")
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})


def verify_otp(request):
    user_id = request.session.get("pending_user_id")
    user = User.objects.filter(pk=user_id, is_active=False).first() if user_id else None
    if not user:
        return redirect("login")

    error = ""
    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        ok, error = check_otp(user, code)
        if ok:
            request.session.pop("pending_user_id", None)
            messages.success(request, "Email verified! You can now log in.")
            return redirect("login")

    return render(request, "accounts/verify_otp.html", {
        "email": mask_email(user.email),
        "error": error,
        "wait": resend_wait_seconds(user),
    })


def resend_otp(request):
    if request.method != "POST":
        return redirect("verify_otp")
    user_id = request.session.get("pending_user_id")
    user = User.objects.filter(pk=user_id, is_active=False).first() if user_id else None
    if not user:
        return redirect("login")

    wait = resend_wait_seconds(user)
    if wait:
        messages.error(request, f"Please wait {wait} seconds before requesting a new code.")
    else:
        send_otp(user)
        messages.info(request, "A new code has been sent.")
    return redirect("verify_otp")

RESET_WINDOW_SECONDS = 600  # time allowed to choose a new password after the code


def get_reset_user(request):
    email = request.session.get("reset_email")
    if not email:
        return None
    return User.objects.filter(email__iexact=email, is_active=True).first()


def reset_wait_seconds(request):
    sent = request.session.get("reset_sent_at")
    if not sent:
        return 0
    return max(0, int(RESEND_SECONDS - (time.time() - sent)))


def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Please enter a valid email address.")
            return render(request, "accounts/forgot_password.html")

        request.session["reset_email"] = email
        request.session.pop("reset_user_id", None)

        user = get_reset_user(request)
        if user and resend_wait_seconds(user, "reset") == 0:
            send_otp(user, "reset")
        request.session["reset_sent_at"] = time.time()
        return redirect("reset_verify")   # same result whether or not the email exists

    return render(request, "accounts/forgot_password.html")


def reset_verify(request):
    email = request.session.get("reset_email")
    if not email:
        return redirect("forgot_password")

    error = ""
    if request.method == "POST":
        code = request.POST.get("code", "").strip()
        user = get_reset_user(request)
        if user:
            ok, error = check_otp(user, code, "reset")
        else:
            ok, error = False, "Incorrect code. Please try again."

        if ok:
            request.session["reset_user_id"] = user.pk
            request.session["reset_verified_at"] = time.time()
            request.session.pop("reset_email", None)
            return redirect("reset_new_password")

    return render(request, "accounts/reset_verify.html", {
        "email": mask_email(email),
        "error": error,
        "wait": reset_wait_seconds(request),
    })


def reset_resend(request):
    if request.method != "POST":
        return redirect("reset_verify")
    if not request.session.get("reset_email"):
        return redirect("forgot_password")

    wait = reset_wait_seconds(request)
    if wait:
        messages.error(request, f"Please wait {wait} seconds before requesting a new code.")
    else:
        user = get_reset_user(request)
        if user and resend_wait_seconds(user, "reset") == 0:
            send_otp(user, "reset")
        request.session["reset_sent_at"] = time.time()
        messages.info(request, "If that email belongs to a verified account, a new code has been sent.")
    return redirect("reset_verify")


def reset_new_password(request):
    user_id = request.session.get("reset_user_id")
    verified_at = request.session.get("reset_verified_at", 0)
    user = User.objects.filter(pk=user_id, is_active=True).first() if user_id else None

    if not user or time.time() - verified_at > RESET_WINDOW_SECONDS:
        messages.error(request, "Your reset session expired. Please start again.")
        return redirect("forgot_password")

    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            for key in ("reset_user_id", "reset_verified_at", "reset_email", "reset_sent_at"):
                request.session.pop(key, None)
            messages.success(request, "Password changed. You can now log in.")
            return redirect("login")
    else:
        form = SetPasswordForm(user)

    return render(request, "accounts/reset_new_password.html", {"form": form})