# services/otp/sms.py

import logging
from .base import OTPProvider

logger = logging.getLogger(__name__)

class SMSProvider(OTPProvider):
    """
    Placeholder SMS provider that logs the OTP.
    Replace with actual SMS gateway (Twilio, MSG91, etc.).
    """

    """def send_otp(self, recipient: str, otp_code: str, purpose: str) -> bool:
        logger.info("[SMS] OTP sent to %s for purpose '%s'", recipient, purpose)
        return True"""
    def send_otp(self, recipient, otp_code, purpose):
        logger.warning(
            f"[DEV OTP] OTP={otp_code} Recipient={recipient}"
        )
        return True