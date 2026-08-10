"""orders payments and delivery

Revision ID: phase4_0001
Revises: phase3_0001
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "phase4_0001"
down_revision: str | Sequence[str] | None = "phase3_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _enum(name: str, *values: str) -> postgresql.ENUM:
    return postgresql.ENUM(*values, name=name, create_type=False)


order_status = _enum(
    "order_status",
    "PENDING",
    "APPROVED",
    "PENDING_DELIVERY",
    "DELIVERED",
    "FAILED",
    "UNFOUND",
    "CANCELLED",
)
order_payment_status = _enum("order_payment_status", "UNPAID", "PARTIAL", "PAID")
order_source = _enum("order_source", "ADMIN", "CUSTOMER")
payment_method = _enum("payment_method", "CASH", "MOBILE_MONEY", "BANK_TRANSFER", "OTHER")
payment_record_status = _enum("payment_record_status", "PENDING", "COLLECTED", "FAILED")
vehicle_type = _enum("delivery_vehicle_type", "MOTORCYCLE", "TRUCK", "VAN", "OTHER")
delivery_status = _enum(
    "delivery_status",
    "NOT_ASSIGNED",
    "ASSIGNED",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "FAILED",
)


def _id() -> sa.Column:
    return sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    ]


def _audit() -> list[sa.Column]:
    return [*_timestamps(), sa.Column("created_by", sa.UUID()), sa.Column("updated_by", sa.UUID())]


def _audit_constraints() -> list[sa.ForeignKeyConstraint]:
    return [
        sa.ForeignKeyConstraint(["created_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["admin_users.id"], ondelete="SET NULL"),
    ]


def _audit_indexes(table: str) -> None:
    op.create_index(f"ix_{table}_created_by", table, ["created_by"])
    op.create_index(f"ix_{table}_updated_by", table, ["updated_by"])


def upgrade() -> None:
    bind = op.get_bind()
    for enum in (
        order_status,
        order_payment_status,
        order_source,
        payment_method,
        payment_record_status,
        vehicle_type,
        delivery_status,
    ):
        enum.create(bind, checkfirst=True)

    op.create_table(
        "orders",
        _id(),
        sa.Column("order_number", sa.String(40), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("warehouse_id", sa.UUID(), nullable=False),
        sa.Column("status", order_status, server_default="PENDING", nullable=False),
        sa.Column("payment_status", order_payment_status, server_default="UNPAID", nullable=False),
        sa.Column("source", order_source, server_default="ADMIN", nullable=False),
        sa.Column("price_tier_id", sa.UUID(), nullable=False),
        sa.Column("subtotal", sa.Numeric(14, 2), nullable=False),
        sa.Column("discount_total", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("tax_total", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("delivery_address", sa.Text()),
        sa.Column("delivery_location", sa.String(200)),
        sa.Column("notes", sa.Text()),
        sa.Column("approved_by", sa.UUID()),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        *_audit(),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("subtotal >= 0", name="ck_orders_subtotal_nonnegative"),
        sa.CheckConstraint("discount_total >= 0", name="ck_orders_discount_nonnegative"),
        sa.CheckConstraint("tax_total >= 0", name="ck_orders_tax_nonnegative"),
        sa.CheckConstraint("total_amount >= 0", name="ck_orders_total_nonnegative"),
        *_audit_constraints(),
        sa.ForeignKeyConstraint(["approved_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["price_tier_id"], ["price_tiers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    _audit_indexes("orders")
    for column in (
        "approved_by",
        "customer_id",
        "warehouse_id",
        "status",
        "payment_status",
        "price_tier_id",
        "created_at",
    ):
        op.create_index(f"ix_orders_{column}", "orders", [column])
    op.create_index("ix_orders_order_number", "orders", ["order_number"], unique=True)

    op.create_table(
        "order_items",
        _id(),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(14, 2), nullable=False),
        sa.Column("price_tier_id", sa.UUID(), nullable=False),
        sa.Column("line_discount", sa.Numeric(14, 2), server_default="0", nullable=False),
        sa.Column("line_total", sa.Numeric(14, 2), nullable=False),
        sa.Column("allocated_quantity", sa.Integer(), server_default="0", nullable=False),
        *_audit(),
        sa.CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        sa.CheckConstraint("unit_price >= 0", name="ck_order_items_price_nonnegative"),
        sa.CheckConstraint("line_discount >= 0", name="ck_order_items_discount_nonnegative"),
        sa.CheckConstraint("line_total >= 0", name="ck_order_items_total_nonnegative"),
        sa.CheckConstraint(
            "allocated_quantity >= 0 AND allocated_quantity <= quantity",
            name="ck_order_items_allocated_valid",
        ),
        *_audit_constraints(),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["price_tier_id"], ["price_tiers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    _audit_indexes("order_items")
    for column in ("order_id", "product_id", "price_tier_id"):
        op.create_index(f"ix_order_items_{column}", "order_items", [column])

    op.create_table(
        "order_item_allocations",
        _id(),
        sa.Column("order_item_id", sa.UUID(), nullable=False),
        sa.Column("batch_id", sa.UUID(), nullable=False),
        sa.Column("warehouse_id", sa.UUID(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        *_audit(),
        sa.CheckConstraint("quantity > 0", name="ck_order_allocations_quantity_positive"),
        *_audit_constraints(),
        sa.ForeignKeyConstraint(["batch_id"], ["product_batches.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_item_id"], ["order_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["warehouse_id"], ["warehouses.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    _audit_indexes("order_item_allocations")
    for column in ("order_item_id", "batch_id", "warehouse_id"):
        op.create_index(f"ix_order_item_allocations_{column}", "order_item_allocations", [column])

    op.create_table(
        "order_status_history",
        _id(),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("from_status", order_status),
        sa.Column("to_status", order_status, nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("changed_by", sa.UUID()),
        *_timestamps(),
        sa.ForeignKeyConstraint(["changed_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("order_id", "to_status", "changed_by"):
        op.create_index(f"ix_order_status_history_{column}", "order_status_history", [column])

    op.create_table(
        "payments",
        _id(),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("method", payment_method, server_default="CASH", nullable=False),
        sa.Column("provider", sa.String(100)),
        sa.Column("transaction_ref", sa.String(150)),
        sa.Column("status", payment_record_status, server_default="COLLECTED", nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
        sa.Column("recorded_by", sa.UUID()),
        *_timestamps(),
        sa.CheckConstraint("amount > 0", name="ck_payments_amount_positive"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recorded_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("order_id", "status", "recorded_by"):
        op.create_index(f"ix_payments_{column}", "payments", [column])

    op.create_table(
        "delivery_agents",
        _id(),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("phone", sa.String(50), nullable=False),
        sa.Column("email", sa.String(320)),
        sa.Column("address", sa.Text()),
        sa.Column("vehicle_type", vehicle_type),
        sa.Column("id_proof_path", sa.String(500)),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_audit(),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        *_audit_constraints(),
        sa.PrimaryKeyConstraint("id"),
    )
    _audit_indexes("delivery_agents")
    op.create_index("ix_delivery_agents_is_active", "delivery_agents", ["is_active"])

    op.create_table(
        "deliveries",
        _id(),
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("agent_id", sa.UUID()),
        sa.Column("status", delivery_status, server_default="NOT_ASSIGNED", nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True)),
        sa.Column("dispatched_at", sa.DateTime(timezone=True)),
        sa.Column("delivered_at", sa.DateTime(timezone=True)),
        sa.Column("proof_path", sa.String(500)),
        sa.Column("notes", sa.Text()),
        *_audit(),
        *_audit_constraints(),
        sa.ForeignKeyConstraint(["agent_id"], ["delivery_agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    _audit_indexes("deliveries")
    op.create_index("ix_deliveries_order_id", "deliveries", ["order_id"], unique=True)
    for column in ("agent_id", "status"):
        op.create_index(f"ix_deliveries_{column}", "deliveries", [column])


def downgrade() -> None:
    for table in (
        "deliveries",
        "delivery_agents",
        "payments",
        "order_status_history",
        "order_item_allocations",
        "order_items",
        "orders",
    ):
        op.drop_table(table)
    bind = op.get_bind()
    for enum in (
        delivery_status,
        vehicle_type,
        payment_record_status,
        payment_method,
        order_source,
        order_payment_status,
        order_status,
    ):
        enum.drop(bind, checkfirst=True)
