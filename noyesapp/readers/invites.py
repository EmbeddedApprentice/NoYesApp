from django.db.models import QuerySet
from django.shortcuts import get_object_or_404

from noyesapp.data.models import Questionnaire, QuestionnaireInvite


def get_questionnaire_invites(
    questionnaire: Questionnaire,
) -> QuerySet[QuestionnaireInvite]:
    """Return all invites for a questionnaire with invited_user pre-loaded."""
    return QuestionnaireInvite.objects.filter(
        questionnaire=questionnaire,
    ).select_related("invited_user")


def get_invite_by_pk(
    questionnaire: Questionnaire, invite_pk: int
) -> QuestionnaireInvite:
    """Get an invite by PK, verifying it belongs to the given questionnaire."""
    return get_object_or_404(
        QuestionnaireInvite.objects.select_related("invited_user"),
        pk=invite_pk,
        questionnaire=questionnaire,
    )
