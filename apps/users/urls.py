from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from .views import (CustomPasswordResetView, CustomPasswordResetDoneView, CustomPasswordResetConfirmView,
                    CustomPasswordResetCompleteView)

app_name = 'users'

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('verify/<uuid:token>/', views.VerifyEmailView.as_view(), name='verify_email'),
    # Password reset URLs
    path('password-reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', CustomPasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
    path('password-reset/complete/', CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),

]