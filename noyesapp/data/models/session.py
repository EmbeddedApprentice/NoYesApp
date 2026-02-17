from django.conf import settings
from django.db import models


class QuestionnaireSession(models.Model):
    questionnaire = models.ForeignKey(  # pyright: ignore[reportUnknownVariableType]
        "data.Questionnaire",
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    user = models.ForeignKey(  # pyright: ignore[reportUnknownVariableType]
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="questionnaire_sessions",
    )
    session_key = models.CharField(max_length=40, blank=True, default="")  # pyright: ignore[reportUnknownVariableType]
    is_complete = models.BooleanField(default=False)  # pyright: ignore[reportUnknownVariableType]
    started_at = models.DateTimeField(auto_now_add=True)  # pyright: ignore[reportUnknownVariableType]
    completed_at = models.DateTimeField(null=True, blank=True)  # pyright: ignore[reportUnknownVariableType]

    class Meta:
        db_table = "questionnaire_sessions"
        ordering = ["-started_at"]

    def __str__(self) -> str:
        user_label = str(self.user) if self.user else "anonymous"  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
        return f"Session({self.questionnaire.slug}, {user_label})"  # pyright: ignore[reportUnknownMemberType]
