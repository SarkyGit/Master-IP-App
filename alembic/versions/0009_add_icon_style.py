"""add icon_style to users"""

from alembic import op
import sqlalchemy as sa

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('icon_style', sa.String(), nullable=False, server_default='lucide'))


def downgrade() -> None:
    op.drop_column('users', 'icon_style')
