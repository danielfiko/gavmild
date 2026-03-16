# AGENTS.md

You must always follow the best practices outlined in this document. If there is a valid reason why you cannot follow one of these practices, you must inform the user and document the reasons.

You must review code related to your request to understand preferred style: for example, you must review existing routes before creating a new one.

## Project Overview

- Stack: Python 3.11, Flask, SQLAlchemy, Flask-Login, Flask-WTF, MariaDB, Docker Compose.
- App factory entrypoint: `app:create_app`.
- Primary runtime modes:
  - Development: Flask dev server on port 5005.
    - The app/ directory is mounted in the container in development mode, so generated files will be accessible here.
  - Production: Gunicorn on port 5005.

## Repository Structure

- `app/`: Main application package.
- `app/auth/`: Authentication flows, user model, auth routes/controllers.
- `app/wishlist/`: Wishlist views, API, models, Prisjakt integration.
- `app/webauthn/`: WebAuthn registration and authentication flows.
- `app/telegram/`: Telegram integration and bot startup.
- `app/admin/`: Admin pages and related access control.
- `app/static/`, `app/templates/`: Frontend assets and Jinja templates.
- `secrets/`: Local secret files mounted into containers (never expose values).
- `compose.yml`: Primary local orchestration definition.

## Dependency Management
```bash
uv add package_name # Add a new package dependency
uv add --group dev package_name # Add a dev dependency
uv remove package_name # Remove a package dependency
```

## Local Development Commands

- Docker:
```bash
docker compose up -d # Start development environment and detach session
docker compose down # Stop development environment (preserves volumes)
docker compose restart # Restart all services without destroying containers or volumes
docker compose logs # View logs from all services
docker compose logs -f # Follow logs in real-time from all services
docker compose logs -f service_name # Follow logs for a specific service
docker compose ps # List running services and their status
docker compose exec service_name bash # Open a bash shell in a running service container
```

## Coding Standards

- Keep changes minimal and focused; do not refactor unrelated code.
- Follow existing Flask blueprint pattern used across modules.
- Prefer explicit, readable controller logic over clever abstractions.
- Keep template, JS, and CSS changes scoped to the feature being modified.
- Preserve current naming and route conventions in each blueprint.
- Prefer existing dependencies over adding new ones when possible.
- For complex code, always consider using third-party libraries instead of writing new code that has to be maintained.
- Use keyword arguments instead of positional arguments when calling functions and methods.
- Do not put import statements inside functions unless necessary to prevent circular imports. Imports must be at the top of the file.
- Most caught exceptions must be logged with logger.exception.
- Always format and check Python files with ruff immediately after writing or editing them: uv run ruff format <file_path> and uv run ruff check --fix <file_path>. Do this for every Python file you create or modify, before moving on to the next step.
- No assert in production code.

## Typing

- Everything must be typed: function signatures (including return values), variables, and anything else.
- Use the union operator for multiple allowed types.
- Do not use Optional: use a union with None (i.e., str | None).
- Use typing library metaclasses instead of native types for objects and lists (i.e., Dict[str, str] and List[str] instead of dict or list).
- Avoid using Any unless absolutely necessary.
- If the schema is defined, use a dataclass with properly typed parameters instead of a dict.

## SQLAlchemy

- Always use async SQLAlchemy APIs with SQLAlchemy 2.0 syntax.
- Represent database tables with the declarative class system.
- Use Alembic to define migrations.

## Database and Startup Notes

- The app currently calls `db.create_all()` inside the app factory.
- The app also performs a startup schema patch for `user.is_admin` when missing.
- Do not introduce destructive schema changes without a migration plan.
- If editing model/schema behavior, document operational impact in your change summary.

## Telegram Bot Behavior

- `create_app()` starts the Telegram bot conditionally.
- Keep protection against duplicate bot start under Flask debug reloader.
- Avoid changes that would create multiple polling instances.

## Secrets and Security

- Never print or commit secret values from `secrets/` files.
- Treat tokens, API keys, and DB credentials as sensitive at all times.
- Avoid adding logs that could leak request bodies containing credentials.

## Agent Working Rules

- Before major edits, inspect related files for local conventions.
- After edits, run the smallest meaningful validation possible.
- If tests are absent for the changed area, mention that explicitly.
- Call out assumptions and potential regressions in your final summary.

## Validation Checklist

- Python syntax remains valid in changed files.
- Imports resolve and no obvious circular imports were introduced.
- Modified routes still match expected template/static resource paths.
- Docker startup path remains functional for local development.
