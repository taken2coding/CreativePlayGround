from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils.translation import gettext_lazy as _
from .models import CustomUser
import re
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import get_user_model

User = get_user_model()


class EmailForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Enter your email'}))



class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(max_length=254, widget=forms.TextInput(attrs={'placeholder': 'Email'}))

    def get_users(self, email):
        active_users = User.objects.filter(email__iexact=email, is_active=True)
        return (u for u in active_users if u.has_usable_password())


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


class CustomLoginForm(forms.Form):
    email = forms.EmailField(label=_('Email'), max_length=254)
    password = forms.CharField(label=_('Password'), widget=forms.PasswordInput)
    remember_me = forms.BooleanField(label=_('Remember Me'), required=False)
    theme = forms.ChoiceField(
        label=_('Theme'),
        choices=[('light', _('Light')), ('dark', _('Dark'))],
        required=False
    )

    def __init__(self, *args, is_remembered=False, remembered_email=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_remembered = is_remembered
        if is_remembered:
            # Pre-check remember_me
            self.fields['remember_me'].initial = True
            # Mask email (e.g., ****@example.com)
            if remembered_email:
                domain = remembered_email.split('@')[-1]
                self.fields['email'].initial = f"****@{domain}"
                self.fields['email'].widget.attrs['readonly'] = True  # Optional: make readonly
            # Set masked password placeholder
            self.fields['password'].initial = '********'
            self.fields['password'].widget.attrs['placeholder'] = '••••••••'

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')
        if self.is_remembered and email and email.startswith('****@'):
            # Skip validation for masked email; rely on token
            return cleaned_data
        if email and password:
            # Normal validation for non-remembered users
            pass
        return cleaned_data



class CustomUserProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'first_name', 'last_name', 'phone_number', 'date_of_birth')

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and not re.match(r'^\+\d{1,14}$', phone_number):
            raise forms.ValidationError(_('Phone number must start with "+" followed by digits.'))
        return phone_number

