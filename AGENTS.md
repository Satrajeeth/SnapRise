# Repository Guidelines

## Project Structure & Module Organization
Primary application code lives in `otp_service/`. Use `otp_service/app/` for FastAPI routes, config, Celery wiring, Redis helpers, and SQLAlchemy models. Database migrations live in `otp_service/alembic/versions/`, and any new tests should go in `otp_service/tests/` beside the app they cover. Supporting artifacts live at the repo root: `Generated_Postman_Collections/` contains API collections, and `fastapi-users/` is a nested upstream checkout for reference only unless you are intentionally syncing that dependency.

## Build, Test, and Development Commands
Run commands from `otp_service/` unless noted otherwise.

- `pip install -r requirements.txt`: install runtime and dev dependencies into a Python 3.11 virtualenv.
- `docker compose up --build`: start Postgres, Redis, RabbitMQ, the API, and the Celery worker.
- `uvicorn app.main:app --reload --port 8000`: run the FastAPI app locally without Docker.
- `celery -A app.core.celery_app worker --loglevel=info`: start the OTP retry worker.
- `alembic upgrade head`: apply the latest schema migrations.
- `pytest`: run the test suite.
- `black . && isort .`: format Python code before opening a PR.

## Coding Style & Naming Conventions
Target Python 3.11. Use 4-space indentation, `snake_case` for functions and modules, `PascalCase` for classes, and descriptive model names such as `OtpChallenge` or `ProviderConfig`. Black is configured with a line length of 88, and isort uses the Black profile. Keep route registration in `app/api/`, infrastructure code in `app/core/`, and persistence logic in `app/models/` or `app/db/`.

## Testing Guidelines
Pytest is configured in `pyproject.toml` with `tests` as the discovery root and `asyncio_mode = auto`. Name files `test_<feature>.py` and prefer focused async tests for API, Redis, Celery, and model behavior. Add regression tests for every bug fix and for each new migration or task flow. Run `pytest` locally before pushing.

## Commit & Pull Request Guidelines
Recent history favors short, imperative messages with prefixes like `feat:` and `Refactor`. Keep using that style consistently, for example `feat: add OTP provider fallback`. PRs should include a clear summary, note any schema or env changes, link the relevant issue, and attach request/response examples or screenshots when API behavior changes.

## Security & Configuration Tips
Copy `otp_service/.env.example` to `.env` and never commit secrets. Keep local ports aligned with `docker-compose.yml`, and update both runtime and sync database URLs when changing database settings for Alembic or app startup.
