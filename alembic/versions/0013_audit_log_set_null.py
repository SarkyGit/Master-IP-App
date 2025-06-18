"""Set audit log device_id to NULL on device deletion"""

from alembic import op
import sqlalchemy as sa

revision = '0013'
down_revision = '0012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint('audit_logs_device_id_fkey', 'audit_logs', type_='foreignkey')
    op.create_foreign_key(
        'audit_logs_device_id_fkey',
        'audit_logs',
        'devices',
        ['device_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint('audit_logs_device_id_fkey', 'audit_logs', type_='foreignkey')
    op.create_foreign_key(
        'audit_logs_device_id_fkey',
        'audit_logs',
        'devices',
        ['device_id'],
        ['id']
    )
