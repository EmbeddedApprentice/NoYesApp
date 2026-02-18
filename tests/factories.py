# pyright: reportUnknownLambdaType=false, reportUnknownArgumentType=false
# pyright: reportPrivateImportUsage=false, reportIncompatibleVariableOverride=false
# pyright: reportUnknownMemberType=false
import factory
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from noyesapp.data.models import (
    Edge,
    Node,
    NodeResponse,
    Profile,
    Questionnaire,
    QuestionnaireInvite,
    QuestionnaireSession,
)

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):  # type: ignore[misc]
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    slug = factory.LazyAttribute(lambda o: slugify(o.username))
    password = factory.django.Password("testpass123")


class ProfileFactory(factory.django.DjangoModelFactory):  # type: ignore[misc]
    class Meta:
        model = Profile

    user = factory.SubFactory(UserFactory)


class QuestionnaireFactory(factory.django.DjangoModelFactory):  # type: ignore[misc]
    class Meta:
        model = Questionnaire

    title = factory.Sequence(lambda n: f"Questionnaire {n}")
    slug = factory.Sequence(lambda n: f"questionnaire-{n}")
    owner = factory.SubFactory(UserFactory)


class NodeFactory(factory.django.DjangoModelFactory):  # type: ignore[misc]
    class Meta:
        model = Node

    questionnaire = factory.SubFactory(QuestionnaireFactory)
    slug = factory.Sequence(lambda n: f"node-{n}")
    content = factory.Sequence(lambda n: f"Node content {n}")
    node_type = Node.NodeType.QUESTION


class EdgeFactory(factory.django.DjangoModelFactory):  # type: ignore[misc]
    class Meta:
        model = Edge

    source = factory.SubFactory(NodeFactory)
    destination = factory.SubFactory(NodeFactory)
    answer_type = Edge.AnswerType.YES


class QuestionnaireSessionFactory(factory.django.DjangoModelFactory):  # type: ignore[misc]
    class Meta:
        model = QuestionnaireSession

    questionnaire = factory.SubFactory(QuestionnaireFactory)
    user = factory.SubFactory(UserFactory)


class NodeResponseFactory(factory.django.DjangoModelFactory):  # type: ignore[misc]
    class Meta:
        model = NodeResponse

    session = factory.SubFactory(QuestionnaireSessionFactory)
    node = factory.SubFactory(NodeFactory)
    order = factory.Sequence(lambda n: n + 1)
    answer_given = ""


class QuestionnaireInviteFactory(factory.django.DjangoModelFactory):  # type: ignore[misc]
    class Meta:
        model = QuestionnaireInvite

    questionnaire = factory.SubFactory(QuestionnaireFactory)
    invited_user = factory.SubFactory(UserFactory)
