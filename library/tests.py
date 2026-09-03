from datetime import timedelta

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase

from library.models import (
    STATUS_AVAILABLE,
    STATUS_BORROWED,
    STATUS_DAMAGED,
    STATUS_MAINTENANCE,
    Author,
    AvailabilitySubscription,
    Book,
    BookCopy,
    Genre,
    Loan,
)
from library.services import issue_book
from library.tasks import send_availability_notifications
from users.models import ROLE_LIBRARIAN, ROLE_READER, User


class LibraryDataMixin:
    """Общие данные для тестов библиотеки."""

    def create_data(self):
        """Создаёт пользователей и книги для тестов библиотеки."""
        self.reader = User.objects.create_user(
            "reader@example.com",
            "StrongPass123!",
            role=ROLE_READER,
            is_active=True,
            is_email_verified=True,
        )
        self.librarian = User.objects.create_user(
            "librarian@example.com",
            "StrongPass123!",
            role=ROLE_LIBRARIAN,
            is_active=True,
            is_email_verified=True,
        )
        self.author = Author.objects.create(full_name="Лев Толстой")
        self.genre = Genre.objects.create(name="Роман")
        self.book = Book.objects.create(
            title="Война и мир",
            isbn="9785170904401",
            publication_year=1869,
            description="Роман о нескольких семьях во время войны 1812 года.",
        )
        self.book.authors.add(self.author)
        self.book.genres.add(self.genre)
        self.copy = BookCopy.objects.create(
            book=self.book,
            inventory_number="BOOK-001",
            status=STATUS_AVAILABLE,
        )
        self.unavailable_book = Book.objects.create(title="Анна Каренина")
        self.unavailable_copy = BookCopy.objects.create(
            book=self.unavailable_book,
            inventory_number="BOOK-002",
            status=STATUS_MAINTENANCE,
        )


class CatalogApiTests(LibraryDataMixin, APITestCase):
    """Тесты API библиотечного каталога."""

    def setUp(self):
        """Создание данных перед каждым тестом каталога."""
        self.create_data()

    def test_catalog_requires_authentication(self):
        """Тестирование запрета просмотра каталога без авторизации."""
        response = self.client.get(reverse("library:books-list"))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_reader_can_search_books(self):
        """Тестирование поиска книг читателем."""
        self.client.force_authenticate(self.reader)

        response = self.client.get(reverse("library:books-list"), {"search": "Толстой"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["title"], "Война и мир")

    def test_reader_cannot_create_book(self):
        """Тестирование запрета создания книги читателем."""
        self.client.force_authenticate(self.reader)

        response = self.client.post(
            reverse("library:books-list"),
            {
                "title": "Новая книга",
                "author_ids": [self.author.id],
                "genre_ids": [self.genre.id],
            },
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_librarian_can_create_book(self):
        """Тестирование создания книги библиотекарем."""
        self.client.force_authenticate(self.librarian)

        response = self.client.post(
            reverse("library:books-list"),
            {
                "title": "Новая книга",
                "author_ids": [self.author.id],
                "genre_ids": [self.genre.id],
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data,
        )
        self.assertTrue(Book.objects.filter(title="Новая книга").exists())

    def test_available_filter(self):
        """Тестирование фильтра доступных книг."""
        self.client.force_authenticate(self.reader)

        response = self.client.get(
            reverse("library:books-list"),
            {"is_available": "true"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)


class LoanApiTests(LibraryDataMixin, APITestCase):
    """Тесты API выдачи и возврата книг."""

    def setUp(self):
        """Создание данных перед каждым тестом выдачи книг."""
        self.create_data()

    def test_librarian_can_issue_and_return_book(self):
        """Тестирование выдачи и возврата книги библиотекарем."""
        self.client.force_authenticate(self.librarian)

        issue_response = self.client.post(
            reverse("library:loan-issue"),
            {
                "reader_email": self.reader.email,
                "inventory_number": self.copy.inventory_number,
            },
        )

        self.assertEqual(issue_response.status_code, status.HTTP_201_CREATED)
        self.copy.refresh_from_db()
        self.assertEqual(self.copy.status, STATUS_BORROWED)

        return_response = self.client.post(
            reverse("library:loan-return"),
            {
                "inventory_number": self.copy.inventory_number,
                "status": STATUS_DAMAGED,
            },
        )

        self.assertEqual(return_response.status_code, status.HTTP_200_OK)
        loan = Loan.objects.get()
        self.assertIsNotNone(loan.returned_at)
        self.assertEqual(loan.returned_by, self.librarian)

    def test_reader_cannot_issue_book(self):
        """Тестирование запрета выдачи книги читателем."""
        self.client.force_authenticate(self.reader)

        response = self.client.post(
            reverse("library:loan-issue"),
            {
                "reader_email": self.reader.email,
                "inventory_number": self.copy.inventory_number,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unavailable_copy_cannot_be_issued(self):
        """Тестирование запрета выдачи недоступного экземпляра."""
        self.client.force_authenticate(self.librarian)

        response = self.client.post(
            reverse("library:loan-issue"),
            {
                "reader_email": self.reader.email,
                "inventory_number": self.unavailable_copy.inventory_number,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reader_sees_only_own_loans(self):
        """Тестирование просмотра читателем только своих выдач."""
        issue_book(self.reader.email, self.copy.inventory_number, self.librarian)
        self.client.force_authenticate(self.reader)

        response = self.client.get(reverse("library:loan-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_overdue_reader_cannot_get_another_book(self):
        """Тестирование запрета новой выдачи при просрочке."""
        Loan.objects.create(
            reader=self.reader,
            book_copy=self.copy,
            issued_by=self.librarian,
            due_at=timezone.now() - timedelta(days=1),
        )
        another_copy = BookCopy.objects.create(
            book=self.book,
            inventory_number="BOOK-003",
            status=STATUS_AVAILABLE,
        )

        with self.assertRaisesMessage(ValidationError, "просроченная книга"):
            issue_book(self.reader.email, another_copy.inventory_number, self.librarian)


class SubscriptionApiTests(LibraryDataMixin, APITestCase):
    """Тесты API подписок на книги."""

    def setUp(self):
        """Создание данных перед каждым тестом подписок."""
        self.create_data()
        self.client.force_authenticate(self.reader)

    def test_reader_can_subscribe_and_unsubscribe(self):
        """Тестирование создания и удаления подписки."""
        create_response = self.client.post(
            reverse("library:subscription-list"),
            {"book_id": self.unavailable_book.id},
        )

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        subscription_id = create_response.data["id"]

        delete_response = self.client.delete(
            reverse("library:subscription-detail", args=[subscription_id])
        )

        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_reader_cannot_subscribe_to_available_book(self):
        """Тестирование запрета подписки на доступную книгу."""
        response = self.client.post(
            reverse("library:subscription-list"),
            {"book_id": self.book.id},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_subscription_is_rejected(self):
        """Тестирование запрета повторной подписки на книгу."""
        AvailabilitySubscription.objects.create(
            reader=self.reader,
            book=self.unavailable_book,
        )

        response = self.client.post(
            reverse("library:subscription-list"),
            {"book_id": self.unavailable_book.id},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@override_settings(
    MAILERS={"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
)
class NotificationTaskTests(LibraryDataMixin, TestCase):
    """Тесты фоновых уведомлений читателей."""

    def setUp(self):
        """Создание данных перед тестом уведомления."""
        self.create_data()

    def test_notification_is_sent_once(self):
        """Тестирование однократной отправки уведомления."""
        subscription = AvailabilitySubscription.objects.create(
            reader=self.reader,
            book=self.book,
        )

        sent_count = send_availability_notifications(self.book.id)

        self.assertEqual(sent_count, 1)
        self.assertEqual(len(mail.outbox), 1)
        subscription.refresh_from_db()
        self.assertIsNotNone(subscription.notified_at)

        second_count = send_availability_notifications(self.book.id)
        self.assertEqual(second_count, 0)
