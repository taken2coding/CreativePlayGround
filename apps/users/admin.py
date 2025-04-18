from django.contrib import admin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('email', 'username', 'is_verified', 'date_joined')
    list_filter = ('is_verified', 'is_staff')
    search_fields = ('email', 'username')