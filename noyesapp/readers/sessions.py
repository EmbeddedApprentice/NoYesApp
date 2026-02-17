from django.db.models import QuerySet

from noyesapp.data.models import NodeResponse, QuestionnaireSession
from noyesapp.data.models.user import User


def get_session_responses(session: QuestionnaireSession) -> QuerySet[NodeResponse]:
    """Get all responses for a session, ordered by path order."""
    return (
        NodeResponse.objects.filter(session=session)
        .select_related("node")
        .order_by("order")
    )


def get_session_current_node_response(
    session: QuestionnaireSession,
) -> NodeResponse | None:
    """Get the most recent response (current position) in a session."""
    return (
        NodeResponse.objects.filter(session=session)
        .select_related("node")
        .order_by("-order")
        .first()
    )


def get_user_completed_sessions(user: User) -> QuerySet[QuestionnaireSession]:
    """Get all completed sessions for a user."""
    return (
        QuestionnaireSession.objects.filter(user=user, is_complete=True)
        .select_related("questionnaire")
        .order_by("-completed_at")
    )
