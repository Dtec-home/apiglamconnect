from django.db import models


class Service(models.Model):
    provider = models.ForeignKey(
        "accounts.ProviderProfile",
        on_delete=models.CASCADE,
        related_name="services",
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.PositiveIntegerField(help_text="Duration in minutes")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Service<{self.title}>"


class PortfolioImage(models.Model):
    provider = models.ForeignKey(
        "accounts.ProviderProfile",
        on_delete=models.CASCADE,
        related_name="portfolio_images",
        null=True,
        blank=True,
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="portfolio_images",
        null=True,
        blank=True,
    )
    image_url = models.URLField(max_length=500)
    caption = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(provider__isnull=False, service__isnull=True)
                    | models.Q(provider__isnull=True, service__isnull=False)
                ),
                name="portfolio_image_single_target",
            ),
        ]

    def __str__(self) -> str:
        return f"PortfolioImage<{self.id}>"


class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        COMPLETED = "COMPLETED", "Completed"

    client = models.ForeignKey(
        "accounts.ClientProfile",
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name="bookings",
    )
    scheduled_for = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    provider_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Booking<{self.id}:{self.status}>"


class Review(models.Model):
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True)
    image_url = models.URLField(max_length=500, blank=True)
    provider_reply = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1, rating__lte=5),
                name="review_rating_between_1_and_5",
            ),
            models.UniqueConstraint(
                fields=["booking"],
                name="one_review_per_booking",
            ),
        ]

    def __str__(self) -> str:
        return f"Review<{self.id}:booking={self.booking_id}>"
