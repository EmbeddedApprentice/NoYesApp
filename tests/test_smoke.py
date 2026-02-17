from django.test import RequestFactory
from django.urls import reverse


def test_settings_load() -> None:
    """Django settings module loads without errors."""
    from django.conf import settings

    assert settings.ROOT_URLCONF == "noyesapp.urls"
    assert settings.DEFAULT_AUTO_FIELD == "django.db.models.BigAutoField"


def test_url_resolver_loads() -> None:
    """URL resolver can resolve the admin URL."""
    url = reverse("admin:index")
    assert url == "/admin/"


def test_admin_redirects(client: object) -> None:
    """Admin page redirects to login for unauthenticated users."""
    from django.test import Client

    assert isinstance(client, Client)
    response = client.get("/admin/")
    assert response.status_code == 302


def test_htmx_middleware_active() -> None:
    """HtmxMiddleware is in MIDDLEWARE setting."""
    from django.conf import settings

    assert "django_htmx.middleware.HtmxMiddleware" in settings.MIDDLEWARE


def test_request_factory_works() -> None:
    """RequestFactory can create a basic request."""
    factory = RequestFactory()
    request = factory.get("/")
    assert request.method == "GET"
