from django.utils import timezone

from noyesapp.data.models import Node, NodeResponse, Questionnaire, QuestionnaireSession
from noyesapp.data.models.user import User


def start_session(
    questionnaire: Questionnaire,
    user: User | None = None,
    session_key: str = "",
) -> QuestionnaireSession:
    """Start a new questionnaire session. Records the first node visit."""
    session: QuestionnaireSession = QuestionnaireSession.objects.create(
        questionnaire=questionnaire,
        user=user,
        session_key=session_key,
    )
    if questionnaire.start_node is not None:  # pyright: ignore[reportUnknownMemberType]
        record_node_visit(session, questionnaire.start_node)  # pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType]
    return session


def record_node_visit(
    session: QuestionnaireSession,
    node: Node,
    answer_given: str = "",
) -> NodeResponse:
    """Record a visit to a node in the session. Order is auto-incremented."""
    last_order = (
        NodeResponse.objects.filter(session=session)
        .order_by("-order")
        .values_list("order", flat=True)
        .first()
    )
    next_order: int = (last_order or 0) + 1  # pyright: ignore[reportOperatorIssue]
    response: NodeResponse = NodeResponse.objects.create(
        session=session,
        node=node,
        answer_given=answer_given,
        order=next_order,
    )
    return response


def record_answer_and_advance(
    session: QuestionnaireSession,
    current_node: Node,
    answer_type: str,
    destination_node: Node,
) -> NodeResponse:
    """Record the answer on the current node, then record visiting the destination."""
    # Update the last response with the answer given
    last_response = (
        NodeResponse.objects.filter(session=session, node=current_node)
        .order_by("-order")
        .first()
    )
    if last_response is not None:
        last_response.answer_given = answer_type  # pyright: ignore[reportAttributeAccessIssue]
        last_response.save(update_fields=["answer_given"])

    # Record the visit to the destination node
    return record_node_visit(session, destination_node)


def complete_session(session: QuestionnaireSession) -> QuestionnaireSession:
    """Mark a session as complete."""
    session.is_complete = True  # pyright: ignore[reportAttributeAccessIssue]
    session.completed_at = timezone.now()  # pyright: ignore[reportAttributeAccessIssue]
    session.save(update_fields=["is_complete", "completed_at"])
    return session


def get_or_create_active_session(
    questionnaire: Questionnaire,
    user: User | None = None,
    session_key: str = "",
) -> QuestionnaireSession:
    """Get an existing incomplete session or start a new one."""
    filters: dict[str, object] = {
        "questionnaire": questionnaire,
        "is_complete": False,
    }
    if user is not None:
        filters["user"] = user
    else:
        filters["session_key"] = session_key

    existing = (
        QuestionnaireSession.objects.filter(**filters).order_by("-started_at").first()
    )
    if existing is not None:
        return existing

    return start_session(questionnaire, user=user, session_key=session_key)
