"""initial schema

Revision ID: 8686d10bf780
Revises: 
Create Date: 2026-04-07 21:33:30.560179

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '8686d10bf780'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("whatsapp_id", sa.String(50), nullable=False, unique=True, index=True),
        sa.Column("allergies", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "chat_history",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "reminders",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("trigger_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(20), server_default="pending", nullable=False),
    )


def downgrade() -> None:
    op.drop_table("reminders")
    op.drop_table("chat_history")
    op.drop_table("users")
