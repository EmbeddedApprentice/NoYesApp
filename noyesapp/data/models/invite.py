from django.conf import settings
from django.db import models


class QuestionnaireInvite(models.Model):
    questionnaire = models.ForeignKey(  # pyright: ignore[reportUnknownVariableType]
        "data.Questionnaire",
        on_delete=models.CASCADE,
        related_name="invites",
    )
    invited_user = models.ForeignKey(  # pyright: ignore[reportUnknownVariableType]
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="questionnaire_invites",
    )
    created_at = models.DateTimeField(auto_now_add=True)  # pyright: ignore[reportUnknownVariableType]

    class Meta:
        db_table = "questionnaire_invites"
        constraints = [
            models.UniqueConstraint(
                fields=["questionnaire", "invited_user"],
                name="unique_questionnaire_invite",
            ),
        ]

    def __str__(self) -> str:
        return f"Invite({self.questionnaire}, {self.invited_user})"  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
