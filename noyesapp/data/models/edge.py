from django.db import models


class Edge(models.Model):
    class AnswerType(models.TextChoices):
        YES = "yes", "Yes"
        NO = "no", "No"
        NEXT = "next", "Next"

    source = models.ForeignKey(  # pyright: ignore[reportUnknownVariableType]
        "data.Node",
        on_delete=models.CASCADE,
        related_name="outgoing_edges",
    )
    destination = models.ForeignKey(  # pyright: ignore[reportUnknownVariableType]
        "data.Node",
        on_delete=models.CASCADE,
        related_name="incoming_edges",
    )
    answer_type = models.CharField(  # pyright: ignore[reportUnknownVariableType]
        max_length=20,
        choices=AnswerType,
    )
    created_at = models.DateTimeField(auto_now_add=True)  # pyright: ignore[reportUnknownVariableType]
    updated_at = models.DateTimeField(auto_now=True)  # pyright: ignore[reportUnknownVariableType]

    class Meta:
        db_table = "edges"
        constraints = [
            models.UniqueConstraint(
                fields=["source", "answer_type"],
                name="unique_answer_type_per_source",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.source} --{self.answer_type}--> {self.destination}"  # pyright: ignore[reportUnknownMemberType]
