# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
import pytest
from django.test import Client
from django.urls import reverse

from noyesapp.actions.invites import create_invite, revoke_invite
from noyesapp.actions.questionnaires import (
    activate_questionnaire,
    create_edge,
    create_node,
    create_questionnaire,
    set_start_node,
)
from noyesapp.data.models import Edge, Node, Questionnaire, QuestionnaireInvite
from noyesapp.readers.invites import get_invite_by_pk, get_questionnaire_invites
from tests.factories import (
    QuestionnaireFactory,
    QuestionnaireInviteFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db

AUTH_BACKEND = "noyesapp.backends.EmailBackend"


def _build_invite_only_questionnaire(slug: str = "inv-quiz") -> dict[str, object]:
    """Build a valid invite-only questionnaire."""
    owner = UserFactory()
    q = create_questionnaire("Invite Quiz", owner, slug=slug)
    question = create_node(q, "Yes?", Node.NodeType.QUESTION, slug="q1")
    yes_end = create_node(q, "Yes!", Node.NodeType.TERMINAL, slug="yes-end")
    no_end = create_node(q, "No!", Node.NodeType.TERMINAL, slug="no-end")
    create_edge(question, yes_end, Edge.AnswerType.YES)
    create_edge(question, no_end, Edge.AnswerType.NO)
    set_start_node(q, question)
    activate_questionnaire(q, Questionnaire.AccessType.INVITE_ONLY)
    return {"questionnaire": q, "owner": owner}


# --- Action tests ---


class TestCreateInvite:
    def test_creates_invite(self) -> None:
        q = QuestionnaireFactory()
        user = UserFactory()
        invite = create_invite(q, user)
        assert invite.questionnaire == q
        assert invite.invited_user == user

    def test_idempotent(self) -> None:
        q = QuestionnaireFactory()
        user = UserFactory()
        i1 = create_invite(q, user)
        i2 = create_invite(q, user)
        assert i1.pk == i2.pk
        assert QuestionnaireInvite.objects.count() == 1


class TestRevokeInvite:
    def test_deletes_invite(self) -> None:
        invite = QuestionnaireInviteFactory()
        pk = invite.pk
        revoke_invite(invite)
        assert not QuestionnaireInvite.objects.filter(pk=pk).exists()


class TestInviteConstraints:
    def test_unique_constraint(self) -> None:
        q = QuestionnaireFactory()
        user = UserFactory()
        QuestionnaireInviteFactory(questionnaire=q, invited_user=user)
        with pytest.raises(Exception):  # noqa: B017
            QuestionnaireInviteFactory(questionnaire=q, invited_user=user)

    def test_cascade_delete_questionnaire(self) -> None:
        invite = QuestionnaireInviteFactory()
        invite.questionnaire.delete()
        assert QuestionnaireInvite.objects.count() == 0

    def test_cascade_delete_user(self) -> None:
        invite = QuestionnaireInviteFactory()
        invite.invited_user.delete()
        assert QuestionnaireInvite.objects.count() == 0


# --- Reader tests ---


class TestInviteReaders:
    def test_get_questionnaire_invites(self) -> None:
        q = QuestionnaireFactory()
        user1 = UserFactory()
        user2 = UserFactory()
        create_invite(q, user1)
        create_invite(q, user2)
        invites = get_questionnaire_invites(q)
        assert invites.count() == 2

    def test_get_invite_by_pk(self) -> None:
        invite = QuestionnaireInviteFactory()
        found = get_invite_by_pk(invite.questionnaire, invite.pk)
        assert found.pk == invite.pk


# --- View tests ---


class TestManageInvitesView:
    def test_shows_invites_page(self, client: Client) -> None:
        data = _build_invite_only_questionnaire(slug="manage-inv")
        client.force_login(data["owner"], backend=AUTH_BACKEND)
        q = data["questionnaire"]
        response = client.get(
            reverse(
                "manage_invites",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": q.slug,
                },
            )
        )
        assert response.status_code == 200
        assert b"Manage Invites" in response.content

    def test_403_for_other_user(self, client: Client) -> None:
        data = _build_invite_only_questionnaire(slug="manage-403")
        other = UserFactory()
        client.force_login(other, backend=AUTH_BACKEND)
        q = data["questionnaire"]
        response = client.get(
            reverse(
                "manage_invites",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": q.slug,
                },
            )
        )
        assert response.status_code == 403


class TestAddInviteView:
    def test_add_invite_by_email(self, client: Client) -> None:
        data = _build_invite_only_questionnaire(slug="add-inv")
        invited = UserFactory(email="invited@example.com")
        client.force_login(data["owner"], backend=AUTH_BACKEND)
        q = data["questionnaire"]
        response = client.post(
            reverse(
                "add_invite",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": q.slug,
                },
            ),
            {"email": "invited@example.com"},
        )
        assert response.status_code == 302
        assert QuestionnaireInvite.objects.filter(
            questionnaire=q, invited_user=invited
        ).exists()

    def test_add_invite_nonexistent_email(self, client: Client) -> None:
        data = _build_invite_only_questionnaire(slug="add-inv-bad")
        client.force_login(data["owner"], backend=AUTH_BACKEND)
        q = data["questionnaire"]
        response = client.post(
            reverse(
                "add_invite",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": q.slug,
                },
            ),
            {"email": "nobody@example.com"},
        )
        assert response.status_code == 200
        assert b"No user found" in response.content

    def test_cannot_invite_self(self, client: Client) -> None:
        data = _build_invite_only_questionnaire(slug="add-inv-self")
        client.force_login(data["owner"], backend=AUTH_BACKEND)
        q = data["questionnaire"]
        response = client.post(
            reverse(
                "add_invite",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": q.slug,
                },
            ),
            {"email": data["owner"].email},
        )
        assert response.status_code == 200
        assert b"cannot invite yourself" in response.content


class TestRevokeInviteView:
    def test_revoke_invite(self, client: Client) -> None:
        data = _build_invite_only_questionnaire(slug="revoke-inv")
        invited = UserFactory()
        q = data["questionnaire"]
        invite = create_invite(q, invited)
        client.force_login(data["owner"], backend=AUTH_BACKEND)
        response = client.post(
            reverse(
                "revoke_invite",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": q.slug,
                    "invite_id": invite.pk,
                },
            )
        )
        assert response.status_code == 302
        assert not QuestionnaireInvite.objects.filter(pk=invite.pk).exists()
