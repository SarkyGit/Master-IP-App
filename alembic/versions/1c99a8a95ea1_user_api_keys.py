"""add user_api_keys table

Revision ID: 1c99a8a95ea1
Revises: ec96754a9596
Create Date: 2025-07-01 00:00:00
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '1c99a8a95ea1'
down_revision: Union[str, None] = 'ec96754a9596'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_api_keys',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )
    op.create_index(op.f('ix_user_api_keys_key'), 'user_api_keys', ['key'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_api_keys_key'), table_name='user_api_keys')
    op.drop_table('user_api_keys')
