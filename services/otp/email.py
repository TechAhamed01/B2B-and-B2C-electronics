# services/otp/email.py

import logging
from django.core.mail import send_mail
from django.conf import settings
from .base import OTPProvider

logger = logging.getLogger(__name__)

class EmailProvider(OTPProvider):

    def send_otp(self, recipient: str, otp_code: str, purpose: str) -> bool:

        subject = f"Your OTP for {purpose}"

        message = (
            f"Your OTP code is: {otp_code}\n"
            f"This code will expire in "
            f"{settings.OTP_EXPIRY_MINUTES} minutes."
        )

        from_email = settings.DEFAULT_FROM_EMAIL

        try:
            send_mail(
                subject,
                message,
                from_email,
                [recipient]
            )

            # Temporary for development only
            logger.warning(
                f"[DEV OTP EMAIL] OTP={otp_code} Recipient={recipient}"
            )

            return True

        except Exception as e:
            logger.error(
                f"[Email] Failed to send OTP to {recipient}: {e}"
            )
            raise