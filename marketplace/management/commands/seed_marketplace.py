from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import ClientProfile, ProviderProfile, User
from marketplace.models import Booking, PortfolioImage, Review, Service

SEED_CODE_SUFFIX = "12345!"

ADMIN_SEED_SECRET = f"Admin{SEED_CODE_SUFFIX}"
PROVIDER_SEED_SECRET = f"Provider{SEED_CODE_SUFFIX}"
CLIENT_SEED_SECRET = f"Client{SEED_CODE_SUFFIX}"


SEED_ADMIN = {
    "username": "admin",
    "email": "admin@wacu.test",
    "password": ADMIN_SEED_SECRET,
}

SEED_PROVIDERS = [
    {
        "username": "ava_smith",
        "email": "ava@wacu.test",
        "password": PROVIDER_SEED_SECRET,
        "location": "Nairobi, Kenya",
        "phone": "+254700000111",
        "bio": "Premium bridal styling, event makeup, and beauty services.",
        "is_verified": True,
        "services": [
            {
                "title": "Bridal Makeup Package",
                "description": "Full bridal makeup with touch-up support for events.",
                "price": "120.00",
                "duration": 180,
            },
            {
                "title": "Classic Hair Styling",
                "description": "Elegant hair styling for events, shoots, and special moments.",
                "price": "55.00",
                "duration": 90,
            },
        ],
        "portfolio_images": [
            {
                "image_url": "https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?auto=format&fit=crop&w=1200&q=80",
                "caption": "Bridal beauty finish",
            },
            {
                "image_url": "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?auto=format&fit=crop&w=1200&q=80",
                "caption": "Event styling showcase",
            },
        ],
    },
    {
        "username": "lina_kariuki",
        "email": "lina@wacu.test",
        "password": PROVIDER_SEED_SECRET,
        "location": "Mombasa, Kenya",
        "phone": "+254700000222",
        "bio": "Reliable home cleaning and organization services for busy clients.",
        "is_verified": False,
        "services": [
            {
                "title": "Deep Home Cleaning",
                "description": "Kitchen, bathroom, and living area deep cleaning service.",
                "price": "85.00",
                "duration": 150,
            },
            {
                "title": "Move-In Reset",
                "description": "Full reset cleaning for new homes and apartments.",
                "price": "110.00",
                "duration": 210,
            },
        ],
        "portfolio_images": [
            {
                "image_url": "https://images.unsplash.com/photo-1556761175-b413da4baf72?auto=format&fit=crop&w=1200&q=80",
                "caption": "Fresh living room",
            },
        ],
    },
]

SEED_CLIENTS = [
    {
        "username": "mia_jones",
        "email": "mia@wacu.test",
        "password": CLIENT_SEED_SECRET,
    },
    {
        "username": "sam_okech",
        "email": "sam@wacu.test",
        "password": CLIENT_SEED_SECRET,
    },
]


class Command(BaseCommand):
    help = "Seed marketplace demo data for manual testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Clear existing marketplace demo data before seeding.",
        )

    @transaction.atomic
    def handle(self, *_args, **options):
        if options["reset"]:
            self._clear_seed_data()

        admin_user = self._upsert_user(
            SEED_ADMIN["username"],
            SEED_ADMIN["email"],
            SEED_ADMIN["password"],
            is_provider=False,
            is_client=False,
            is_staff=True,
            is_superuser=True,
        )

        provider_profiles: list[ProviderProfile] = []
        for provider_data in SEED_PROVIDERS:
            user = self._upsert_user(
                provider_data["username"],
                provider_data["email"],
                provider_data["password"],
                is_provider=True,
                is_client=False,
            )
            provider_profile, _ = ProviderProfile.objects.update_or_create(
                user=user,
                defaults={
                    "location": provider_data["location"],
                    "phone": provider_data["phone"],
                    "bio": provider_data["bio"],
                    "is_verified": provider_data["is_verified"],
                },
            )
            provider_profiles.append(provider_profile)

        client_profiles: list[ClientProfile] = []
        for client_data in SEED_CLIENTS:
            user = self._upsert_user(
                client_data["username"],
                client_data["email"],
                client_data["password"],
                is_provider=False,
                is_client=True,
            )
            client_profile, _ = ClientProfile.objects.update_or_create(user=user)
            client_profiles.append(client_profile)

        for provider_profile, provider_data in zip(provider_profiles, SEED_PROVIDERS, strict=True):
            Service.objects.filter(provider=provider_profile).delete()
            for service_data in provider_data["services"]:
                Service.objects.create(
                    provider=provider_profile,
                    title=service_data["title"],
                    description=service_data["description"],
                    price=service_data["price"],
                    duration=service_data["duration"],
                )

        for provider_profile, provider_data in zip(provider_profiles, SEED_PROVIDERS, strict=True):
            for image_data in provider_data["portfolio_images"]:
                PortfolioImage.objects.create(
                    provider=provider_profile,
                    image_url=image_data["image_url"],
                    caption=image_data["caption"],
                )

        self._seed_bookings_and_reviews(client_profiles)

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded marketplace demo data successfully.\n"
                f"Admin: {admin_user.username} / {SEED_ADMIN['password']}\n"
                f"Client: {SEED_CLIENTS[0]['username']} / {SEED_CLIENTS[0]['password']}\n"
                f"Provider: {SEED_PROVIDERS[0]['username']} / {SEED_PROVIDERS[0]['password']}",
            )
        )

    def _upsert_user(
        self,
        username: str,
        email: str,
        password: str,
        *,
        is_provider: bool,
        is_client: bool,
        is_staff: bool = False,
        is_superuser: bool = False,
    ):
        user, _ = User.objects.get_or_create(username=username)
        user.email = email
        user.is_provider = is_provider
        user.is_client = is_client
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.set_password(password)
        user.save()
        return user

    def _clear_seed_data(self):
        seed_usernames = [SEED_ADMIN["username"]]
        seed_usernames.extend(provider["username"] for provider in SEED_PROVIDERS)
        seed_usernames.extend(client["username"] for client in SEED_CLIENTS)

        User.objects.filter(username__in=seed_usernames).delete()
        Review.objects.all().delete()
        Booking.objects.all().delete()
        Service.objects.all().delete()
        PortfolioImage.objects.all().delete()
        ProviderProfile.objects.all().delete()
        ClientProfile.objects.all().delete()

    def _seed_bookings_and_reviews(self, client_profiles: list[ClientProfile]) -> None:
        now = timezone.now()
        services = list(Service.objects.select_related("provider__user").all())

        if len(services) < 3:
            return

        Booking.objects.all().delete()
        Review.objects.all().delete()

        completed_booking = Booking.objects.create(
            client=client_profiles[0],
            service=services[0],
            scheduled_for=now - timedelta(days=2),
            status=Booking.Status.COMPLETED,
            provider_notes="Client was punctual and great to work with.",
        )
        Booking.objects.create(
            client=client_profiles[1],
            service=services[1],
            scheduled_for=now + timedelta(days=2),
            status=Booking.Status.ACCEPTED,
            provider_notes="Bring inspiration photos.",
        )
        Booking.objects.create(
            client=client_profiles[0],
            service=services[2],
            scheduled_for=now + timedelta(days=4),
            status=Booking.Status.PENDING,
            provider_notes="Awaiting provider review.",
        )
        Booking.objects.create(
            client=client_profiles[1],
            service=services[3],
            scheduled_for=now + timedelta(days=5),
            status=Booking.Status.REJECTED,
            provider_notes="Outside current service area.",
        )

        Review.objects.create(
            booking=completed_booking,
            rating=5,
            comment="Excellent service, great communication, and beautiful final result.",
            image_url="https://images.unsplash.com/photo-1522335789203-aabd1fc54bc9?auto=format&fit=crop&w=1200&q=80",
            provider_reply="Thank you for booking with us. Looking forward to seeing you again!",
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Created seed bookings for testing across completed, accepted, pending, and rejected states."
            )
        )
