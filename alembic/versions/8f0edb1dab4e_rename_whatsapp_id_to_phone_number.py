"""rename whatsapp_id to phone_number

Revision ID: 8f0edb1dab4e
Revises: 8686d10bf780
Create Date: 2026-04-12 14:52:56.333509

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8f0edb1dab4e"
down_revision: Union[str, Sequence[str], None] = "8686d10bf780"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "whatsapp_id", new_column_name="phone_number", type_=sa.String(length=20))
    op.drop_index(op.f("ix_users_whatsapp_id"), table_name="users")
    op.create_index(op.f("ix_users_phone_number"), "users", ["phone_number"], unique=True)


def downgrade() -> None:
    op.alter_column("users", "phone_number", new_column_name="whatsapp_id", type_=sa.String(length=50))
    op.drop_index(op.f("ix_users_phone_number"), table_name="users")
    op.create_index(op.f("ix_users_whatsapp_id"), "users", ["whatsapp_id"], unique=True)
