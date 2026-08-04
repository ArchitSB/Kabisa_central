"""Add immutable audit records and production query indexes.

Revision ID: phase6_0001
Revises: phase5_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "phase6_0001"
down_revision: str | None = "phase5_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("changes", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_entity_type", "audit_logs", ["entity_type"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    op.create_index(
        "ix_audit_logs_entity_created_at",
        "audit_logs",
        ["entity_type", "created_at"],
    )

    op.create_index("ix_orders_status_created_at", "orders", ["status", "created_at"])
    op.create_index(
        "ix_orders_payment_status_created_at",
        "orders",
        ["payment_status", "created_at"],
    )
    op.create_index(
        "ix_orders_customer_created_at",
        "orders",
        ["customer_id", "created_at"],
    )
    op.create_index(
        "ix_orders_warehouse_created_at",
        "orders",
        ["warehouse_id", "created_at"],
    )
    op.create_index("ix_payments_order_status", "payments", ["order_id", "status"])
    op.create_index(
        "ix_payments_status_created_at",
        "payments",
        ["status", "created_at"],
    )
    op.create_index(
        "ix_product_batches_warehouse_status_expiry",
        "product_batches",
        ["warehouse_id", "status", "expiry_date"],
    )
    op.create_index(
        "ix_product_batches_product_status_expiry",
        "product_batches",
        ["product_id", "status", "expiry_date"],
    )
    op.create_index(
        "ix_stock_movements_warehouse_type_created",
        "stock_movements",
        ["warehouse_id", "movement_type", "created_at"],
    )
    op.create_index(
        "ix_stock_movements_batch_type_created",
        "stock_movements",
        ["batch_id", "movement_type", "created_at"],
    )
    op.create_index(
        "ix_customers_status_created_at",
        "customers",
        ["status", "created_at"],
    )

    op.execute(
        sa.text(
            """
            INSERT INTO permissions (id, code, description, "group", created_at, updated_at)
            VALUES (
                gen_random_uuid(),
                'audit.view',
                'View immutable administrative audit records.',
                'admin',
                now(),
                now()
            )
            ON CONFLICT (code) DO UPDATE
            SET description = EXCLUDED.description,
                "group" = EXCLUDED."group",
                updated_at = now()
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id, created_at, updated_at)
            SELECT r.id, p.id, now(), now()
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name IN ('super_admin', 'manager')
              AND p.code = 'audit.view'
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id = (SELECT id FROM permissions WHERE code = 'audit.view')
            """
        )
    )
    op.execute(sa.text("DELETE FROM permissions WHERE code = 'audit.view'"))

    op.drop_index("ix_customers_status_created_at", table_name="customers")
    op.drop_index("ix_stock_movements_batch_type_created", table_name="stock_movements")
    op.drop_index("ix_stock_movements_warehouse_type_created", table_name="stock_movements")
    op.drop_index("ix_product_batches_product_status_expiry", table_name="product_batches")
    op.drop_index("ix_product_batches_warehouse_status_expiry", table_name="product_batches")
    op.drop_index("ix_payments_status_created_at", table_name="payments")
    op.drop_index("ix_payments_order_status", table_name="payments")
    op.drop_index("ix_orders_warehouse_created_at", table_name="orders")
    op.drop_index("ix_orders_customer_created_at", table_name="orders")
    op.drop_index("ix_orders_payment_status_created_at", table_name="orders")
    op.drop_index("ix_orders_status_created_at", table_name="orders")
    op.drop_table("audit_logs")
