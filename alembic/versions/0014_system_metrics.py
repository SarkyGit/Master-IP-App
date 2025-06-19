"""add system metrics table"""

from alembic import op
import sqlalchemy as sa

revision = '0014'
down_revision = '0013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'system_metrics',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('system_metrics')
