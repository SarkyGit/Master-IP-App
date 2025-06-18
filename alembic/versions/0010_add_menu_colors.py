"""add menu color settings to users"""

from alembic import op
import sqlalchemy as sa

revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('menu_tab_color', sa.String(), nullable=True))
    op.add_column('users', sa.Column('menu_bg_color', sa.String(), nullable=True))
    op.add_column('users', sa.Column('menu_stick_theme', sa.Boolean(), nullable=False, server_default='true'))


def downgrade() -> None:
    op.drop_column('users', 'menu_stick_theme')
    op.drop_column('users', 'menu_bg_color')
    op.drop_column('users', 'menu_tab_color')
