"""add clinic phone_number and email fields

Revision ID: c1d2e3f4g5h6
Revises: 5a6b7c8d9e0f
Create Date: 2026-02-13
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c1d2e3f4g5h6"
down_revision = "5a6b7c8d9e0f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add phone_number and email columns to clinics table
    op.add_column("clinics", sa.Column("phone_number", sa.String(length=50), nullable=True))
    op.add_column("clinics", sa.Column("email", sa.String(length=255), nullable=True))


def downgrade() -> None:
    # Remove phone_number and email columns from clinics table
    op.drop_column("clinics", "email")
    op.drop_column("clinics", "phone_number")
