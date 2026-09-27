"""customer storefront and mobile foundation

Revision ID: storefront_0001
Revises: data_controls_0001
Create Date: 2026-09-12 00:15:13.801812
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "storefront_0001"
down_revision: str | Sequence[str] | None = "data_controls_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index(
        "ix_products_name_trgm",
        "products",
        ["name"],
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_products_generic_trgm",
        "products",
        ["generic_name"],
        postgresql_using="gin",
        postgresql_ops={"generic_name": "gin_trgm_ops"},
    )
    # Additive storefront tables. Existing commerce tables and data are preserved.
    op.create_table(
        "customer_otp_codes",
        sa.Column("identifier", sa.String(length=320), nullable=False),
        sa.Column("channel", sa.String(length=10), nullable=False),
        sa.Column("purpose", sa.String(length=30), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.CheckConstraint("channel IN ('SMS','EMAIL')", name="ck_otp_channel"),
        sa.CheckConstraint(
            "purpose IN ('REGISTRATION','LOGIN','PASSWORD_RESET','VERIFY_CONTACT')",
            name="ck_otp_purpose",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_customer_otp_codes_identifier"), "customer_otp_codes", ["identifier"], unique=False
    )
    op.create_table(
        "storefront_announcements",
        sa.Column("message", sa.String(length=1000), nullable=False),
        sa.Column("type", sa.String(length=20), server_default="info", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_storefront_announcements_created_by"),
        "storefront_announcements",
        ["created_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_storefront_announcements_updated_by"),
        "storefront_announcements",
        ["updated_by"],
        unique=False,
    )
    op.create_table(
        "storefront_banners",
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("subtitle", sa.Text(), nullable=True),
        sa.Column("image_path", sa.String(length=500), nullable=True),
        sa.Column("mobile_image_path", sa.String(length=500), nullable=True),
        sa.Column("link_url", sa.String(length=500), nullable=True),
        sa.Column("link_label", sa.String(length=100), nullable=True),
        sa.Column("placement", sa.String(length=30), server_default="HOME_HERO", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_storefront_banners_created_by"), "storefront_banners", ["created_by"], unique=False
    )
    op.create_index(
        op.f("ix_storefront_banners_updated_by"), "storefront_banners", ["updated_by"], unique=False
    )
    op.create_table(
        "storefront_collections",
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("subtitle", sa.Text(), nullable=True),
        sa.Column("mode", sa.String(length=20), server_default="MANUAL", nullable=False),
        sa.Column(
            "rules", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(
        op.f("ix_storefront_collections_created_by"),
        "storefront_collections",
        ["created_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_storefront_collections_updated_by"),
        "storefront_collections",
        ["updated_by"],
        unique=False,
    )
    op.create_table(
        "storefront_faqs",
        sa.Column("question", sa.String(length=500), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_storefront_faqs_created_by"), "storefront_faqs", ["created_by"], unique=False
    )
    op.create_index(
        op.f("ix_storefront_faqs_updated_by"), "storefront_faqs", ["updated_by"], unique=False
    )
    op.create_table(
        "storefront_menu_items",
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("link_url", sa.String(length=500), nullable=False),
        sa.Column("placement", sa.String(length=20), server_default="HEADER", nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_storefront_menu_items_created_by"),
        "storefront_menu_items",
        ["created_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_storefront_menu_items_updated_by"),
        "storefront_menu_items",
        ["updated_by"],
        unique=False,
    )
    op.create_table(
        "storefront_pages",
        sa.Column("slug", sa.String(length=180), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(
        op.f("ix_storefront_pages_created_by"), "storefront_pages", ["created_by"], unique=False
    )
    op.create_index(
        op.f("ix_storefront_pages_updated_by"), "storefront_pages", ["updated_by"], unique=False
    )
    op.create_table(
        "storefront_testimonials",
        sa.Column("author", sa.String(length=150), nullable=False),
        sa.Column("organisation", sa.String(length=200), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_storefront_testimonials_created_by"),
        "storefront_testimonials",
        ["created_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_storefront_testimonials_updated_by"),
        "storefront_testimonials",
        ["updated_by"],
        unique=False,
    )
    op.create_table(
        "carts",
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("warehouse_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="ACTIVE", nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('ACTIVE','CONVERTED','ABANDONED')", name="ck_cart_status"),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
        ),
        sa.ForeignKeyConstraint(
            ["warehouse_id"],
            ["warehouses.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_carts_customer_id"), "carts", ["customer_id"], unique=False)
    op.create_index(
        "uq_customer_active_cart",
        "carts",
        ["customer_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE' AND deleted_at IS NULL"),
    )
    op.create_table(
        "customer_notifications",
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "payload", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivery_attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_customer_notifications_customer_id"),
        "customer_notifications",
        ["customer_id"],
        unique=False,
    )
    op.create_table(
        "customer_users",
        sa.Column("customer_id", sa.UUID(), nullable=True),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("role", sa.String(length=20), server_default="OWNER", nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("role IN ('OWNER','STAFF')", name="ck_customer_user_role"),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("phone"),
    )
    op.create_index(
        op.f("ix_customer_users_customer_id"), "customer_users", ["customer_id"], unique=False
    )
    op.create_table(
        "favourites",
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id", "product_id", name="uq_favourite_product"),
    )
    op.create_index(op.f("ix_favourites_customer_id"), "favourites", ["customer_id"], unique=False)
    op.create_table(
        "order_templates",
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_order_templates_customer_id"), "order_templates", ["customer_id"], unique=False
    )
    op.create_table(
        "storefront_collection_items",
        sa.Column("collection_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"], ["storefront_collections.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("collection_id", "product_id", name="uq_collection_product"),
    )
    op.create_index(
        op.f("ix_storefront_collection_items_collection_id"),
        "storefront_collection_items",
        ["collection_id"],
        unique=False,
    )
    op.create_table(
        "cart_items",
        sa.Column("cart_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.CheckConstraint("quantity > 0 AND quantity <= 100000", name="ck_cart_quantity"),
        sa.ForeignKeyConstraint(["cart_id"], ["carts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cart_id", "product_id", name="uq_cart_product"),
    )
    op.create_index(op.f("ix_cart_items_cart_id"), "cart_items", ["cart_id"], unique=False)
    op.create_table(
        "customer_sessions",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("customer_user_id", sa.UUID(), nullable=False),
        sa.Column("device_label", sa.String(length=150), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.ForeignKeyConstraint(["customer_user_id"], ["customer_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_customer_sessions_customer_user_id"),
        "customer_sessions",
        ["customer_user_id"],
        unique=False,
    )
    op.create_table(
        "device_tokens",
        sa.Column("customer_user_id", sa.UUID(), nullable=False),
        sa.Column("platform", sa.String(length=10), nullable=False),
        sa.Column("token", sa.String(length=500), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.CheckConstraint("platform IN ('WEB','ANDROID','IOS')", name="ck_device_platform"),
        sa.ForeignKeyConstraint(["customer_user_id"], ["customer_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(
        op.f("ix_device_tokens_customer_user_id"),
        "device_tokens",
        ["customer_user_id"],
        unique=False,
    )
    op.create_table(
        "order_template_items",
        sa.Column("template_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.CheckConstraint("quantity > 0 AND quantity <= 100000", name="ck_template_quantity"),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
        ),
        sa.ForeignKeyConstraint(["template_id"], ["order_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_id", "product_id", name="uq_template_product"),
    )
    op.create_index(
        op.f("ix_order_template_items_template_id"),
        "order_template_items",
        ["template_id"],
        unique=False,
    )
    op.create_table(
        "prescription_uploads",
        sa.Column("order_id", sa.UUID(), nullable=True),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="PENDING", nullable=False),
        sa.Column("reviewed_by", sa.UUID(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.CheckConstraint(
            "status IN ('PENDING','APPROVED','REJECTED')", name="ck_prescription_status"
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["admin_users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_prescription_uploads_customer_id"),
        "prescription_uploads",
        ["customer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_prescription_uploads_order_id"), "prescription_uploads", ["order_id"], unique=False
    )
    op.create_table(
        "store_order_metadata",
        sa.Column("order_id", sa.UUID(), nullable=False),
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=100), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("payment_method", sa.String(length=30), nullable=False),
        sa.Column(
            "delivery_fee", sa.Numeric(precision=14, scale=2), server_default="0", nullable=False
        ),
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["customer_id"],
            ["customers.id"],
        ),
        sa.ForeignKeyConstraint(
            ["order_id"],
            ["orders.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id", "idempotency_key", name="uq_store_order_idempotency"),
        sa.UniqueConstraint("order_id"),
    )
    op.create_index(
        op.f("ix_store_order_metadata_customer_id"),
        "store_order_metadata",
        ["customer_id"],
        unique=False,
    )
    # ### end Alembic commands ###

    # Persist installation defaults without overwriting staff configuration.
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.guest_price_visibility", value='"login_to_see"')
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.unverified_price_visibility", value='"visible"')
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.guest_price_tier", value='"COMMUNITY"')
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.min_order_value", value="0")
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.delivery_fee_mode", value='"flat"')
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.delivery_fee_value", value="0")
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.free_delivery_threshold", value="0")
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.delivery_zones", value="{}")
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.support_phone", value='""')
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.support_whatsapp", value='""')
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.support_email", value='""')
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.business_hours", value='""')
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.low_stock_display_threshold", value="10")
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.enable_registration", value="true")
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.require_verification_to_order", value="true")
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.enable_reviews", value="false")
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.enable_wishlist", value="true")
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.maintenance_mode", value="false")
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(
            key="storefront.maintenance_message",
            value='"We are making a few improvements. Please check back shortly."',
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.announcement_enabled", value="true")
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.social_links", value="{}")
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.seo_title", value='"Kabisa Pharmacy"')
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(
            key="storefront.seo_description",
            value='"Medicines and medical supplies for licensed healthcare businesses."',
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.seo_og_image", value='""')
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.tax_rate", value="0")
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.trust_badges", value="[]")
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.facility_count", value="0")
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.home_eyebrow", value='"Your partner in better care"')
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(
            key="storefront.home_categories_title", value='"Care starts with the right supplies"'
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(
            key="storefront.home_categories_subtitle",
            value='"Find what your facility needs, all in one place."',
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(
            key="storefront.home_featured_title", value='"Everyday essentials, reliably supplied"'
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(
            key="storefront.home_featured_subtitle",
            value='"Explore medicines and supplies from our catalog."',
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(
            key="storefront.home_quick_title", value='"Your stock list. One simple order."'
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(
            key="storefront.home_quick_body",
            value=(
                '"Paste your SKUs and quantities, review your basket and get back'
                ' to what matters."'
            ),
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(key="storefront.home_trust_title", value='"Better supply. Better care."')
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(
            key="storefront.home_trust_body",
            value='"A dependable partner for your healthcare business."',
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(
            key="storefront.footer_description",
            value='"Supporting the people who care for our communities."',
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(
            key="storefront.verification_messages",
            value=(
                '{"PENDING": "Your account is ready. Upload your business '
                'certificates to start verification.", "UNDER_REVIEW": "Our team '
                "is reviewing your business. We will let you know when you can "
                'order.", "VERIFIED": "Your business is verified. Your facility '
                'pricing is ready.", "REJECTED": "Please review the feedback and '
                'upload updated documents.", "SUSPENDED": "Ordering is paused for'
                ' this account. Contact our team for help."}'
            ),
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
        ).bindparams(
            key="storefront.notification_messages",
            value=(
                '{"PENDING": "Order received", "APPROVED": "Order approved", '
                '"PENDING_DELIVERY": "Order prepared for delivery", '
                '"OUT_FOR_DELIVERY": "Your order is on its way", "DELIVERED": '
                '"Order delivered", "CANCELLED": "Order cancelled", "PAYMENT": '
                '"Payment recorded", "VERIFIED": "Business verified", "REJECTED":'
                ' "Verification update"}'
            ),
        )
    )
    op.execute(
        sa.text(
            'INSERT INTO permissions (code, description, "group") VALUES '
            "(:code, :description, 'storefront') ON CONFLICT (code) DO "
            "NOTHING"
        ).bindparams(code="storefront.view", description="Storefront view")
    )
    op.execute(
        sa.text(
            'INSERT INTO permissions (code, description, "group") VALUES '
            "(:code, :description, 'storefront') ON CONFLICT (code) DO "
            "NOTHING"
        ).bindparams(code="storefront.manage", description="Storefront manage")
    )
    op.execute(
        sa.text(
            'INSERT INTO permissions (code, description, "group") VALUES '
            "(:code, :description, 'storefront') ON CONFLICT (code) DO "
            "NOTHING"
        ).bindparams(code="storefront.delete", description="Storefront delete")
    )
    op.execute(
        sa.text(
            'INSERT INTO permissions (code, description, "group") VALUES '
            "(:code, :description, 'storefront') ON CONFLICT (code) DO "
            "NOTHING"
        ).bindparams(code="storefront.export", description="Storefront export")
    )
    op.execute(
        "INSERT INTO role_permissions (role_id, permission_id) SELECT "
        "r.id, p.id FROM roles r CROSS JOIN permissions p WHERE r.name IN"
        " ('super_admin', 'manager') AND p.code LIKE 'storefront.%' ON "
        "CONFLICT DO NOTHING"
    )


def downgrade() -> None:
    op.drop_index("ix_products_name_trgm", table_name="products")
    op.drop_index("ix_products_generic_trgm", table_name="products")
    op.execute("DELETE FROM permissions WHERE code LIKE 'storefront.%'")
    op.execute("DELETE FROM settings WHERE key LIKE 'storefront.%'")
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f("ix_store_order_metadata_customer_id"), table_name="store_order_metadata")
    op.drop_table("store_order_metadata")
    op.drop_index(op.f("ix_prescription_uploads_order_id"), table_name="prescription_uploads")
    op.drop_index(op.f("ix_prescription_uploads_customer_id"), table_name="prescription_uploads")
    op.drop_table("prescription_uploads")
    op.drop_index(op.f("ix_order_template_items_template_id"), table_name="order_template_items")
    op.drop_table("order_template_items")
    op.drop_index(op.f("ix_device_tokens_customer_user_id"), table_name="device_tokens")
    op.drop_table("device_tokens")
    op.drop_index(op.f("ix_customer_sessions_customer_user_id"), table_name="customer_sessions")
    op.drop_table("customer_sessions")
    op.drop_index(op.f("ix_cart_items_cart_id"), table_name="cart_items")
    op.drop_table("cart_items")
    op.drop_index(
        op.f("ix_storefront_collection_items_collection_id"),
        table_name="storefront_collection_items",
    )
    op.drop_table("storefront_collection_items")
    op.drop_index(op.f("ix_order_templates_customer_id"), table_name="order_templates")
    op.drop_table("order_templates")
    op.drop_index(op.f("ix_favourites_customer_id"), table_name="favourites")
    op.drop_table("favourites")
    op.drop_index(op.f("ix_customer_users_customer_id"), table_name="customer_users")
    op.drop_table("customer_users")
    op.drop_index(
        op.f("ix_customer_notifications_customer_id"), table_name="customer_notifications"
    )
    op.drop_table("customer_notifications")
    op.drop_index(
        "uq_customer_active_cart",
        table_name="carts",
        postgresql_where=sa.text("status = 'ACTIVE' AND deleted_at IS NULL"),
    )
    op.drop_index(op.f("ix_carts_customer_id"), table_name="carts")
    op.drop_table("carts")
    op.drop_index(
        op.f("ix_storefront_testimonials_updated_by"), table_name="storefront_testimonials"
    )
    op.drop_index(
        op.f("ix_storefront_testimonials_created_by"), table_name="storefront_testimonials"
    )
    op.drop_table("storefront_testimonials")
    op.drop_index(op.f("ix_storefront_pages_updated_by"), table_name="storefront_pages")
    op.drop_index(op.f("ix_storefront_pages_created_by"), table_name="storefront_pages")
    op.drop_table("storefront_pages")
    op.drop_index(op.f("ix_storefront_menu_items_updated_by"), table_name="storefront_menu_items")
    op.drop_index(op.f("ix_storefront_menu_items_created_by"), table_name="storefront_menu_items")
    op.drop_table("storefront_menu_items")
    op.drop_index(op.f("ix_storefront_faqs_updated_by"), table_name="storefront_faqs")
    op.drop_index(op.f("ix_storefront_faqs_created_by"), table_name="storefront_faqs")
    op.drop_table("storefront_faqs")
    op.drop_index(op.f("ix_storefront_collections_updated_by"), table_name="storefront_collections")
    op.drop_index(op.f("ix_storefront_collections_created_by"), table_name="storefront_collections")
    op.drop_table("storefront_collections")
    op.drop_index(op.f("ix_storefront_banners_updated_by"), table_name="storefront_banners")
    op.drop_index(op.f("ix_storefront_banners_created_by"), table_name="storefront_banners")
    op.drop_table("storefront_banners")
    op.drop_index(
        op.f("ix_storefront_announcements_updated_by"), table_name="storefront_announcements"
    )
    op.drop_index(
        op.f("ix_storefront_announcements_created_by"), table_name="storefront_announcements"
    )
    op.drop_table("storefront_announcements")
    op.drop_index(op.f("ix_customer_otp_codes_identifier"), table_name="customer_otp_codes")
    op.drop_table("customer_otp_codes")
    # ### end Alembic commands ###
