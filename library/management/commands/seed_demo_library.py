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
    help = "Удаляет старые данные библиотеки и создаёт демонстрационный каталог"

    def handle(self, *args, **options):
        AvailabilitySubscription.objects.all().delete()
        Loan.objects.all().delete()
        BookCopy.objects.all().delete()
        Book.objects.all().delete()
        Author.objects.all().delete()
        Genre.objects.all().delete()

        call_command("loaddata", "demo_library.json")
