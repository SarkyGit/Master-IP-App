"""add version and conflict fields"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('devices', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('devices', sa.Column('conflict_data', postgresql.JSONB(), nullable=True))
    op.add_column('vlans', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('vlans', sa.Column('conflict_data', postgresql.JSONB(), nullable=True))
    op.add_column('ssh_credentials', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('ssh_credentials', sa.Column('conflict_data', postgresql.JSONB(), nullable=True))
    op.add_column('users', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('users', sa.Column('conflict_data', postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'conflict_data')
    op.drop_column('users', 'version')
    op.drop_column('ssh_credentials', 'conflict_data')
    op.drop_column('ssh_credentials', 'version')
    op.drop_column('vlans', 'conflict_data')
    op.drop_column('vlans', 'version')
    op.drop_column('devices', 'conflict_data')
    op.drop_column('devices', 'version')
