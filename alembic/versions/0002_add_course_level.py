"""add course level

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-05 20:46:43.005456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema — three steps for a NOT NULL column on existing data."""
    # Step 1: add column allowing NULL
    op.add_column('courses', sa.Column('level', sa.Text(), nullable=True))
    # Step 2: fill existing rows (electives -> beginner, rest -> intermediate)
    op.execute(
        "UPDATE courses SET level = CASE WHEN is_elective THEN 'beginner' "
        "ELSE 'intermediate' END"
    )
    # Step 3: now enforce NOT NULL
    op.alter_column('courses', 'level', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('courses', 'level')
