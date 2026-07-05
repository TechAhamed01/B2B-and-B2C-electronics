# apps/accounts/backends.py

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()

class MobileOrEmailBackend(BaseBackend):
    """
    Authentication backend that allows login using either mobile number or email.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            return None
        # Try to find user by mobile_number or email
        try:
            user = User.objects.get(Q(mobile_number=username) | Q(email__iexact=username))
        except User.DoesNotExist:
            return None
        # Check password
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def user_can_authenticate(self, user):
        return user.is_active

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None