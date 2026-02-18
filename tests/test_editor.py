# pyright: reportUnknownMemberType=false, reportUnknownArgumentType=false
# pyright: reportArgumentType=false, reportAttributeAccessIssue=false
import pytest
from django.test import Client
from django.urls import reverse

from noyesapp.actions.questionnaires import (
    activate_questionnaire,
    create_edge,
    create_node,
    create_questionnaire,
    delete_edge,
    delete_node,
    delete_questionnaire,
    set_start_node,
    update_node,
    update_questionnaire,
)
from noyesapp.data.models import Edge, Node, Questionnaire
from tests.factories import (
    QuestionnaireFactory,
    UserFactory,
)

pytestmark = pytest.mark.django_db

AUTH_BACKEND = "noyesapp.backends.EmailBackend"


def _login(client: Client, user: object) -> None:
    client.force_login(user, backend=AUTH_BACKEND)  # type: ignore[arg-type]


def _build_questionnaire_with_owner() -> dict[str, object]:
    """Create a user with slug and a questionnaire owned by them."""
    owner = UserFactory()
    q = create_questionnaire("Test Quiz", owner, slug="test-quiz")
    return {"owner": owner, "questionnaire": q}


# --- Action Tests (update/delete) ---


class TestUpdateQuestionnaire:
    def test_update_title(self) -> None:
        owner = UserFactory()
        q = create_questionnaire("Old Title", owner)
        update_questionnaire(q, title="New Title")
        q.refresh_from_db()
        assert q.title == "New Title"

    def test_update_description(self) -> None:
        owner = UserFactory()
        q = create_questionnaire("Quiz", owner)
        update_questionnaire(q, description="New description")
        q.refresh_from_db()
        assert q.description == "New description"

    def test_update_both(self) -> None:
        owner = UserFactory()
        q = create_questionnaire("Quiz", owner)
        update_questionnaire(q, title="Updated", description="Updated desc")
        q.refresh_from_db()
        assert q.title == "Updated"
        assert q.description == "Updated desc"


class TestDeleteQuestionnaire:
    def test_deletes_questionnaire(self) -> None:
        owner = UserFactory()
        q = create_questionnaire("Delete Me", owner)
        pk = q.pk
        delete_questionnaire(q)
        assert not Questionnaire.objects.filter(pk=pk).exists()

    def test_cascades_nodes(self) -> None:
        owner = UserFactory()
        q = create_questionnaire("Cascade", owner)
        create_node(q, "Node 1", Node.NodeType.TERMINAL)
        delete_questionnaire(q)
        assert Node.objects.count() == 0


class TestUpdateNode:
    def test_update_content(self) -> None:
        q = QuestionnaireFactory()
        node = create_node(q, "Old content", Node.NodeType.QUESTION)
        update_node(node, content="New content")
        node.refresh_from_db()
        assert node.content == "New content"

    def test_update_node_type(self) -> None:
        q = QuestionnaireFactory()
        node = create_node(q, "Content", Node.NodeType.QUESTION)
        update_node(node, node_type=Node.NodeType.STATEMENT)
        node.refresh_from_db()
        assert node.node_type == Node.NodeType.STATEMENT

    def test_invalid_node_type(self) -> None:
        q = QuestionnaireFactory()
        node = create_node(q, "Content", Node.NodeType.QUESTION)
        with pytest.raises(ValueError, match="Invalid node_type"):
            update_node(node, node_type="invalid")


class TestDeleteNode:
    def test_deletes_node(self) -> None:
        q = QuestionnaireFactory()
        node = create_node(q, "Delete Me", Node.NodeType.TERMINAL)
        pk = node.pk
        delete_node(node)
        assert not Node.objects.filter(pk=pk).exists()

    def test_clears_start_node(self) -> None:
        owner = UserFactory()
        q = create_questionnaire("Quiz", owner)
        node = create_node(q, "Start", Node.NodeType.QUESTION)
        set_start_node(q, node)
        delete_node(node)
        q.refresh_from_db()
        assert q.start_node is None

    def test_cascades_edges(self) -> None:
        q = QuestionnaireFactory()
        source = create_node(q, "Source", Node.NodeType.QUESTION)
        dest = create_node(q, "Dest", Node.NodeType.TERMINAL)
        create_edge(source, dest, Edge.AnswerType.YES)
        delete_node(source)
        assert Edge.objects.count() == 0


class TestDeleteEdge:
    def test_deletes_edge(self) -> None:
        q = QuestionnaireFactory()
        source = create_node(q, "Source", Node.NodeType.QUESTION)
        dest = create_node(q, "Dest", Node.NodeType.TERMINAL)
        edge = create_edge(source, dest, Edge.AnswerType.YES)
        pk = edge.pk
        delete_edge(edge)
        assert not Edge.objects.filter(pk=pk).exists()


# --- Dashboard View Tests ---


class TestDashboardView:
    def test_shows_own_questionnaires(self, client: Client) -> None:
        data = _build_questionnaire_with_owner()
        _login(client, data["owner"])
        response = client.get(
            reverse("dashboard", kwargs={"user_slug": data["owner"].slug})
        )
        assert response.status_code == 200
        assert b"Test Quiz" in response.content

    def test_403_for_other_user(self, client: Client) -> None:
        data = _build_questionnaire_with_owner()
        other = UserFactory()
        _login(client, other)
        response = client.get(
            reverse("dashboard", kwargs={"user_slug": data["owner"].slug})
        )
        assert response.status_code == 403

    def test_redirects_anonymous(self, client: Client) -> None:
        owner = UserFactory()
        response = client.get(reverse("dashboard", kwargs={"user_slug": owner.slug}))
        assert response.status_code == 302
        assert "login" in response.url


class TestCreateQuestionnaireView:
    def test_get_shows_form(self, client: Client) -> None:
        owner = UserFactory()
        _login(client, owner)
        response = client.get(
            reverse("create_questionnaire", kwargs={"user_slug": owner.slug})
        )
        assert response.status_code == 200
        assert b"Create Questionnaire" in response.content

    def test_post_creates_questionnaire(self, client: Client) -> None:
        owner = UserFactory()
        _login(client, owner)
        response = client.post(
            reverse("create_questionnaire", kwargs={"user_slug": owner.slug}),
            {"title": "My New Quiz", "description": "A new quiz"},
        )
        assert response.status_code == 302
        assert Questionnaire.objects.filter(owner=owner, title="My New Quiz").exists()

    def test_redirects_to_edit(self, client: Client) -> None:
        owner = UserFactory()
        _login(client, owner)
        response = client.post(
            reverse("create_questionnaire", kwargs={"user_slug": owner.slug}),
            {"title": "Redirect Quiz", "description": ""},
        )
        assert response.status_code == 302
        assert "/edit/" in response.url

    def test_403_for_other_user(self, client: Client) -> None:
        owner = UserFactory()
        other = UserFactory()
        _login(client, other)
        response = client.get(
            reverse("create_questionnaire", kwargs={"user_slug": owner.slug})
        )
        assert response.status_code == 403


class TestEditQuestionnaireView:
    def test_get_shows_form_and_nodes(self, client: Client) -> None:
        data = _build_questionnaire_with_owner()
        q = data["questionnaire"]
        create_node(q, "A question?", Node.NodeType.QUESTION)
        _login(client, data["owner"])
        response = client.get(
            reverse(
                "edit_questionnaire",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": q.slug,
                },
            )
        )
        assert response.status_code == 200
        assert b"A question?" in response.content

    def test_post_updates_details(self, client: Client) -> None:
        data = _build_questionnaire_with_owner()
        q = data["questionnaire"]
        _login(client, data["owner"])
        client.post(
            reverse(
                "edit_questionnaire",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": q.slug,
                },
            ),
            {"title": "Updated Title", "description": "Updated desc"},
        )
        q.refresh_from_db()
        assert q.title == "Updated Title"

    def test_403_for_other_user(self, client: Client) -> None:
        data = _build_questionnaire_with_owner()
        other = UserFactory()
        _login(client, other)
        response = client.get(
            reverse(
                "edit_questionnaire",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": data["questionnaire"].slug,
                },
            )
        )
        assert response.status_code == 403


class TestDeleteQuestionnaireView:
    def test_get_shows_confirmation(self, client: Client) -> None:
        data = _build_questionnaire_with_owner()
        _login(client, data["owner"])
        response = client.get(
            reverse(
                "delete_questionnaire",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": data["questionnaire"].slug,
                },
            )
        )
        assert response.status_code == 200
        assert b"Are you sure" in response.content

    def test_post_deletes_questionnaire(self, client: Client) -> None:
        data = _build_questionnaire_with_owner()
        q = data["questionnaire"]
        _login(client, data["owner"])
        response = client.post(
            reverse(
                "delete_questionnaire",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": q.slug,
                },
            )
        )
        assert response.status_code == 302
        assert not Questionnaire.objects.filter(pk=q.pk).exists()

    def test_403_for_other_user(self, client: Client) -> None:
        data = _build_questionnaire_with_owner()
        other = UserFactory()
        _login(client, other)
        response = client.post(
            reverse(
                "delete_questionnaire",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": data["questionnaire"].slug,
                },
            )
        )
        assert response.status_code == 403


class TestSetAccessTypeView:
    def test_activate_valid_questionnaire(self, client: Client) -> None:
        owner = UserFactory()
        q = create_questionnaire("Pub Quiz", owner, slug="pub-quiz")
        question = create_node(q, "Yes?", Node.NodeType.QUESTION)
        yes_end = create_node(q, "Yes end", Node.NodeType.TERMINAL)
        no_end = create_node(q, "No end", Node.NodeType.TERMINAL)
        create_edge(question, yes_end, Edge.AnswerType.YES)
        create_edge(question, no_end, Edge.AnswerType.NO)
        set_start_node(q, question)
        _login(client, owner)

        client.post(
            reverse(
                "set_access_type",
                kwargs={
                    "user_slug": owner.slug,
                    "questionnaire_slug": "pub-quiz",
                },
            ),
            {"access_type": "public"},
        )
        q.refresh_from_db()
        assert q.access_type == Questionnaire.AccessType.PUBLIC

    def test_deactivate(self, client: Client) -> None:
        owner = UserFactory()
        q = create_questionnaire("Deact", owner, slug="deact")
        question = create_node(q, "Yes?", Node.NodeType.QUESTION)
        yes_end = create_node(q, "Yes end", Node.NodeType.TERMINAL)
        no_end = create_node(q, "No end", Node.NodeType.TERMINAL)
        create_edge(question, yes_end, Edge.AnswerType.YES)
        create_edge(question, no_end, Edge.AnswerType.NO)
        set_start_node(q, question)
        activate_questionnaire(q, Questionnaire.AccessType.PUBLIC)
        _login(client, owner)

        client.post(
            reverse(
                "set_access_type",
                kwargs={
                    "user_slug": owner.slug,
                    "questionnaire_slug": "deact",
                },
            ),
            {"access_type": "draft"},
        )
        q.refresh_from_db()
        assert q.access_type == Questionnaire.AccessType.DRAFT

    def test_activate_invalid_shows_error(self, client: Client) -> None:
        data = _build_questionnaire_with_owner()
        _login(client, data["owner"])
        response = client.post(
            reverse(
                "set_access_type",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": data["questionnaire"].slug,
                },
            ),
            {"access_type": "public"},
        )
        assert response.status_code == 200
        assert b"Cannot activate" in response.content


# --- Node Editor View Tests ---


class TestAddNodeView:
    def test_get_shows_form(self, client: Client) -> None:
        data = _build_questionnaire_with_owner()
        _login(client, data["owner"])
        response = client.get(
            reverse(
                "add_node",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": data["questionnaire"].slug,
                },
            )
        )
        assert response.status_code == 200
        assert b"Add Step" in response.content

    def test_post_creates_node(self, client: Client) -> None:
        data = _build_questionnaire_with_owner()
        _login(client, data["owner"])
        client.post(
            reverse(
                "add_node",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": data["questionnaire"].slug,
                },
            ),
            {"content": "Is this a test?", "node_type": Node.NodeType.QUESTION},
        )
        assert Node.objects.filter(
            questionnaire=data["questionnaire"], content="Is this a test?"
        ).exists()

    def test_redirects_to_edit_questionnaire(self, client: Client) -> None:
        data = _build_questionnaire_with_owner()
        _login(client, data["owner"])
        response = client.post(
            reverse(
                "add_node",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": data["questionnaire"].slug,
                },
            ),
            {"content": "New node", "node_type": Node.NodeType.TERMINAL},
        )
        assert response.status_code == 302
        assert "/edit/" in response.url


class TestEditNodeView:
    def test_get_shows_form(self, client: Client) -> None:
        data = _build_questionnaire_with_owner()
        q = data["questionnaire"]
        node = create_node(q, "Edit me", Node.NodeType.QUESTION)
        _login(client, data["owner"])
        response = client.get(
            reverse(
                "edit_node",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": q.slug,
                    "node_slug": node.slug,
                },
            )
        )
        assert response.status_code == 200
        assert b"Edit me" in response.content

    def test_post_updates_node(self, client: Client) -> None:
        data = _build_questionnaire_with_owner()
        q = data["questionnaire"]
        node = create_node(q, "Old content", Node.NodeType.QUESTION)
        _login(client, data["owner"])
        client.post(
            reverse(
                "edit_node",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": q.slug,
                    "node_slug": node.slug,
                },
            ),
            {"content": "Updated content", "node_type": Node.NodeType.STATEMENT},
        )
        node.refresh_from_db()
        assert node.content == "Updated content"
        assert node.node_type == Node.NodeType.STATEMENT

    def test_shows_outgoing_edges(self, client: Client) -> None:
        data = _build_questionnaire_with_owner()
        q = data["questionnaire"]
        source = create_node(q, "Source", Node.NodeType.QUESTION)
        dest = create_node(q, "Dest", Node.NodeType.TERMINAL, slug="dest-node")
        create_edge(source, dest, Edge.AnswerType.YES)
        _login(client, data["owner"])
        response = client.get(
            reverse(
                "edit_node",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": q.slug,
                    "node_slug": source.slug,
                },
            )
        )
        assert b"dest-node" in response.content
        assert b"YES" in response.content


class TestDeleteNodeView:
    def test_get_shows_confirmation(self, client: Client) -> None:
        data = _build_questionnaire_with_owner()
        q = data["questionnaire"]
        node = create_node(q, "Delete me", Node.NodeType.TERMINAL)
        _login(client, data["owner"])
        response = client.get(
            reverse(
                "delete_node",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": q.slug,
                    "node_slug": node.slug,
                },
            )
        )
        assert response.status_code == 200
        assert b"Delete me" in response.content

    def test_post_deletes_node(self, client: Client) -> None:
        data = _build_questionnaire_with_owner()
        q = data["questionnaire"]
        node = create_node(q, "Delete me", Node.NodeType.TERMINAL)
        pk = node.pk
        _login(client, data["owner"])
        response = client.post(
            reverse(
                "delete_node",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": q.slug,
                    "node_slug": node.slug,
                },
            )
        )
        assert response.status_code == 302
        assert not Node.objects.filter(pk=pk).exists()


class TestSetStartNodeView:
    def test_sets_start_node(self, client: Client) -> None:
        data = _build_questionnaire_with_owner()
        q = data["questionnaire"]
        node = create_node(q, "Start here", Node.NodeType.QUESTION)
        _login(client, data["owner"])
        client.post(
            reverse(
                "set_start_node",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": q.slug,
                    "node_slug": node.slug,
                },
            )
        )
        q.refresh_from_db()
        assert q.start_node == node


# --- Edge Management View Tests ---


class TestAddEdgeView:
    def test_post_creates_edge(self, client: Client) -> None:
        data = _build_questionnaire_with_owner()
        q = data["questionnaire"]
        source = create_node(q, "Source", Node.NodeType.QUESTION)
        dest = create_node(q, "Dest", Node.NodeType.TERMINAL)
        _login(client, data["owner"])
        client.post(
            reverse(
                "add_edge",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": q.slug,
                    "node_slug": source.slug,
                },
            ),
            {"answer_type": Edge.AnswerType.YES, "destination": dest.pk},
        )
        assert Edge.objects.filter(
            source=source, destination=dest, answer_type=Edge.AnswerType.YES
        ).exists()

    def test_redirects_to_edit_node(self, client: Client) -> None:
        data = _build_questionnaire_with_owner()
        q = data["questionnaire"]
        source = create_node(q, "Source", Node.NodeType.QUESTION)
        dest = create_node(q, "Dest", Node.NodeType.TERMINAL)
        _login(client, data["owner"])
        response = client.post(
            reverse(
                "add_edge",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": q.slug,
                    "node_slug": source.slug,
                },
            ),
            {"answer_type": Edge.AnswerType.YES, "destination": dest.pk},
        )
        assert response.status_code == 302
        assert f"/nodes/{source.slug}/edit/" in response.url


class TestDeleteEdgeView:
    def test_post_deletes_edge(self, client: Client) -> None:
        data = _build_questionnaire_with_owner()
        q = data["questionnaire"]
        source = create_node(q, "Source", Node.NodeType.QUESTION)
        dest = create_node(q, "Dest", Node.NodeType.TERMINAL)
        edge = create_edge(source, dest, Edge.AnswerType.YES)
        _login(client, data["owner"])
        response = client.post(
            reverse(
                "delete_edge",
                kwargs={
                    "user_slug": data["owner"].slug,
                    "questionnaire_slug": q.slug,
                    "node_slug": source.slug,
                    "edge_id": edge.pk,
                },
            )
        )
        assert response.status_code == 302
        assert not Edge.objects.filter(pk=edge.pk).exists()
