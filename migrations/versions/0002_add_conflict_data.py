"""add conflict_data json fields"""

from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('devices', sa.Column('conflict_data', sa.JSON(), nullable=True))
    op.add_column('vlans', sa.Column('conflict_data', sa.JSON(), nullable=True))
    op.add_column('ssh_credentials', sa.Column('conflict_data', sa.JSON(), nullable=True))
    op.add_column('users', sa.Column('conflict_data', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'conflict_data')
    op.drop_column('ssh_credentials', 'conflict_data')
    op.drop_column('vlans', 'conflict_data')
    op.drop_column('devices', 'conflict_data')
