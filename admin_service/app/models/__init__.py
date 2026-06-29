"""Model registry.

Alembic's ``env.py`` does ``import app.models`` so every model must be imported
here for autogenerate and the mapper to see it.
"""

from app.models.lead import Lead

__all__ = ["Lead"]
