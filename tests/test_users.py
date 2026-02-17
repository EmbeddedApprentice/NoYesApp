import pytest
from django.test import Client
from django.urls import reverse

from noyesapp.actions.users import create_user, generate_unique_slug
from noyesapp.data.models import Profile, User
from noyesapp.readers.users import get_user_by_slug
from tests.factories import ProfileFactory, UserFactory

pytestmark = pytest.mark.django_db


# --- Model tests ---


class TestUserModel:
    def test_create_user_with_slug(self) -> None:
        user = UserFactory(username="alice", slug="alice")
        assert user.username == "alice"
        assert user.slug == "alice"
        assert str(user) == "alice"

    def test_email_is_unique(self) -> None:
        UserFactory(email="dupe@example.com")
        with pytest.raises(Exception):  # noqa: B017
            UserFactory(email="dupe@example.com", username="other", slug="other")

    def test_slug_is_unique(self) -> None:
        UserFactory(slug="sameslug", username="user-a", email="a@example.com")
        with pytest.raises(Exception):  # noqa: B017
            UserFactory(slug="sameslug", username="user-b", email="b@example.com")

    def test_username_field_is_email(self) -> None:
        assert User.USERNAME_FIELD == "email"  # pyright: ignore[reportUnknownMemberType]


class TestProfileModel:
    def test_profile_creation(self) -> None:
        profile = ProfileFactory()
        assert profile.user is not None
        assert profile.created_at is not None
        assert profile.updated_at is not None

    def test_profile_str(self) -> None:
        profile = ProfileFactory(user__username="bob")
        assert str(profile) == "Profile(bob)"

    def test_user_profile_relationship(self) -> None:
        profile = ProfileFactory(user__username="charlie")
        assert profile.user.profile == profile  # type: ignore[attr-defined]


# --- Action tests ---


class TestCreateUser:
    def test_creates_user_and_profile(self) -> None:
        user = create_user("newuser", "new@example.com", "strongpass123")
        assert user.username == "newuser"  # pyright: ignore[reportUnknownMemberType]
        assert user.email == "new@example.com"  # pyright: ignore[reportUnknownMemberType]
        assert user.slug == "newuser"  # pyright: ignore[reportUnknownMemberType]
        assert Profile.objects.filter(user=user).exists()

    def test_auto_generates_slug(self) -> None:
        user = create_user("My User", "myuser@example.com", "strongpass123")
        assert user.slug == "my-user"  # pyright: ignore[reportUnknownMemberType]


class TestGenerateUniqueSlug:
    def test_basic_slug(self) -> None:
        assert generate_unique_slug("hello") == "hello"

    def test_slugifies_spaces(self) -> None:
        assert generate_unique_slug("hello world") == "hello-world"

    def test_handles_duplicates(self) -> None:
        UserFactory(slug="taken")
        assert generate_unique_slug("taken") == "taken-1"

    def test_handles_multiple_duplicates(self) -> None:
        UserFactory(slug="taken", username="u1", email="u1@example.com")
        UserFactory(slug="taken-1", username="u2", email="u2@example.com")
        assert generate_unique_slug("taken") == "taken-2"


# --- Reader tests ---


class TestGetUserBySlug:
    def test_returns_user(self) -> None:
        user = UserFactory(slug="findme")
        ProfileFactory(user=user)
        found = get_user_by_slug("findme")
        assert found.pk == user.pk

    def test_raises_404_for_missing(self) -> None:
        from django.http import Http404

        with pytest.raises(Http404):
            get_user_by_slug("nonexistent")


# --- View tests ---


class TestRegisterView:
    def test_get_returns_200(self, client: Client) -> None:
        response = client.get(reverse("register"))
        assert response.status_code == 200

    def test_post_valid_creates_user_and_redirects(self, client: Client) -> None:
        response = client.post(
            reverse("register"),
            {
                "username": "newbie",
                "email": "newbie@example.com",
                "password1": "xK9#mP2$vL",
                "password2": "xK9#mP2$vL",
            },
        )
        assert response.status_code == 302
        assert User.objects.filter(email="newbie@example.com").exists()

    def test_post_duplicate_email_shows_error(self, client: Client) -> None:
        UserFactory(email="taken@example.com")
        response = client.post(
            reverse("register"),
            {
                "username": "another",
                "email": "taken@example.com",
                "password1": "xK9#mP2$vL",
                "password2": "xK9#mP2$vL",
            },
        )
        assert response.status_code == 200  # re-renders form with errors

    def test_authenticated_user_redirects(self, client: Client) -> None:
        user = UserFactory()
        client.force_login(user, backend="noyesapp.backends.EmailBackend")
        response = client.get(reverse("register"))
        assert response.status_code == 302

    def test_post_creates_profile(self, client: Client) -> None:
        client.post(
            reverse("register"),
            {
                "username": "withprofile",
                "email": "profile@example.com",
                "password1": "xK9#mP2$vL",
                "password2": "xK9#mP2$vL",
            },
        )
        user = User.objects.get(email="profile@example.com")
        assert Profile.objects.filter(user=user).exists()

    def test_post_auto_logs_in(self, client: Client) -> None:
        client.post(
            reverse("register"),
            {
                "username": "autologin",
                "email": "auto@example.com",
                "password1": "xK9#mP2$vL",
                "password2": "xK9#mP2$vL",
            },
        )
        response = client.get(reverse("register"))
        assert response.status_code == 302  # redirected because logged in


class TestLoginView:
    def test_get_returns_200(self, client: Client) -> None:
        response = client.get(reverse("login"))
        assert response.status_code == 200

    def test_post_valid_credentials_logs_in(self, client: Client) -> None:
        create_user("loginuser", "login@example.com", "xK9#mP2$vL")
        response = client.post(
            reverse("login"),
            {"email": "login@example.com", "password": "xK9#mP2$vL"},
        )
        assert response.status_code == 302

    def test_post_invalid_credentials_shows_error(self, client: Client) -> None:
        response = client.post(
            reverse("login"),
            {"email": "bad@example.com", "password": "wrongpass"},
        )
        assert response.status_code == 200  # re-renders form

    def test_authenticated_user_redirects(self, client: Client) -> None:
        user = UserFactory()
        client.force_login(user, backend="noyesapp.backends.EmailBackend")
        response = client.get(reverse("login"))
        assert response.status_code == 302

    def test_login_uses_email(self, client: Client) -> None:
        create_user("emaillogin", "emaillogin@example.com", "xK9#mP2$vL")
        response = client.post(
            reverse("login"),
            {"email": "emaillogin@example.com", "password": "xK9#mP2$vL"},
        )
        assert response.status_code == 302


class TestLogoutView:
    def test_post_logs_out_and_redirects(self, client: Client) -> None:
        user = UserFactory()
        client.force_login(user, backend="noyesapp.backends.EmailBackend")
        response = client.post(reverse("logout"))
        assert response.status_code == 302

    def test_get_does_not_logout(self, client: Client) -> None:
        user = UserFactory()
        client.force_login(user, backend="noyesapp.backends.EmailBackend")
        client.get(reverse("logout"))
        # GET should still redirect but not log out
        response = client.get(reverse("register"))
        assert response.status_code == 302  # still authenticated
