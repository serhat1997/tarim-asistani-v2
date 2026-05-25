from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Admin kullanicisi yoksa olusturur'

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(username='admin')
        user.email = 'admin@admin.com'
        user.is_staff = True
        user.is_superuser = True
        user.set_password('admin123')
        user.save()
        action = 'olusturuldu' if created else 'sifre guncellendi'
        self.stdout.write(self.style.SUCCESS(f'Admin kullanicisi {action}.'))
