# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

NoYesApp is a directed-graph questionnaire app. Users navigate questionnaires by answering YES/NO questions, reading statements (NEXT), and reaching terminal nodes. The graph supports loops and rejoins. See `docs/` for full requirements, technical spec, and implementation plan.

## Architecture: Django RAPID

This project follows the [Django RAPID architecture](https://www.django-rapid-architecture.org/) — horizontal layers instead of vertical apps.

```
noyesapp/
├── actions/          # State-changing business logic
├── data/
│   ├── migrations/
│   └── models/       # Minimal models (fields + Meta + __str__ only)
├── interfaces/
│   ├── management_commands/
│   └── http/         # Views, URLs, API
├── readers/          # Data retrieval logic
├── settings.py
└── wsgi.py
```

- `INSTALLED_APPS`: only `noyesapp.data` and `noyesapp.interfaces.management_commands`
- `ROOT_URLCONF`: `noyesapp.interfaces.http.urls`
- No business logic in models — use Actions (writes) and Readers (reads)

## Stack

- **Python**: 3.12+
- **Django**: 6.x (latest stable)
- **Database**: PostgreSQL
- **Frontend**: HTMX + Bootstrap 5
- **Templates**: Django templates with inheritance; partials use `_partial.html` naming
- **Package Manager**: uv
- **Type Checking**: pyright (strict mode)
- **Linting/Formatting**: Ruff (replaces black, isort, flake8)
- **Testing**: pytest + pytest-django + Factory Boy

## Commands

```bash
uv run pytest                         # Run all tests
uv run pytest -x --lf                 # Run last failed, stop on first failure
uv run pytest path/to/test_file.py    # Run a single test file
uv run pytest -k "test_name"          # Run tests matching name
uv run ruff check .                   # Lint
uv run ruff format .                  # Format
uv run pyright                        # Type check
uv run python manage.py runserver     # Dev server
uv run python manage.py makemigrations
uv run python manage.py migrate
uv sync                               # Install dependencies
```

## Code Conventions

- Type hints required everywhere; no `Any` types
- Function-based views preferred
- Early returns over nested conditionals
- Composition over inheritance
- Use `select_related()`/`prefetch_related()` to avoid N+1 queries
- ALWAYS use slugs in URLs — never expose database PKs/IDs
- Conventional Commits format (`feat:`, `fix:`, `docs:`, etc.)
- Branch naming: `{initials}/{description}`
- Test with Factory Boy and pytest fixtures; TDD approach

## Testing

Always run the full test suite (`uv run pytest`) after making changes and confirm all tests pass before committing.

## Database

Use Unix socket peer auth for local PostgreSQL connections (no password/TCP). Production database config must use `dj_database_url.config()` consistently — never mix manual env var parsing with `dj_database_url` imports.

## Git Workflow

Before using the `gh` CLI for commits or PRs, verify `gh auth status`. If not authenticated, prompt the user before proceeding.

## HTMX Patterns

- Views detect `HX-Request` header to return partials vs full pages
- Questionnaire player prefetches next-node partials on load (`hx-trigger="load"`)
- On answer click, swap prefetched content immediately (no network wait)
- Use `hx-indicator` for loading states during prefetch

## Key Documentation

- `docs/technical_spec.md` — architecture, stack, HTMX strategy, URL scheme
- `docs/noyesapp_requirements.md` — app purpose, graph behavior, user stories
- `docs/noyesapp_plan.md` — implementation phases

## Claude Code Configuration

Copied from `claude-code-django/` reference repo:
- `.claude/settings.json` — hooks for auto-format, auto-test, type checking, linting, branch protection
- Skills: django-models, django-forms, django-templates, htmx-patterns, pytest-django-patterns, systematic-debugging, django-extensions
- Agents: code-reviewer, github-workflow
- Commands: /onboard, /pr-review, /pr-summary, /code-quality
