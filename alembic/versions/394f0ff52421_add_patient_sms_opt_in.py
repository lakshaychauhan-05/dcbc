"""add_patient_sms_opt_in

Revision ID: 394f0ff52421
Revises: 98965d653844
Create Date: 2026-02-09 13:41:34.934245

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '394f0ff52421'
down_revision = '98965d653844'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add column with server default first (for existing rows)
    op.add_column('patients', sa.Column('sms_opt_in', sa.Boolean(), nullable=False, server_default=sa.text('true')))
    # Remove server default after column is added (optional, keeps model clean)
    op.alter_column('patients', 'sms_opt_in', server_default=None)


def downgrade() -> None:
    op.drop_column('patients', 'sms_opt_in')
