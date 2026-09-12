"""add server_info_panels table

Revision ID: a71f9c3d2e05
Revises: 6f3f5b942ade
Create Date: 2026-09-12 18:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a71f9c3d2e05"
down_revision: Union[str, Sequence[str], None] = "6f3f5b942ade"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "server_info_panels",
        sa.Column("guild_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("guild_id"),
    )
    with op.batch_alter_table("server_info_panels", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_server_info_panels_channel_id"), ["channel_id"], unique=False
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("server_info_panels", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_server_info_panels_channel_id"))

    op.drop_table("server_info_panels")
