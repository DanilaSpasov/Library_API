from rest_framework import serializers

from library.models import STATUS_AVAILABLE, Author, Book, BookCopy, Genre
from users.models import ROLE_ADMIN


class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = (
            "id",
            "full_name",
            "birth_date",
            "biography",
        )


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = (
            "id",
            "name",
            "description",
        )


class BookSerializer(serializers.ModelSerializer):
    authors = AuthorSerializer(
        many=True,
        read_only=True,
    )
    genres = GenreSerializer(
        many=True,
        read_only=True,
    )
    author_ids = serializers.PrimaryKeyRelatedField(
        source="authors",
        queryset=Author.objects.all(),
        many=True,
        write_only=True,
    )
    genre_ids = serializers.PrimaryKeyRelatedField(
        source="genres",
        queryset=Genre.objects.all(),
        many=True,
        write_only=True,
    )
    available_copies_count = serializers.SerializerMethodField()
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields = (
            "id",
            "title",
            "isbn",
            "publication_year",
            "description",
            "authors",
            "genres",
            "author_ids",
            "genre_ids",
            "is_active",
            "available_copies_count",
            "is_available",
        )

    def get_available_copies_count(self, obj):
        return obj.copies.filter(status=STATUS_AVAILABLE).count()

    def get_is_available(self, obj):
        return self.get_available_copies_count(obj) > 0

    def validate_is_active(self, value):
        request = self.context.get("request")

        if request and request.user.role != ROLE_ADMIN:
            raise serializers.ValidationError(
                "Изменять активность книги может только администратор."
            )

        return value


class BookCopySerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(
        source="book.title",
        read_only=True,
    )
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = BookCopy
        fields = (
            "id",
            "book",
            "book_title",
            "inventory_number",
            "status",
            "status_display",
        )
