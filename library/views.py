from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from library.models import Author, Book, BookCopy, Genre
from library.permissions import IsCatalogManager
from library.serializers import (
    AuthorSerializer,
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

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            permission_classes = (IsAuthenticated,)
        else:
            permission_classes = (IsCatalogManager,)

        return [permission() for permission in permission_classes]


class AuthorViewSet(CatalogViewSet):
    queryset = Author.objects.all().order_by("full_name")
    serializer_class = AuthorSerializer


class GenreViewSet(CatalogViewSet):
    queryset = Genre.objects.all().order_by("name")
    serializer_class = GenreSerializer


class BookViewSet(CatalogViewSet):
    serializer_class = BookSerializer

    def get_queryset(self):
        queryset = Book.objects.prefetch_related("authors", "genres").order_by("title")

        if self.request.user.role in (ROLE_LIBRARIAN, ROLE_ADMIN):
            return queryset

        return queryset.filter(is_active=True)


class BookCopyViewSet(CatalogViewSet):
    queryset = BookCopy.objects.select_related("book").order_by("inventory_number")
    serializer_class = BookCopySerializer
    permission_classes = (IsCatalogManager,)

    def get_permissions(self):
        return [permission() for permission in self.permission_classes]
