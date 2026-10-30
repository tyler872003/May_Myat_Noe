from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .forms import LoginForm

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html', authentication_form=LoginForm), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path("verify-otp/resend/", views.resend_otp, name="resend_otp"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("forgot-password/verify/", views.reset_verify, name="reset_verify"),
    path("forgot-password/resend/", views.reset_resend, name="reset_resend"),
    path("forgot-password/new/", views.reset_new_password, name="reset_new_password"),
]