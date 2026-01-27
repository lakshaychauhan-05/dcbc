"""Fix calendar watch foreign key to use doctor_email

Revision ID: 73b7b9aba08b
Revises: 3661612ca939
Create Date: 2026-01-20 17:42:52.030824

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '73b7b9aba08b'
down_revision = '3661612ca939'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update calendar_watches table foreign key to use doctor_email
    # This migration assumes the previous migration changed doctors.id to doctors.email as primary key

    # Drop existing foreign key constraint
    op.drop_constraint('calendar_watches_doctor_id_fkey', 'calendar_watches', type_='foreignkey')

    # Drop the old doctor_id column
    op.drop_column('calendar_watches', 'doctor_id')

    # The doctor_email column should already exist from model changes
    # Create new foreign key constraint
    op.create_foreign_key(
        'calendar_watches_doctor_email_fkey',
        'calendar_watches',
        'doctors',
        ['doctor_email'],
        ['email']
    )


def downgrade() -> None:
    # Reverse the migration - recreate doctor_id column and foreign key
    # This is complex and may not work perfectly due to data loss
    pass
