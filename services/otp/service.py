# services/otp/service.py

import secrets
import logging
from datetime import timedelta

from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.db import transaction

from apps.accounts.models import OTPVerification, User
from .base import OTPProvider
from .sms import SMSProvider
from .whatsapp import WhatsAppProvider
from .email import EmailProvider
from ..exceptions import (
    OTPGenerationError,
    OTPSendError,
    OTPVerificationError,
    OTPExpiredError,
    OTPAttemptsExceededError,
    OTPAlreadyUsedError,
    OTPSendLimitExceeded,
)

logger = logging.getLogger(__name__)


class OTPService:
    """
    Coordinates OTP generation, storage, sending, and verification.
    """

    # Configuration – can be overridden in settings
    OTP_LENGTH = getattr(settings, 'OTP_LENGTH', 6)
    OTP_EXPIRY_MINUTES = getattr(settings, 'OTP_EXPIRY_MINUTES', 5)
    MAX_ATTEMPTS = getattr(settings, 'OTP_MAX_ATTEMPTS', 5)
    RATE_LIMIT_PER_MINUTE = getattr(settings, 'OTP_RATE_LIMIT', 3)
    RATE_LIMIT_WINDOW = 60  # seconds

    # Provider mapping: classes, not instances
    _provider_classes = {
        'sms': SMSProvider,
        'whatsapp': WhatsAppProvider,
        'email': EmailProvider,
    }

    @classmethod
    def get_provider(cls, channel: str) -> OTPProvider:
        """Instantiate and return the provider for the given channel."""
        provider_class = cls._provider_classes.get(channel)
        if not provider_class:
            raise ValueError(f"Unsupported OTP channel: {channel}")
        return provider_class()  # instantiate

    @classmethod
    def _check_rate_limit(cls, recipient: str, purpose: str, channel: str) -> None:
        """
        Check if the recipient has exceeded the OTP request rate limit.
        Uses atomic increment with cache.incr().
        Raises OTPSendLimitExceeded if limit is reached.
        """
        cache_key = f"otp_rate_limit:{purpose}:{channel}:{recipient}"
        try:
            current_count = cache.incr(cache_key)
        except ValueError:
            cache.set(cache_key, 1, cls.RATE_LIMIT_WINDOW)
            current_count = 1

        if current_count > cls.RATE_LIMIT_PER_MINUTE:
            raise OTPSendLimitExceeded(
                "Too many OTP requests. Please wait a moment."
            )

    @classmethod
    def generate_otp(cls) -> str:
        """Generate a cryptographically secure numeric OTP."""
        return ''.join(secrets.choice('0123456789') for _ in range(cls.OTP_LENGTH))

    @classmethod
    def _invalidate_previous_otps(cls, recipient: str, purpose: str, channel: str) -> None:
        """
        Mark any existing, unused OTPs for this recipient and purpose as used.
        This prevents multiple active OTPs for the same purpose.
        """
        filter_kwargs = {
            'purpose': purpose,
            'is_used': False,
        }
        if channel == 'sms':
            filter_kwargs['mobile_number'] = recipient
        elif channel == 'whatsapp':
            filter_kwargs['whatsapp_number'] = recipient
        elif channel == 'email':
            filter_kwargs['email'] = recipient
        else:
            raise ValueError(f"Unsupported channel: {channel}")

        OTPVerification.objects.filter(**filter_kwargs).update(is_used=True)

    @classmethod
    def _create_otp_record(cls, user: User, recipient: str, purpose: str, channel: str) -> tuple[OTPVerification, str]:
        """
        Create an OTPVerification instance with hashed OTP and expiry.
        Returns (otp_obj, raw_otp).
        """
        raw_otp = cls.generate_otp()
        expires_at = timezone.now() + timedelta(minutes=cls.OTP_EXPIRY_MINUTES)

        data = {
            'user': user if user and user.pk else None,
            'purpose': purpose,
            'expires_at': expires_at,
        }
        if channel == 'sms':
            data['mobile_number'] = recipient
        elif channel == 'whatsapp':
            data['whatsapp_number'] = recipient
        elif channel == 'email':
            data['email'] = recipient
        else:
            raise ValueError(f"Unsupported channel: {channel}")

        otp_obj = OTPVerification(**data)
        otp_obj.set_otp_code(raw_otp)
        otp_obj.save()
        return otp_obj, raw_otp

    @classmethod
    def send_otp(cls, recipient: str, purpose: str, channel: str, user: User = None) -> dict:
        """
        High-level method to generate, store, and send an OTP.
        Returns a generic success message (no recipient details, no expires_at).
        Raises OTPGenerationError, OTPSendError, or OTPSendLimitExceeded.
        """
        cls._check_rate_limit(recipient, purpose, channel)

        try:
            with transaction.atomic():
                cls._invalidate_previous_otps(recipient, purpose, channel)
                otp_obj, raw_otp = cls._create_otp_record(user, recipient, purpose, channel)
        except Exception as e:
            logger.error(f"Failed to create OTP record: {e}")
            raise OTPGenerationError("Failed to generate OTP")

        try:
            provider = cls.get_provider(channel)
            success = provider.send_otp(recipient, raw_otp, purpose)
            if not success:
                otp_obj.delete()
                raise OTPSendError("Provider failed to send OTP")
        except Exception as e:
            otp_obj.delete()
            logger.error(f"OTP send failed: {e}")
            raise OTPSendError("Failed to send OTP")

        return {
            "message": "OTP sent successfully",
        }

    @classmethod
    def verify_otp(cls, recipient: str, purpose: str, channel: str, raw_otp: str) -> bool:
        """
        Verify an OTP by recipient, purpose, channel, and raw code.
        Returns True if verified successfully.
        Raises:
            OTPVerificationError - generic invalid
            OTPExpiredError
            OTPAttemptsExceededError
            OTPAlreadyUsedError
        """
        # Filter by recipient based on channel
        filter_kwargs = {
            'purpose': purpose,
            'is_used': False,
        }
        if channel == 'sms':
            filter_kwargs['mobile_number'] = recipient
        elif channel == 'whatsapp':
            filter_kwargs['whatsapp_number'] = recipient
        elif channel == 'email':
            filter_kwargs['email'] = recipient
        else:
            raise ValueError(f"Unsupported channel: {channel}")

        try:
            # Fetch the latest unused OTP for this recipient/purpose/channel
            otp_obj = OTPVerification.objects.filter(**filter_kwargs).latest('created_at')
        except OTPVerification.DoesNotExist:
            raise OTPVerificationError("No active OTP found for this recipient and purpose")

        # Check expiry
        if timezone.now() > otp_obj.expires_at:
            otp_obj.is_used = True
            otp_obj.save()
            raise OTPExpiredError("OTP expired")

        if otp_obj.attempts >= cls.MAX_ATTEMPTS:
            otp_obj.attempts += 1
            otp_obj.is_used = True
            otp_obj.save(update_fields=['attempts', 'is_used'])
            raise OTPAttemptsExceededError("Maximum verification attempts exceeded")

        if otp_obj.verify_otp(raw_otp):
            otp_obj.is_used = True
            otp_obj.save(update_fields=['is_used'])
            return True
        else:
            otp_obj.attempts += 1
            otp_obj.save(update_fields=['attempts'])
            raise OTPVerificationError("Invalid OTP code")

    # TODO: Add a periodic cleanup task (Celery/cron) to delete expired OTP records
    # that are older than, say, 24 hours to keep the table size manageable.