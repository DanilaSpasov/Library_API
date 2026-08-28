from rest_framework import filters, mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_201_CREATED
from rest_framework.views import APIView
from django.utils import timezone

from library.models import (
    STATUS_AVAILABLE,
    Author,
    AvailabilitySubscription,
    Book,
    BookCopy,
    Genre,
    Loan,
)
from library.paginators import CatalogPagination
from library.permissions import IsCatalogManager, IsLibrarianOrAdmin, IsReader
from library.serializers import (
    AuthorSerializer,
    AvailabilitySubscriptionSerializer,
    BookFilterSerializer,
    BookCopySerializer,
    BookSerializer,
    GenreSerializer,
    LoanFilterSerializer,
    LoanIssueSerializer,
    LoanReturnSerializer,
    ReaderLoanSerializer,
    StaffLoanSerializer,
)
from library.services import issue_book, return_book
from library.tasks import send_availability_notifications
from users.models import ROLE_ADMIN, ROLE_LIBRARIAN


class CatalogViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Базовый ViewSet каталога без физического удаления объектов."""

    pagination_class = CatalogPagination

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            permission_classes = (IsAuthenticated,)
        else:
            permission_classes = (IsCatalogManager,)

        return [permission() for permission in permission_classes]


class AuthorViewSet(CatalogViewSet):
    queryset = Author.objects.all().order_by("full_name")
    serializer_class = AuthorSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("full_name",)
    ordering_fields = ("full_name", "birth_date")
    ordering = ("full_name",)


class GenreViewSet(CatalogViewSet):
    queryset = Genre.objects.all().order_by("name")
    serializer_class = GenreSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = ("name",)
    ordering_fields = ("name",)
    ordering = ("name",)


class BookViewSet(CatalogViewSet):
    serializer_class = BookSerializer
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = (
        "title",
        "isbn",
        "authors__full_name",
        "genres__name",
    )
    ordering_fields = (
        "title",
        "publication_year",
    )
    ordering = ("title",)

    def get_queryset(self):
        queryset = Book.objects.prefetch_related("authors", "genres")

        if self.request.user.role not in (ROLE_LIBRARIAN, ROLE_ADMIN):
            queryset = queryset.filter(is_active=True)

        filter_serializer = BookFilterSerializer(data=self.request.query_params.dict())
        filter_serializer.is_valid(raise_exception=True)
        filters_data = filter_serializer.validated_data

        author_id = filters_data.get("author")
        if author_id:
            queryset = queryset.filter(authors__id=author_id)

        genre_id = filters_data.get("genre")
        if genre_id:
            queryset = queryset.filter(genres__id=genre_id)

        if "is_available" in filters_data:
            if filters_data["is_available"]:
                queryset = queryset.filter(copies__status=STATUS_AVAILABLE).distinct()
            else:
                queryset = queryset.exclude(copies__status=STATUS_AVAILABLE)

        return queryset


class BookCopyViewSet(CatalogViewSet):
    queryset = BookCopy.objects.select_related("book").order_by("inventory_number")
    serializer_class = BookCopySerializer
    permission_classes = (IsCatalogManager,)
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = (
        "inventory_number",
        "book__title",
        "book__isbn",
    )
    ordering_fields = ("inventory_number", "status", "book__title")
    ordering = ("inventory_number",)

    def get_permissions(self):
        return [permission() for permission in self.permission_classes]

    def perform_create(self, serializer):
        book_copy = serializer.save()

        if book_copy.status == STATUS_AVAILABLE:
            send_availability_notifications.delay(book_copy.book_id)

    def perform_update(self, serializer):
        previous_status = serializer.instance.status
        book_copy = serializer.save()

        if previous_status != STATUS_AVAILABLE and book_copy.status == STATUS_AVAILABLE:
            send_availability_notifications.delay(book_copy.book_id)


class LoanViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (IsAuthenticated,)
    pagination_class = CatalogPagination
    filter_backends = (filters.SearchFilter, filters.OrderingFilter)
    search_fields = (
        "reader__email",
        "book_copy__book__title",
        "book_copy__inventory_number",
    )
    ordering_fields = ("issued_at", "due_at", "returned_at")
    ordering = ("-issued_at",)

    def get_queryset(self):
        queryset = Loan.objects.select_related(
            "reader",
            "book_copy",
            "book_copy__book",
            "issued_by",
            "returned_by",
        )

        if self.request.user.role not in (ROLE_LIBRARIAN, ROLE_ADMIN):
            queryset = queryset.filter(reader=self.request.user)

        filter_serializer = LoanFilterSerializer(data=self.request.query_params.dict())
        filter_serializer.is_valid(raise_exception=True)
        loan_status = filter_serializer.validated_data.get("status")

        if loan_status == "active":
            queryset = queryset.filter(returned_at__isnull=True)
        elif loan_status == "returned":
            queryset = queryset.filter(returned_at__isnull=False)
        elif loan_status == "overdue":
            queryset = queryset.filter(
                returned_at__isnull=True,
                due_at__lt=timezone.now(),
            )

        return queryset

    def get_serializer_class(self):
        if self.request.user.role in (ROLE_LIBRARIAN, ROLE_ADMIN):
            return StaffLoanSerializer

        return ReaderLoanSerializer


class LoanIssueAPIView(APIView):
    permission_classes = (IsLibrarianOrAdmin,)

    def post(self, request):
        serializer = LoanIssueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        loan = issue_book(
            reader_email=serializer.validated_data["reader_email"],
            inventory_number=serializer.validated_data["inventory_number"],
            issued_by=request.user,
        )

        return Response(
            StaffLoanSerializer(loan).data,
            status=HTTP_201_CREATED,
        )


class LoanReturnAPIView(APIView):
    permission_classes = (IsLibrarianOrAdmin,)

    def post(self, request):
        serializer = LoanReturnSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        loan = return_book(
            inventory_number=serializer.validated_data["inventory_number"],
            returned_by=request.user,
            return_status=serializer.validated_data["status"],
        )

        return Response(
            StaffLoanSerializer(loan).data,
            status=HTTP_200_OK,
        )


class AvailabilitySubscriptionViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = AvailabilitySubscriptionSerializer
    permission_classes = (IsReader,)
    pagination_class = CatalogPagination

    def get_queryset(self):
        return (
            AvailabilitySubscription.objects.filter(
                reader=self.request.user,
                notified_at__isnull=True,
            )
            .select_related("book")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(reader=self.request.user)
