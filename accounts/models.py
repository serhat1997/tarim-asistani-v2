import random
import secrets
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.user.username} profili"


class PasswordResetCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    @classmethod
    def create_for(cls, user):
        cls.objects.filter(user=user, is_used=False).delete()
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        token = secrets.token_urlsafe(32)
        return cls.objects.create(user=user, code=code, token=token)

    def is_valid(self):
        elapsed = (timezone.now() - self.created_at).total_seconds()
        return not self.is_used and elapsed < 600

    def __str__(self):
        return f"{self.user.username} — {self.code}"
