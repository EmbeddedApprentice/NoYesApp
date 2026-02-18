# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
import pytest
from django.http import Http404

from noyesapp.actions.questionnaires import (
    activate_questionnaire,
    create_edge,
    create_node,
    create_questionnaire,
    deactivate_questionnaire,
    generate_unique_node_slug,
    generate_unique_questionnaire_slug,
    set_start_node,
    validate_node_edges,
    validate_questionnaire_graph,
)
from noyesapp.data.models import Edge, Node, Questionnaire
from noyesapp.readers.questionnaires import (
    get_destination_for_answer,
    get_node_by_slugs,
    get_outgoing_edges,
    get_public_questionnaires,
    get_questionnaire_by_slug,
    get_user_questionnaires,
)
from tests.factories import (
    EdgeFactory,
    NodeFactory,
    QuestionnaireFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db


# --- Model tests ---


class TestQuestionnaireModel:
    def test_create_questionnaire(self) -> None:
        q = QuestionnaireFactory(title="My Quiz", slug="my-quiz")
        assert q.title == "My Quiz"
        assert q.slug == "my-quiz"
        assert q.access_type == Questionnaire.AccessType.DRAFT
        assert q.start_node is None

    def test_str(self) -> None:
        q = QuestionnaireFactory(title="Test Quiz")
        assert str(q) == "Test Quiz"

    def test_slug_uniqueness(self) -> None:
        QuestionnaireFactory(slug="unique-slug")
        with pytest.raises(Exception):  # noqa: B017
            QuestionnaireFactory(slug="unique-slug")

    def test_owner_relationship(self) -> None:
        owner = UserFactory()
        q = QuestionnaireFactory(owner=owner)
        assert q.owner == owner
        assert q in owner.questionnaires.all()  # type: ignore[attr-defined]

    def test_default_ordering(self) -> None:
        q1 = QuestionnaireFactory()
        q2 = QuestionnaireFactory()
        qs = list(Questionnaire.objects.all())
        assert qs == [q2, q1]  # newest first

    def test_cascade_delete_owner(self) -> None:
        owner = UserFactory()
        QuestionnaireFactory(owner=owner)
        owner.delete()
        assert Questionnaire.objects.count() == 0


class TestNodeModel:
    def test_create_node(self) -> None:
        node = NodeFactory(content="Is the sky blue?", node_type=Node.NodeType.QUESTION)
        assert node.content == "Is the sky blue?"
        assert node.node_type == Node.NodeType.QUESTION

    def test_str(self) -> None:
        q = QuestionnaireFactory(slug="quiz")
        node = NodeFactory(questionnaire=q, slug="q1")
        assert str(node) == "quiz/q1"

    def test_slug_unique_per_questionnaire(self) -> None:
        q = QuestionnaireFactory()
        NodeFactory(questionnaire=q, slug="same-slug")
        with pytest.raises(Exception):  # noqa: B017
            NodeFactory(questionnaire=q, slug="same-slug")

    def test_same_slug_different_questionnaires(self) -> None:
        q1 = QuestionnaireFactory()
        q2 = QuestionnaireFactory()
        n1 = NodeFactory(questionnaire=q1, slug="shared-slug")
        n2 = NodeFactory(questionnaire=q2, slug="shared-slug")
        assert n1.slug == n2.slug

    def test_node_types(self) -> None:
        assert Node.NodeType.QUESTION == "question"
        assert Node.NodeType.STATEMENT == "statement"
        assert Node.NodeType.TERMINAL == "terminal"

    def test_cascade_delete_questionnaire(self) -> None:
        q = QuestionnaireFactory()
        NodeFactory(questionnaire=q)
        q.delete()
        assert Node.objects.count() == 0


class TestEdgeModel:
    def test_create_edge(self) -> None:
        q = QuestionnaireFactory()
        source = NodeFactory(questionnaire=q)
        dest = NodeFactory(questionnaire=q)
        edge = EdgeFactory(
            source=source, destination=dest, answer_type=Edge.AnswerType.YES
        )
        assert edge.source == source
        assert edge.destination == dest
        assert edge.answer_type == Edge.AnswerType.YES

    def test_str(self) -> None:
        q = QuestionnaireFactory(slug="quiz")
        source = NodeFactory(questionnaire=q, slug="q1")
        dest = NodeFactory(questionnaire=q, slug="q2")
        edge = EdgeFactory(
            source=source, destination=dest, answer_type=Edge.AnswerType.NO
        )
        assert str(edge) == "quiz/q1 --no--> quiz/q2"

    def test_answer_types(self) -> None:
        assert Edge.AnswerType.YES == "yes"
        assert Edge.AnswerType.NO == "no"
        assert Edge.AnswerType.NEXT == "next"

    def test_unique_answer_type_per_source(self) -> None:
        q = QuestionnaireFactory()
        source = NodeFactory(questionnaire=q)
        dest1 = NodeFactory(questionnaire=q)
        dest2 = NodeFactory(questionnaire=q)
        EdgeFactory(source=source, destination=dest1, answer_type=Edge.AnswerType.YES)
        with pytest.raises(Exception):  # noqa: B017
            EdgeFactory(
                source=source, destination=dest2, answer_type=Edge.AnswerType.YES
            )

    def test_related_names(self) -> None:
        q = QuestionnaireFactory()
        source = NodeFactory(questionnaire=q)
        dest = NodeFactory(questionnaire=q)
        edge = EdgeFactory(
            source=source, destination=dest, answer_type=Edge.AnswerType.NEXT
        )
        assert edge in source.outgoing_edges.all()  # pyright: ignore[reportUnknownMemberType]
        assert edge in dest.incoming_edges.all()  # pyright: ignore[reportUnknownMemberType]

    def test_cascade_delete_source(self) -> None:
        q = QuestionnaireFactory()
        source = NodeFactory(questionnaire=q)
        dest = NodeFactory(questionnaire=q)
        EdgeFactory(source=source, destination=dest)
        source.delete()
        assert Edge.objects.count() == 0


# --- Action tests ---


class TestSlugGeneration:
    def test_basic_questionnaire_slug(self) -> None:
        assert generate_unique_questionnaire_slug("My Quiz") == "my-quiz"

    def test_duplicate_questionnaire_slug(self) -> None:
        QuestionnaireFactory(slug="my-quiz")
        assert generate_unique_questionnaire_slug("My Quiz") == "my-quiz-1"

    def test_empty_title_fallback(self) -> None:
        assert generate_unique_questionnaire_slug("") == "questionnaire"

    def test_basic_node_slug(self) -> None:
        q = QuestionnaireFactory()
        assert generate_unique_node_slug(q, "Is the sky blue?") == "is-the-sky-blue"

    def test_duplicate_node_slug(self) -> None:
        q = QuestionnaireFactory()
        NodeFactory(questionnaire=q, slug="is-the-sky-blue")
        assert generate_unique_node_slug(q, "Is the sky blue?") == "is-the-sky-blue-1"

    def test_long_content_truncation(self) -> None:
        q = QuestionnaireFactory()
        long_content = "a " * 100  # very long content
        slug = generate_unique_node_slug(q, long_content)
        assert len(slug) <= 50


class TestCreateActions:
    def test_create_questionnaire(self) -> None:
        owner = UserFactory()
        q = create_questionnaire("My Quiz", owner, description="A test quiz")
        assert q.title == "My Quiz"
        assert q.slug == "my-quiz"
        assert q.owner == owner
        assert q.description == "A test quiz"

    def test_create_questionnaire_custom_slug(self) -> None:
        owner = UserFactory()
        q = create_questionnaire("My Quiz", owner, slug="custom-slug")
        assert q.slug == "custom-slug"

    def test_create_node_question(self) -> None:
        q = QuestionnaireFactory()
        node = create_node(q, "Is the sky blue?", Node.NodeType.QUESTION)
        assert node.node_type == Node.NodeType.QUESTION
        assert node.questionnaire == q

    def test_create_node_statement(self) -> None:
        q = QuestionnaireFactory()
        node = create_node(q, "Welcome to the quiz.", Node.NodeType.STATEMENT)
        assert node.node_type == Node.NodeType.STATEMENT

    def test_create_node_terminal(self) -> None:
        q = QuestionnaireFactory()
        node = create_node(q, "You are done!", Node.NodeType.TERMINAL)
        assert node.node_type == Node.NodeType.TERMINAL

    def test_create_node_custom_slug(self) -> None:
        q = QuestionnaireFactory()
        node = create_node(q, "Content", Node.NodeType.QUESTION, slug="my-node")
        assert node.slug == "my-node"

    def test_create_node_invalid_type(self) -> None:
        q = QuestionnaireFactory()
        with pytest.raises(ValueError, match="Invalid node_type"):
            create_node(q, "Content", "invalid")

    def test_create_edge(self) -> None:
        q = QuestionnaireFactory()
        source = NodeFactory(questionnaire=q)
        dest = NodeFactory(questionnaire=q)
        edge = create_edge(source, dest, Edge.AnswerType.YES)
        assert edge.source == source
        assert edge.destination == dest

    def test_create_edge_invalid_type(self) -> None:
        q = QuestionnaireFactory()
        source = NodeFactory(questionnaire=q)
        dest = NodeFactory(questionnaire=q)
        with pytest.raises(ValueError, match="Invalid answer_type"):
            create_edge(source, dest, "invalid")

    def test_create_edge_cross_questionnaire(self) -> None:
        q1 = QuestionnaireFactory()
        q2 = QuestionnaireFactory()
        source = NodeFactory(questionnaire=q1)
        dest = NodeFactory(questionnaire=q2)
        with pytest.raises(ValueError, match="same questionnaire"):
            create_edge(source, dest, Edge.AnswerType.YES)


class TestSetStartNode:
    def test_set_start_node(self) -> None:
        q = QuestionnaireFactory()
        node = NodeFactory(questionnaire=q)
        set_start_node(q, node)
        q.refresh_from_db()
        assert q.start_node == node

    def test_set_start_node_wrong_questionnaire(self) -> None:
        q1 = QuestionnaireFactory()
        q2 = QuestionnaireFactory()
        node = NodeFactory(questionnaire=q2)
        with pytest.raises(ValueError, match="does not belong"):
            set_start_node(q1, node)


class TestValidation:
    def _build_valid_graph(self) -> Questionnaire:
        """Build a minimal valid questionnaire: question -> (yes: terminal, no: terminal)."""
        owner = UserFactory()
        q = create_questionnaire("Valid Quiz", owner)
        question = create_node(q, "Yes or No?", Node.NodeType.QUESTION)
        yes_end = create_node(q, "You said yes!", Node.NodeType.TERMINAL)
        no_end = create_node(q, "You said no!", Node.NodeType.TERMINAL)
        create_edge(question, yes_end, Edge.AnswerType.YES)
        create_edge(question, no_end, Edge.AnswerType.NO)
        set_start_node(q, question)
        return q

    def test_valid_graph(self) -> None:
        q = self._build_valid_graph()
        errors = validate_questionnaire_graph(q)
        assert errors == []

    def test_missing_start_node(self) -> None:
        q = QuestionnaireFactory()
        NodeFactory(questionnaire=q, node_type=Node.NodeType.TERMINAL)
        errors = validate_questionnaire_graph(q)
        assert any("starting step" in e for e in errors)

    def test_question_missing_edges(self) -> None:
        q = QuestionnaireFactory()
        question = NodeFactory(questionnaire=q, node_type=Node.NodeType.QUESTION)
        set_start_node(q, question)
        errors = validate_questionnaire_graph(q)
        assert any("YES" in e for e in errors)
        assert any("NO" in e for e in errors)

    def test_statement_wrong_edge_type(self) -> None:
        q = QuestionnaireFactory()
        stmt = NodeFactory(questionnaire=q, node_type=Node.NodeType.STATEMENT)
        dest = NodeFactory(questionnaire=q, node_type=Node.NodeType.TERMINAL)
        EdgeFactory(source=stmt, destination=dest, answer_type=Edge.AnswerType.YES)
        set_start_node(q, stmt)
        errors = validate_node_edges(stmt)
        assert any("NEXT" in e for e in errors)

    def test_terminal_with_edges(self) -> None:
        q = QuestionnaireFactory()
        terminal = NodeFactory(questionnaire=q, node_type=Node.NodeType.TERMINAL)
        dest = NodeFactory(questionnaire=q, node_type=Node.NodeType.TERMINAL)
        EdgeFactory(source=terminal, destination=dest, answer_type=Edge.AnswerType.NEXT)
        errors = validate_node_edges(terminal)
        assert any("no outgoing answers" in e for e in errors)


class TestActivateDeactivate:
    def test_activate_valid_questionnaire_public(self) -> None:
        owner = UserFactory()
        q = create_questionnaire("Pub Quiz", owner)
        question = create_node(q, "Yes?", Node.NodeType.QUESTION)
        yes_end = create_node(q, "Yes end", Node.NodeType.TERMINAL)
        no_end = create_node(q, "No end", Node.NodeType.TERMINAL)
        create_edge(question, yes_end, Edge.AnswerType.YES)
        create_edge(question, no_end, Edge.AnswerType.NO)
        set_start_node(q, question)

        activate_questionnaire(q, Questionnaire.AccessType.PUBLIC)
        q.refresh_from_db()
        assert q.access_type == Questionnaire.AccessType.PUBLIC

    def test_activate_invalid_questionnaire(self) -> None:
        q = QuestionnaireFactory()
        with pytest.raises(ValueError, match="Cannot activate"):
            activate_questionnaire(q, Questionnaire.AccessType.PUBLIC)

    def test_activate_with_draft_raises(self) -> None:
        q = QuestionnaireFactory()
        with pytest.raises(ValueError, match="deactivate_questionnaire"):
            activate_questionnaire(q, Questionnaire.AccessType.DRAFT)

    def test_deactivate(self) -> None:
        owner = UserFactory()
        q = create_questionnaire("Deact Quiz", owner)
        question = create_node(q, "Yes?", Node.NodeType.QUESTION)
        yes_end = create_node(q, "Yes end", Node.NodeType.TERMINAL)
        no_end = create_node(q, "No end", Node.NodeType.TERMINAL)
        create_edge(question, yes_end, Edge.AnswerType.YES)
        create_edge(question, no_end, Edge.AnswerType.NO)
        set_start_node(q, question)
        activate_questionnaire(q, Questionnaire.AccessType.PUBLIC)

        deactivate_questionnaire(q)
        q.refresh_from_db()
        assert q.access_type == Questionnaire.AccessType.DRAFT


# --- Reader tests ---


class TestGetQuestionnaireBySlug:
    def test_found(self) -> None:
        q = QuestionnaireFactory(slug="findme")
        found = get_questionnaire_by_slug("findme")
        assert found.pk == q.pk

    def test_not_found(self) -> None:
        with pytest.raises(Http404):
            get_questionnaire_by_slug("nonexistent")


class TestGetPublicQuestionnaires:
    def test_only_public(self) -> None:
        QuestionnaireFactory(access_type=Questionnaire.AccessType.PUBLIC)
        QuestionnaireFactory(access_type=Questionnaire.AccessType.DRAFT)
        qs = get_public_questionnaires()
        assert qs.count() == 1
        assert all(q.access_type == Questionnaire.AccessType.PUBLIC for q in qs)


class TestGetUserQuestionnaires:
    def test_only_owned(self) -> None:
        owner = UserFactory()
        QuestionnaireFactory(owner=owner)
        QuestionnaireFactory()  # different owner
        qs = get_user_questionnaires(owner)
        assert qs.count() == 1
        assert all(q.owner == owner for q in qs)


class TestGetNodeBySlugs:
    def test_found(self) -> None:
        q = QuestionnaireFactory(slug="quiz")
        node = NodeFactory(questionnaire=q, slug="q1")
        found = get_node_by_slugs("quiz", "q1")
        assert found.pk == node.pk

    def test_missing_questionnaire(self) -> None:
        with pytest.raises(Http404):
            get_node_by_slugs("nonexistent", "q1")

    def test_missing_node(self) -> None:
        QuestionnaireFactory(slug="quiz")
        with pytest.raises(Http404):
            get_node_by_slugs("quiz", "nonexistent")


class TestGetOutgoingEdges:
    def test_returns_edges(self) -> None:
        q = QuestionnaireFactory()
        source = NodeFactory(questionnaire=q)
        dest = NodeFactory(questionnaire=q)
        EdgeFactory(source=source, destination=dest)
        edges = get_outgoing_edges(source)
        assert edges.count() == 1

    def test_empty_for_terminal(self) -> None:
        node = NodeFactory(node_type=Node.NodeType.TERMINAL)
        edges = get_outgoing_edges(node)
        assert edges.count() == 0


class TestGetDestinationForAnswer:
    def test_found(self) -> None:
        q = QuestionnaireFactory()
        source = NodeFactory(questionnaire=q, node_type=Node.NodeType.QUESTION)
        dest = NodeFactory(questionnaire=q, node_type=Node.NodeType.TERMINAL)
        EdgeFactory(source=source, destination=dest, answer_type=Edge.AnswerType.YES)
        result = get_destination_for_answer(source, Edge.AnswerType.YES)
        assert result.pk == dest.pk

    def test_not_found(self) -> None:
        node = NodeFactory(node_type=Node.NodeType.QUESTION)
        with pytest.raises(Http404):
            get_destination_for_answer(node, Edge.AnswerType.YES)
