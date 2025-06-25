"""add updated_at onupdate

Revision ID: 92afc614eeae
Revises: 193aae3f5005
Create Date: 2025-06-25 19:03:32.652540

"""
from typing import Sequence, Union

# No schema changes are required for this revision. It only ensures
# instances upgrade to the new software version where updated_at columns
# now include an ``onupdate`` clause handled in application code.

from alembic import op  # noqa: F401 - imported for Alembic context
import sqlalchemy as sa  # noqa: F401 - imported for Alembic context


# revision identifiers, used by Alembic.
revision: str = '92afc614eeae'
down_revision: Union[str, None] = '193aae3f5005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op migration for application version tracking."""
    pass


def downgrade() -> None:
    """No-op downgrade."""
    pass
