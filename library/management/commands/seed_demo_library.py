from django.core.management import call_command
from django.core.management.base import BaseCommand

from library.models import (
    Author,
    AvailabilitySubscription,
    Book,
    BookCopy,
    Genre,
    Loan,
)


class Command(BaseCommand):
    """Заполняет базу демонстрационными библиотечными данными."""

    help = "Удаляет старые данные библиотеки и создаёт демонстрационный каталог"

    def handle(self, *args, **options):
        """Очищает библиотечные таблицы и загружает фикстуру."""
        AvailabilitySubscription.objects.all().delete()
        Loan.objects.all().delete()
        BookCopy.objects.all().delete()
        Book.objects.all().delete()
        Author.objects.all().delete()
        Genre.objects.all().delete()

        call_command("loaddata", "demo_library.json")
