"""add uploaded_by_id to works

Revision ID: a1b2c3d4e5f6
Revises: d31734ccdcfb
Create Date: 2026-04-16 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'd31734ccdcfb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('works', sa.Column('uploaded_by_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_works_uploaded_by_id', 'works', 'users', ['uploaded_by_id'], ['id'])


def downgrade() -> None:
    op.drop_constraint('fk_works_uploaded_by_id', 'works', type_='foreignkey')
    op.drop_column('works', 'uploaded_by_id')
