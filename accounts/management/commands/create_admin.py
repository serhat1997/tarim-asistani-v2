from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Admin kullanicisi yoksa olusturur'

    def handle(self, *args, **options):
        if User.objects.filter(username='admin').exists():
            self.stdout.write('Admin kullanicisi zaten mevcut, atlandi.')
            return
        User.objects.create_superuser(
            username='admin',
            email='admin@admin.com',
            password='admin123',
        )
        self.stdout.write(self.style.SUCCESS('Admin kullanicisi basariyla olusturuldu.'))
