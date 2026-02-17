# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false
from django.db import migrations


def populate_site_and_flatpages(apps: object, schema_editor: object) -> None:
    Site = apps.get_model("sites", "Site")  # type: ignore[union-attr]
    FlatPage = apps.get_model("flatpages", "FlatPage")  # type: ignore[union-attr]

    # Update the default Site (created by sites migration)
    site, _ = Site.objects.update_or_create(
        pk=1,
        defaults={"domain": "localhost:8000", "name": "NoYesApp"},
    )

    # Landing page
    landing = FlatPage.objects.create(
        url="/",
        title="Welcome to NoYesApp",
        content=(
            "<p class='lead'>NoYesApp is a directed-graph questionnaire platform. "
            "Navigate through questions by answering YES or NO, read statements, "
            "and reach your conclusion.</p>"
            "<p>Browse the published questionnaires below to get started, "
            "or <a href='/register/'>create an account</a> to build your own.</p>"
        ),
    )
    landing.sites.add(site)

    # About page
    about = FlatPage.objects.create(
        url="/about/",
        title="About NoYesApp",
        content=(
            "<h3>What is NoYesApp?</h3>"
            "<p>NoYesApp is a directed-graph questionnaire application. "
            "Authors create questionnaires as graphs of interconnected nodes &mdash; "
            "questions with YES/NO answers, informational statements, and terminal endpoints. "
            "The graph structure supports loops and rejoins, enabling complex decision trees.</p>"
            "<h3>How it works</h3>"
            "<ul>"
            "<li><strong>Questions</strong> present a YES or NO choice, each leading to a different node.</li>"
            "<li><strong>Statements</strong> display information and advance with a NEXT button.</li>"
            "<li><strong>Terminals</strong> mark the end of a path through the questionnaire.</li>"
            "</ul>"
            "<h3>Built by</h3>"
            "<p>NoYesApp was built by Claude, an AI assistant by Anthropic.</p>"
        ),
    )
    about.sites.add(site)


def remove_flatpages(apps: object, schema_editor: object) -> None:
    FlatPage = apps.get_model("flatpages", "FlatPage")  # type: ignore[union-attr]
    FlatPage.objects.filter(url__in=["/", "/about/"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("data", "0003_questionnairesession_noderesponse"),
        ("sites", "0002_alter_domain_unique"),
        ("flatpages", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            populate_site_and_flatpages,
            remove_flatpages,
        ),
    ]
