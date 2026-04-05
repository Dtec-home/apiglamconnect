from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from accounts.models import ClientProfile, ProviderProfile, User


@admin.register(User)
class MarketplaceUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "is_provider",
        "is_client",
        "is_staff",
        "is_active",
    )
    list_filter = ("is_provider", "is_client", "is_staff", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        ("Marketplace Role", {"fields": ("is_provider", "is_client")}),
    )


@admin.action(description="Mark selected providers as verified")
def verify_selected_providers(_modeladmin, _request, queryset):
    queryset.update(is_verified=True)


@admin.register(ProviderProfile)
class ProviderProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "location", "phone", "is_verified")
    list_filter = ("is_verified", "location")
    search_fields = ("user__username", "user__email", "location", "phone")
    actions = (verify_selected_providers,)


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ("user",)
    search_fields = ("user__username", "user__email")
