from django.db import models


class Node(models.Model):
    class NodeType(models.TextChoices):
        QUESTION = "question", "Question"
        STATEMENT = "statement", "Statement"
        TERMINAL = "terminal", "Terminal"

    questionnaire = models.ForeignKey(  # pyright: ignore[reportUnknownVariableType]
        "data.Questionnaire",
        on_delete=models.CASCADE,
        related_name="nodes",
    )
    slug = models.SlugField(max_length=255)  # pyright: ignore[reportUnknownVariableType]
    content = models.TextField()  # pyright: ignore[reportUnknownVariableType]
    node_type = models.CharField(  # pyright: ignore[reportUnknownVariableType]
        max_length=20,
        choices=NodeType,
    )
    created_at = models.DateTimeField(auto_now_add=True)  # pyright: ignore[reportUnknownVariableType]
    updated_at = models.DateTimeField(auto_now=True)  # pyright: ignore[reportUnknownVariableType]

    class Meta:
        db_table = "nodes"
        constraints = [
            models.UniqueConstraint(
                fields=["questionnaire", "slug"],
                name="unique_node_slug_per_questionnaire",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.questionnaire.slug}/{self.slug}"  # pyright: ignore[reportUnknownMemberType]
