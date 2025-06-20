from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    cols = {c["name"]: c for c in inspector.get_columns("snmp_communities")}

    # rename string "version" column to "snmp_version" if needed
    col = cols.get("version")
    if col and isinstance(col["type"], sa.String) and "snmp_version" not in cols:
        op.alter_column(
            "snmp_communities",
            "version",
            new_column_name="snmp_version",
            existing_type=sa.String(),
            existing_nullable=False,
        )
        cols = {c["name"]: c for c in inspector.get_columns("snmp_communities")}

    if "snmp_version" not in cols:
        op.add_column(
            "snmp_communities",
            sa.Column("snmp_version", sa.String(), nullable=False),
        )

    if "version" not in cols:
        op.add_column(
            "snmp_communities",
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        )

    cols = {c["name"]: c for c in inspector.get_columns("snmp_communities")}
    if "conflict_data" not in cols:
        op.add_column(
            "snmp_communities",
            sa.Column("conflict_data", postgresql.JSONB(), nullable=True),
        )

    if "sync_state" not in cols:
        op.add_column(
            "snmp_communities",
            sa.Column("sync_state", postgresql.JSONB(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    cols = {c["name"] for c in inspector.get_columns("snmp_communities")}

    if "sync_state" in cols:
        op.drop_column("snmp_communities", "sync_state")
    if "conflict_data" in cols:
        op.drop_column("snmp_communities", "conflict_data")
    if "version" in cols:
        op.drop_column("snmp_communities", "version")
    if "snmp_version" in cols and "version" not in cols:
        op.alter_column(
            "snmp_communities",
            "snmp_version",
            new_column_name="version",
            existing_type=sa.String(),
            existing_nullable=False,
        )
