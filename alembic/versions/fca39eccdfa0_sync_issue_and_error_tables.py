"""sync issue and error tables

Revision ID: fca39eccdfa0
Revises: 0019
Create Date: 2025-06-22 12:25:53.815946

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fca39eccdfa0'
down_revision: Union[str, None] = '0019'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if not inspector.has_table("sync_issues"):
        op.create_table(
            "sync_issues",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("model_name", sa.String(), nullable=False),
            sa.Column("field_name", sa.String(), nullable=False),
            sa.Column("issue_type", sa.String(), nullable=False),
            sa.Column("instance", sa.String(), nullable=False),
            sa.Column(
                "timestamp",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.UniqueConstraint(
                "model_name",
                "field_name",
                "issue_type",
                "instance",
                name="uix_sync_issues_unique",
            ),
        )

    if not inspector.has_table("sync_errors"):
        op.create_table(
            "sync_errors",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("model_name", sa.String(), nullable=False),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("error_trace", sa.Text(), nullable=False),
            sa.Column("error_hash", sa.String(), nullable=False),
            sa.Column(
                "timestamp",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.UniqueConstraint("error_hash", name="uix_sync_errors_hash"),
        )


def downgrade() -> None:
    op.drop_table("sync_errors")
    op.drop_table("sync_issues")
