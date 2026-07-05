# services/exceptions.py

class OTPError(Exception):
    """Base exception for OTP-related errors."""
    pass

class OTPGenerationError(OTPError):
    pass

class OTPSendError(OTPError):
    pass

class OTPVerificationError(OTPError):
    pass

class OTPExpiredError(OTPVerificationError):
    pass

class OTPAttemptsExceededError(OTPVerificationError):
    pass

class OTPAlreadyUsedError(OTPVerificationError):
    pass

class OTPSendLimitExceeded(OTPError):
    """Raised when too many OTP requests are made in a short time."""
    pass