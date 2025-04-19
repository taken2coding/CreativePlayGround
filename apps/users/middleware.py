from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class UserActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Initialize session activities list if not exists
            if 'user_activities' not in request.session:
                request.session['user_activities'] = []

            # Log activity (limit to last 10 activities)
            activities = request.session['user_activities']
            activity = {
                'path': request.path,
                'method': request.method,
                'timestamp': timezone.now().isoformat()
            }
            activities.append(activity)
            request.session['user_activities'] = activities[-10:]  # Keep last 10
            request.session.modified = True
            logger.info(f"User {request.user.email} visited {request.path} via {request.method}")

        response = self.get_response(request)
        return response
