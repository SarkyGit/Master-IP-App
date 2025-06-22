"""add cloud_user_id

Revision ID: ec96754a9596
Revises: c63b4137b41c
Create Date: 2025-06-22 21:43:47.987410

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ec96754a9596"
down_revision: Union[str, None] = "c63b4137b41c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("cloud_user_id", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "cloud_user_id")
