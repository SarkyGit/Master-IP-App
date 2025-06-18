"""add custom columns table"""

from alembic import op
import sqlalchemy as sa

revision = '0012'
down_revision = '0011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'custom_columns',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('table_name', sa.String(), nullable=False),
        sa.Column('column_name', sa.String(), nullable=False),
        sa.Column('data_type', sa.String(), nullable=False),
        sa.Column('default_value', sa.String(), nullable=True),
        sa.Column('user_visible', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('custom_columns')
