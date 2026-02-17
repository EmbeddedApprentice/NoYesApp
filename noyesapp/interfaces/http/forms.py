from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.http import HttpRequest

from noyesapp.data.models import Edge, Node, Questionnaire

User = get_user_model()


class RegistrationForm(UserCreationForm):  # type: ignore[type-arg]
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        labels = {"username": "Nickname"}
        help_texts = {"username": "A display name shown to other users."}


class EmailAuthenticationForm(forms.Form):
    """Login form that authenticates by email instead of username."""

    email = forms.EmailField(widget=forms.EmailInput(attrs={"autofocus": True}))
    password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(
        self,
        request: HttpRequest | None = None,
        *args: object,
        **kwargs: object,
    ) -> None:
        self.request = request
        self.user_cache: User | None = None  # type: ignore[assignment]
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]

    def clean(self) -> dict[str, object]:
        email = self.cleaned_data.get("email")
        password = self.cleaned_data.get("password")

        if email is not None and password is not None:
            self.user_cache = authenticate(
                self.request, username=email, password=password
            )
            if self.user_cache is None:
                raise forms.ValidationError(
                    "Please enter a correct email and password.",
                    code="invalid_login",
                )
            if not self.user_cache.is_active:
                raise forms.ValidationError(
                    "This account is inactive.",
                    code="inactive",
                )
        return self.cleaned_data

    def get_user(self) -> User | None:  # type: ignore[return]
        return self.user_cache  # type: ignore[return-value]


class QuestionnaireForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = Questionnaire
        fields = ("title", "description")
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "form-control", "autofocus": True}
            ),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }


class NodeForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = Node
        fields = ("content", "node_type")
        labels = {"node_type": "Type"}
        widgets = {
            "content": forms.Textarea(
                attrs={"class": "form-control", "rows": 3, "autofocus": True}
            ),
            "node_type": forms.Select(attrs={"class": "form-select"}),
        }


class EdgeForm(forms.Form):
    answer_type = forms.ChoiceField(
        choices=Edge.AnswerType.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    destination = forms.ModelChoiceField(
        queryset=Node.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(
        self, questionnaire: Questionnaire, *args: object, **kwargs: object
    ) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.fields["destination"].queryset = Node.objects.filter(  # type: ignore[union-attr]
            questionnaire=questionnaire
        )
