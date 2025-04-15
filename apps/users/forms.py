from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils.translation import gettext_lazy as _
from .models import CustomUser
import re


class CustomUserCreationForm(UserCreationForm):
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        help_text=_('Optional. Format: +1234567890')
    )

    class Meta:
        model = CustomUser
        fields = ('email', 'username', 'phone_number', 'password1', 'password2')

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and not re.match(r'^\+\d{1,14}$', phone_number):
            raise forms.ValidationError(_('Phone number must start with "+" followed by digits.'))
        return phone_number

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError(_('This email is already in use.'))
        return email


class CustomUserLoginForm(AuthenticationForm):
    username = forms.EmailField(label=_('Email'), max_length=254)

    class Meta:
        model = CustomUser
        fields = ('username', 'password')


class CustomUserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'phone_number', 'date_of_birth')

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and not re.match(r'^\+\d{1,14}$', phone_number):
            raise forms.ValidationError(_('Phone number must start with "+" followed by digits.'))
        return phone_number
