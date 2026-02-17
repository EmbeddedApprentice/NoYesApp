from django.utils.text import slugify

from noyesapp.data.models import Profile, User


def generate_unique_slug(username: str) -> str:
    """Generate a unique slug from a username, appending a counter if needed."""
    base_slug = slugify(username)
    slug = base_slug
    counter = 1
    while User.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def create_user(username: str, email: str, password: str) -> User:
    """Create a new User with auto-generated slug and linked Profile."""
    slug = generate_unique_slug(username)
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        slug=slug,
    )
    Profile.objects.create(user=user)
    return user
