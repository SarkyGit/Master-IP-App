"""add sync_state columns"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0015'
down_revision = '0014'
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = ['vlans', 'ssh_credentials', 'locations', 'device_types', 'sites', 'tags', 'devices', 'users']
    for table in tables:
        op.add_column(table, sa.Column('sync_state', postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    tables = ['vlans', 'ssh_credentials', 'locations', 'device_types', 'sites', 'tags', 'devices', 'users']
    for table in tables:
        op.drop_column(table, 'sync_state')
