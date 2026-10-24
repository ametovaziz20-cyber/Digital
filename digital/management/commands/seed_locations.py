from django.core.management.base import BaseCommand
from digital.models import Region, City


class Command(BaseCommand):
    help = 'Создать пример региона и города для формы доставки'

    def handle(self, *args, **options):
        region, _ = Region.objects.get_or_create(name='Ташкент')
        City.objects.get_or_create(region=region, name='Ташкент')
        self.stdout.write(self.style.SUCCESS('Регион и город Ташкент готовы.'))
