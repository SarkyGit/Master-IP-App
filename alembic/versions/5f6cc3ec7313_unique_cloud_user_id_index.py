"""add unique index for cloud_user_id

Revision ID: 5f6cc3ec7313
Revises: ec96754a9596
Create Date: 2025-06-23 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '5f6cc3ec7313'
down_revision: Union[str, None] = 'ec96754a9596'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'ix_users_cloud_user_id_unique',
        'users',
        ['cloud_user_id'],
        unique=True,
        postgresql_where=sa.text('cloud_user_id IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('ix_users_cloud_user_id_unique', table_name='users')
