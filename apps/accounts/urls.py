# apps/accounts/urls.py

from django.urls import path
from .views import (
    OTPRequestView, OTPVerifyView,
    CustomerRegistrationView, DealerRegistrationView, MobileLoginView
)

urlpatterns = [
    path('auth/otp/request/', OTPRequestView.as_view(), name='otp-request'),
    path('auth/otp/verify/', OTPVerifyView.as_view(), name='otp-verify'),
    path('auth/register/customer/', CustomerRegistrationView.as_view(), name='customer-register'),
    path('auth/register/dealer/', DealerRegistrationView.as_view(), name='dealer-register'),
]