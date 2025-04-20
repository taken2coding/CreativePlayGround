from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from .models import CookieAuthToken
from django.utils import timezone
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django.contrib.auth.hashers import check_password
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

'''
class CustomAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(email=username)
        except UserModel.DoesNotExist:
            try:
                user = UserModel.objects.get(phone_number=username)
            except UserModel.DoesNotExist:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

'''

class CookieAuthBackend(ModelBackend):
    def authenticate(self, request, token=None, **kwargs):
        if token is None:
            return None
        try:
            signer = TimestampSigner(salt=settings.SIGNING_SALT)
            token_value = signer.unsign(token, max_age=settings.REMEMBER_ME_COOKIE_AGE)
            auth_token = CookieAuthToken.objects.get(
                expires_at__gt=timezone.now()
            )
            if check_password(token_value, auth_token.token_hash):
                user = auth_token.user
                if user.is_active:
                    logger.info(f"Authenticated user {user.email} via cookie token")
                    return user
        except (BadSignature, SignatureExpired):
            logger.warning("Invalid or expired signed token attempted")
            return None
        except CookieAuthToken.DoesNotExist:
            logger.warning("Token not found in database")
            return None
        except Exception as e:
            logger.error(f"Cookie authentication error: {str(e)}")
            return None
        return None

    def get_user(self, user_id):
        try:
            return get_user_model().objects.get(pk=user_id)
        except get_user_model().DoesNotExist:
            return None
