from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    tables = [
        "vlans",
        "ssh_credentials",
        "snmp_communities",
        "locations",
        "device_types",
        "sites",
        "tags",
        "devices",
        "users",
    ]
    for table in tables:
        cols = [c["name"] for c in inspector.get_columns(table)]
        if "uuid" not in cols:
            op.add_column(
                table,
                sa.Column(
                    "uuid",
                    postgresql.UUID(as_uuid=True),
                    nullable=False,
                    server_default=sa.text("gen_random_uuid()"),
                ),
            )
            op.create_index(f"ix_{table}_uuid", table, ["uuid"], unique=True)
        if "updated_at" not in cols:
            op.add_column(
                table,
                sa.Column(
                    "updated_at",
                    sa.DateTime(timezone=True),
                    nullable=False,
                    server_default=sa.text("now()"),
                ),
            )
        if "deleted_at" not in cols:
            op.add_column(
                table,
                sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            )


def downgrade() -> None:
    tables = [
        "vlans",
        "ssh_credentials",
        "snmp_communities",
        "locations",
        "device_types",
        "sites",
        "tags",
        "devices",
        "users",
    ]
    for table in tables:
        op.drop_index(f"ix_{table}_uuid", table_name=table)
        op.drop_column(table, "uuid")
        op.drop_column(table, "updated_at")
        op.drop_column(table, "deleted_at")
