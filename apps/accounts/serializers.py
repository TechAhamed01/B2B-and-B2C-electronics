# apps/accounts/serializers.py

import re
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, UserProfile, DealerRegistration, Address, OTPVerification
from services.otp.service import OTPService
from services.exceptions import (
    OTPVerificationError,
    OTPExpiredError,
    OTPAttemptsExceededError,
    OTPAlreadyUsedError,
)


class OTPRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting OTP.
    """
    recipient = serializers.CharField(max_length=100, help_text="Mobile number, email, or WhatsApp number")
    purpose = serializers.ChoiceField(choices=OTPVerification.PURPOSE_CHOICES)
    channel = serializers.ChoiceField(choices=[('sms', 'SMS'), ('whatsapp', 'WhatsApp'), ('email', 'Email')])

    def validate_recipient(self, value):
        # Basic validation based on channel could be added here, but we'll let the service handle it.
        # We can do a simple check: if channel is email, validate email format; if sms/whatsapp, validate numeric.
        # For flexibility, we skip heavy validation and rely on service.
        return value.strip()


class OTPVerifySerializer(serializers.Serializer):
    """
    Serializer for verifying OTP.
    """
    recipient = serializers.CharField(max_length=100)
    purpose = serializers.ChoiceField(choices=OTPVerification.PURPOSE_CHOICES)
    channel = serializers.ChoiceField(choices=[('sms', 'SMS'), ('whatsapp', 'WhatsApp'), ('email', 'Email')])
    otp_code = serializers.CharField(max_length=10, min_length=4)  # OTP can be 4-10 digits

    def validate(self, attrs):
        recipient = attrs['recipient']
        purpose = attrs['purpose']
        channel = attrs['channel']
        otp_code = attrs['otp_code']

        try:
            verified = OTPService.verify_otp(recipient, purpose, otp_code)
            # If we get here, verification succeeded
            attrs['verified'] = True
            return attrs
        except (OTPVerificationError, OTPExpiredError, OTPAttemptsExceededError, OTPAlreadyUsedError) as e:
            raise serializers.ValidationError({"otp_code": str(e)})
        except Exception as e:
            raise serializers.ValidationError({"otp_code": "OTP verification failed"})


class MobileLoginSerializer(serializers.Serializer):
    mobile_number = serializers.CharField(max_length=10)
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['mobile_number'], password=attrs['password'])
        if user is None or not user.is_active:
            raise serializers.ValidationError({"detail": "Invalid credentials"})
        attrs['user'] = user
        return attrs


class UserSerializer(serializers.ModelSerializer):
    """
    Base user serializer for read operations.
    """
    class Meta:
        model = User
        fields = ('id', 'mobile_number', 'email', 'full_name', 'whatsapp_number', 'alternate_mobile',
                  'is_mobile_verified', 'is_email_verified', 'is_whatsapp_verified', 'is_dealer',
                  'is_verified', 'date_joined')
        read_only_fields = fields


class CustomerRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for customer registration.
    Accepts OTP fields for verification.
    """
    otp_code = serializers.CharField(max_length=10, min_length=4, write_only=True)
    otp_recipient = serializers.CharField(max_length=100, write_only=True)
    otp_purpose = serializers.ChoiceField(choices=OTPVerification.PURPOSE_CHOICES, write_only=True)
    otp_channel = serializers.ChoiceField(choices=[('sms', 'SMS'), ('whatsapp', 'WhatsApp'), ('email', 'Email')], write_only=True)
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = (
            'mobile_number', 'email', 'full_name', 'whatsapp_number', 'alternate_mobile',
            'password', 'otp_code', 'otp_recipient', 'otp_purpose', 'otp_channel'
        )

    def validate_mobile_number(self, value):
        value = value.strip()
        if not re.fullmatch(r'^[6-9]\d{9}$', value):
            raise serializers.ValidationError("Mobile number must be a valid Indian mobile number.")
        if User.objects.filter(mobile_number=value).exists():
            raise serializers.ValidationError("A user with this mobile number already exists.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate(self, attrs):
        # Verify OTP
        try:
            verified = OTPService.verify_otp(
                attrs['otp_recipient'],
                attrs['otp_purpose'],
                attrs['otp_code']
            )
            if not verified:
                raise serializers.ValidationError({"otp_code": "Invalid OTP"})
        except (OTPVerificationError, OTPExpiredError, OTPAttemptsExceededError, OTPAlreadyUsedError) as e:
            raise serializers.ValidationError({"otp_code": str(e)})
        except Exception as e:
            raise serializers.ValidationError({"otp_code": "OTP verification failed"})

        # Ensure the recipient matches the mobile number or email
        # For registration, we expect the recipient to be either mobile or email
        recipient = attrs['otp_recipient']
        if attrs['otp_channel'] == 'sms' and recipient != attrs['mobile_number']:
            raise serializers.ValidationError({"otp_recipient": "Recipient does not match mobile number"})
        if attrs['otp_channel'] == 'email' and recipient != attrs['email']:
            raise serializers.ValidationError({"otp_recipient": "Recipient does not match email"})
        # For WhatsApp, we allow either, but we'll check if recipient matches whatsapp_number or mobile_number
        if attrs['otp_channel'] == 'whatsapp':
            if recipient != attrs['mobile_number'] and recipient != attrs.get('whatsapp_number'):
                raise serializers.ValidationError({"otp_recipient": "Recipient does not match mobile or WhatsApp number"})

        return attrs

    def create(self, validated_data):
        validated_data.pop('otp_code')
        validated_data.pop('otp_recipient')
        validated_data.pop('otp_purpose')
        otp_channel = validated_data.pop('otp_channel')

        password = validated_data.pop('password')
        user = User.objects.create_user(
            mobile_number=validated_data['mobile_number'],
            email=validated_data['email'],
            full_name=validated_data['full_name'],
            password=password,
            whatsapp_number=validated_data.get('whatsapp_number'),
            alternate_mobile=validated_data.get('alternate_mobile'),
            is_dealer=False,
        )

        if otp_channel == 'sms':
            user.is_mobile_verified = True
        elif otp_channel == 'email':
            user.is_email_verified = True
        elif otp_channel == 'whatsapp':
            user.is_whatsapp_verified = True

        user.save(update_fields=['is_mobile_verified', 'is_email_verified', 'is_whatsapp_verified'])
        return user


class DealerRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for dealer registration.
    Includes file uploads and OTP verification.
    """
    otp_code = serializers.CharField(max_length=10, min_length=4, write_only=True)
    otp_recipient = serializers.CharField(max_length=100, write_only=True)
    otp_purpose = serializers.ChoiceField(choices=OTPVerification.PURPOSE_CHOICES, write_only=True)
    otp_channel = serializers.ChoiceField(choices=[('sms', 'SMS'), ('whatsapp', 'WhatsApp'), ('email', 'Email')], write_only=True)
    password = serializers.CharField(write_only=True, validators=[validate_password])

    # Dealer-specific fields
    company_name = serializers.CharField(max_length=255)
    gstin = serializers.CharField(max_length=15, required=False, allow_blank=True, allow_null=True)
    pan = serializers.CharField(max_length=10, required=False, allow_blank=True, allow_null=True)
    msme_registration = serializers.CharField(max_length=50, required=False, allow_blank=True, allow_null=True)
    owner_name = serializers.CharField(max_length=150)
    contact_person_name = serializers.CharField(max_length=150)
    nature_of_organization = serializers.ChoiceField(choices=DealerRegistration.NATURE_CHOICES)
    gst_certificate = serializers.FileField(required=False, allow_null=True)
    owner_id_proof = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = (
            'mobile_number', 'email', 'full_name', 'whatsapp_number', 'alternate_mobile',
            'password',
            'company_name', 'gstin', 'pan', 'msme_registration', 'owner_name',
            'contact_person_name', 'nature_of_organization', 'gst_certificate', 'owner_id_proof',
            'otp_code', 'otp_recipient', 'otp_purpose', 'otp_channel'
        )

    def validate_mobile_number(self, value):
        value = value.strip()
        if not re.fullmatch(r'^[6-9]\d{9}$', value):
            raise serializers.ValidationError("Mobile number must be a valid Indian mobile number.")
        if User.objects.filter(mobile_number=value).exists():
            raise serializers.ValidationError("A user with this mobile number already exists.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_gstin(self, value):
        if value and len(value) != 15:
            raise serializers.ValidationError("GSTIN must be 15 characters.")
        # Add more validation (e.g., pattern) if needed
        if value and DealerRegistration.objects.filter(gstin=value).exists():
            raise serializers.ValidationError("This GSTIN is already registered.")
        return value

    def validate_pan(self, value):
        if value and len(value) != 10:
            raise serializers.ValidationError("PAN must be 10 characters.")
        if value and DealerRegistration.objects.filter(pan=value).exists():
            raise serializers.ValidationError("This PAN is already registered.")
        return value

    def validate(self, attrs):
        # Verify OTP
        try:
            verified = OTPService.verify_otp(
                attrs['otp_recipient'],
                attrs['otp_purpose'],
                attrs['otp_code']
            )
            if not verified:
                raise serializers.ValidationError({"otp_code": "Invalid OTP"})
        except (OTPVerificationError, OTPExpiredError, OTPAttemptsExceededError, OTPAlreadyUsedError) as e:
            raise serializers.ValidationError({"otp_code": str(e)})
        except Exception as e:
            raise serializers.ValidationError({"otp_code": "OTP verification failed"})

        # Ensure recipient matches mobile/email as before
        recipient = attrs['otp_recipient']
        if attrs['otp_channel'] == 'sms' and recipient != attrs['mobile_number']:
            raise serializers.ValidationError({"otp_recipient": "Recipient does not match mobile number"})
        if attrs['otp_channel'] == 'email' and recipient != attrs['email']:
            raise serializers.ValidationError({"otp_recipient": "Recipient does not match email"})
        if attrs['otp_channel'] == 'whatsapp':
            if recipient != attrs['mobile_number'] and recipient != attrs.get('whatsapp_number'):
                raise serializers.ValidationError({"otp_recipient": "Recipient does not match mobile or WhatsApp number"})

        return attrs

    def create(self, validated_data):
        # Extract OTP fields
        validated_data.pop('otp_code')
        validated_data.pop('otp_recipient')
        validated_data.pop('otp_purpose')
        validated_data.pop('otp_channel')

        # Extract dealer-specific fields
        dealer_fields = {
            'company_name': validated_data.pop('company_name'),
            'gstin': validated_data.pop('gstin', None),
            'pan': validated_data.pop('pan', None),
            'msme_registration': validated_data.pop('msme_registration', None),
            'owner_name': validated_data.pop('owner_name'),
            'contact_person_name': validated_data.pop('contact_person_name'),
            'nature_of_organization': validated_data.pop('nature_of_organization'),
            'gst_certificate': validated_data.pop('gst_certificate', None),
            'owner_id_proof': validated_data.pop('owner_id_proof', None),
        }

        password = validated_data.pop('password')
        # Create user with is_dealer=True
        user = User.objects.create_user(
            mobile_number=validated_data['mobile_number'],
            email=validated_data['email'],
            full_name=validated_data['full_name'],
            password=password,
            whatsapp_number=validated_data.get('whatsapp_number'),
            alternate_mobile=validated_data.get('alternate_mobile'),
            is_dealer=True,
            # Approval status is PENDING by default (via default in model)
        )

        # Create DealerRegistration
        dealer_reg = DealerRegistration.objects.create(
            user=user,
            **dealer_fields
        )

        return user
    


class LoginSerializer(serializers.Serializer):
    """
    Serializer for password-based login using mobile or email.
    """
    identifier = serializers.CharField(help_text="Mobile number or email")
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        identifier = attrs.get('identifier')
        password = attrs.get('password')
        request = self.context.get('request')

        # Authenticate using our custom backend
        user = authenticate(request, username=identifier, password=password)
        if user is None:
            raise serializers.ValidationError({"detail": "Invalid credentials"})

        # Ensure user is active
        if not user.is_active:
            raise serializers.ValidationError({"detail": "User account is inactive"})

        attrs['user'] = user
        return attrs


class OTPLoginSerializer(serializers.Serializer):
    """
    Serializer for OTP-based login.
    """
    recipient = serializers.CharField(max_length=100)
    channel = serializers.ChoiceField(choices=[('sms', 'SMS'), ('whatsapp', 'WhatsApp'), ('email', 'Email')])
    otp_code = serializers.CharField(max_length=10, min_length=4)

    def validate(self, attrs):
        recipient = attrs['recipient']
        channel = attrs['channel']
        otp_code = attrs['otp_code']

        try:
            verified = OTPService.verify_otp(recipient, 'LOGIN', otp_code)
            if not verified:
                raise serializers.ValidationError({"otp_code": "Invalid OTP"})
        except (OTPVerificationError, OTPExpiredError, OTPAttemptsExceededError, OTPAlreadyUsedError) as e:
            raise serializers.ValidationError({"otp_code": str(e)})
        except Exception:
            raise serializers.ValidationError({"otp_code": "OTP verification failed"})

        from django.db.models import Q
        try:
            if channel == 'sms':
                user = User.objects.get(mobile_number=recipient)
            elif channel == 'email':
                user = User.objects.get(email__iexact=recipient)
            elif channel == 'whatsapp':
                user = User.objects.get(Q(mobile_number=recipient) | Q(whatsapp_number=recipient))
            else:
                raise serializers.ValidationError({"detail": "Invalid channel"})
        except User.DoesNotExist:
            raise serializers.ValidationError({"detail": "No user found with this contact detail"})

        if not user.is_active:
            raise serializers.ValidationError({"detail": "User account is inactive"})

        attrs['user'] = user
        return attrs


def get_tokens_for_user(user):
    """
    Generate access and refresh tokens for a user.
    """
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }