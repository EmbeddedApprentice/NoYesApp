from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.http import HttpRequest

User = get_user_model()


class EmailBackend(ModelBackend):
    """Authenticate using email address instead of username."""

    def authenticate(
        self,
        request: HttpRequest | None,
        username: str | None = None,
        password: str | None = None,
        **kwargs: object,
    ) -> User | None:  # type: ignore[override]
        if username is None or password is None:
            return None
        try:
            user = User.objects.get(email=username)  # type: ignore[assignment]
        except User.DoesNotExist:
            # Run the default password hasher to mitigate timing attacks
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user  # type: ignore[return-value]
        return None
