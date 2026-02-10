"""add_notes_updated_at_columns

Revision ID: 5a6b7c8d9e0f
Revises: 394f0ff52421
Create Date: 2026-02-10

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5a6b7c8d9e0f'
down_revision = '394f0ff52421'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add notes column to appointments (nullable Text)
    op.add_column('appointments', sa.Column('notes', sa.Text(), nullable=True))
    # Add updated_at column to appointments (nullable DateTime with timezone)
    op.add_column('appointments', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))
    # Add updated_at column to patients (nullable DateTime with timezone)
    op.add_column('patients', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('patients', 'updated_at')
    op.drop_column('appointments', 'updated_at')
    op.drop_column('appointments', 'notes')
