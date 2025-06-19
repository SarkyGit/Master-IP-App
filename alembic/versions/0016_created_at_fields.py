from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = [
        "vlans",
        "ssh_credentials",
        "snmp_communities",
        "locations",
        "device_types",
        "tags",
    ]
    for table in tables:
        op.add_column(
            table,
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )


def downgrade() -> None:
    tables = [
        "vlans",
        "ssh_credentials",
        "snmp_communities",
        "locations",
        "device_types",
        "tags",
    ]
    for table in tables:
        op.drop_column(table, "created_at")
