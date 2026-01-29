"""add clinics table and link doctors

Revision ID: 2f3b6a4d1c90
Revises: d6c0f6b7e8a1
Create Date: 2026-01-29
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from datetime import datetime


# revision identifiers, used by Alembic.
revision = "2f3b6a4d1c90"
down_revision = "d6c0f6b7e8a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create clinics table
    op.create_table(
        "clinics",
        sa.Column("id", postgresql.UUID(), primary_key=True, index=True),
        sa.Column("name", sa.String(length=255), nullable=False, unique=True),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("address", sa.String(length=512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(op.f("ix_clinics_is_active"), "clinics", ["is_active"], unique=False)

    # Backfill clinics from existing doctors (best-effort)
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT DISTINCT clinic_id FROM doctors WHERE clinic_id IS NOT NULL")).fetchall()
    for idx, row in enumerate(rows):
        clinic_id = row[0]
        if not clinic_id:
            continue
        name = f"Legacy Clinic {idx + 1}"
        conn.execute(
            sa.text(
                """
                INSERT INTO clinics (id, name, timezone, is_active, created_at, updated_at)
                VALUES (:id, :name, 'UTC', true, :now, :now)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": clinic_id, "name": name, "now": datetime.utcnow()},
        )

    # Add FK from doctors to clinics
    op.create_foreign_key(
        "fk_doctors_clinic_id",
        source_table="doctors",
        referent_table="clinics",
        local_cols=["clinic_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # Drop FK then clinics table
    op.drop_constraint("fk_doctors_clinic_id", "doctors", type_="foreignkey")
    op.drop_index(op.f("ix_clinics_is_active"), table_name="clinics")
    op.drop_table("clinics")
