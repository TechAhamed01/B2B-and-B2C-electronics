from django.shortcuts import render

# Create your views here.
# apps/accounts/views.py

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from services.otp.service import OTPService
from services.exceptions import OTPSendError, OTPSendLimitExceeded
from .serializers import (
    OTPRequestSerializer, OTPVerifySerializer,
    CustomerRegistrationSerializer, DealerRegistrationSerializer,
    MobileLoginSerializer, UserSerializer
)
from .models import User


class OTPRequestView(APIView):
    permission_classes = [AllowAny]
    serializer_class = OTPRequestSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        recipient = serializer.validated_data['recipient']
        purpose = serializer.validated_data['purpose']
        channel = serializer.validated_data['channel']

        try:
            # Send OTP; user may be None for registration, but for other purposes we might need user
            # For now, we pass None; we could later pass user if authenticated and purpose is e.g., login.
            result = OTPService.send_otp(recipient, purpose, channel, user=None)
            return Response(result, status=status.HTTP_200_OK)
        except (OTPSendError, OTPSendLimitExceeded) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "Failed to send OTP"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]
    serializer_class = OTPVerifySerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        # If verification succeeded, serializer.validated_data has 'verified': True
        return Response({"message": "OTP verified successfully"}, status=status.HTTP_200_OK)


class CustomerRegistrationView(APIView):
    permission_classes = [AllowAny]
    serializer_class = CustomerRegistrationSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user_serializer = UserSerializer(user)
        return Response(user_serializer.data, status=status.HTTP_201_CREATED)


class MobileLoginView(APIView):
    permission_classes = [AllowAny]
    serializer_class = MobileLoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_200_OK)


class DealerRegistrationView(APIView):
    permission_classes = [AllowAny]
    serializer_class = DealerRegistrationSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user_serializer = UserSerializer(user)
        return Response(user_serializer.data, status=status.HTTP_201_CREATED)