from rest_framework import filters, mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from library.models import STATUS_AVAILABLE, Author, Book, BookCopy, Genre
from library.paginators import CatalogPagination
from library.permissions import IsCatalogManager
from library.serializers import (
    AuthorSerializer,
    BookFilterSerializer,
    BookCopySerializer,
    BookSerializer,
    GenreSerializer,
)
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
