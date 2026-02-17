from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from noyesapp.data.models import Edge, Node, Questionnaire
from noyesapp.data.models.user import User


def get_questionnaire_by_slug(slug: str) -> Questionnaire:
    """Retrieve a questionnaire by slug with owner and start_node pre-loaded."""
    return get_object_or_404(
        Questionnaire.objects.select_related("owner", "start_node"),
        slug=slug,
    )


def get_published_questionnaires() -> QuerySet[Questionnaire]:
    """Return all published questionnaires."""
    return Questionnaire.objects.filter(is_published=True).select_related("owner")


def get_user_questionnaires(owner: User) -> QuerySet[Questionnaire]:
    """Return all questionnaires owned by a user."""
    return Questionnaire.objects.filter(owner=owner).select_related("owner")


def get_node_by_slugs(questionnaire_slug: str, node_slug: str) -> Node:
    """Retrieve a node by questionnaire slug and node slug (URL resolution)."""
    return get_object_or_404(
        Node.objects.select_related("questionnaire"),
        questionnaire__slug=questionnaire_slug,
        slug=node_slug,
    )


def get_node_with_edges(node: Node) -> Node:
    """Return a node with outgoing edges and their destinations prefetched."""
    return Node.objects.prefetch_related("outgoing_edges__destination").get(pk=node.pk)


def get_questionnaire_nodes(questionnaire: Questionnaire) -> QuerySet[Node]:
    """Return all nodes for a questionnaire with edges prefetched."""
    return Node.objects.filter(questionnaire=questionnaire).prefetch_related(
        "outgoing_edges", "outgoing_edges__destination"
    )


def get_outgoing_edges(node: Node) -> QuerySet[Edge]:
    """Return all outgoing edges for a node with destinations pre-loaded."""
    return Edge.objects.filter(source=node).select_related("destination")


def get_questionnaire_for_owner(slug: str, owner: User) -> Questionnaire:
    """Get a questionnaire by slug, verifying ownership. 404 if not found or not owned."""
    return get_object_or_404(
        Questionnaire.objects.select_related("owner", "start_node"),
        slug=slug,
        owner=owner,
    )


def get_node_for_questionnaire(questionnaire: Questionnaire, node_slug: str) -> Node:
    """Get a node by slug within a specific questionnaire. 404 if not found."""
    return get_object_or_404(
        Node.objects.select_related("questionnaire").prefetch_related(
            "outgoing_edges", "outgoing_edges__destination"
        ),
        questionnaire=questionnaire,
        slug=node_slug,
    )


def get_edge_for_node(node: Node, edge_pk: int) -> Edge:
    """Get an edge by PK, verifying it belongs to the given node."""
    return get_object_or_404(
        Edge.objects.select_related("source", "destination"),
        pk=edge_pk,
        source=node,
    )


def get_destination_for_answer(node: Node, answer_type: str) -> Node:
    """Get the destination node for a given answer type. Used by the player."""
    edge = get_object_or_404(
        Edge.objects.select_related("destination"),
        source=node,
        answer_type=answer_type,
    )
    destination: Node = edge.destination  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType, reportAssignmentType]
    return destination  # pyright: ignore[reportUnknownVariableType]
