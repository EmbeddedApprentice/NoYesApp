from django.db import models


class NodeResponse(models.Model):
    session = models.ForeignKey(  # pyright: ignore[reportUnknownVariableType]
        "data.QuestionnaireSession",
        on_delete=models.CASCADE,
        related_name="responses",
    )
    node = models.ForeignKey(  # pyright: ignore[reportUnknownVariableType]
        "data.Node",
        on_delete=models.CASCADE,
        related_name="responses",
    )
    answer_given = models.CharField(  # pyright: ignore[reportUnknownVariableType]
        max_length=20,
        blank=True,
        default="",
    )
    order = models.PositiveIntegerField()  # pyright: ignore[reportUnknownVariableType]
    created_at = models.DateTimeField(auto_now_add=True)  # pyright: ignore[reportUnknownVariableType]

    class Meta:
        db_table = "node_responses"
        ordering = ["order"]
        constraints = [
            models.UniqueConstraint(
                fields=["session", "order"],
                name="unique_response_order_per_session",
            ),
        ]

    def __str__(self) -> str:
        return f"Response({self.session_id}, {self.node.slug}, {self.answer_given})"  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
