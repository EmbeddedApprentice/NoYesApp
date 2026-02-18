from noyesapp.data.models import Questionnaire, QuestionnaireInvite
from noyesapp.data.models.user import User


def create_invite(
    questionnaire: Questionnaire, invited_user: User
) -> QuestionnaireInvite:
    """Create an invite for a user to a questionnaire. Idempotent (get_or_create)."""
    invite: QuestionnaireInvite
    invite, _ = QuestionnaireInvite.objects.get_or_create(  # pyright: ignore[reportUnknownMemberType]
        questionnaire=questionnaire,
        invited_user=invited_user,
    )
    return invite


def revoke_invite(invite: QuestionnaireInvite) -> None:
    """Delete an invite."""
    invite.delete()
