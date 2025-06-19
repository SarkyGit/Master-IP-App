from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "snmp_communities",
        "version",
        new_column_name="snmp_version",
        existing_type=sa.String(),
        existing_nullable=False,
    )
    op.add_column(
        "snmp_communities",
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "snmp_communities",
        sa.Column("conflict_data", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "snmp_communities",
        sa.Column("sync_state", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("snmp_communities", "sync_state")
    op.drop_column("snmp_communities", "conflict_data")
    op.drop_column("snmp_communities", "version")
    op.alter_column(
        "snmp_communities",
        "snmp_version",
        new_column_name="version",
        existing_type=sa.String(),
        existing_nullable=False,
    )
