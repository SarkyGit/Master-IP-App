from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = '0018'
down_revision = '0017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    # Soft delete fields for devices
    device_cols = [c['name'] for c in inspector.get_columns('devices')]
    if 'is_deleted' not in device_cols:
        op.add_column('devices', sa.Column('is_deleted', sa.Boolean(), nullable=True, server_default='false'))
    if 'deleted_by_id' not in device_cols:
        op.add_column('devices', sa.Column('deleted_by_id', sa.Integer(), nullable=True))
    if 'deleted_at' not in device_cols:
        op.add_column('devices', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    if 'deleted_origin' not in device_cols:
        op.add_column('devices', sa.Column('deleted_origin', sa.String(), nullable=True))

    fk_names = [fk['name'] for fk in inspector.get_foreign_keys('devices')]
    if 'fk_devices_deleted_by_id_users' not in fk_names:
        op.create_foreign_key(
            'fk_devices_deleted_by_id_users',
            'devices',
            'users',
            ['deleted_by_id'],
            ['id'],
        )

    # Sync log table
    if not inspector.has_table('sync_logs'):
        op.create_table(
            'sync_logs',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('record_id', sa.Integer(), nullable=False),
            sa.Column('model_name', sa.String(), nullable=False),
            sa.Column('action', sa.String(), nullable=False),
            sa.Column('origin', sa.String(), nullable=False),
            sa.Column('target', sa.String(), nullable=False),
            sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        )

    # Conflict log table
    if not inspector.has_table('conflict_logs'):
        op.create_table(
            'conflict_logs',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('record_id', sa.Integer(), nullable=False),
            sa.Column('model_name', sa.String(), nullable=False),
            sa.Column('local_version', sa.Integer(), nullable=False),
            sa.Column('cloud_version', sa.Integer(), nullable=False),
            sa.Column('resolved_version', sa.Integer(), nullable=False),
            sa.Column('resolution_time', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        )

    # Duplicate resolution log table
    if not inspector.has_table('duplicate_resolution_logs'):
        op.create_table(
            'duplicate_resolution_logs',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('model_name', sa.String(), nullable=False),
            sa.Column('kept_id', sa.Integer(), nullable=False),
            sa.Column('removed_id', sa.Integer(), nullable=False),
            sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        )

    # Deletion log table
    if not inspector.has_table('deletion_logs'):
        op.create_table(
            'deletion_logs',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('record_id', sa.Integer(), nullable=False),
            sa.Column('model_name', sa.String(), nullable=False),
            sa.Column('deleted_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
            sa.Column('origin', sa.String(), nullable=True),
        )



def downgrade() -> None:
    op.drop_table('deletion_logs')
    op.drop_table('duplicate_resolution_logs')
    op.drop_table('conflict_logs')
    op.drop_table('sync_logs')
    op.drop_constraint('fk_devices_deleted_by_id_users', 'devices', type_='foreignkey')
    op.drop_column('devices', 'deleted_origin')
    op.drop_column('devices', 'deleted_at')
    op.drop_column('devices', 'deleted_by_id')
    op.drop_column('devices', 'is_deleted')
