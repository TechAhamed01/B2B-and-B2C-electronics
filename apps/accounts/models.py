

# Create your models here.
# apps/accounts/models.py

import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

from .managers import UserManager

# -------------------- Base Model --------------------
class BaseModel(models.Model):
    """
    Abstract base model providing timestamp fields only.
    """
    created_at = models.DateTimeField(_('created at'), auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True, editable=False)

    class Meta:
        abstract = True

# -------------------- Custom User Model --------------------
class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    """
    Custom User model with mobile_number as the unique identifier.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    mobile_validator = RegexValidator(
    regex=r'^[6-9]\d{9}$',
    message='Enter a valid Indian mobile number'
    )
    mobile_number = models.CharField(
        _('mobile number'),
        max_length=10,
            # India only
        unique=True,
        db_index=True,
        help_text=_('10-digit mobile number without country code'),
        validators=[mobile_validator]
    )
    email = models.EmailField(
        _('email address'),
        unique=True,
        db_index=True,
        blank=False,
        null=False,
    )
    
    whatsapp_number = models.CharField(
        _('whatsapp number'),
        max_length=10,  # India only
        blank=True,
        null=True,
        help_text=_('Optional 10-digit WhatsApp number'),
        validators=[mobile_validator]
    )
    alternate_mobile = models.CharField(
        _('alternate mobile number'),
        max_length=10,  # India only
        blank=True,
        null=True,
        help_text=_('Optional alternate 10-digit mobile number'),
        validators=[mobile_validator]
    )
    full_name = models.CharField(_('full name'), max_length=150)
    
    # Verification flags
    is_mobile_verified = models.BooleanField(_('mobile verified'), default=False)
    is_email_verified = models.BooleanField(_('email verified'), default=False)
    is_whatsapp_verified = models.BooleanField(_('whatsapp verified'), default=False)
    
    # Dealer flag
    is_dealer = models.BooleanField(
        _('dealer status'),
        default=False,
        help_text=_('Designates whether the user is a dealer.'),
    )
    
    # Required fields for AbstractBaseUser
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_('Designates whether this user should be treated as active. Unselect instead of deleting accounts.'),
    )
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    USERNAME_FIELD = 'mobile_number'
    REQUIRED_FIELDS = ['email', 'full_name']

    objects = UserManager()

    class Meta:
        db_table = 'users'
        verbose_name = _('user')
        verbose_name_plural = _('users')
        indexes = [
            models.Index(fields=['mobile_number', 'is_active']),
            models.Index(fields=['email', 'is_active']),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.mobile_number})"

    @property
    def is_verified(self):
        """Primary verification is mobile verification."""
        return self.is_mobile_verified

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        if self.mobile_number:
            self.mobile_number = self.mobile_number.strip()
        if self.whatsapp_number:
            self.whatsapp_number = self.whatsapp_number.strip()
        if self.alternate_mobile:
            self.alternate_mobile = self.alternate_mobile.strip()

        self.full_clean()
        super().save(*args, **kwargs)


# -------------------- User Profile --------------------
class UserProfile(BaseModel):
    """
    One‑to‑one profile for additional user information.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        primary_key=True,  # uses the same UUID as User
    )
    date_of_birth = models.DateField(_('date of birth'), blank=True, null=True)
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    gender = models.CharField(
        max_length=1,
        choices=GENDER_CHOICES,
        blank=True,
        null=True,
    )

    class Meta:
        db_table = 'user_profiles'
        verbose_name = _('user profile')
        verbose_name_plural = _('user profiles')

    def __str__(self):
        return f"Profile of {self.user.full_name}"


# -------------------- Dealer Registration --------------------
class DealerRegistration(BaseModel):
    """
    Dealer‑specific information, linked one‑to‑one with User.
    Uses default AutoField primary key.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='dealer_info',
        # no primary_key=True – uses auto-increment id
    )
    company_name = models.CharField(_('company name'), max_length=255)
    gst_validator = RegexValidator(
    regex=r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[A-Z0-9]{3}$',
    message='Invalid GSTIN'
    )
    gstin = models.CharField(
        _('GSTIN'),
        max_length=15,
        unique=True,
        db_index=True,
        blank=True,
        null=True,
        help_text=_('Goods and Services Tax Identification Number'),
        validators=[gst_validator]
    )
    pan_validator=RegexValidator(
    regex=r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$',
    message='Invalid PAN'
    )
    pan = models.CharField(
        _('PAN'),
        max_length=10,
        unique=True,
        db_index=True,
        blank=True,
        null=True,
        help_text=_('Permanent Account Number'),
        validators=[pan_validator]  
    )
    msme_registration = models.CharField(
        _('MSME registration'),
        max_length=50,
        blank=True,
        null=True,
        help_text=_('Micro, Small and Medium Enterprises registration number'),
    )
    owner_name = models.CharField(_('owner name'), max_length=150)
    contact_person_name = models.CharField(_('contact person name'), max_length=150)
    
    NATURE_CHOICES = (
        ('PROPRIETORSHIP', 'Proprietorship'),
        ('PARTNERSHIP', 'Partnership'),
        ('LLP', 'LLP'),
        ('PRIVATE_LIMITED', 'Private Limited Company'),
        ('LIMITED', 'Limited Company'),
        ('OTHERS', 'Others'),
    )
    nature_of_organization = models.CharField(
        _('nature of organization'),
        max_length=20,
        choices=NATURE_CHOICES,
        default='PROPRIETORSHIP',
    )
    
    # File uploads
    gst_certificate = models.FileField(
        _('GST certificate'),
        upload_to='dealer_documents/gst/',
        blank=True,
        null=True,
    )
    owner_id_proof = models.FileField(
        _('owner ID proof'),
        upload_to='dealer_documents/id_proof/',
        blank=True,
        null=True,
    )
    
    # Approval workflow fields
    DEALER_APPROVAL_STATUS = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    )
    approval_status = models.CharField(
        max_length=10,
        choices=DEALER_APPROVAL_STATUS,
        default='PENDING',
        help_text=_('Approval status for dealer application.'),
    )
    approved_at = models.DateTimeField(_('approved at'), blank=True, null=True)
    rejection_reason = models.TextField(_('rejection reason'), blank=True, null=True)

    class Meta:
        db_table = 'dealer_registrations'
        verbose_name = _('dealer registration')
        verbose_name_plural = _('dealer registrations')
        indexes = [
            models.Index(fields=['gstin']),
            models.Index(fields=['pan']),
        ]

    def __str__(self):
        return f"{self.company_name} ({self.user.mobile_number})"


# -------------------- Address Model --------------------
class Address(BaseModel):
    """
    User addresses for shipping/billing.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='addresses',
    )
    ADDRESS_TYPE_CHOICES = (
        ('HOME', 'Home'),
        ('OFFICE', 'Office'),
        ('WAREHOUSE', 'Warehouse'),
        ('BILLING', 'Billing'),
        ('SHIPPING', 'Shipping'),
    )
    address_type = models.CharField(
        max_length=10,
        choices=ADDRESS_TYPE_CHOICES,
        default='SHIPPING',
    )
    line1 = models.CharField(_('address line 1'), max_length=255)
    line2 = models.CharField(_('address line 2'), max_length=255, blank=True, null=True)
    city = models.CharField(_('city'), max_length=100)
    state = models.CharField(_('state'), max_length=100)
    country = models.CharField(_('country'), max_length=100, default='India')
    pincode = models.CharField(
        _('pincode'),
        max_length=6,
        validators=[RegexValidator(r'^\d{6}$', 'Enter a valid 6-digit pincode.')],
    )
    landmark = models.CharField(_('landmark'), max_length=255, blank=True, null=True)
    is_default = models.BooleanField(_('default address'), default=False)

    class Meta:
        db_table = 'addresses'
        verbose_name = _('address')
        verbose_name_plural = _('addresses')
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_default']),
            models.Index(fields=['pincode']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['user'],
                condition=Q(is_default=True),
                name='unique_default_address_per_user'
            )
        ]

    def __str__(self):
        return f"{self.line1}, {self.city}"


# -------------------- OTP Verification Model --------------------
class OTPVerification(BaseModel):
    """
    Tracks OTP requests and verifications. Stores hashed OTP for security.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='otp_verifications',
        blank=True,
        null=True,
    )
    mobile_number = models.CharField(
        _('mobile number'),
        max_length=10,
        blank=True,
        null=True,
        db_index=True,
    )
    email = models.EmailField(_('email'), blank=True, null=True, db_index=True)
    whatsapp_number = models.CharField(
        _('whatsapp number'),
        max_length=10,
        blank=True,
        null=True,
    )
    # Store hashed OTP
    otp_code = models.CharField(_('OTP code (hashed)'), max_length=128)

    PURPOSE_CHOICES = (
        ('REGISTRATION', 'Registration'),
        ('LOGIN', 'Login'),
        ('PASSWORD_RESET', 'Password Reset'),
        ('DEALER_VERIFICATION', 'Dealer Verification'),
    )
    purpose = models.CharField(
        max_length=20,
        choices=PURPOSE_CHOICES,
        default='REGISTRATION',
    )
    is_used = models.BooleanField(_('used'), default=False)
    attempts = models.PositiveSmallIntegerField(_('attempts'), default=0)
    expires_at = models.DateTimeField(_('expires at'))
    MAX_OTP_ATTEMPTS=5

    class Meta:
        db_table = 'otp_verifications'
        verbose_name = _('OTP verification')
        verbose_name_plural = _('OTP verifications')
        indexes = [
            models.Index(fields=['mobile_number', 'purpose', 'expires_at']),
            models.Index(fields=['email', 'purpose', 'expires_at']),
        ]

    def __str__(self):
        return f"OTP for {self.mobile_number or self.email} ({self.purpose})"

    def set_otp_code(self, raw_otp):
        self.otp_code = make_password(raw_otp)

    def verify_otp(self, raw_otp):
        if self.is_used:
            return False
        if timezone.now() > self.expires_at:
            return False
        return check_password(raw_otp, self.otp_code)
    @property
    def can_attempt(self):
        return self.attempts < self.MAX_OTP_ATTEMPTS
        