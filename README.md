# NoYesApp

A directed-graph questionnaire application built with Django, HTMX, and PostgreSQL.

Users navigate questionnaires node by node — answering YES/NO questions, reading statements, and reaching terminal endpoints. The graph supports loops and rejoins (not a strict tree), so questionnaire designers can build branching, cyclical, or converging paths.

## Features

- **Graph-based questionnaires** — nodes connected by typed edges (YES, NO, NEXT)
- **Three node types** — Question (YES/NO), Statement (NEXT), Terminal (end of path)
- **Access control** — questionnaires can be Public, Private, or Invite-Only
- **Instant responses** — HTMX prefetches the next node on page load; answer clicks feel immediate with no network wait
- **Anonymous play** — public questionnaires need no account to play
- **Response history** — logged-in users can review their path through completed questionnaires
- **Visual editor** — authenticated users create and edit questionnaires with a graph editor

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| Framework | Django 6.x |
| Database | PostgreSQL |
| Frontend | HTMX + Bootstrap 5 |
| Package manager | uv |
| Type checking | pyright (strict) |
| Linting / formatting | Ruff |
| Testing | pytest + pytest-django + Factory Boy |

## Architecture

NoYesApp follows the [Django RAPID architecture](https://www.django-rapid-architecture.org/) — horizontal layers instead of vertical Django apps:

```
noyesapp/
├── actions/        # State-changing business logic
├── data/
│   ├── migrations/
│   └── models/     # Minimal models (fields + Meta + __str__ only)
├── interfaces/
│   ├── management_commands/
│   └── http/       # Views, URLs
├── readers/        # Data retrieval logic
├── settings.py
└── wsgi.py
```

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL
- [uv](https://docs.astral.sh/uv/)

### Setup

```bash
# Clone the repo
git clone https://github.com/EmbeddedApprentice/NoYesApp.git
cd NoYesApp

# Install dependencies
uv sync

# Configure environment (copy and edit as needed)
cp .env.example .env

# Run migrations
uv run python manage.py migrate

# Start the dev server
uv run python manage.py runserver
```

### Running Tests

```bash
uv run pytest                   # All tests
uv run pytest -x --lf           # Stop on first failure, re-run last failed
uv run pytest path/to/test.py   # Single file
```

### Code Quality

```bash
uv run ruff check .             # Lint
uv run ruff format .            # Format
uv run pyright                  # Type check
```

## Authors

- **Doug** — project owner
- **[Claude](https://claude.ai)** (Anthropic) — primary implementation via [Claude Code](https://claude.ai/claude-code)
