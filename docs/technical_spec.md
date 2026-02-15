# Technical Specification

## Architecture: Django RAPID

NoYesApp follows the [Django RAPID architecture](https://www.django-rapid-architecture.org/) — horizontal layers instead of vertical Django apps.

- **Readers** — data retrieval logic
- **Actions** — state-changing business logic
- **Models** — minimal: field declarations, `Meta`, `__str__` only (no business logic)
- **Interfaces** — HTTP views and management commands

### Project Structure

```
noyesapp/
├── actions/
│   └── questionnaires.py
├── data/
│   ├── migrations/
│   │   └── 0001_initial.py
│   └── models/
│       └── questionnaire.py
├── interfaces/
│   ├── management_commands/
│   │   └── management/
│   │       └── commands/
│   │           └── some_management_command.py
│   └── http/
│       ├── api/
│       │   ├── urls.py
│       │   └── views.py
│       └── urls.py
├── readers/
│   └── questionnaires.py
├── settings.py
└── wsgi.py
```

### Django Configuration

- `INSTALLED_APPS`: only `noyesapp.data` and `noyesapp.interfaces.management_commands`
- `ROOT_URLCONF`: `noyesapp.interfaces.http.urls`

## Application Stack

- **Python**: 3.12+
- **Django**: 6.x (latest stable)
- **Database**: PostgreSQL
- **Frontend**: HTMX (dynamic questionnaire navigation) + Bootstrap 5 (styling)
- **Templates**: Django templates with inheritance
- **Optional**: django-readers (for reader composition/piping)

## HTMX & Template Strategy

- Partial templates use `_partial.html` naming convention for HTMX fragment responses
- Views detect `HX-Request` header to return partials vs full pages

### Questionnaire Player Prefetch Pattern

The questionnaire player uses HTMX to **prefetch** next-node partials on page load so responses feel instant:

1. On page load, use `hx-get` with `hx-trigger="load"` to prefetch both YES and NO next-node partials into hidden containers
2. On YES/NO button click, swap the prefetched content into the visible question area (no network wait)
3. Include `hx-indicator` for loading states on the initial prefetch
4. NEXT buttons (statement nodes) work the same way — single prefetch, swap on click
5. Terminal nodes (no outgoing edges): no prefetch, display final content

## Package Management & Tooling

- **uv** — package manager + task runner
- **Ruff** — linting + formatting (replaces black, isort, flake8)
- **pyright** — strict mode type checking

## Testing

- **pytest** + **pytest-django** — test runner
- **Factory Boy** — model factories

## Deferred (Not in MVP)

- Celery + Redis (async tasks — email notifications, analytics)

## Claude Code Integration

Configuration copied from the `claude-code-django/` reference repo.

### Settings & Hooks (`.claude/settings.json`)

- Auto-format with Ruff on file save
- Auto-run tests on test file changes
- pyright type checking
- Ruff linting
- Main branch edit protection

### Skills to Copy

- django-models, django-forms, django-templates
- htmx-patterns, pytest-django-patterns
- systematic-debugging, django-extensions

### Agents to Copy

- code-reviewer (post-change review)
- github-workflow (git operations)

### Commands to Copy

- /onboard, /pr-review, /pr-summary, /code-quality

### Hooks to Copy

- Skill evaluation system (prompt analysis -> skill suggestions)

## MCP Servers

- **GitHub MCP** — PR/issue workflows
- **PostgreSQL MCP** — direct DB inspection during development

## URL Scheme

```
# Public pages
noyesapp/                                              # Landing page (list of open questionnaires)
noyesapp/about/                                        # About page

# Auth
noyesapp/register/                                     # User registration
noyesapp/login/                                        # Login
noyesapp/logout/                                       # Logout

# Questionnaire player (public, anonymous allowed)
noyesapp/<questionnaire_slug>/                         # Start questionnaire (first node)
noyesapp/<questionnaire_slug>/<node_slug>/             # View/answer a specific node
noyesapp/<questionnaire_slug>/complete/                # Terminal node / completion page

# User dashboard (authenticated)
noyesapp/<user_slug>/                                  # User profile / dashboard
noyesapp/<user_slug>/history/                          # List of completed questionnaires
noyesapp/<user_slug>/<questionnaire_slug>/results/     # Review path through a completed questionnaire

# Questionnaire editor (authenticated)
noyesapp/<user_slug>/create/                           # Create new questionnaire
noyesapp/<user_slug>/<questionnaire_slug>/edit/        # Edit questionnaire (graph editor)
noyesapp/<user_slug>/<questionnaire_slug>/delete/      # Delete questionnaire
noyesapp/<user_slug>/<questionnaire_slug>/publish/     # Publish/unpublish questionnaire

# HTMX partials (not user-facing, used for prefetch/swap)
noyesapp/<questionnaire_slug>/<node_slug>/partial/     # Prefetch node content as partial
```
