"""Add patient_display_name to appointments

Revision ID: f885aa056771
Revises: c1d2e3f4g5h6
Create Date: 2026-02-20 13:44:43.015967

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f885aa056771'
down_revision = 'c1d2e3f4g5h6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add patient_display_name column to preserve the name given at booking time
    op.add_column('appointments', sa.Column('patient_display_name', sa.String(255), nullable=True))


def downgrade() -> None:
    # Remove patient_display_name column
    op.drop_column('appointments', 'patient_display_name')
