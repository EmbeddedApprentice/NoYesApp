from django.conf import settings
from django.db import models


class Questionnaire(models.Model):
    title = models.CharField(max_length=255)  # pyright: ignore[reportUnknownVariableType]
    slug = models.SlugField(unique=True, max_length=255)  # pyright: ignore[reportUnknownVariableType]
    description = models.TextField(blank=True, default="")  # pyright: ignore[reportUnknownVariableType]
    owner = models.ForeignKey(  # pyright: ignore[reportUnknownVariableType]
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="questionnaires",
    )
    is_published = models.BooleanField(default=False)  # pyright: ignore[reportUnknownVariableType]
    start_node = models.ForeignKey(  # pyright: ignore[reportUnknownVariableType]
        "data.Node",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    created_at = models.DateTimeField(auto_now_add=True)  # pyright: ignore[reportUnknownVariableType]
    updated_at = models.DateTimeField(auto_now=True)  # pyright: ignore[reportUnknownVariableType]

    class Meta:
        db_table = "questionnaires"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return str(self.title)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
