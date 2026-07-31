"""customers and verification

Revision ID: phase3_0001
Revises: phase2_0001
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "phase3_0001"
down_revision: str | Sequence[str] | None = "phase2_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

business_type = postgresql.ENUM(
    "DLDM",
    "COMMUNITY_PHARMACY",
    "WHOLESALE",
    "HOSPITAL",
    "CLINIC",
    "GOVERNMENT",
    "NGO",
    "FBO",
    name="customer_business_type",
    create_type=False,
)
customer_status = postgresql.ENUM(
    "PENDING",
    "UNDER_REVIEW",
    "VERIFIED",
    "REJECTED",
    "SUSPENDED",
    name="customer_status",
    create_type=False,
)
payment_terms = postgresql.ENUM(
    "CASH",
    "CREDIT",
    name="customer_payment_terms",
    create_type=False,
)
document_type = postgresql.ENUM(
    "TIN",
    "TMDA",
    "PHARMACY_COUNCIL",
    "TBS",
    "OTHER",
    name="customer_document_type",
    create_type=False,
)
document_status = postgresql.ENUM(
    "PENDING",
    "APPROVED",
    "REJECTED",
    name="customer_document_status",
    create_type=False,
)


def _audit_columns() -> list[sa.Column]:
    return [
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
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
    ]


def _create_audit_indexes(table_name: str) -> None:
    op.create_index(op.f(f"ix_{table_name}_created_by"), table_name, ["created_by"])
    op.create_index(op.f(f"ix_{table_name}_updated_by"), table_name, ["updated_by"])


def upgrade() -> None:
    bind = op.get_bind()
    business_type.create(bind, checkfirst=True)
    customer_status.create(bind, checkfirst=True)
    payment_terms.create(bind, checkfirst=True)
    document_type.create(bind, checkfirst=True)
    document_status.create(bind, checkfirst=True)

    op.create_table(
        "customers",
        sa.Column("business_name", sa.String(length=200), nullable=False),
        sa.Column("business_type", business_type, nullable=False),
        sa.Column("price_tier_id", sa.UUID(), nullable=False),
        sa.Column("contact_person", sa.String(length=150), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=False),
        sa.Column("physical_address", sa.Text(), nullable=False),
        sa.Column("region", sa.String(length=120), nullable=True),
        sa.Column("referred_by", sa.String(length=200), nullable=True),
        sa.Column("status", customer_status, server_default="PENDING", nullable=False),
        sa.Column("payment_terms", payment_terms, server_default="CASH", nullable=False),
        sa.Column("credit_limit", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("verified_by", sa.UUID(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        *_audit_columns(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "credit_limit IS NULL OR credit_limit >= 0",
            name="ck_customers_credit_limit_nonnegative",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["price_tier_id"], ["price_tiers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["updated_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["verified_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_audit_indexes("customers")
    op.create_index("ix_customers_business_type", "customers", ["business_type"])
    op.create_index("ix_customers_email", "customers", ["email"])
    op.create_index("ix_customers_payment_terms", "customers", ["payment_terms"])
    op.create_index("ix_customers_phone", "customers", ["phone"])
    op.create_index("ix_customers_price_tier_id", "customers", ["price_tier_id"])
    op.create_index("ix_customers_status", "customers", ["status"])
    op.create_index("ix_customers_verified_by", "customers", ["verified_by"])

    op.create_table(
        "customer_documents",
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("doc_type", document_type, nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=True),
        sa.Column("status", document_status, server_default="PENDING", nullable=False),
        sa.Column("reviewed_by", sa.UUID(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["created_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_audit_indexes("customer_documents")
    op.create_index("ix_customer_documents_customer_id", "customer_documents", ["customer_id"])
    op.create_index("ix_customer_documents_doc_type", "customer_documents", ["doc_type"])
    op.create_index("ix_customer_documents_reviewed_by", "customer_documents", ["reviewed_by"])
    op.create_index("ix_customer_documents_status", "customer_documents", ["status"])

    op.create_table(
        "customer_addresses",
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("region", sa.String(length=120), nullable=True),
        sa.Column("contact_person", sa.String(length=150), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *_audit_columns(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_audit_indexes("customer_addresses")
    op.create_index("ix_customer_addresses_customer_id", "customer_addresses", ["customer_id"])
    op.create_index(
        "uq_customer_addresses_default",
        "customer_addresses",
        ["customer_id"],
        unique=True,
        postgresql_where=sa.text("is_default AND deleted_at IS NULL"),
    )

    op.create_table(
        "customer_feedback",
        sa.Column("customer_id", sa.UUID(), nullable=True),
        sa.Column("subject", sa.String(length=200), nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_handled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("handled_by", sa.UUID(), nullable=True),
        sa.Column("handled_at", sa.DateTime(timezone=True), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["created_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["handled_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_audit_indexes("customer_feedback")
    op.create_index("ix_customer_feedback_customer_id", "customer_feedback", ["customer_id"])
    op.create_index("ix_customer_feedback_handled_by", "customer_feedback", ["handled_by"])
    op.create_index("ix_customer_feedback_is_handled", "customer_feedback", ["is_handled"])

    op.create_table(
        "customer_status_history",
        sa.Column("customer_id", sa.UUID(), nullable=False),
        sa.Column("from_status", customer_status, nullable=True),
        sa.Column("to_status", customer_status, nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        *_audit_columns(),
        sa.ForeignKeyConstraint(["created_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["admin_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    _create_audit_indexes("customer_status_history")
    op.create_index(
        "ix_customer_status_history_customer_id",
        "customer_status_history",
        ["customer_id"],
    )
    op.create_index(
        "ix_customer_status_history_to_status",
        "customer_status_history",
        ["to_status"],
    )


def downgrade() -> None:
    for table_name in (
        "customer_status_history",
        "customer_feedback",
        "customer_addresses",
        "customer_documents",
        "customers",
    ):
        op.drop_table(table_name)

    bind = op.get_bind()
    document_status.drop(bind, checkfirst=True)
    document_type.drop(bind, checkfirst=True)
    payment_terms.drop(bind, checkfirst=True)
    customer_status.drop(bind, checkfirst=True)
    business_type.drop(bind, checkfirst=True)
