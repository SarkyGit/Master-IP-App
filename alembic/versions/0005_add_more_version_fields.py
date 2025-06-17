"""add version/conflict fields to more tables"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = ['locations', 'device_types', 'sites', 'tags']
    for table in tables:
        op.add_column(table, sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
        op.add_column(table, sa.Column('conflict_data', postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    tables = ['locations', 'device_types', 'sites', 'tags']
    for table in tables:
        op.drop_column(table, 'conflict_data')
        op.drop_column(table, 'version')
