from django.utils import timezone
import logging
from .models import UserActivity

logger = logging.getLogger(__name__)


class UserActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Save activity to database
            UserActivity.objects.create(
                user=request.user,
                path=request.path,
                method=request.method,
                timestamp=timezone.now()
            )
            logger.info(f"User {request.user.email} visited {request.path} via {request.method} at {timezone.now()}")
        response = self.get_response(request)
        return response
