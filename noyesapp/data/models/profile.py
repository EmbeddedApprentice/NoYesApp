from django.conf import settings
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(  # pyright: ignore[reportUnknownVariableType]
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    created_at = models.DateTimeField(auto_now_add=True)  # pyright: ignore[reportUnknownVariableType]
    updated_at = models.DateTimeField(auto_now=True)  # pyright: ignore[reportUnknownVariableType]

    class Meta:
        db_table = "profiles"

    def __str__(self) -> str:
        return f"Profile({self.user.username})"  # pyright: ignore[reportUnknownMemberType]
