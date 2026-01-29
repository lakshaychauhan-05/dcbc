"""
Add doctor_accounts table for portal authentication

Revision ID: d6c0f6b7e8a1
Revises: 9c2f0f1b5c2a
Create Date: 2026-01-29 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "d6c0f6b7e8a1"
down_revision = "9c2f0f1b5c2a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "doctor_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("doctor_email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("timezone('utc', now())")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("timezone('utc', now())")),
        sa.ForeignKeyConstraint(["doctor_email"], ["doctors.email"], ondelete="CASCADE"),
        sa.UniqueConstraint("doctor_email", name="uq_doctor_accounts_doctor_email"),
    )
    op.create_index("ix_doctor_accounts_id", "doctor_accounts", ["id"], unique=False)
    op.create_index("ix_doctor_accounts_doctor_email", "doctor_accounts", ["doctor_email"], unique=False)
    op.create_index("ix_doctor_accounts_is_active", "doctor_accounts", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_doctor_accounts_is_active", table_name="doctor_accounts")
    op.drop_index("ix_doctor_accounts_doctor_email", table_name="doctor_accounts")
    op.drop_index("ix_doctor_accounts_id", table_name="doctor_accounts")
    op.drop_table("doctor_accounts")
