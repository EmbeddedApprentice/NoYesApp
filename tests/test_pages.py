# pyright: reportAttributeAccessIssue=false, reportUnknownMemberType=false
import pytest
from django.test import Client
from django.urls import reverse

from tests.factories import (
    QuestionnaireFactory,
    QuestionnaireSessionFactory,
    UserFactory,
)


@pytest.mark.django_db
class TestLandingPage:
    def test_anonymous_sees_landing_page(self, client: Client) -> None:
        response = client.get("/")
        assert response.status_code == 200
        assert b"NoYesApp" in response.content

    def test_authenticated_user_redirected_to_dashboard(self, client: Client) -> None:
        user = UserFactory()
        client.force_login(user)
        response = client.get("/")
        assert response.status_code == 302
        assert response.url == reverse("dashboard", kwargs={"user_slug": user.slug})

    def test_landing_page_shows_published_questionnaires(self, client: Client) -> None:
        q = QuestionnaireFactory(is_published=True)
        QuestionnaireFactory(is_published=False)  # draft, should not appear
        response = client.get("/")
        assert response.status_code == 200
        assert q.title.encode() in response.content

    def test_landing_page_hides_unpublished_questionnaires(
        self, client: Client
    ) -> None:
        draft = QuestionnaireFactory(is_published=False)
        response = client.get("/")
        assert response.status_code == 200
        assert draft.title.encode() not in response.content

    def test_landing_page_has_register_link(self, client: Client) -> None:
        response = client.get("/")
        assert response.status_code == 200
        assert b"/register/" in response.content


@pytest.mark.django_db
class TestAboutPage:
    def test_about_page_accessible(self, client: Client) -> None:
        response = client.get("/about/")
        assert response.status_code == 200
        assert b"About NoYesApp" in response.content

    def test_about_page_mentions_claude(self, client: Client) -> None:
        response = client.get("/about/")
        assert response.status_code == 200
        assert b"Claude" in response.content


@pytest.mark.django_db
class TestNavbar:
    def test_about_link_in_footer(self, client: Client) -> None:
        response = client.get("/")
        assert response.status_code == 200
        assert b"/about/" in response.content

    def test_dashboard_link_for_authenticated_user(self, client: Client) -> None:
        user = UserFactory()
        client.force_login(user)
        response = client.get("/about/")
        assert response.status_code == 200
        dashboard_url = reverse("dashboard", kwargs={"user_slug": user.slug})
        assert dashboard_url.encode() in response.content

    def test_login_register_links_for_anonymous(self, client: Client) -> None:
        response = client.get("/about/")
        assert response.status_code == 200
        assert b"/login/" in response.content
        assert b"/register/" in response.content


@pytest.mark.django_db
class TestDashboardResponseHistory:
    def test_dashboard_shows_completed_sessions(self, client: Client) -> None:
        user = UserFactory()
        q = QuestionnaireFactory(owner=user, is_published=True)
        QuestionnaireSessionFactory(questionnaire=q, user=user, is_complete=True)
        client.force_login(user)
        response = client.get(reverse("dashboard", kwargs={"user_slug": user.slug}))
        assert response.status_code == 200
        assert b"Response History" in response.content
        assert q.title.encode() in response.content

    def test_dashboard_shows_no_history_message(self, client: Client) -> None:
        user = UserFactory()
        client.force_login(user)
        response = client.get(reverse("dashboard", kwargs={"user_slug": user.slug}))
        assert response.status_code == 200
        assert (
            b"haven&#x27;t completed any" in response.content
            or b"haven't completed any" in response.content
        )
