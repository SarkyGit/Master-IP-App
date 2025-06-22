"""add local_recovery_events table

Revision ID: c63b4137b41c
Revises: b41a94cd99a1
Create Date: 2025-06-22 17:30:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'c63b4137b41c'
down_revision: Union[str, None] = 'b41a94cd99a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'local_recovery_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('num_records', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('local_recovery_events')
