"""add schema_validation_issues table

Revision ID: 2e4e28454f6b
Revises: 4fa5ed6e5a8e
Create Date: 2025-06-22 16:25:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2e4e28454f6b'
down_revision: Union[str, None] = '4fa5ed6e5a8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'schema_validation_issues',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('table_name', sa.String(), nullable=False),
        sa.Column('column_name', sa.String(), nullable=True),
        sa.Column('expected_type', sa.String(), nullable=True),
        sa.Column('actual_type', sa.String(), nullable=True),
        sa.Column('issue_type', sa.String(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('schema_validation_issues')
