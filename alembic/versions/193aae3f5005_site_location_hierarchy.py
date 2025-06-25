"""site_location_hierarchy

Revision ID: 193aae3f5005
Revises: 661a20b8021c
Create Date: 2025-06-25 18:45:27.745111

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from uuid import uuid4


# revision identifiers, used by Alembic.
revision: str = '193aae3f5005'
down_revision: Union[str, None] = '661a20b8021c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("locations", sa.Column("site_id", sa.Integer(), nullable=True))
    op.create_foreign_key(None, "locations", "sites", ["site_id"], ["id"])
    op.create_check_constraint("ck_locations_not_virtual", "locations", "site_id <> 100")

    op.execute(
        sa.text(
            "INSERT INTO sites (id, uuid, version, name, created_at, updated_at) "
            "VALUES (100, :uuid, 1, 'Virtual Warehouse', now(), now()) "
            "ON CONFLICT (id) DO NOTHING"
        ).bindparams(uuid=str(uuid4()))
    )

    op.execute(
        "UPDATE devices SET site_id = 100 WHERE site_id IS NULL OR site_id NOT IN (SELECT id FROM sites)"
    )

    op.execute(
        "UPDATE locations SET site_id = (SELECT id FROM sites WHERE id <> 100 ORDER BY id LIMIT 1) WHERE site_id IS NULL"
    )

    op.alter_column("locations", "site_id", nullable=False)
    op.alter_column("devices", "site_id", existing_type=sa.Integer(), nullable=False, server_default="100")
    op.create_check_constraint(
        "ck_devices_virtual_no_location",
        "devices",
        "site_id != 100 OR location_id IS NULL",
    )
    op.alter_column("devices", "site_id", server_default=None)


def downgrade() -> None:
    op.alter_column("devices", "site_id", server_default=None)
    op.drop_constraint("ck_devices_virtual_no_location", "devices", type_="check")
    op.alter_column("devices", "site_id", nullable=True)

    op.drop_constraint("ck_locations_not_virtual", "locations", type_="check")
    op.drop_constraint(None, "locations", type_="foreignkey")
    op.drop_column("locations", "site_id")

    op.execute("DELETE FROM sites WHERE id = 100")
