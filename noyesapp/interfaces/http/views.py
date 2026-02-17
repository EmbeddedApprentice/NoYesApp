import contextlib

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from noyesapp.actions.questionnaires import (
    create_edge,
    create_node,
    create_questionnaire,
    delete_edge,
    delete_node,
    delete_questionnaire,
    publish_questionnaire,
    set_start_node,
    unpublish_questionnaire,
    update_node,
    update_questionnaire,
    validate_questionnaire_graph,
)
from noyesapp.actions.sessions import (
    complete_session,
    get_or_create_active_session,
    record_answer_and_advance,
)
from noyesapp.actions.users import create_user
from noyesapp.data.models import Node
from noyesapp.interfaces.http.forms import (
    EdgeForm,
    EmailAuthenticationForm,
    NodeForm,
    QuestionnaireForm,
    RegistrationForm,
)
from noyesapp.readers.questionnaires import (
    get_destination_for_answer,
    get_edge_for_node,
    get_node_by_slugs,
    get_node_for_questionnaire,
    get_node_with_edges,
    get_published_questionnaires,
    get_questionnaire_by_slug,
    get_questionnaire_for_owner,
    get_questionnaire_nodes,
    get_user_questionnaires,
)
from noyesapp.readers.sessions import get_session_responses, get_user_completed_sessions
from noyesapp.readers.users import get_user_by_slug


def home_view(request: HttpRequest) -> HttpResponse:
    """Landing page. Authenticated users are redirected to their dashboard."""
    if request.user.is_authenticated:
        user_slug: str = request.user.slug  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUnknownVariableType]
        return redirect("dashboard", user_slug=user_slug)

    questionnaires = get_published_questionnaires()
    return render(
        request,
        "flatpages/landing.html",
        {"questionnaires": questionnaires},
    )


def register_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password1"],
            )
            login(request, user, backend="noyesapp.backends.EmailBackend")
            return redirect("/")
    else:
        form = RegistrationForm()

    return render(request, "registration/register.html", {"form": form})


def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if user is not None:
                login(request, user, backend="noyesapp.backends.EmailBackend")
                next_url = request.GET.get("next", "/")
                return redirect(next_url)
    else:
        form = EmailAuthenticationForm()

    return render(request, "registration/login.html", {"form": form})


def logout_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        logout(request)
    return redirect("/")


# --- Questionnaire Player ---


def start_questionnaire_view(
    request: HttpRequest, questionnaire_slug: str
) -> HttpResponse:
    """Start or resume a questionnaire. Redirects to the start node."""
    questionnaire = get_questionnaire_by_slug(questionnaire_slug)

    if questionnaire.start_node is None:  # pyright: ignore[reportUnknownMemberType]
        return render(
            request,
            "player/error.html",
            {
                "message": "This questionnaire has no starting step.",
            },
        )

    start_node_slug: str = questionnaire.start_node.slug  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    # Ensure a session exists
    user = request.user if request.user.is_authenticated else None
    session_key = request.session.session_key or ""
    if not session_key and not request.user.is_authenticated:
        request.session.create()
        session_key = request.session.session_key or ""

    get_or_create_active_session(
        questionnaire,
        user=user,  # pyright: ignore[reportArgumentType]
        session_key=session_key,
    )

    return redirect(
        "play_node",
        questionnaire_slug=questionnaire_slug,
        node_slug=start_node_slug,
    )


def play_node_view(
    request: HttpRequest, questionnaire_slug: str, node_slug: str
) -> HttpResponse:
    """Display a node in the questionnaire player."""
    node = get_node_by_slugs(questionnaire_slug, node_slug)
    node = get_node_with_edges(node)
    questionnaire = node.questionnaire  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    # Get edges for template context
    outgoing_edges: list[object] = list(node.outgoing_edges.all())  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUnknownArgumentType]

    # Check if terminal
    is_terminal: bool = node.node_type == Node.NodeType.TERMINAL  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    context: dict[str, object] = {
        "questionnaire": questionnaire,
        "node": node,
        "outgoing_edges": outgoing_edges,
        "is_terminal": is_terminal,
    }

    if getattr(request, "htmx", None) and request.htmx:  # type: ignore[union-attr]
        return render(request, "player/_node_partial.html", context)

    return render(request, "player/play_node.html", context)


def node_partial_view(
    request: HttpRequest, questionnaire_slug: str, node_slug: str
) -> HttpResponse:
    """Return a node partial for HTMX prefetch."""
    node = get_node_by_slugs(questionnaire_slug, node_slug)
    node = get_node_with_edges(node)
    questionnaire = node.questionnaire  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    outgoing_edges: list[object] = list(node.outgoing_edges.all())  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUnknownArgumentType]
    is_terminal: bool = node.node_type == Node.NodeType.TERMINAL  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

    return render(
        request,
        "player/_node_partial.html",
        {
            "questionnaire": questionnaire,
            "node": node,
            "outgoing_edges": outgoing_edges,
            "is_terminal": is_terminal,
        },
    )


def answer_node_view(
    request: HttpRequest, questionnaire_slug: str, node_slug: str
) -> HttpResponse:
    """Handle an answer submission (POST). Record the answer and redirect to next node."""
    if request.method != "POST":
        return redirect(
            "play_node", questionnaire_slug=questionnaire_slug, node_slug=node_slug
        )

    answer_type = request.POST.get("answer_type", "")
    node = get_node_by_slugs(questionnaire_slug, node_slug)
    destination = get_destination_for_answer(node, answer_type)
    questionnaire = get_questionnaire_by_slug(questionnaire_slug)

    # Get or create session
    user = request.user if request.user.is_authenticated else None
    session_key = request.session.session_key or ""
    if not session_key and not request.user.is_authenticated:
        request.session.create()
        session_key = request.session.session_key or ""

    session = get_or_create_active_session(
        questionnaire,
        user=user,  # pyright: ignore[reportArgumentType]
        session_key=session_key,
    )

    record_answer_and_advance(session, node, answer_type, destination)

    dest_slug: str = destination.slug  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
    return redirect(
        "play_node",
        questionnaire_slug=questionnaire_slug,
        node_slug=dest_slug,
    )


def complete_questionnaire_view(
    request: HttpRequest, questionnaire_slug: str
) -> HttpResponse:
    """Complete and show the completion page for a questionnaire."""
    questionnaire = get_questionnaire_by_slug(questionnaire_slug)

    user = request.user if request.user.is_authenticated else None
    session_key = request.session.session_key or ""

    from noyesapp.data.models import QuestionnaireSession

    # On POST, complete the active session
    if request.method == "POST":
        active_filters: dict[str, object] = {
            "questionnaire": questionnaire,
            "is_complete": False,
        }
        if user is not None:
            active_filters["user"] = user
        else:
            active_filters["session_key"] = session_key

        active_session = (
            QuestionnaireSession.objects.filter(**active_filters)
            .order_by("-started_at")
            .first()
        )
        if active_session is not None:
            complete_session(active_session)

    # Find the completed session to show the path
    completed_filters: dict[str, object] = {
        "questionnaire": questionnaire,
        "is_complete": True,
    }
    if user is not None:
        completed_filters["user"] = user
    else:
        completed_filters["session_key"] = session_key

    session = (
        QuestionnaireSession.objects.filter(**completed_filters)
        .order_by("-completed_at")
        .first()
    )

    responses: object = get_session_responses(session) if session else []

    return render(
        request,
        "player/complete.html",
        {
            "questionnaire": questionnaire,
            "session": session,
            "responses": responses,
        },
    )


# --- Questionnaire Editor ---


@login_required
def dashboard_view(request: HttpRequest, user_slug: str) -> HttpResponse:
    """User dashboard showing their questionnaires."""
    profile_user = get_user_by_slug(user_slug)
    if profile_user.pk != request.user.pk:
        return render(request, "editor/forbidden.html", status=403)

    questionnaires = get_user_questionnaires(profile_user)
    completed_sessions = get_user_completed_sessions(profile_user)
    return render(
        request,
        "editor/dashboard.html",
        {
            "profile_user": profile_user,
            "questionnaires": questionnaires,
            "completed_sessions": completed_sessions,
        },
    )


@login_required
def create_questionnaire_view(request: HttpRequest, user_slug: str) -> HttpResponse:
    """Create a new questionnaire."""
    profile_user = get_user_by_slug(user_slug)
    if profile_user.pk != request.user.pk:
        return render(request, "editor/forbidden.html", status=403)

    if request.method == "POST":
        form = QuestionnaireForm(request.POST)
        if form.is_valid():
            q = create_questionnaire(
                title=form.cleaned_data["title"],
                owner=profile_user,
                description=form.cleaned_data["description"],
            )
            q_slug: str = q.slug  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            return redirect(
                "edit_questionnaire",
                user_slug=user_slug,
                questionnaire_slug=q_slug,
            )
    else:
        form = QuestionnaireForm()

    return render(
        request,
        "editor/create_questionnaire.html",
        {"form": form, "profile_user": profile_user},
    )


@login_required
def edit_questionnaire_view(
    request: HttpRequest, user_slug: str, questionnaire_slug: str
) -> HttpResponse:
    """Edit questionnaire details and manage nodes."""
    profile_user = get_user_by_slug(user_slug)
    if profile_user.pk != request.user.pk:
        return render(request, "editor/forbidden.html", status=403)

    questionnaire = get_questionnaire_for_owner(questionnaire_slug, profile_user)
    nodes = get_questionnaire_nodes(questionnaire)
    validation_errors = validate_questionnaire_graph(questionnaire)

    if request.method == "POST":
        form = QuestionnaireForm(request.POST)
        if form.is_valid():
            update_questionnaire(
                questionnaire,
                title=form.cleaned_data["title"],
                description=form.cleaned_data["description"],
            )
            return redirect(
                "edit_questionnaire",
                user_slug=user_slug,
                questionnaire_slug=questionnaire_slug,
            )
    else:
        form = QuestionnaireForm(
            initial={
                "title": questionnaire.title,  # pyright: ignore[reportUnknownMemberType]
                "description": questionnaire.description,  # pyright: ignore[reportUnknownMemberType]
            }
        )

    return render(
        request,
        "editor/edit_questionnaire.html",
        {
            "questionnaire": questionnaire,
            "nodes": nodes,
            "form": form,
            "profile_user": profile_user,
            "validation_errors": validation_errors,
        },
    )


@login_required
def delete_questionnaire_view(
    request: HttpRequest, user_slug: str, questionnaire_slug: str
) -> HttpResponse:
    """Delete a questionnaire with confirmation."""
    profile_user = get_user_by_slug(user_slug)
    if profile_user.pk != request.user.pk:
        return render(request, "editor/forbidden.html", status=403)

    questionnaire = get_questionnaire_for_owner(questionnaire_slug, profile_user)

    if request.method == "POST":
        delete_questionnaire(questionnaire)
        return redirect("dashboard", user_slug=user_slug)

    return render(
        request,
        "editor/delete_questionnaire.html",
        {"questionnaire": questionnaire, "profile_user": profile_user},
    )


@login_required
def publish_questionnaire_view(
    request: HttpRequest, user_slug: str, questionnaire_slug: str
) -> HttpResponse:
    """Toggle publish/unpublish for a questionnaire."""
    profile_user = get_user_by_slug(user_slug)
    if profile_user.pk != request.user.pk:
        return render(request, "editor/forbidden.html", status=403)

    questionnaire = get_questionnaire_for_owner(questionnaire_slug, profile_user)

    if request.method == "POST":
        if questionnaire.is_published:  # pyright: ignore[reportUnknownMemberType]
            unpublish_questionnaire(questionnaire)
        else:
            try:
                publish_questionnaire(questionnaire)
            except ValueError as e:
                nodes = get_questionnaire_nodes(questionnaire)
                validation_errors = validate_questionnaire_graph(questionnaire)
                form = QuestionnaireForm(
                    initial={
                        "title": questionnaire.title,  # pyright: ignore[reportUnknownMemberType]
                        "description": questionnaire.description,  # pyright: ignore[reportUnknownMemberType]
                    }
                )
                return render(
                    request,
                    "editor/edit_questionnaire.html",
                    {
                        "questionnaire": questionnaire,
                        "nodes": nodes,
                        "form": form,
                        "profile_user": profile_user,
                        "validation_errors": validation_errors,
                        "publish_error": str(e),
                    },
                )

    return redirect(
        "edit_questionnaire",
        user_slug=user_slug,
        questionnaire_slug=questionnaire_slug,
    )


@login_required
def add_node_view(
    request: HttpRequest, user_slug: str, questionnaire_slug: str
) -> HttpResponse:
    """Add a new node to a questionnaire."""
    profile_user = get_user_by_slug(user_slug)
    if profile_user.pk != request.user.pk:
        return render(request, "editor/forbidden.html", status=403)

    questionnaire = get_questionnaire_for_owner(questionnaire_slug, profile_user)

    if request.method == "POST":
        form = NodeForm(request.POST)
        if form.is_valid():
            create_node(
                questionnaire,
                content=form.cleaned_data["content"],
                node_type=form.cleaned_data["node_type"],
            )
            return redirect(
                "edit_questionnaire",
                user_slug=user_slug,
                questionnaire_slug=questionnaire_slug,
            )
    else:
        form = NodeForm()

    return render(
        request,
        "editor/add_node.html",
        {
            "form": form,
            "questionnaire": questionnaire,
            "profile_user": profile_user,
        },
    )


@login_required
def edit_node_view(
    request: HttpRequest,
    user_slug: str,
    questionnaire_slug: str,
    node_slug: str,
) -> HttpResponse:
    """Edit a node's content, type, and manage its edges."""
    profile_user = get_user_by_slug(user_slug)
    if profile_user.pk != request.user.pk:
        return render(request, "editor/forbidden.html", status=403)

    questionnaire = get_questionnaire_for_owner(questionnaire_slug, profile_user)
    node = get_node_for_questionnaire(questionnaire, node_slug)

    if request.method == "POST":
        form = NodeForm(request.POST)
        if form.is_valid():
            update_node(
                node,
                content=form.cleaned_data["content"],
                node_type=form.cleaned_data["node_type"],
            )
            return redirect(
                "edit_node",
                user_slug=user_slug,
                questionnaire_slug=questionnaire_slug,
                node_slug=node_slug,
            )
    else:
        form = NodeForm(
            initial={
                "content": node.content,  # pyright: ignore[reportUnknownMemberType]
                "node_type": node.node_type,  # pyright: ignore[reportUnknownMemberType]
            }
        )

    edge_form = EdgeForm(questionnaire)
    outgoing_edges: list[object] = list(node.outgoing_edges.all())  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUnknownArgumentType]
    is_start_node: bool = questionnaire.start_node_id == node.pk  # pyright: ignore[reportUnknownMemberType, reportAttributeAccessIssue, reportUnknownVariableType]

    return render(
        request,
        "editor/edit_node.html",
        {
            "form": form,
            "edge_form": edge_form,
            "node": node,
            "questionnaire": questionnaire,
            "profile_user": profile_user,
            "outgoing_edges": outgoing_edges,
            "is_start_node": is_start_node,
        },
    )


@login_required
def delete_node_view(
    request: HttpRequest,
    user_slug: str,
    questionnaire_slug: str,
    node_slug: str,
) -> HttpResponse:
    """Delete a node from a questionnaire."""
    profile_user = get_user_by_slug(user_slug)
    if profile_user.pk != request.user.pk:
        return render(request, "editor/forbidden.html", status=403)

    questionnaire = get_questionnaire_for_owner(questionnaire_slug, profile_user)
    node = get_node_for_questionnaire(questionnaire, node_slug)

    if request.method == "POST":
        delete_node(node)
        return redirect(
            "edit_questionnaire",
            user_slug=user_slug,
            questionnaire_slug=questionnaire_slug,
        )

    return render(
        request,
        "editor/delete_node.html",
        {
            "node": node,
            "questionnaire": questionnaire,
            "profile_user": profile_user,
        },
    )


@login_required
def set_start_node_view(
    request: HttpRequest,
    user_slug: str,
    questionnaire_slug: str,
    node_slug: str,
) -> HttpResponse:
    """Set a node as the start node for the questionnaire."""
    profile_user = get_user_by_slug(user_slug)
    if profile_user.pk != request.user.pk:
        return render(request, "editor/forbidden.html", status=403)

    questionnaire = get_questionnaire_for_owner(questionnaire_slug, profile_user)
    node = get_node_for_questionnaire(questionnaire, node_slug)

    if request.method == "POST":
        set_start_node(questionnaire, node)

    return redirect(
        "edit_questionnaire",
        user_slug=user_slug,
        questionnaire_slug=questionnaire_slug,
    )


@login_required
def add_edge_view(
    request: HttpRequest,
    user_slug: str,
    questionnaire_slug: str,
    node_slug: str,
) -> HttpResponse:
    """Add an edge from a node to a destination."""
    profile_user = get_user_by_slug(user_slug)
    if profile_user.pk != request.user.pk:
        return render(request, "editor/forbidden.html", status=403)

    questionnaire = get_questionnaire_for_owner(questionnaire_slug, profile_user)
    node = get_node_for_questionnaire(questionnaire, node_slug)

    if request.method == "POST":
        form = EdgeForm(questionnaire, request.POST)
        if form.is_valid():
            with contextlib.suppress(ValueError):
                create_edge(
                    source=node,
                    destination=form.cleaned_data["destination"],
                    answer_type=form.cleaned_data["answer_type"],
                )
            return redirect(
                "edit_node",
                user_slug=user_slug,
                questionnaire_slug=questionnaire_slug,
                node_slug=node_slug,
            )

    return redirect(
        "edit_node",
        user_slug=user_slug,
        questionnaire_slug=questionnaire_slug,
        node_slug=node_slug,
    )


@login_required
def delete_edge_view(
    request: HttpRequest,
    user_slug: str,
    questionnaire_slug: str,
    node_slug: str,
    edge_id: int,
) -> HttpResponse:
    """Delete an edge from a node."""
    profile_user = get_user_by_slug(user_slug)
    if profile_user.pk != request.user.pk:
        return render(request, "editor/forbidden.html", status=403)

    questionnaire = get_questionnaire_for_owner(questionnaire_slug, profile_user)
    node = get_node_for_questionnaire(questionnaire, node_slug)
    edge = get_edge_for_node(node, edge_id)

    if request.method == "POST":
        delete_edge(edge)

    return redirect(
        "edit_node",
        user_slug=user_slug,
        questionnaire_slug=questionnaire_slug,
        node_slug=node_slug,
    )
