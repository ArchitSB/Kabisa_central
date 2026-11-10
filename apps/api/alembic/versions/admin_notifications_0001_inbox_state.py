"""Persist each staff member's notification inbox watermark.

Revision ID: admin_notifications_0001
Revises: storefront_0001
"""

import sqlalchemy as sa
from alembic import op

revision = "admin_notifications_0001"
down_revision = "storefront_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_notification_states",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("opened_through", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["admin_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("admin_notification_states")
