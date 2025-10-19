from django.contrib import admin
from django.contrib import admin
from .models import Profile, Address

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'phone', 'gender', 'birthday')

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['city', 'is_default', 'created_at']
    list_filter = ['is_default', 'city']
