from rest_framework import serializers

from library.models import (
    STATUS_AVAILABLE,
    STATUS_DAMAGED,
    Author,
    Book,
    BookCopy,
    Genre,
    Loan,
)
from users.models import ROLE_ADMIN


class BookFilterSerializer(serializers.Serializer):
    author = serializers.IntegerField(
        min_value=1,
        required=False,
    )
    genre = serializers.IntegerField(
        min_value=1,
        required=False,
    )
    is_available = serializers.BooleanField(required=False)


class LoanIssueSerializer(serializers.Serializer):
    reader_email = serializers.EmailField()
    inventory_number = serializers.CharField(max_length=50)


class LoanReturnSerializer(serializers.Serializer):
    inventory_number = serializers.CharField(max_length=50)
    status = serializers.ChoiceField(
        choices=(
            (STATUS_AVAILABLE, "Доступен"),
            (STATUS_DAMAGED, "Повреждён"),
        ),
        default=STATUS_AVAILABLE,
    )


class LoanFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=("active", "returned", "overdue"),
        required=False,
    )


class ReaderLoanSerializer(serializers.ModelSerializer):
    book_title = serializers.CharField(
        source="book_copy.book.title",
        read_only=True,
    )
    is_active = serializers.BooleanField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Loan
        fields = (
            "id",
            "book_title",
            "issued_at",
            "due_at",
            "returned_at",
            "is_active",
            "is_overdue",
        )


class StaffLoanSerializer(serializers.ModelSerializer):
    reader_email = serializers.EmailField(
        source="reader.email",
        read_only=True,
    )
    book_title = serializers.CharField(
        source="book_copy.book.title",
        read_only=True,
    )
    inventory_number = serializers.CharField(
        source="book_copy.inventory_number",
        read_only=True,
    )
    issued_by_email = serializers.EmailField(
        source="issued_by.email",
        read_only=True,
    )
    returned_by_email = serializers.EmailField(
        source="returned_by.email",
        read_only=True,
        allow_null=True,
    )
    is_active = serializers.BooleanField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = Loan
        fields = (
            "id",
            "reader_email",
            "book_title",
            "inventory_number",
            "issued_by_email",
            "issued_at",
            "due_at",
            "returned_at",
            "returned_by_email",
            "is_active",
            "is_overdue",
        )


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
