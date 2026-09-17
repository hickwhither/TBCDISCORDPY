"""add birthday tables

Revision ID: 888d5bd70151
Revises: a71f9c3d2e05
Create Date: 2026-09-17 13:37:53.587213

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "888d5bd70151"
down_revision: Union[str, Sequence[str], None] = "a71f9c3d2e05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "birthday_celebrations",
        sa.Column("guild_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("user_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("celebrated_on", sa.Date(), autoincrement=False, nullable=False),
        sa.PrimaryKeyConstraint("guild_id", "user_id", "celebrated_on"),
    )
    op.create_table(
        "birthday_channels",
        sa.Column("guild_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("guild_id"),
    )
    with op.batch_alter_table("birthday_channels", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_birthday_channels_channel_id"),
            ["channel_id"],
            unique=False,
        )

    op.create_table(
        "birthdays",
        sa.Column("user_id", sa.BigInteger(), autoincrement=False, nullable=False),
        sa.Column("birth_date", sa.Date(), nullable=False),
        sa.Column("last_gift_year", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("birthdays")
    with op.batch_alter_table("birthday_channels", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_birthday_channels_channel_id"))

    op.drop_table("birthday_channels")
    op.drop_table("birthday_celebrations")
