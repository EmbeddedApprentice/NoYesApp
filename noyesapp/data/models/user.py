from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model with email-based login and slug for URLs."""

    email = models.EmailField(unique=True)  # pyright: ignore[reportUnknownVariableType]
    slug = models.SlugField(unique=True, max_length=150)  # pyright: ignore[reportUnknownVariableType]

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        db_table = "users"

    def __str__(self) -> str:
        return str(self.username)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
