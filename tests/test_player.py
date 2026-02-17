# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
# pyright: reportArgumentType=false
import pytest
from django.test import Client
from django.urls import reverse

from noyesapp.actions.questionnaires import (
    create_edge,
    create_node,
    create_questionnaire,
    publish_questionnaire,
    set_start_node,
)
from noyesapp.actions.sessions import (
    complete_session,
    get_or_create_active_session,
    record_answer_and_advance,
    record_node_visit,
    start_session,
)
from noyesapp.data.models import Edge, Node, NodeResponse, QuestionnaireSession
from noyesapp.readers.sessions import (
    get_session_current_node_response,
    get_session_responses,
    get_user_completed_sessions,
)
from tests.factories import (
    NodeFactory,
    QuestionnaireFactory,
    QuestionnaireSessionFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


def _build_published_questionnaire(
    slug: str = "test-quiz",
) -> dict[str, object]:
    """Build a minimal published questionnaire: question -> (yes: terminal, no: terminal).

    Returns dict with keys: questionnaire, question, yes_end, no_end, owner.
    """
    owner = UserFactory()
    q = create_questionnaire("Test Quiz", owner, slug=slug)
    question = create_node(q, "Is the sky blue?", Node.NodeType.QUESTION, slug="q1")
    yes_end = create_node(q, "Correct!", Node.NodeType.TERMINAL, slug="yes-end")
    no_end = create_node(q, "Wrong!", Node.NodeType.TERMINAL, slug="no-end")
    create_edge(question, yes_end, Edge.AnswerType.YES)
    create_edge(question, no_end, Edge.AnswerType.NO)
    set_start_node(q, question)
    publish_questionnaire(q)
    return {
        "questionnaire": q,
        "question": question,
        "yes_end": yes_end,
        "no_end": no_end,
        "owner": owner,
    }


def _build_multi_step_questionnaire(
    slug: str = "multi-quiz",
) -> dict[str, object]:
    """Build a multi-step questionnaire: statement -> question -> terminals.

    Returns dict with keys: questionnaire, statement, question, yes_end, no_end, owner.
    """
    owner = UserFactory()
    q = create_questionnaire("Multi Quiz", owner, slug=slug)
    statement = create_node(q, "Welcome!", Node.NodeType.STATEMENT, slug="welcome")
    question = create_node(q, "Do you like it?", Node.NodeType.QUESTION, slug="q1")
    yes_end = create_node(q, "Great!", Node.NodeType.TERMINAL, slug="yes-end")
    no_end = create_node(q, "Sorry!", Node.NodeType.TERMINAL, slug="no-end")
    create_edge(statement, question, Edge.AnswerType.NEXT)
    create_edge(question, yes_end, Edge.AnswerType.YES)
    create_edge(question, no_end, Edge.AnswerType.NO)
    set_start_node(q, statement)
    publish_questionnaire(q)
    return {
        "questionnaire": q,
        "statement": statement,
        "question": question,
        "yes_end": yes_end,
        "no_end": no_end,
        "owner": owner,
    }


# --- Session/Response Model Tests ---


class TestQuestionnaireSessionModel:
    def test_create_session(self) -> None:
        session = QuestionnaireSessionFactory()
        assert session.questionnaire is not None
        assert session.user is not None
        assert session.is_complete is False
        assert session.completed_at is None

    def test_str_with_user(self) -> None:
        user = UserFactory(username="alice")
        q = QuestionnaireFactory(slug="quiz")
        session = QuestionnaireSessionFactory(questionnaire=q, user=user)
        assert str(session) == "Session(quiz, alice)"

    def test_str_anonymous(self) -> None:
        q = QuestionnaireFactory(slug="quiz")
        session = QuestionnaireSessionFactory(
            questionnaire=q, user=None, session_key="abc123"
        )
        assert str(session) == "Session(quiz, anonymous)"

    def test_cascade_delete_questionnaire(self) -> None:
        session = QuestionnaireSessionFactory()
        session.questionnaire.delete()
        assert QuestionnaireSession.objects.count() == 0

    def test_cascade_delete_user(self) -> None:
        session = QuestionnaireSessionFactory()
        session.user.delete()
        assert QuestionnaireSession.objects.count() == 0


class TestNodeResponseModel:
    def test_create_response(self) -> None:
        q = QuestionnaireFactory()
        node = NodeFactory(questionnaire=q)
        session = QuestionnaireSessionFactory(questionnaire=q)
        response = NodeResponse.objects.create(session=session, node=node, order=1)
        assert response.order == 1
        assert response.answer_given == ""

    def test_ordering(self) -> None:
        q = QuestionnaireFactory()
        n1 = NodeFactory(questionnaire=q)
        n2 = NodeFactory(questionnaire=q)
        session = QuestionnaireSessionFactory(questionnaire=q)
        NodeResponse.objects.create(session=session, node=n2, order=2)
        NodeResponse.objects.create(session=session, node=n1, order=1)
        responses = list(NodeResponse.objects.filter(session=session))
        assert responses[0].order == 1
        assert responses[1].order == 2

    def test_unique_order_per_session(self) -> None:
        q = QuestionnaireFactory()
        node = NodeFactory(questionnaire=q)
        session = QuestionnaireSessionFactory(questionnaire=q)
        NodeResponse.objects.create(session=session, node=node, order=1)
        with pytest.raises(Exception):  # noqa: B017
            NodeResponse.objects.create(session=session, node=node, order=1)


# --- Session Action Tests ---


class TestStartSession:
    def test_start_session_with_user(self) -> None:
        data = _build_published_questionnaire()
        user = UserFactory()
        session = start_session(data["questionnaire"], user=user)  # type: ignore[arg-type]
        assert session.user == user
        assert session.is_complete is False
        # Should have recorded the start node visit
        assert NodeResponse.objects.filter(session=session).count() == 1

    def test_start_session_anonymous(self) -> None:
        data = _build_published_questionnaire()
        session = start_session(data["questionnaire"], session_key="test-key")  # type: ignore[arg-type]
        assert session.user is None
        assert session.session_key == "test-key"

    def test_start_session_records_start_node(self) -> None:
        data = _build_published_questionnaire()
        session = start_session(data["questionnaire"])  # type: ignore[arg-type]
        response = NodeResponse.objects.get(session=session)
        assert response.node == data["question"]
        assert response.order == 1


class TestRecordNodeVisit:
    def test_auto_increments_order(self) -> None:
        data = _build_published_questionnaire()
        session = start_session(data["questionnaire"])  # type: ignore[arg-type]
        # Start already recorded order=1, now record order=2
        r2 = record_node_visit(session, data["yes_end"])  # type: ignore[arg-type]
        assert r2.order == 2


class TestRecordAnswerAndAdvance:
    def test_records_answer_and_next_visit(self) -> None:
        data = _build_published_questionnaire()
        session = start_session(data["questionnaire"])  # type: ignore[arg-type]
        response = record_answer_and_advance(
            session,
            data["question"],  # type: ignore[arg-type]
            Edge.AnswerType.YES,
            data["yes_end"],  # type: ignore[arg-type]
        )
        # The answer should be recorded on the question response
        question_response = NodeResponse.objects.get(
            session=session, node=data["question"]
        )
        assert question_response.answer_given == Edge.AnswerType.YES
        # New response for yes_end
        assert response.node == data["yes_end"]
        assert response.order == 2


class TestCompleteSession:
    def test_marks_complete(self) -> None:
        session = QuestionnaireSessionFactory()
        complete_session(session)
        session.refresh_from_db()
        assert session.is_complete is True
        assert session.completed_at is not None


class TestGetOrCreateActiveSession:
    def test_creates_new_session(self) -> None:
        data = _build_published_questionnaire()
        user = UserFactory()
        session = get_or_create_active_session(data["questionnaire"], user=user)  # type: ignore[arg-type]
        assert session.user == user
        assert session.is_complete is False

    def test_returns_existing_session(self) -> None:
        data = _build_published_questionnaire()
        user = UserFactory()
        s1 = get_or_create_active_session(data["questionnaire"], user=user)  # type: ignore[arg-type]
        s2 = get_or_create_active_session(data["questionnaire"], user=user)  # type: ignore[arg-type]
        assert s1.pk == s2.pk

    def test_creates_new_after_complete(self) -> None:
        data = _build_published_questionnaire()
        user = UserFactory()
        s1 = get_or_create_active_session(data["questionnaire"], user=user)  # type: ignore[arg-type]
        complete_session(s1)
        s2 = get_or_create_active_session(data["questionnaire"], user=user)  # type: ignore[arg-type]
        assert s1.pk != s2.pk

    def test_anonymous_by_session_key(self) -> None:
        data = _build_published_questionnaire()
        s1 = get_or_create_active_session(
            data["questionnaire"],
            session_key="key-1",  # type: ignore[arg-type]
        )
        s2 = get_or_create_active_session(
            data["questionnaire"],
            session_key="key-1",  # type: ignore[arg-type]
        )
        assert s1.pk == s2.pk


# --- Session Reader Tests ---


class TestSessionReaders:
    def test_get_session_responses(self) -> None:
        data = _build_published_questionnaire()
        session = start_session(data["questionnaire"])  # type: ignore[arg-type]
        record_answer_and_advance(
            session,
            data["question"],  # type: ignore[arg-type]
            Edge.AnswerType.YES,
            data["yes_end"],  # type: ignore[arg-type]
        )
        responses = get_session_responses(session)
        assert responses.count() == 2

    def test_get_session_current_node_response(self) -> None:
        data = _build_published_questionnaire()
        session = start_session(data["questionnaire"])  # type: ignore[arg-type]
        current = get_session_current_node_response(session)
        assert current is not None
        assert current.node == data["question"]

    def test_get_user_completed_sessions(self) -> None:
        user = UserFactory()
        s1 = QuestionnaireSessionFactory(user=user)
        QuestionnaireSessionFactory(user=user)  # not completed
        complete_session(s1)
        completed = get_user_completed_sessions(user)
        assert completed.count() == 1
        assert completed.first() == s1


# --- Player View Tests ---


class TestStartQuestionnaireView:
    def test_redirects_to_start_node(self, client: Client) -> None:
        _build_published_questionnaire(slug="play-quiz")
        response = client.get(
            reverse("start_questionnaire", kwargs={"questionnaire_slug": "play-quiz"})
        )
        assert response.status_code == 302
        assert "/play-quiz/q1/" in response.url  # type: ignore[union-attr]

    def test_404_for_nonexistent(self, client: Client) -> None:
        response = client.get(
            reverse("start_questionnaire", kwargs={"questionnaire_slug": "nonexistent"})
        )
        assert response.status_code == 404

    def test_error_for_no_start_node(self, client: Client) -> None:
        QuestionnaireFactory(slug="no-start", is_published=True)
        response = client.get(
            reverse("start_questionnaire", kwargs={"questionnaire_slug": "no-start"})
        )
        assert response.status_code == 200
        assert b"no start node" in response.content

    def test_creates_session_for_authenticated_user(self, client: Client) -> None:
        data = _build_published_questionnaire(slug="auth-quiz")
        user = UserFactory()
        client.force_login(user, backend="noyesapp.backends.EmailBackend")
        client.get(
            reverse("start_questionnaire", kwargs={"questionnaire_slug": "auth-quiz"})
        )
        assert QuestionnaireSession.objects.filter(
            questionnaire=data["questionnaire"], user=user
        ).exists()


class TestPlayNodeView:
    def test_displays_question_node(self, client: Client) -> None:
        _build_published_questionnaire(slug="node-quiz")
        response = client.get(
            reverse(
                "play_node",
                kwargs={"questionnaire_slug": "node-quiz", "node_slug": "q1"},
            )
        )
        assert response.status_code == 200
        assert b"Is the sky blue?" in response.content

    def test_displays_yes_no_buttons_for_question(self, client: Client) -> None:
        _build_published_questionnaire(slug="btn-quiz")
        response = client.get(
            reverse(
                "play_node",
                kwargs={"questionnaire_slug": "btn-quiz", "node_slug": "q1"},
            )
        )
        assert b"Yes" in response.content
        assert b"No" in response.content

    def test_displays_terminal_node(self, client: Client) -> None:
        _build_published_questionnaire(slug="term-quiz")
        response = client.get(
            reverse(
                "play_node",
                kwargs={"questionnaire_slug": "term-quiz", "node_slug": "yes-end"},
            )
        )
        assert response.status_code == 200
        assert b"Correct!" in response.content
        assert b"View Results" in response.content

    def test_404_for_nonexistent_node(self, client: Client) -> None:
        _build_published_questionnaire(slug="miss-quiz")
        response = client.get(
            reverse(
                "play_node",
                kwargs={"questionnaire_slug": "miss-quiz", "node_slug": "nope"},
            )
        )
        assert response.status_code == 404

    def test_statement_node_shows_next_button(self, client: Client) -> None:
        _build_multi_step_questionnaire(slug="stmt-quiz")
        response = client.get(
            reverse(
                "play_node",
                kwargs={"questionnaire_slug": "stmt-quiz", "node_slug": "welcome"},
            )
        )
        assert b"Next" in response.content
        assert b"Welcome!" in response.content


class TestNodePartialView:
    def test_returns_partial(self, client: Client) -> None:
        _build_published_questionnaire(slug="partial-quiz")
        response = client.get(
            reverse(
                "node_partial",
                kwargs={"questionnaire_slug": "partial-quiz", "node_slug": "q1"},
            )
        )
        assert response.status_code == 200
        assert b"Is the sky blue?" in response.content
        # Should be a partial (no full HTML wrapper)
        assert b"<!DOCTYPE" not in response.content


class TestAnswerNodeView:
    def test_answer_yes_redirects_to_terminal(self, client: Client) -> None:
        _build_published_questionnaire(slug="ans-quiz")
        response = client.post(
            reverse(
                "answer_node",
                kwargs={"questionnaire_slug": "ans-quiz", "node_slug": "q1"},
            ),
            {"answer_type": "yes"},
        )
        # Terminal should redirect to complete page
        assert response.status_code == 302
        assert "/ans-quiz/complete/" in response.url  # type: ignore[union-attr]

    def test_answer_no_redirects_to_terminal(self, client: Client) -> None:
        _build_published_questionnaire(slug="no-quiz")
        response = client.post(
            reverse(
                "answer_node",
                kwargs={"questionnaire_slug": "no-quiz", "node_slug": "q1"},
            ),
            {"answer_type": "no"},
        )
        assert response.status_code == 302
        assert "/no-quiz/complete/" in response.url  # type: ignore[union-attr]

    def test_answer_next_on_statement(self, client: Client) -> None:
        _build_multi_step_questionnaire(slug="next-quiz")
        response = client.post(
            reverse(
                "answer_node",
                kwargs={"questionnaire_slug": "next-quiz", "node_slug": "welcome"},
            ),
            {"answer_type": "next"},
        )
        assert response.status_code == 302
        assert "/next-quiz/q1/" in response.url  # type: ignore[union-attr]

    def test_get_redirects_to_play_node(self, client: Client) -> None:
        _build_published_questionnaire(slug="get-quiz")
        response = client.get(
            reverse(
                "answer_node",
                kwargs={"questionnaire_slug": "get-quiz", "node_slug": "q1"},
            )
        )
        assert response.status_code == 302
        assert "/get-quiz/q1/" in response.url  # type: ignore[union-attr]

    def test_records_session_response(self, client: Client) -> None:
        data = _build_published_questionnaire(slug="rec-quiz")
        user = UserFactory()
        client.force_login(user, backend="noyesapp.backends.EmailBackend")
        # Start the questionnaire first to create session
        client.get(
            reverse("start_questionnaire", kwargs={"questionnaire_slug": "rec-quiz"})
        )
        # Answer the question
        client.post(
            reverse(
                "answer_node",
                kwargs={"questionnaire_slug": "rec-quiz", "node_slug": "q1"},
            ),
            {"answer_type": "yes"},
        )
        session = QuestionnaireSession.objects.get(
            questionnaire=data["questionnaire"], user=user
        )
        assert session.is_complete is True
        responses = NodeResponse.objects.filter(session=session)
        assert responses.count() == 2  # start node + yes_end

    def test_invalid_answer_type_returns_404(self, client: Client) -> None:
        _build_published_questionnaire(slug="inv-quiz")
        response = client.post(
            reverse(
                "answer_node",
                kwargs={"questionnaire_slug": "inv-quiz", "node_slug": "q1"},
            ),
            {"answer_type": "invalid"},
        )
        assert response.status_code == 404


class TestCompleteQuestionnaireView:
    def test_displays_completion_page(self, client: Client) -> None:
        _build_published_questionnaire(slug="done-quiz")
        user = UserFactory()
        client.force_login(user, backend="noyesapp.backends.EmailBackend")
        # Play through the questionnaire
        client.get(
            reverse("start_questionnaire", kwargs={"questionnaire_slug": "done-quiz"})
        )
        client.post(
            reverse(
                "answer_node",
                kwargs={"questionnaire_slug": "done-quiz", "node_slug": "q1"},
            ),
            {"answer_type": "yes"},
        )
        response = client.get(
            reverse(
                "complete_questionnaire",
                kwargs={"questionnaire_slug": "done-quiz"},
            )
        )
        assert response.status_code == 200
        assert b"Questionnaire Complete" in response.content
        assert b"Test Quiz" in response.content

    def test_shows_path(self, client: Client) -> None:
        _build_published_questionnaire(slug="path-quiz")
        user = UserFactory()
        client.force_login(user, backend="noyesapp.backends.EmailBackend")
        client.get(
            reverse("start_questionnaire", kwargs={"questionnaire_slug": "path-quiz"})
        )
        client.post(
            reverse(
                "answer_node",
                kwargs={"questionnaire_slug": "path-quiz", "node_slug": "q1"},
            ),
            {"answer_type": "yes"},
        )
        response = client.get(
            reverse(
                "complete_questionnaire",
                kwargs={"questionnaire_slug": "path-quiz"},
            )
        )
        assert b"Is the sky blue?" in response.content
        assert b"Correct!" in response.content

    def test_404_for_nonexistent_questionnaire(self, client: Client) -> None:
        response = client.get(
            reverse(
                "complete_questionnaire",
                kwargs={"questionnaire_slug": "nonexistent"},
            )
        )
        assert response.status_code == 404

    def test_try_again_link(self, client: Client) -> None:
        _build_published_questionnaire(slug="again-quiz")
        response = client.get(
            reverse(
                "complete_questionnaire",
                kwargs={"questionnaire_slug": "again-quiz"},
            )
        )
        assert response.status_code == 200
        assert b"Try Again" in response.content
