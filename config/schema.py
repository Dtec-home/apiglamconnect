from datetime import datetime, timezone
from typing import Optional

import jwt
import strawberry
from django.db.models import Avg
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from strawberry.schema.config import StrawberryConfig

from accounts.models import ClientProfile, ProviderProfile
from marketplace.models import Booking, PortfolioImage, Review, Service

User = get_user_model()


def _issue_token(user: User) -> str:
    payload = {
        "user_id": user.id,
        "username": user.username,
        "exp": int(datetime.now(timezone.utc).timestamp()) + 60 * 60 * 24,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def _extract_user_from_context(info: strawberry.Info) -> Optional[User]:
    request = info.context.request
    header = request.headers.get("Authorization", "")

    if not header.startswith("Bearer "):
        return None

    token = header.replace("Bearer ", "", 1)

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return User.objects.get(id=payload["user_id"])
    except (jwt.InvalidTokenError, User.DoesNotExist, KeyError):
        return None


@strawberry.type
class UserType:
    id: strawberry.ID
    username: str
    email: str
    is_provider: bool
    is_client: bool


@strawberry.type
class ProviderProfileType:
    id: strawberry.ID
    user: UserType
    location: str
    phone: str
    bio: str
    is_verified: bool


@strawberry.type
class ServiceType:
    id: strawberry.ID
    provider: ProviderProfileType
    title: str
    description: str
    price: str
    duration: int


@strawberry.type
class PortfolioImageType:
    id: strawberry.ID
    image_url: str
    caption: str
    provider_id: Optional[int]
    service_id: Optional[int]


@strawberry.type
class BookingType:
    id: strawberry.ID
    client: UserType
    service: ServiceType
    scheduled_for: str
    status: str
    provider_notes: str


@strawberry.type
class ReviewType:
    id: strawberry.ID
    booking_id: int
    client: UserType
    rating: int
    comment: str
    image_url: str
    provider_reply: str
    created_at: str


@strawberry.type
class ProviderRatingSummaryType:
    average_rating: float
    review_count: int


@strawberry.type
class AuthPayload:
    token: str
    user: UserType


@strawberry.input
class RegisterInput:
    username: str
    email: str
    password: str
    role: str


@strawberry.input
class LoginInput:
    username: str
    password: str


@strawberry.input
class CreateServiceInput:
    title: str
    description: str
    price: float
    duration: int


@strawberry.input
class AddPortfolioImageInput:
    image_url: str
    caption: Optional[str] = ""
    provider_id: Optional[int] = None
    service_id: Optional[int] = None


@strawberry.input
class CreateBookingInput:
    service_id: int
    scheduled_for: str


@strawberry.input
class UpdateBookingStatusInput:
    booking_id: int
    status: str
    provider_notes: Optional[str] = ""


@strawberry.input
class LeaveReviewInput:
    booking_id: int
    rating: int
    comment: Optional[str] = ""
    image_url: Optional[str] = ""


@strawberry.input
class ReplyToReviewInput:
    review_id: int
    provider_reply: str


def _to_user_type(user: User) -> UserType:
    return UserType(
        id=user.id,
        username=user.username,
        email=user.email,
        is_provider=user.is_provider,
        is_client=user.is_client,
    )


def _to_provider_type(profile: ProviderProfile) -> ProviderProfileType:
    return ProviderProfileType(
        id=profile.id,
        user=_to_user_type(profile.user),
        location=profile.location,
        phone=profile.phone,
        bio=profile.bio,
        is_verified=profile.is_verified,
    )


def _to_service_type(service: Service) -> ServiceType:
    return ServiceType(
        id=service.id,
        provider=_to_provider_type(service.provider),
        title=service.title,
        description=service.description,
        price=str(service.price),
        duration=service.duration,
    )


def _to_portfolio_image_type(image: PortfolioImage) -> PortfolioImageType:
    return PortfolioImageType(
        id=image.id,
        image_url=image.image_url,
        caption=image.caption,
        provider_id=image.provider_id,
        service_id=image.service_id,
    )


def _to_booking_type(booking: Booking) -> BookingType:
    return BookingType(
        id=booking.id,
        client=_to_user_type(booking.client.user),
        service=_to_service_type(booking.service),
        scheduled_for=booking.scheduled_for.isoformat(),
        status=booking.status,
        provider_notes=booking.provider_notes,
    )


def _to_review_type(review: Review) -> ReviewType:
    return ReviewType(
        id=review.id,
        booking_id=review.booking_id,
        client=_to_user_type(review.booking.client.user),
        rating=review.rating,
        comment=review.comment,
        image_url=review.image_url,
        provider_reply=review.provider_reply,
        created_at=review.created_at.isoformat(),
    )


def _require_provider(info: strawberry.Info) -> ProviderProfile:
    user = _extract_user_from_context(info)
    if not user:
        raise ValueError("Authentication required. Send header: Authorization: Bearer <token>.")

    try:
        return user.provider_profile
    except ProviderProfile.DoesNotExist as exc:
        raise ValueError("Provider account required.") from exc


def _require_client(info: strawberry.Info) -> ClientProfile:
    user = _extract_user_from_context(info)
    if not user:
        raise ValueError("Authentication required. Send header: Authorization: Bearer <token>.")

    try:
        return user.client_profile
    except ClientProfile.DoesNotExist as exc:
        raise ValueError("Client account required.") from exc


@strawberry.type
class Query:
    @strawberry.field
    def healthcheck(self) -> str:
        return "ok"

    @strawberry.field
    def server_time(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    @strawberry.field
    def me(self, info: strawberry.Info) -> Optional[UserType]:
        user = _extract_user_from_context(info)
        if not user:
            return None

        return _to_user_type(user)

    @strawberry.field
    def providers(self) -> list[ProviderProfileType]:
        provider_profiles = ProviderProfile.objects.select_related("user").all()
        return [_to_provider_type(profile) for profile in provider_profiles]

    @strawberry.field
    def provider(self, provider_id: int) -> Optional[ProviderProfileType]:
        profile = ProviderProfile.objects.select_related("user").filter(
            id=provider_id,
        ).first()
        if not profile:
            return None
        return _to_provider_type(profile)

    @strawberry.field
    def my_services(self, info: strawberry.Info) -> list[ServiceType]:
        provider = _require_provider(info)
        services = Service.objects.select_related("provider__user").filter(provider=provider)
        return [_to_service_type(service) for service in services]

    @strawberry.field
    def provider_services(self, provider_id: int) -> list[ServiceType]:
        services = Service.objects.select_related("provider__user").filter(
            provider_id=provider_id,
        )
        return [_to_service_type(service) for service in services]

    @strawberry.field
    def portfolio_images(
        self,
        provider_id: Optional[int] = None,
        service_id: Optional[int] = None,
    ) -> list[PortfolioImageType]:
        images = PortfolioImage.objects.all()
        if provider_id is not None:
            images = images.filter(provider_id=provider_id)
        if service_id is not None:
            images = images.filter(service_id=service_id)

        return [_to_portfolio_image_type(image) for image in images]

    @strawberry.field
    def my_client_bookings(self, info: strawberry.Info) -> list[BookingType]:
        client = _require_client(info)
        bookings = Booking.objects.select_related(
            "client__user",
            "service__provider__user",
        ).filter(client=client)
        return [_to_booking_type(booking) for booking in bookings]

    @strawberry.field
    def my_provider_bookings(self, info: strawberry.Info) -> list[BookingType]:
        provider = _require_provider(info)
        bookings = Booking.objects.select_related(
            "client__user",
            "service__provider__user",
        ).filter(service__provider=provider)
        return [_to_booking_type(booking) for booking in bookings]

    @strawberry.field
    def reviews_for_provider(self, provider_id: int) -> list[ReviewType]:
        reviews = Review.objects.select_related(
            "booking__client__user",
            "booking__service__provider__user",
        ).filter(
            booking__service__provider_id=provider_id,
        ).order_by("-created_at")
        return [_to_review_type(review) for review in reviews]

    @strawberry.field
    def my_provider_reviews(self, info: strawberry.Info) -> list[ReviewType]:
        provider = _require_provider(info)
        reviews = Review.objects.select_related(
            "booking__client__user",
            "booking__service__provider__user",
        ).filter(
            booking__service__provider=provider,
        ).order_by("-created_at")
        return [_to_review_type(review) for review in reviews]

    @strawberry.field
    def provider_rating_summary(self, provider_id: int) -> ProviderRatingSummaryType:
        aggregation = Review.objects.filter(
            booking__service__provider_id=provider_id,
        ).aggregate(
            average_rating=Avg("rating"),
        )
        review_count = Review.objects.filter(
            booking__service__provider_id=provider_id,
        ).count()
        average = aggregation.get("average_rating") or 0
        return ProviderRatingSummaryType(
            average_rating=round(float(average), 2),
            review_count=review_count,
        )


@strawberry.type
class Mutation:
    @strawberry.mutation
    def register(self, data: RegisterInput) -> AuthPayload:
        normalized_role = data.role.strip().lower()
        if normalized_role not in {"provider", "client"}:
            raise ValueError("Role must be either 'provider' or 'client'.")

        user = User.objects.create_user(
            username=data.username,
            email=data.email,
            password=data.password,
            is_provider=normalized_role == "provider",
            is_client=normalized_role == "client",
        )

        if user.is_provider:
            ProviderProfile.objects.create(user=user)
        if user.is_client:
            ClientProfile.objects.create(user=user)

        return AuthPayload(
            token=_issue_token(user),
            user=_to_user_type(user),
        )

    @strawberry.mutation
    def login(self, data: LoginInput) -> AuthPayload:
        user = authenticate(username=data.username, password=data.password)
        if not user:
            raise ValueError("Invalid username or password.")

        return AuthPayload(
            token=_issue_token(user),
            user=_to_user_type(user),
        )

    @strawberry.mutation
    def create_service(self, info: strawberry.Info, data: CreateServiceInput) -> ServiceType:
        provider = _require_provider(info)

        service = Service.objects.create(
            provider=provider,
            title=data.title,
            description=data.description,
            price=data.price,
            duration=data.duration,
        )

        return _to_service_type(service)

    @strawberry.mutation
    def add_portfolio_image(
        self,
        info: strawberry.Info,
        data: AddPortfolioImageInput,
    ) -> PortfolioImageType:
        provider = _require_provider(info)

        target_provider = provider
        target_service = None

        if data.provider_id is not None and data.provider_id != provider.id:
            raise ValueError("Cannot attach image to another provider profile.")

        if data.service_id is not None:
            target_service = Service.objects.filter(
                id=data.service_id,
                provider=provider,
            ).first()
            if not target_service:
                raise ValueError("Service not found for current provider.")
            target_provider = None

        image = PortfolioImage.objects.create(
            provider=target_provider,
            service=target_service,
            image_url=data.image_url,
            caption=data.caption or "",
        )

        return _to_portfolio_image_type(image)

    @strawberry.mutation
    def create_booking(self, info: strawberry.Info, data: CreateBookingInput) -> BookingType:
        client = _require_client(info)

        service = Service.objects.select_related("provider__user").filter(
            id=data.service_id,
        ).first()
        if not service:
            raise ValueError("Service not found.")

        when = datetime.fromisoformat(data.scheduled_for.replace("Z", "+00:00"))

        booking = Booking.objects.create(
            client=client,
            service=service,
            scheduled_for=when,
        )
        booking = Booking.objects.select_related(
            "client__user",
            "service__provider__user",
        ).get(id=booking.id)
        return _to_booking_type(booking)

    @strawberry.mutation
    def update_booking_status(
        self,
        info: strawberry.Info,
        data: UpdateBookingStatusInput,
    ) -> BookingType:
        provider = _require_provider(info)
        booking = Booking.objects.select_related(
            "client__user",
            "service__provider__user",
        ).filter(id=data.booking_id, service__provider=provider).first()

        if not booking:
            raise ValueError("Booking not found for current provider.")

        allowed_status = {choice[0] for choice in Booking.Status.choices}
        status = data.status.strip().upper()
        if status not in allowed_status:
            raise ValueError("Invalid booking status.")

        booking.status = status
        if data.provider_notes is not None:
            booking.provider_notes = data.provider_notes
        booking.save(update_fields=["status", "provider_notes"])

        return _to_booking_type(booking)

    @strawberry.mutation
    def leave_review(self, info: strawberry.Info, data: LeaveReviewInput) -> ReviewType:
        client = _require_client(info)
        booking = Booking.objects.select_related(
            "client__user",
            "service__provider__user",
        ).filter(
            id=data.booking_id,
            client=client,
        ).first()

        if not booking:
            raise ValueError("Booking not found for current client.")

        if booking.status != Booking.Status.COMPLETED:
            raise ValueError("Only completed bookings can be reviewed.")

        if not (1 <= data.rating <= 5):
            raise ValueError("Rating must be between 1 and 5.")

        if Review.objects.filter(booking=booking).exists():
            raise ValueError("Review already submitted for this booking.")

        review = Review.objects.create(
            booking=booking,
            rating=data.rating,
            comment=data.comment or "",
            image_url=data.image_url or "",
        )
        review = Review.objects.select_related(
            "booking__client__user",
            "booking__service__provider__user",
        ).get(id=review.id)
        return _to_review_type(review)

    @strawberry.mutation
    def reply_to_review(self, info: strawberry.Info, data: ReplyToReviewInput) -> ReviewType:
        provider = _require_provider(info)
        review = Review.objects.select_related(
            "booking__client__user",
            "booking__service__provider__user",
        ).filter(
            id=data.review_id,
            booking__service__provider=provider,
        ).first()

        if not review:
            raise ValueError("Review not found for current provider.")

        reply = data.provider_reply.strip()
        if not reply:
            raise ValueError("Reply text is required.")

        review.provider_reply = reply
        review.save(update_fields=["provider_reply"])
        return _to_review_type(review)


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    config=StrawberryConfig(auto_camel_case=False),
)
