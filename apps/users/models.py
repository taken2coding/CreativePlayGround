from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid
from .managers import CustomUserManager


class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(
        max_length=150,
        unique=True,
        blank=True,
        null=True,
    )
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    email_verification_token = models.CharField(max_length=36, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile_images/%Y/%m/%d/', blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    receive_newsletter = models.BooleanField(default=False)
    theme = models.CharField(max_length=20, choices=[('light', 'Light'), ('dark', 'Dark')], default='light')

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['email']

    def __str__(self):
        return self.email


    def clean(self):
        super().clean()
        if self.phone_number and not self.phone_number.startswith('+'):
            from django.core.exceptions import ValidationError
            raise ValidationError(_('Phone number must start with a "+" followed by country code.'))


class UserActivity(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='activities')
    path = models.CharField(max_length=255, verbose_name=_('Path'))
    method = models.CharField(max_length=10, verbose_name=_('Method'))
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_('Timestamp'))

    class Meta:
        verbose_name = _('User Activity')
        verbose_name_plural = _('User Activities')
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.email} - {self.method} {self.path} at {self.timestamp}"


class CookieAuthToken(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='auth_tokens')
    token_hash = models.CharField(max_length=255, unique=True, verbose_name=_('Token Hash'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Created At'))
    expires_at = models.DateTimeField(verbose_name=_('Expires At'))

    class Meta:
        verbose_name = _('Cookie Auth Token')
        verbose_name_plural = _('Cookie Auth Tokens')

    def __str__(self):
        return f"Token for {self.user.email} (expires {self.expires_at})"