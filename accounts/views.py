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
from .tokens import email_token

User = get_user_model()

def send_verification_email(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_token.make_token(user)
    link = request.build_absolute_uri(
        reverse("verify_email", kwargs={"uidb64": uid, "token": token})
    )
    send_mail(
        subject="Verify your email - AI Finance",
        message=f"Hi {user.username},\n\nClick the link to verify your account:\n{link}\n\nIf you didn't sign up, ignore this email.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()
            send_verification_email(request, user)
            return render(request, "accounts/check_email.html", {"email": user.email})
    else:
        form = RegisterForm()
    return render(request, "accounts/register.html", {"form": form})

def check_verified(request):
    email = request.GET.get("email", "")
    verified = User.objects.filter(email__iexact=email, is_active=True).exists()
    return JsonResponse({"verified": verified})

def verify_email(request, uidb64, token):
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        user = None

    if user and email_token.check_token(user, token):
        user.is_active = True
        user.save()
        return render(request, "accounts/email_verified.html")   # no redirect

    return render(request, "accounts/verification_failed.html")


def resend_verification(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        user = User.objects.filter(email__iexact=email, is_active=False).first()
        if user:
            send_verification_email(request, user)
        messages.info(request, "If that account needs verification, a new email has been sent.")
        return redirect("login")
    return render(request, "accounts/resend.html")

