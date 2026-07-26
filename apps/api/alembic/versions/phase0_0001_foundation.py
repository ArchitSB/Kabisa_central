"""Create the Phase 0 migration baseline.

Revision ID: phase0_0001
Revises:
Create Date: 2026-07-26
"""

from collections.abc import Sequence

revision: str = "phase0_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Reserve the baseline; domain tables begin in Phase 1."""


def downgrade() -> None:
    """The baseline contains no schema objects to remove."""
