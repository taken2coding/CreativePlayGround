from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import View, FormView, UpdateView
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from .models import CustomUser
from .forms import CustomUserCreationForm, CustomUserLoginForm, CustomUserProfileForm
import uuid


def home(request):
    return render(request,"users/home.html")


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
