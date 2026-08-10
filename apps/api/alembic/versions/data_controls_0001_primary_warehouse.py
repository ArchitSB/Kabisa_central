"""Guarantee at most one live primary warehouse.

Revision ID: data_controls_0001
Revises: phase6_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "data_controls_0001"
down_revision: str | None = "phase6_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            WITH chosen AS (
                SELECT id
                FROM warehouses
                WHERE deleted_at IS NULL
                ORDER BY is_primary DESC, is_active DESC, created_at ASC, id ASC
                LIMIT 1
            )
            UPDATE warehouses AS warehouse
            SET is_primary = (warehouse.id = chosen.id),
                is_active = CASE
                    WHEN warehouse.id = chosen.id THEN true
                    ELSE warehouse.is_active
                END
            FROM chosen
            WHERE warehouse.deleted_at IS NULL
            """
        )
    )
    op.create_index(
        "uq_warehouses_one_primary",
        "warehouses",
        ["is_primary"],
        unique=True,
        postgresql_where=sa.text("is_primary AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_warehouses_one_primary", table_name="warehouses")
