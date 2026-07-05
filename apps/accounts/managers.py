# apps/accounts/managers.py

from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    def create_user(self, mobile_number, email, full_name, password=None, **extra_fields):
        if not mobile_number:
            raise ValueError(_('The Mobile Number must be set'))
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        mobile_number = mobile_number.strip()
        user = self.model(
            mobile_number=mobile_number,
            email=email,
            full_name=full_name,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, mobile_number, email, full_name, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_mobile_verified', True)
        extra_fields.setdefault('is_email_verified', True)
        extra_fields.setdefault('is_whatsapp_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(mobile_number, email, full_name, password, **extra_fields)