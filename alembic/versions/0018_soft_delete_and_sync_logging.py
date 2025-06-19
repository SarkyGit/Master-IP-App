from alembic import op
import sqlalchemy as sa

revision = '0018'
down_revision = '0017'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Soft delete fields for devices
    op.add_column('devices', sa.Column('is_deleted', sa.Boolean(), nullable=True, server_default='false'))
    op.add_column('devices', sa.Column('deleted_by_id', sa.Integer(), nullable=True))
    op.add_column('devices', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('devices', sa.Column('deleted_origin', sa.String(), nullable=True))
    op.create_foreign_key(
        'fk_devices_deleted_by_id_users',
        'devices',
        'users',
        ['deleted_by_id'],
        ['id'],
    )

    # Sync log table
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
    op.create_table(
        'duplicate_resolution_logs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('kept_id', sa.Integer(), nullable=False),
        sa.Column('removed_id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
    )

    # Deletion log table
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
