from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from noyesapp.data.models import (
    Edge,
    Node,
    NodeResponse,
    Profile,
    Questionnaire,
    QuestionnaireInvite,
    QuestionnaireSession,
    User,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):  # type: ignore[type-arg]
    list_display = ("username", "email", "slug", "is_staff")
    prepopulated_fields = {"slug": ("username",)}
    fieldsets = (
        *UserAdmin.fieldsets,  # type: ignore[misc]
        ("Extra", {"fields": ("slug",)}),
    )
    add_fieldsets = (
        *UserAdmin.add_fieldsets,  # type: ignore[misc]
        ("Extra", {"fields": ("email", "slug")}),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("user", "created_at", "updated_at")
    raw_id_fields = ("user",)


class QuestionnaireInviteInline(admin.TabularInline):  # type: ignore[type-arg]
    model = QuestionnaireInvite
    fields = ("invited_user", "created_at")
    readonly_fields = ("created_at",)
    extra = 0
    raw_id_fields = ("invited_user",)


class NodeInline(admin.TabularInline):  # type: ignore[type-arg]
    model = Node
    fields = ("slug", "content", "node_type")
    extra = 1


class EdgeInline(admin.TabularInline):  # type: ignore[type-arg]
    model = Edge
    fk_name = "source"
    fields = ("answer_type", "destination")
    extra = 1


@admin.register(Questionnaire)
class QuestionnaireAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("title", "slug", "owner", "access_type", "created_at")
    list_filter = ("access_type",)
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    raw_id_fields = ("owner", "start_node")
    inlines = [NodeInline, QuestionnaireInviteInline]  # pyright: ignore[reportUnknownVariableType]


@admin.register(QuestionnaireInvite)
class QuestionnaireInviteAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("questionnaire", "invited_user", "created_at")
    list_select_related = ("questionnaire", "invited_user")
    raw_id_fields = ("questionnaire", "invited_user")


@admin.register(Node)
class NodeAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("slug", "questionnaire", "node_type", "created_at")
    list_filter = ("node_type",)
    raw_id_fields = ("questionnaire",)
    inlines = [EdgeInline]  # pyright: ignore[reportUnknownVariableType]


@admin.register(Edge)
class EdgeAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("source", "answer_type", "destination", "created_at")
    list_filter = ("answer_type",)
    list_select_related = ("source", "destination")
    raw_id_fields = ("source", "destination")


class NodeResponseInline(admin.TabularInline):  # type: ignore[type-arg]
    model = NodeResponse
    fields = ("order", "node", "answer_given", "created_at")
    readonly_fields = ("created_at",)
    extra = 0


@admin.register(QuestionnaireSession)
class QuestionnaireSessionAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = (
        "questionnaire",
        "user",
        "is_complete",
        "started_at",
        "completed_at",
    )
    list_filter = ("is_complete",)
    list_select_related = ("questionnaire", "user")
    raw_id_fields = ("questionnaire", "user")
    inlines = [NodeResponseInline]  # pyright: ignore[reportUnknownVariableType]


@admin.register(NodeResponse)
class NodeResponseAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    list_display = ("session", "node", "answer_given", "order", "created_at")
    list_select_related = ("session", "node")
    raw_id_fields = ("session", "node")
