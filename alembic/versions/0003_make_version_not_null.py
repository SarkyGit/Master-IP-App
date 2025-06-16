"""make version columns non-nullable"""

from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = ['devices', 'vlans', 'ssh_credentials', 'users']
    for table in tables:
        op.alter_column(table, 'version', existing_type=sa.Integer(), nullable=False, server_default='1')


def downgrade() -> None:
    tables = ['devices', 'vlans', 'ssh_credentials', 'users']
    for table in tables:
        op.alter_column(table, 'version', existing_type=sa.Integer(), nullable=True)
