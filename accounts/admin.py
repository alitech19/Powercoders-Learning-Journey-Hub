from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'role', 'cohort', 'is_staff')
    list_filter = ('role', 'cohort', 'is_staff', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        ('Powerhub', {'fields': ('role', 'cohort')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Powerhub', {'fields': ('role', 'cohort')}),
    )
