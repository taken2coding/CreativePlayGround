from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid


class CustomUser(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        blank=True,
        null=True,
        help_text=_('Optional. 150 characters or fewer. Letters, digits, and @/./+/-/_ only.'),
    )
    email = models.EmailField(_('email address'), unique=True, blank=False)
    phone_number = models.CharField(
        _('phone number'),
        max_length=15,
        blank=True,
        help_text=_('Optional. Format: +1234567890')
    )
    date_of_birth = models.DateField(_('date of birth'), null=True, blank=True)
    is_verified = models.BooleanField(
        _('verified'),
        default=False,
        help_text=_('Indicates whether the user has verified their email.')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    email_verification_token = models.CharField(max_length=36, blank=True, null=True)

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