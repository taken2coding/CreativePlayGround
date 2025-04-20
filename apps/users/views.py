from django.contrib.auth.views import (PasswordResetView,
                                       PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView)
from .forms import CustomPasswordResetForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views.generic import View, FormView, UpdateView, TemplateView
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomLoginForm, CustomUserProfileForm
import uuid
from django.urls import reverse_lazy
from .models import CustomUser
from django.contrib.auth.views import PasswordResetView
import logging
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from .forms import EmailForm
from .models import CookieAuthToken
from django.utils import timezone
from datetime import timedelta
from django.core.signing import TimestampSigner
from django.contrib.auth.hashers import make_password
logger = logging.getLogger(__name__)


class CustomLoginView(FormView):
    template_name = 'users/login.html'
    form_class = CustomLoginForm
    success_url = reverse_lazy('users:profile')

    @method_decorator(ratelimit(key='user_or_ip', rate='5/m', method=ratelimit.ALL, block=True), name='dispatch')
    def dispatch(self, request, *args, **kwargs):
        token = request.COOKIES.get('myapp_auth_token')
        if token and not request.user.is_authenticated:
            user = authenticate(request, token=token)
            if user:
                login(request, user, backend='apps.users.backends.CookieAuthBackend')
                logger.info(f"Auto-login via cookie for {user.email}")
                return redirect(self.success_url)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        email = form.cleaned_data['email']
        password = form.cleaned_data['password']
        remember_me = form.cleaned_data['remember_me']
        theme = form.cleaned_data['theme'] or 'light'

        user = authenticate(request=self.request, username=email, password=password)
        if user is None:
            logger.warning(f"Failed login attempt for {email}")
            form.add_error(None, _('Invalid email or password'))
            return self.form_invalid(form)

        login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')
        logger.info(f"User {email} logged in")

        response = redirect(self.success_url)

        # Set theme cookie
        response.set_signed_cookie(
            'myapp_theme',
            theme,
            max_age=settings.THEME_COOKIE_AGE,
            secure=settings.SECURE_COOKIES,
            httponly=True,
            samesite='Lax',
            salt=settings.SIGNING_SALT
        )

        # Set remember me token
        if remember_me:
            token = str(uuid.uuid4())
            signer = TimestampSigner(salt=settings.SIGNING_SALT)
            signed_token = signer.sign(token)
            token_hash = make_password(token)
            CookieAuthToken.objects.create(
                user=user,
                token_hash=token_hash,
                expires_at=timezone.now() + timedelta(seconds=settings.REMEMBER_ME_COOKIE_AGE)
            )
            response.set_cookie(
                'myapp_auth_token',
                signed_token,
                max_age=settings.REMEMBER_ME_COOKIE_AGE,
                secure=settings.SECURE_COOKIES,
                httponly=True,
                samesite='Lax'
            )
            logger.info(f"Set remember me token for {email}")

        return response


class CustomPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.html'
    success_url = '/password-reset/done/'

    @method_decorator(ratelimit(key='user_or_ip', rate='5/m', method=ratelimit.ALL, block=True), name='dispatch')
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'users/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'users/password_reset_confirm.html'
    success_url = '/password-reset/complete/'


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'users/password_reset_complete.html'


def home(request):
    return render(request, "users/home.html")


class SignUpView(FormView):
    template_name = 'users/signup.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('users:login')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.is_active = False
        user.save()

        token = str(uuid.uuid4())
        user.email_verification_token = token
        user.save()

        verification_url = self.request.build_absolute_uri(
            reverse_lazy('users:verify_email', kwargs={'token': token})
        )
        send_mail(
            subject=_('Verify Your Email'),
            message=f'Click to verify your account: {verification_url}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        messages.success(self.request, _('Please check your email to verify your account.'))
        return super().form_valid(form)


class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('users:home')


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = CustomUserProfileForm
    template_name = 'users/profile_update.html'
    success_url = reverse_lazy('users:profile')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, _('Profile updated successfully.'))
        return super().form_valid(form)


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'users/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        # Fetch last 10 activities from database
        activities = user.activities.all()[:10]
        context['activities'] = [
            {
                'path': activity.path,
                'method': activity.method,
                'timestamp': activity.timestamp.isoformat()
            } for activity in activities
        ]
        logger.info(f"Profile accessed by user: {user.email}")
        return context


class VerifyEmailView(View):
    def get(self, request, token):
        try:
            user = CustomUser.objects.get(email_verification_token=token)
            if not user.is_active:
                user.is_active = True
                user.is_verified = True
                user.email_verification_token = None
                user.save()
                messages.success(request, _('Email verified successfully. You can now log in.'))
            else:
                messages.info(request, _('Email already verified.'))
        except CustomUser.DoesNotExist:
            messages.error(request, _('Invalid verification token.'))
        return redirect('users:login')


def resend_verification_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if CustomUser.objects.resend_verification(email):
            messages.success(request, _('Verification email resent.'))
        else:
            logger.warning(f"incorrect email from {request.user}")
            messages.error(request, _('Email not found or already verified.'))
    form = EmailForm()
    return render(request, 'users/resend_verification.html', {'form': form})