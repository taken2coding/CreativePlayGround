import logging
import re
import uuid
from datetime import timedelta

from django.contrib.auth.models import BaseUserManager
from django.db import models, transaction
from django.db.models import Count
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class CustomUserManager(BaseUserManager):
    """
    A custom user manager for the CustomUser model, providing secure and efficient
    user creation, querying, and management.
    """

    def _validate_email(self, email):
        """Validate email format and presence."""
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email).strip()
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValueError(_('Invalid email format'))
        return email

    def _validate_phone_number(self, phone_number):
        """Validate phone number format if provided."""
        if phone_number and not re.match(r'^\+\d{1,14}$', phone_number):
            raise ValueError(_('Phone number must start with "+" followed by digits'))
        return phone_number

    @transaction.atomic
    def create_user(self, email, password=None, **extra_fields):
        """
        Create a regular user with the given email and password.
        """
        email = self._validate_email(email)
        extra_fields.setdefault('is_verified', False)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('username', email.split('@')[0][:150])

        # Validate phone number if provided
        phone_number = extra_fields.get('phone_number')
        if phone_number:
            extra_fields['phone_number'] = self._validate_phone_number(phone_number)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        logger.info(f"Created user with email: {email}")
        return user

    @transaction.atomic
    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create a superuser with admin privileges.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True'))

        user = self.create_user(email, password, **extra_fields)
        logger.info(f"Created superuser with email: {email}")
        return user

    def create_guest_user(self):
        """
        Create a guest user with a temporary email and no password.
        """
        email = f"guest_{uuid.uuid4()}@example.com"
        user = self.create_user(email=email, password=None, is_active=True)
        logger.info(f"Created guest user: {email}")
        return user

    def normalize_email(self, email):
        """
        Normalize email by converting to lowercase and removing whitespace.
        """
        email = super().normalize_email(email)
        return email.strip()

    def verified_users(self):
        """
        Return all verified users.
        """
        return self.filter(is_verified=True, is_active=True)

    def needs_verification(self):
        """
        Return users who need email verification.
        """
        return self.filter(is_verified=False, is_active=True)

    def recently_joined(self, days=30):
        """
        Return users who joined in the last specified days.
        """
        since = timezone.now() - timedelta(days=days)
        return self.filter(created_at__gte=since, is_active=True)

    def by_phone_number(self, phone_number):
        """
        Return users with the specified phone number.
        """
        if not phone_number:
            return self.none()
        return self.filter(phone_number=phone_number)

    def get_for_password_reset(self, email):
        """
        Return a user eligible for password reset (active and verified).
        """
        return self.filter(email=email, is_active=True, is_verified=True).first()

    @transaction.atomic
    def resend_verification(self, email):
        """
        Resend verification email to an unverified user.
        """
        from django.core.mail import send_mail
        from django.conf import settings
        from django.urls import reverse

        try:
            user = self.get(email=email, is_verified=False, is_active=True)
            token = str(uuid.uuid4())
            user.email_verification_token = token
            user.save()

            verification_url = settings.SITE_URL + reverse('users:verify_email', kwargs={'token': token})
            send_mail(
                subject=_('Verify Your Email'),
                message=f'Click to verify your account: {verification_url}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            logger.info(f"Resent verification email to: {email}")
            return True
        except self.model.DoesNotExist:
            logger.warning(f"Verification resend failed for email: {email}")
            return False

    def user_stats(self):
        """
        Return user statistics for analytics.
        """
        total = self.count()
        return {
            'total_users': total,
            'verified_users': self.verified_users().count(),
            'recent_users': self.recently_joined().count(),
            'theme_distribution': list(
                self.values('theme').annotate(count=Count('id')).order_by('-count')
            ),
            'verification_rate': (self.verified_users().count() / total * 100) if total else 0,
        }

    @transaction.atomic
    def verify_users(self, user_ids):
        """
        Mark multiple users as verified.
        """
        updated = self.filter(id__in=user_ids, is_verified=False).update(
            is_verified=True, email_verification_token=None
        )
        logger.info(f"Verified {updated} users")
        return updated

    @transaction.atomic
    def deactivate_users(self, user_ids):
        """
        Deactivate multiple users.
        """
        updated = self.filter(id__in=user_ids, is_active=True).update(is_active=False)
        logger.info(f"Deactivated {updated} users")
        return updated
