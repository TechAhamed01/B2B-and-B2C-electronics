# services/otp/whatsapp.py

import logging
from .base import OTPProvider

logger = logging.getLogger(__name__)

class WhatsAppProvider(OTPProvider):
    """
    Placeholder WhatsApp provider that logs the OTP.
    Replace with actual WhatsApp Business API or third-party service.
    """

    """def send_otp(self, recipient: str, otp_code: str, purpose: str) -> bool:
        logger.info("[WhatsApp] OTP sent to %s for purpose '%s'", recipient, purpose)
        return True"""
    def send_otp(self, recipient, otp_code, purpose):
        logger.warning(
            f"[DEV OTP] OTP={otp_code} Recipient={recipient}"
        )
        return True