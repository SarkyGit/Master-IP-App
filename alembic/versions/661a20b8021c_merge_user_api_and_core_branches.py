"""merge user API and core branches

Revision ID: 661a20b8021c
Revises: 1c99a8a95ea1, 33c2fcb07ec6
Create Date: 2025-06-23 16:01:00.038792

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '661a20b8021c'
down_revision: Union[str, None] = ('1c99a8a95ea1', '33c2fcb07ec6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
