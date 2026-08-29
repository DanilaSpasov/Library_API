from django.conf import settings
from django.db import models
from django.utils import timezone

STATUS_AVAILABLE = "available"
STATUS_BORROWED = "borrowed"
STATUS_DAMAGED = "damaged"
STATUS_MAINTENANCE = "maintenance"
STATUS_LOST = "lost"
STATUS_WITHDRAWN = "withdrawn"

BOOK_COPY_STATUS_CHOICES = (
    (STATUS_AVAILABLE, "Доступен"),
    (STATUS_BORROWED, "Выдан"),
    (STATUS_DAMAGED, "Повреждён"),
    (STATUS_MAINTENANCE, "На ремонте"),
    (STATUS_LOST, "Утерян"),
    (STATUS_WITHDRAWN, "Списан"),
)


class Author(models.Model):
    """Автор книги."""

    full_name = models.CharField(
        "Полное имя",
        max_length=255,
    )
    birth_date = models.DateField(
        "Дата рождения",
        null=True,
        blank=True,
    )
    biography = models.TextField(
        "Биография",
        blank=True,
    )

    class Meta:
        """Названия модели автора в админ-панели."""

        verbose_name = "Автор"
        verbose_name_plural = "Авторы"

    def __str__(self):
        """Возвращает полное имя автора."""
        return self.full_name


class Genre(models.Model):
    """Жанр книги."""

    name = models.CharField(
        "Название",
        max_length=100,
        unique=True,
    )
    description = models.TextField(
        "Описание",
        blank=True,
    )

    class Meta:
        """Названия модели жанра в админ-панели."""

        verbose_name = "Жанр"
        verbose_name_plural = "Жанры"

    def __str__(self):
        """Возвращает название жанра."""
        return self.name


class Book(models.Model):
    """Книга в библиотечном каталоге."""

    title = models.CharField(
        "Название",
        max_length=255,
    )
    isbn = models.CharField(
        "ISBN",
        max_length=17,
        unique=True,
        null=True,
        blank=True,
    )
    publication_year = models.PositiveSmallIntegerField(
        "Год публикации",
        null=True,
        blank=True,
    )
    description = models.TextField(
        "Описание",
        blank=True,
    )
    authors = models.ManyToManyField(
        Author,
        verbose_name="Авторы",
        related_name="books",
    )
    genres = models.ManyToManyField(
        Genre,
        verbose_name="Жанры",
        related_name="books",
    )
    is_active = models.BooleanField(
        "Активна",
        default=True,
    )

    class Meta:
        """Названия модели книги в админ-панели."""

        verbose_name = "Книга"
        verbose_name_plural = "Книги"

    def __str__(self):
        """Возвращает название книги."""
        return self.title


class BookCopy(models.Model):
    """Физический экземпляр книги."""

    book = models.ForeignKey(
        Book,
        verbose_name="Книга",
        on_delete=models.PROTECT,
        related_name="copies",
    )
    inventory_number = models.CharField(
        "Инвентарный номер",
        max_length=50,
        unique=True,
    )
    status = models.CharField(
        "Статус",
        max_length=20,
        choices=BOOK_COPY_STATUS_CHOICES,
        default=STATUS_AVAILABLE,
    )

    class Meta:
        """Названия модели экземпляра в админ-панели."""

        verbose_name = "Экземпляр книги"
        verbose_name_plural = "Экземпляры книг"

    def __str__(self):
        """Возвращает инвентарный номер и название книги."""
        return f"{self.inventory_number} — {self.book.title}"


class Loan(models.Model):
    """Выдача экземпляра книги читателю."""

    reader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Читатель",
        on_delete=models.PROTECT,
        related_name="loans",
    )
    book_copy = models.ForeignKey(
        BookCopy,
        verbose_name="Экземпляр книги",
        on_delete=models.PROTECT,
        related_name="loans",
    )
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Выдал",
        on_delete=models.PROTECT,
        related_name="issued_loans",
    )
    issued_at = models.DateTimeField(
        "Дата выдачи",
        auto_now_add=True,
    )
    due_at = models.DateTimeField("Срок возврата")
    returned_at = models.DateTimeField(
        "Дата возврата",
        null=True,
        blank=True,
    )
    returned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Принял возврат",
        on_delete=models.PROTECT,
        related_name="returned_loans",
        null=True,
        blank=True,
    )

    class Meta:
        """Названия и ограничения модели выдачи."""

        verbose_name = "Выдача"
        verbose_name_plural = "Выдачи"
        constraints = [
            models.UniqueConstraint(
                fields=["book_copy"],
                condition=models.Q(returned_at__isnull=True),
                name="unique_active_loan_per_copy",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        returned_at__isnull=True,
                        returned_by__isnull=True,
                    )
                    | models.Q(
                        returned_at__isnull=False,
                        returned_by__isnull=False,
                    )
                ),
                name="returned_at_and_returned_by_match",
            ),
        ]

    @property
    def is_active(self):
        """Показывает, что книга ещё не возвращена."""
        return self.returned_at is None

    @property
    def is_overdue(self):
        """Показывает, что активная выдача просрочена."""
        return self.is_active and self.due_at < timezone.now()

    def __str__(self):
        """Возвращает экземпляр и email читателя."""
        return f"{self.book_copy.inventory_number} — " f"{self.reader.email}"


class AvailabilitySubscription(models.Model):
    """Подписка читателя на появление доступной книги."""

    reader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Читатель",
        on_delete=models.PROTECT,
        related_name="availability_subscriptions",
    )
    book = models.ForeignKey(
        Book,
        verbose_name="Книга",
        on_delete=models.PROTECT,
        related_name="availability_subscriptions",
    )
    created_at = models.DateTimeField(
        "Дата создания",
        auto_now_add=True,
    )
    notified_at = models.DateTimeField(
        "Дата уведомления",
        null=True,
        blank=True,
    )

    class Meta:
        """Названия и ограничения модели подписки."""

        verbose_name = "Подписка на доступность"
        verbose_name_plural = "Подписки на доступность"
        constraints = [
            models.UniqueConstraint(
                fields=["reader", "book"],
                condition=models.Q(notified_at__isnull=True),
                name="unique_pending_subscription_per_reader_book",
            ),
        ]

    def __str__(self):
        """Возвращает читателя и название книги."""
        return f"{self.reader.email} — {self.book.title}"
