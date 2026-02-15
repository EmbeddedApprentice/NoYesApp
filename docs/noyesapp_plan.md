# NoYesApp Implementation Plan

## Per-Phase Requirements

Every phase must follow these rules:

- Write pytest tests for every new feature; run them before moving on
- Check for N+1 queries in all views (use `select_related`/`prefetch_related`)
- Build out `admin.py` with Django admin registration for each new model
- ALWAYS use slugs for URL navigation — never expose database PKs/IDs in URLs

## Phase 1: Project Scaffolding

- Initialize Django project with RAPID architecture layout
- Configure uv with `pyproject.toml`
- Set up PostgreSQL database connection
- Configure Ruff, pyright, pytest
- Copy Claude Code configuration from `claude-code-django/` reference repo
- Initialize git repository
- Verify `uv run python manage.py runserver` works

## Phase 2: User System

- User model (or extend Django's built-in User)
- Profile model linked to User (for future expansion, not MVP-critical)
- User registration view + template
- Login/logout views + templates
- User slug generation
- Django admin registration for User/Profile
- Tests for registration, login, logout, profile creation

## Phase 3: Data Model

- Questionnaire model (title, slug, owner, published status, timestamps)
- Node model (questionnaire FK, slug, content, node type enum)
- Edge model (source node FK, destination node FK, answer type)
- Model validation (question nodes need 2 edges, statement nodes need 1, terminals need 0)
- Django admin registration with inline editors
- Factory Boy factories for all models
- Tests for model creation, validation, graph integrity

## Phase 4: Questionnaire Player

- Start questionnaire view (redirect to first node)
- Node display view (show question/statement content)
- Answer handling (record response, advance to next node)
- Session/response tracking (record the user's path through the graph)
- Terminal/completion view
- HTMX partials for node prefetching
- Tests for navigation, response recording, edge cases (loops, dead ends)

## Phase 5: Questionnaire Editor

- Create questionnaire view + form
- Edit questionnaire view (add/remove/reorder nodes)
- Node editor (set content, type, outgoing edges)
- Graph visualization or structured list UI
- Delete questionnaire (with confirmation)
- Publish/unpublish toggle
- Tests for CRUD operations, permission checks, graph validation

## Phase 6: Polish

- HTMX prefetch interactions (instant-feel responses)
- Bootstrap 5 styling across all pages
- Landing page with published questionnaire listing
- About page
- User dashboard with response history
- Error handling (404s, permission denied, invalid graph states)
- Final test pass across all features
