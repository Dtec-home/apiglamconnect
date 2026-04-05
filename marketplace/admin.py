from django.contrib import admin

from marketplace.models import Booking, PortfolioImage, Review, Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("title", "provider", "price", "duration", "created_at")
    search_fields = ("title", "provider__user__username", "provider__user__email")
    list_filter = ("created_at",)


@admin.register(PortfolioImage)
class PortfolioImageAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "service", "image_url", "created_at")
    search_fields = (
        "provider__user__username",
        "service__title",
        "image_url",
    )
    list_filter = ("created_at",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "client",
        "service",
        "scheduled_for",
        "status",
        "created_at",
    )
    list_filter = ("status", "scheduled_for", "created_at")
    search_fields = (
        "client__user__username",
        "service__title",
        "service__provider__user__username",
    )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "booking",
        "rating",
        "provider_reply",
        "created_at",
    )
    list_filter = ("rating", "created_at")
    search_fields = (
        "booking__client__user__username",
        "booking__service__provider__user__username",
        "comment",
        "provider_reply",
    )
