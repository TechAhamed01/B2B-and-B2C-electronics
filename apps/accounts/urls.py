# apps/accounts/urls.py

from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    OTPRequestView, OTPVerifyView,
    CustomerRegistrationView, DealerRegistrationView, MobileLoginView,
    LoginView, OTPLoginView, TestProtectedView
)

urlpatterns = [
    path('auth/otp/request/', OTPRequestView.as_view(), name='otp-request'),
    path('auth/otp/verify/', OTPVerifyView.as_view(), name='otp-verify'),
    path('auth/register/customer/', CustomerRegistrationView.as_view(), name='customer-register'),
    path('auth/register/dealer/', DealerRegistrationView.as_view(), name='dealer-register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/login/otp/', OTPLoginView.as_view(), name='otp-login'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('test-protected/', TestProtectedView.as_view(), name='test-protected'),
]