from django.shortcuts import get_object_or_404

from noyesapp.data.models import User


def get_user_by_slug(slug: str) -> User:
    """Retrieve a user by slug with profile pre-loaded."""
    return get_object_or_404(User.objects.select_related("profile"), slug=slug)
