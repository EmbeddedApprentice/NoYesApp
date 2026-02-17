from django.utils.text import slugify

from noyesapp.data.models import Edge, Node, Questionnaire
from noyesapp.data.models.user import User


def generate_unique_questionnaire_slug(title: str) -> str:
    """Generate a unique questionnaire slug from title, appending counter if needed."""
    base_slug = slugify(title) or "questionnaire"
    slug = base_slug
    counter = 1
    while Questionnaire.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def generate_unique_node_slug(questionnaire: Questionnaire, content: str) -> str:
    """Generate a unique node slug within a questionnaire, from content."""
    base_slug = slugify(content)[:50] or "node"
    slug = base_slug
    counter = 1
    while Node.objects.filter(questionnaire=questionnaire, slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def create_questionnaire(
    title: str,
    owner: User,
    description: str = "",
    slug: str | None = None,
) -> Questionnaire:
    """Create a new questionnaire with auto-generated slug if not provided."""
    if slug is None:
        slug = generate_unique_questionnaire_slug(title)
    questionnaire: Questionnaire = Questionnaire.objects.create(
        title=title,
        slug=slug,
        description=description,
        owner=owner,
    )
    return questionnaire


def create_node(
    questionnaire: Questionnaire,
    content: str,
    node_type: str,
    slug: str | None = None,
) -> Node:
    """Create a new node within a questionnaire."""
    valid_types = {choice.value for choice in Node.NodeType}
    if node_type not in valid_types:
        raise ValueError(
            f"Invalid node_type '{node_type}'. Must be one of: {valid_types}"
        )
    if slug is None:
        slug = generate_unique_node_slug(questionnaire, content)
    node: Node = Node.objects.create(
        questionnaire=questionnaire,
        slug=slug,
        content=content,
        node_type=node_type,
    )
    return node


def create_edge(
    source: Node,
    destination: Node,
    answer_type: str,
) -> Edge:
    """Create an edge between two nodes. Both must belong to the same questionnaire."""
    valid_types = {choice.value for choice in Edge.AnswerType}
    if answer_type not in valid_types:
        raise ValueError(
            f"Invalid answer_type '{answer_type}'. Must be one of: {valid_types}"
        )
    if source.questionnaire_id != destination.questionnaire_id:  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
        raise ValueError(
            "Source and destination nodes must belong to the same questionnaire."
        )
    edge: Edge = Edge.objects.create(
        source=source,
        destination=destination,
        answer_type=answer_type,
    )
    return edge


def set_start_node(questionnaire: Questionnaire, node: Node) -> Questionnaire:
    """Set the start node for a questionnaire. Node must belong to the questionnaire."""
    if node.questionnaire_id != questionnaire.pk:  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
        raise ValueError("Node does not belong to this questionnaire.")
    questionnaire.start_node = node  # pyright: ignore[reportAttributeAccessIssue]
    questionnaire.save(update_fields=["start_node", "updated_at"])
    return questionnaire


def validate_node_edges(node: Node) -> list[str]:
    """Validate edges for a single node based on its type."""
    errors: list[str] = []
    outgoing: list[Edge] = list(node.outgoing_edges.all())  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUnknownArgumentType]
    edge_types = {e.answer_type for e in outgoing}  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType]

    if node.node_type == Node.NodeType.QUESTION:  # pyright: ignore[reportUnknownMemberType]
        if len(outgoing) != 2:
            errors.append(
                f"Question node '{node.slug}' must have exactly 2 edges (YES and NO)."  # pyright: ignore[reportUnknownMemberType]
            )
        if Edge.AnswerType.YES not in edge_types:
            errors.append(f"Question node '{node.slug}' is missing a YES edge.")  # pyright: ignore[reportUnknownMemberType]
        if Edge.AnswerType.NO not in edge_types:
            errors.append(f"Question node '{node.slug}' is missing a NO edge.")  # pyright: ignore[reportUnknownMemberType]
    elif node.node_type == Node.NodeType.STATEMENT:  # pyright: ignore[reportUnknownMemberType]
        if len(outgoing) != 1:
            errors.append(
                f"Statement node '{node.slug}' must have exactly 1 edge (NEXT)."  # pyright: ignore[reportUnknownMemberType]
            )
        if outgoing and Edge.AnswerType.NEXT not in edge_types:
            errors.append(f"Statement node '{node.slug}' must have a NEXT edge.")  # pyright: ignore[reportUnknownMemberType]
    elif node.node_type == Node.NodeType.TERMINAL:  # pyright: ignore[reportUnknownMemberType]
        if len(outgoing) != 0:
            errors.append(f"Terminal node '{node.slug}' must have no outgoing edges.")  # pyright: ignore[reportUnknownMemberType]

    return errors


def validate_questionnaire_graph(questionnaire: Questionnaire) -> list[str]:
    """Validate the entire questionnaire graph. Returns list of error strings."""
    errors: list[str] = []

    if questionnaire.start_node is None:  # pyright: ignore[reportUnknownMemberType]
        errors.append("Questionnaire must have a start node.")

    nodes = questionnaire.nodes.prefetch_related("outgoing_edges").all()  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUnknownVariableType]
    for node in nodes:  # pyright: ignore[reportUnknownVariableType]
        errors.extend(validate_node_edges(node))  # pyright: ignore[reportUnknownArgumentType]

    return errors


def publish_questionnaire(questionnaire: Questionnaire) -> Questionnaire:
    """Publish a questionnaire after validating its graph."""
    errors = validate_questionnaire_graph(questionnaire)
    if errors:
        raise ValueError(f"Cannot publish questionnaire: {'; '.join(errors)}")
    questionnaire.is_published = True  # pyright: ignore[reportAttributeAccessIssue]
    questionnaire.save(update_fields=["is_published", "updated_at"])
    return questionnaire


def unpublish_questionnaire(questionnaire: Questionnaire) -> Questionnaire:
    """Unpublish a questionnaire."""
    questionnaire.is_published = False  # pyright: ignore[reportAttributeAccessIssue]
    questionnaire.save(update_fields=["is_published", "updated_at"])
    return questionnaire


def update_questionnaire(
    questionnaire: Questionnaire,
    title: str | None = None,
    description: str | None = None,
) -> Questionnaire:
    """Update questionnaire fields."""
    update_fields: list[str] = ["updated_at"]
    if title is not None:
        questionnaire.title = title  # pyright: ignore[reportAttributeAccessIssue]
        update_fields.append("title")
    if description is not None:
        questionnaire.description = description  # pyright: ignore[reportAttributeAccessIssue]
        update_fields.append("description")
    questionnaire.save(update_fields=update_fields)
    return questionnaire


def delete_questionnaire(questionnaire: Questionnaire) -> None:
    """Delete a questionnaire and all its nodes/edges (via CASCADE)."""
    questionnaire.delete()


def update_node(
    node: Node,
    content: str | None = None,
    node_type: str | None = None,
) -> Node:
    """Update node fields."""
    update_fields: list[str] = ["updated_at"]
    if content is not None:
        node.content = content  # pyright: ignore[reportAttributeAccessIssue]
        update_fields.append("content")
    if node_type is not None:
        valid_types = {choice.value for choice in Node.NodeType}
        if node_type not in valid_types:
            raise ValueError(
                f"Invalid node_type '{node_type}'. Must be one of: {valid_types}"
            )
        node.node_type = node_type  # pyright: ignore[reportAttributeAccessIssue]
        update_fields.append("node_type")
    node.save(update_fields=update_fields)
    return node


def delete_node(node: Node) -> None:
    """Delete a node and its edges (via CASCADE).

    Also clears start_node on the questionnaire if this was the start node.
    """
    questionnaire = node.questionnaire  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    if questionnaire.start_node_id == node.pk:  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue]
        questionnaire.start_node = None  # pyright: ignore[reportAttributeAccessIssue]
        questionnaire.save(update_fields=["start_node", "updated_at"])  # pyright: ignore[reportUnknownMemberType]
    node.delete()


def delete_edge(edge: Edge) -> None:
    """Delete an edge."""
    edge.delete()
