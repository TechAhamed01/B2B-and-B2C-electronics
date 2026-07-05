

# Register your models here.
# apps/accounts/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile, DealerRegistration, Address, OTPVerification

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('mobile_number', 'email', 'full_name', 'is_dealer', 'is_active', 'is_verified')
    list_filter = ('is_dealer', 'is_active', 'is_mobile_verified', 'is_email_verified', 'is_whatsapp_verified', 'is_staff', 'is_superuser')
    search_fields = ('mobile_number', 'email', 'full_name')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('mobile_number', 'email', 'password')}),
        (_('Personal info'), {'fields': ('full_name', 'whatsapp_number', 'alternate_mobile')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 
                       'is_mobile_verified', 'is_email_verified', 'is_whatsapp_verified',
                       'is_dealer', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('mobile_number', 'email', 'full_name', 'password1', 'password2'),
        }),
    )

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'gender', 'date_of_birth')
    search_fields = ('user__mobile_number', 'user__email', 'user__full_name')
    raw_id_fields = ('user',)

@admin.register(DealerRegistration)
class DealerRegistrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name', 'gstin', 'pan', 'approval_status', 'approved_at')
    search_fields = ('company_name', 'gstin', 'pan', 'user__mobile_number')
    list_filter = ('nature_of_organization', 'approval_status')
    raw_id_fields = ('user',)

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'line1', 'city', 'state', 'pincode', 'is_default')
    search_fields = ('user__mobile_number', 'user__email', 'line1', 'city', 'pincode')
    list_filter = ('address_type', 'is_default')
    raw_id_fields = ('user',)

@admin.register(OTPVerification)
class OTPVerificationAdmin(admin.ModelAdmin):
    list_display = ('mobile_number', 'email', 'purpose', 'is_used', 'attempts', 'expires_at', 'created_at')
    search_fields = ('mobile_number', 'email')  # removed 'otp_code'
    list_filter = ('purpose', 'is_used')
    raw_id_fields = ('user',)
    readonly_fields = ('otp_code',)