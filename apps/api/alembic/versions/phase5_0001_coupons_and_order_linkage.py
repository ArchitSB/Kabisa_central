"""Add coupons and order coupon snapshots.

Revision ID: phase5_0001
Revises: phase4_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "phase5_0001"
down_revision: str | None = "phase4_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    coupon_discount_type = postgresql.ENUM(
        "PERCENT", "FLAT", name="coupon_discount_type", create_type=False
    )
    coupon_discount_type.create(op.get_bind(), checkfirst=True)
    op.create_table(
        "coupons",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("discount_type", coupon_discount_type, nullable=False),
        sa.Column("discount_value", sa.Numeric(14, 2), nullable=False),
        sa.Column("min_order_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("usage_limit", sa.Integer(), nullable=True),
        sa.Column("used_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("discount_value > 0", name="ck_coupons_discount_positive"),
        sa.CheckConstraint(
            "discount_type <> 'PERCENT' OR discount_value <= 100",
            name="ck_coupons_percent_maximum",
        ),
        sa.CheckConstraint(
            "min_order_amount IS NULL OR min_order_amount >= 0",
            name="ck_coupons_min_order_nonnegative",
        ),
        sa.CheckConstraint(
            "usage_limit IS NULL OR usage_limit > 0",
            name="ck_coupons_usage_limit_positive",
        ),
        sa.CheckConstraint("used_count >= 0", name="ck_coupons_used_count_nonnegative"),
        sa.CheckConstraint(
            "usage_limit IS NULL OR used_count <= usage_limit",
            name="ck_coupons_usage_within_limit",
        ),
        sa.CheckConstraint("start_date <= end_date", name="ck_coupons_date_range"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_coupons_code", "coupons", ["code"], unique=True)
    op.create_index("ix_coupons_is_active", "coupons", ["is_active"])
    op.create_index("ix_coupons_created_by", "coupons", ["created_by"])
    op.create_index("ix_coupons_updated_by", "coupons", ["updated_by"])

    op.add_column("orders", sa.Column("coupon_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("orders", sa.Column("coupon_code", sa.String(length=80), nullable=True))
    op.add_column(
        "orders",
        sa.Column("coupon_discount", sa.Numeric(14, 2), server_default="0", nullable=False),
    )
    op.create_check_constraint(
        "ck_orders_coupon_discount_nonnegative", "orders", "coupon_discount >= 0"
    )
    op.create_foreign_key(
        "fk_orders_coupon_id_coupons",
        "orders",
        "coupons",
        ["coupon_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_orders_coupon_id", "orders", ["coupon_id"])


def downgrade() -> None:
    op.drop_index("ix_orders_coupon_id", table_name="orders")
    op.drop_constraint("fk_orders_coupon_id_coupons", "orders", type_="foreignkey")
    op.drop_constraint("ck_orders_coupon_discount_nonnegative", "orders", type_="check")
    op.drop_column("orders", "coupon_discount")
    op.drop_column("orders", "coupon_code")
    op.drop_column("orders", "coupon_id")
    op.drop_table("coupons")
    postgresql.ENUM(name="coupon_discount_type").drop(op.get_bind(), checkfirst=True)
