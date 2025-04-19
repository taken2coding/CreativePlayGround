from django.contrib.auth.models import BaseUserManager
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
import uuid
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        extra_fields.setdefault('is_verified', False)
        extra_fields.setdefault('username', email.split('@')[0])
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)

    def create_guest_user(self):
        email = f"guest_{uuid.uuid4()}@example.com"
        return self.create_user(email=email, password=None, is_active=True)

    def verified_users(self):
        return self.filter(is_verified=True)

    def needs_verification(self):
        return self.filter(is_verified=False, is_active=True)

    def recently_joined(self, days=30):
        since = timezone.now() - timedelta(days=days)
        return self.filter(created_at__gte=since, is_active=True)

    def by_phone_number(self, phone_number):
        return self.filter(phone_number=phone_number)

    def user_stats(self):
        return {
            'total_users': self.count(),
            'verified_users': self.verified_users().count(),
            'recent_users': self.recently_joined().count(),
        }

    def resend_verification(self, email):
        try:
            user = self.get(email=email, is_verified=False)
            token = str(uuid.uuid4())
            user.email_verification_token = token
            user.save()
            send_mail(
                subject=_('Verify Your Email'),
                message=f'Click to verify: {settings.SITE_URL}/accounts/verify/{token}/',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
            )
            logger.info(self, "requested for verification link")
            return True
        except self.model.DoesNotExist:
            return False

    def get_for_password_reset(self, email):
        return self.filter(email=email, is_active=True, is_verified=True).first()
