# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
# pyright: reportArgumentType=false, reportUnnecessaryComparison=false
import pytest
from django.test import Client
from django.urls import reverse

from noyesapp.actions.invites import create_invite
from noyesapp.actions.questionnaires import (
    activate_questionnaire,
    create_edge,
    create_node,
    create_questionnaire,
    set_start_node,
)
from noyesapp.data.models import Edge, Node, Questionnaire
from noyesapp.readers.questionnaires import (
    can_user_play_questionnaire,
    get_public_questionnaires,
)
from tests.factories import (
    UserFactory,
)

pytestmark = pytest.mark.django_db

AUTH_BACKEND = "noyesapp.backends.EmailBackend"


def _build_questionnaire(
    access_type: str, slug: str = "test-quiz"
) -> dict[str, object]:
    """Build a valid questionnaire with the given access type."""
    owner = UserFactory()
    q = create_questionnaire("Test Quiz", owner, slug=slug)
    question = create_node(q, "Is the sky blue?", Node.NodeType.QUESTION, slug="q1")
    yes_end = create_node(q, "Correct!", Node.NodeType.TERMINAL, slug="yes-end")
    no_end = create_node(q, "Wrong!", Node.NodeType.TERMINAL, slug="no-end")
    create_edge(question, yes_end, Edge.AnswerType.YES)
    create_edge(question, no_end, Edge.AnswerType.NO)
    set_start_node(q, question)
    if access_type != Questionnaire.AccessType.DRAFT:
        activate_questionnaire(q, access_type)
    return {"questionnaire": q, "owner": owner, "question": question}


# --- Reader unit tests ---


class TestCanUserPlayQuestionnaire:
    def test_draft_owner_can_play(self) -> None:
        data = _build_questionnaire(Questionnaire.AccessType.DRAFT)
        assert can_user_play_questionnaire(data["questionnaire"], data["owner"]) is True  # type: ignore[arg-type]

    def test_draft_other_user_denied(self) -> None:
        data = _build_questionnaire(Questionnaire.AccessType.DRAFT)
        other = UserFactory()
        assert can_user_play_questionnaire(data["questionnaire"], other) is False  # type: ignore[arg-type]

    def test_draft_anonymous_denied(self) -> None:
        data = _build_questionnaire(Questionnaire.AccessType.DRAFT)
        assert can_user_play_questionnaire(data["questionnaire"], None) is False  # type: ignore[arg-type]

    def test_public_owner_can_play(self) -> None:
        data = _build_questionnaire(Questionnaire.AccessType.PUBLIC)
        assert can_user_play_questionnaire(data["questionnaire"], data["owner"]) is True  # type: ignore[arg-type]

    def test_public_other_user_can_play(self) -> None:
        data = _build_questionnaire(Questionnaire.AccessType.PUBLIC)
        other = UserFactory()
        assert can_user_play_questionnaire(data["questionnaire"], other) is True  # type: ignore[arg-type]

    def test_public_anonymous_can_play(self) -> None:
        data = _build_questionnaire(Questionnaire.AccessType.PUBLIC)
        assert can_user_play_questionnaire(data["questionnaire"], None) is True  # type: ignore[arg-type]

    def test_private_owner_can_play(self) -> None:
        data = _build_questionnaire(Questionnaire.AccessType.PRIVATE)
        assert can_user_play_questionnaire(data["questionnaire"], data["owner"]) is True  # type: ignore[arg-type]

    def test_private_other_user_denied(self) -> None:
        data = _build_questionnaire(Questionnaire.AccessType.PRIVATE)
        other = UserFactory()
        assert can_user_play_questionnaire(data["questionnaire"], other) is False  # type: ignore[arg-type]

    def test_private_anonymous_denied(self) -> None:
        data = _build_questionnaire(Questionnaire.AccessType.PRIVATE)
        assert can_user_play_questionnaire(data["questionnaire"], None) is False  # type: ignore[arg-type]

    def test_invite_only_owner_can_play(self) -> None:
        data = _build_questionnaire(Questionnaire.AccessType.INVITE_ONLY)
        assert can_user_play_questionnaire(data["questionnaire"], data["owner"]) is True  # type: ignore[arg-type]

    def test_invite_only_invited_user_can_play(self) -> None:
        data = _build_questionnaire(Questionnaire.AccessType.INVITE_ONLY)
        invited = UserFactory()
        create_invite(data["questionnaire"], invited)  # type: ignore[arg-type]
        assert can_user_play_questionnaire(data["questionnaire"], invited) is True  # type: ignore[arg-type]

    def test_invite_only_uninvited_user_denied(self) -> None:
        data = _build_questionnaire(Questionnaire.AccessType.INVITE_ONLY)
        other = UserFactory()
        assert can_user_play_questionnaire(data["questionnaire"], other) is False  # type: ignore[arg-type]

    def test_invite_only_anonymous_denied(self) -> None:
        data = _build_questionnaire(Questionnaire.AccessType.INVITE_ONLY)
        assert can_user_play_questionnaire(data["questionnaire"], None) is False  # type: ignore[arg-type]


# --- View-level access control tests ---


class TestPlayerAccessControl:
    def test_public_anonymous_can_start(self, client: Client) -> None:
        _build_questionnaire(Questionnaire.AccessType.PUBLIC, slug="pub-ac")
        response = client.get(
            reverse("start_questionnaire", kwargs={"questionnaire_slug": "pub-ac"})
        )
        assert response.status_code == 302
        assert "/pub-ac/q1/" in response.url  # type: ignore[union-attr]

    def test_draft_anonymous_gets_403(self, client: Client) -> None:
        _build_questionnaire(Questionnaire.AccessType.DRAFT, slug="draft-ac")
        response = client.get(
            reverse("start_questionnaire", kwargs={"questionnaire_slug": "draft-ac"})
        )
        assert response.status_code == 403

    def test_draft_owner_can_start(self, client: Client) -> None:
        data = _build_questionnaire(Questionnaire.AccessType.DRAFT, slug="draft-own")
        client.force_login(data["owner"], backend=AUTH_BACKEND)  # type: ignore[arg-type]
        response = client.get(
            reverse("start_questionnaire", kwargs={"questionnaire_slug": "draft-own"})
        )
        assert response.status_code == 302
        assert "/draft-own/q1/" in response.url  # type: ignore[union-attr]

    def test_private_other_user_gets_403(self, client: Client) -> None:
        _build_questionnaire(Questionnaire.AccessType.PRIVATE, slug="priv-ac")
        other = UserFactory()
        client.force_login(other, backend=AUTH_BACKEND)
        response = client.get(
            reverse("start_questionnaire", kwargs={"questionnaire_slug": "priv-ac"})
        )
        assert response.status_code == 403

    def test_private_owner_can_start(self, client: Client) -> None:
        data = _build_questionnaire(Questionnaire.AccessType.PRIVATE, slug="priv-own")
        client.force_login(data["owner"], backend=AUTH_BACKEND)  # type: ignore[arg-type]
        response = client.get(
            reverse("start_questionnaire", kwargs={"questionnaire_slug": "priv-own"})
        )
        assert response.status_code == 302
        assert "/priv-own/q1/" in response.url  # type: ignore[union-attr]

    def test_invite_only_anonymous_redirects_to_login(self, client: Client) -> None:
        _build_questionnaire(Questionnaire.AccessType.INVITE_ONLY, slug="inv-anon")
        response = client.get(
            reverse("start_questionnaire", kwargs={"questionnaire_slug": "inv-anon"})
        )
        assert response.status_code == 302
        assert "/login/" in response.url  # type: ignore[union-attr]

    def test_invite_only_uninvited_gets_403(self, client: Client) -> None:
        _build_questionnaire(Questionnaire.AccessType.INVITE_ONLY, slug="inv-no")
        other = UserFactory()
        client.force_login(other, backend=AUTH_BACKEND)
        response = client.get(
            reverse("start_questionnaire", kwargs={"questionnaire_slug": "inv-no"})
        )
        assert response.status_code == 403

    def test_invite_only_invited_can_start(self, client: Client) -> None:
        data = _build_questionnaire(Questionnaire.AccessType.INVITE_ONLY, slug="inv-ok")
        invited = UserFactory()
        create_invite(data["questionnaire"], invited)  # type: ignore[arg-type]
        client.force_login(invited, backend=AUTH_BACKEND)
        response = client.get(
            reverse("start_questionnaire", kwargs={"questionnaire_slug": "inv-ok"})
        )
        assert response.status_code == 302
        assert "/inv-ok/q1/" in response.url  # type: ignore[union-attr]

    def test_play_node_access_denied(self, client: Client) -> None:
        _build_questionnaire(Questionnaire.AccessType.PRIVATE, slug="play-deny")
        other = UserFactory()
        client.force_login(other, backend=AUTH_BACKEND)
        response = client.get(
            reverse(
                "play_node",
                kwargs={"questionnaire_slug": "play-deny", "node_slug": "q1"},
            )
        )
        assert response.status_code == 403

    def test_answer_node_access_denied(self, client: Client) -> None:
        _build_questionnaire(Questionnaire.AccessType.PRIVATE, slug="ans-deny")
        other = UserFactory()
        client.force_login(other, backend=AUTH_BACKEND)
        response = client.post(
            reverse(
                "answer_node",
                kwargs={"questionnaire_slug": "ans-deny", "node_slug": "q1"},
            ),
            {"answer_type": "yes"},
        )
        assert response.status_code == 403

    def test_complete_access_denied(self, client: Client) -> None:
        _build_questionnaire(Questionnaire.AccessType.PRIVATE, slug="comp-deny")
        other = UserFactory()
        client.force_login(other, backend=AUTH_BACKEND)
        response = client.get(
            reverse(
                "complete_questionnaire",
                kwargs={"questionnaire_slug": "comp-deny"},
            )
        )
        assert response.status_code == 403


class TestLandingPageOnlyShowsPublic:
    def test_only_public_on_landing(self, client: Client) -> None:
        pub = _build_questionnaire(Questionnaire.AccessType.PUBLIC, slug="landing-pub")
        _build_questionnaire(Questionnaire.AccessType.PRIVATE, slug="landing-priv")
        _build_questionnaire(Questionnaire.AccessType.INVITE_ONLY, slug="landing-inv")
        _build_questionnaire(Questionnaire.AccessType.DRAFT, slug="landing-draft")
        qs = get_public_questionnaires()
        assert qs.count() == 1
        assert qs.first().pk == pub["questionnaire"].pk  # type: ignore[union-attr]
