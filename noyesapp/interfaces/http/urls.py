from django.contrib.flatpages import views as flatpages_views
from django.urls import path

from noyesapp.interfaces.http import views

urlpatterns = [
    # Home / landing page
    path("", views.home_view, name="home"),
    # Auth
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    # Questionnaire start (prefixed to avoid conflict with dashboard)
    path(
        "q/<slug:questionnaire_slug>/",
        views.start_questionnaire_view,
        name="start_questionnaire",
    ),
    # Editor — user-scoped (must come before player catch-all)
    path(
        "<slug:user_slug>/create/",
        views.create_questionnaire_view,
        name="create_questionnaire",
    ),
    path(
        "<slug:user_slug>/<slug:questionnaire_slug>/edit/",
        views.edit_questionnaire_view,
        name="edit_questionnaire",
    ),
    path(
        "<slug:user_slug>/<slug:questionnaire_slug>/delete/",
        views.delete_questionnaire_view,
        name="delete_questionnaire",
    ),
    path(
        "<slug:user_slug>/<slug:questionnaire_slug>/access/",
        views.set_access_type_view,
        name="set_access_type",
    ),
    path(
        "<slug:user_slug>/<slug:questionnaire_slug>/invites/",
        views.manage_invites_view,
        name="manage_invites",
    ),
    path(
        "<slug:user_slug>/<slug:questionnaire_slug>/invites/add/",
        views.add_invite_view,
        name="add_invite",
    ),
    path(
        "<slug:user_slug>/<slug:questionnaire_slug>/invites/<int:invite_id>/revoke/",
        views.revoke_invite_view,
        name="revoke_invite",
    ),
    path(
        "<slug:user_slug>/<slug:questionnaire_slug>/nodes/add/",
        views.add_node_view,
        name="add_node",
    ),
    path(
        "<slug:user_slug>/<slug:questionnaire_slug>/nodes/<slug:node_slug>/edit/",
        views.edit_node_view,
        name="edit_node",
    ),
    path(
        "<slug:user_slug>/<slug:questionnaire_slug>/nodes/<slug:node_slug>/delete/",
        views.delete_node_view,
        name="delete_node",
    ),
    path(
        "<slug:user_slug>/<slug:questionnaire_slug>/nodes/<slug:node_slug>/set-start/",
        views.set_start_node_view,
        name="set_start_node",
    ),
    path(
        "<slug:user_slug>/<slug:questionnaire_slug>/nodes/<slug:node_slug>/edges/add/",
        views.add_edge_view,
        name="add_edge",
    ),
    path(
        "<slug:user_slug>/<slug:questionnaire_slug>/nodes/<slug:node_slug>/edges/<int:edge_id>/delete/",
        views.delete_edge_view,
        name="delete_edge",
    ),
    # Flatpages (must come before slug catch-alls)
    path("about/", flatpages_views.flatpage, {"url": "/about/"}, name="about"),
    # User dashboard (single slug catch-all for users)
    path(
        "<slug:user_slug>/",
        views.dashboard_view,
        name="dashboard",
    ),
    # Questionnaire player
    path(
        "<slug:questionnaire_slug>/complete/",
        views.complete_questionnaire_view,
        name="complete_questionnaire",
    ),
    path(
        "<slug:questionnaire_slug>/<slug:node_slug>/partial/",
        views.node_partial_view,
        name="node_partial",
    ),
    path(
        "<slug:questionnaire_slug>/<slug:node_slug>/answer/",
        views.answer_node_view,
        name="answer_node",
    ),
    path(
        "<slug:questionnaire_slug>/<slug:node_slug>/",
        views.play_node_view,
        name="play_node",
    ),
]
