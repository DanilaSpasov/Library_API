from django.contrib import admin

from library.models import (
    Author,
    AvailabilitySubscription,
    Book,
    BookCopy,
    Genre,
    Loan,
)


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "birth_date",
    )
    search_fields = ("full_name",)


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "isbn",
        "publication_year",
        "is_active",
    )
    list_filter = (
        "is_active",
        "genres",
    )
    search_fields = (
        "title",
        "isbn",
        "authors__full_name",
    )
    filter_horizontal = (
        "authors",
        "genres",
    )

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BookCopy)
class BookCopyAdmin(admin.ModelAdmin):
    list_display = (
        "inventory_number",
        "book",
        "status",
    )
    list_filter = ("status",)
    search_fields = (
        "inventory_number",
        "book__title",
        "book__isbn",
    )
    autocomplete_fields = ("book",)
    list_select_related = ("book",)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = (
        "book_copy",
        "reader",
        "issued_by",
        "issued_at",
        "due_at",
        "returned_at",
        "active_status",
        "overdue_status",
    )
    list_filter = (
        "issued_at",
        "due_at",
        "returned_at",
    )
    search_fields = (
        "book_copy__inventory_number",
        "book_copy__book__title",
        "reader__email",
        "issued_by__email",
        "returned_by__email",
    )
    autocomplete_fields = (
        "reader",
        "book_copy",
        "issued_by",
        "returned_by",
    )
    readonly_fields = (
        "issued_at",
        "active_status",
        "overdue_status",
    )
    list_select_related = (
        "reader",
        "book_copy",
        "book_copy__book",
        "issued_by",
        "returned_by",
    )
    date_hierarchy = "issued_at"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(boolean=True, description="Активна")
    def active_status(self, obj):
        return obj.is_active

    @admin.display(boolean=True, description="Просрочена")
    def overdue_status(self, obj):
        return obj.is_overdue


@admin.register(AvailabilitySubscription)
class AvailabilitySubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "reader",
        "book",
        "created_at",
        "notified_at",
    )
    list_filter = (
        "created_at",
        "notified_at",
    )
    search_fields = (
        "reader__email",
        "book__title",
        "book__isbn",
    )
    autocomplete_fields = (
        "reader",
        "book",
    )
    readonly_fields = ("created_at",)
    list_select_related = (
        "reader",
        "book",
    )
