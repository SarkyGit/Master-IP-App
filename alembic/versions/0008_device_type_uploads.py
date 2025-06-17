"""add upload fields to device_types"""

from alembic import op
import sqlalchemy as sa

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('device_types', sa.Column('upload_icon', sa.String(), nullable=True))
    op.add_column('device_types', sa.Column('upload_image', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('device_types', 'upload_image')
    op.drop_column('device_types', 'upload_icon')
