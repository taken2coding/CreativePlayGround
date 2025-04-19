from django.contrib.auth.views import (PasswordResetView,
                                       PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView)
from .forms import CustomPasswordResetForm
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views.generic import View, FormView, UpdateView
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomUserLoginForm, CustomUserProfileForm
import uuid
from django.urls import reverse_lazy
from .models import CustomUser
from django.contrib.auth.views import PasswordResetView
import logging
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from .forms import EmailForm

logger = logging.getLogger(__name__)


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


class LoginView(FormView):
    template_name = 'users/login.html'
    form_class = CustomUserLoginForm
    success_url = reverse_lazy('users:profile')

    def form_valid(self, form):
        user = form.get_user()
        if user.is_active:
            login(self.request, user)
            return super().form_valid(form)
        else:
            form.add_error(None, _('Please verify your email before logging in.'))
            return self.form_invalid(form)

class LogoutView(View):
    def get(self, request):
        logout(request)
        return redirect('users:login')


class ProfileView(LoginRequiredMixin, UpdateView):
    model = CustomUser
    form_class = CustomUserProfileForm
    template_name = 'users/profile.html'
    success_url = reverse_lazy('users:profile')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, _('Profile updated successfully.'))
        return super().form_valid(form)


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