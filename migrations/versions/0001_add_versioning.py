"""add versioning fields"""

from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column('devices', sa.Column('version', sa.Integer(), nullable=True, server_default='1'))
    op.add_column('devices', sa.Column('has_conflict', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('vlans', sa.Column('version', sa.Integer(), nullable=True, server_default='1'))
    op.add_column('vlans', sa.Column('has_conflict', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('ssh_credentials', sa.Column('version', sa.Integer(), nullable=True, server_default='1'))
    op.add_column('ssh_credentials', sa.Column('has_conflict', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('users', sa.Column('version', sa.Integer(), nullable=True, server_default='1'))
    op.add_column('users', sa.Column('has_conflict', sa.Boolean(), nullable=True, server_default='false'))

def downgrade() -> None:
    op.drop_column('users', 'has_conflict')
    op.drop_column('users', 'version')
    op.drop_column('ssh_credentials', 'has_conflict')
    op.drop_column('ssh_credentials', 'version')
    op.drop_column('vlans', 'has_conflict')
    op.drop_column('vlans', 'version')
    op.drop_column('devices', 'has_conflict')
    op.drop_column('devices', 'version')
