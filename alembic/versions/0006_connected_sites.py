"""create connected_sites table"""

from alembic import op
import sqlalchemy as sa

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'connected_sites',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('site_id', sa.String(), nullable=False, unique=True),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_version', sa.String(), nullable=True),
        sa.Column('sync_status', sa.String(), nullable=True),
        sa.Column('last_update_status', sa.String(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('connected_sites')
