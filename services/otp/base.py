# services/otp/base.py (unchanged)
from abc import ABC, abstractmethod

class OTPProvider(ABC):
    @abstractmethod
    def send_otp(self, recipient: str, otp_code: str, purpose: str) -> bool:
        pass