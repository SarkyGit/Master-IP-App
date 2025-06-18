"""add menu_tab_colors and table_grid_style"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('menu_tab_colors', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('users', sa.Column('table_grid_style', sa.String(), nullable=False, server_default='normal'))


def downgrade() -> None:
    op.drop_column('users', 'table_grid_style')
    op.drop_column('users', 'menu_tab_colors')
