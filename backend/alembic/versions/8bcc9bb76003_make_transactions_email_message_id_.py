"""make transactions.email_message_id nullable (H2, COR-5)

Revision ID: 8bcc9bb76003
Revises: dcdef4f896b2
Create Date: 2026-07-19 09:45:55.672536

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8bcc9bb76003'
down_revision: Union[str, None] = 'dcdef4f896b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite has no ALTER support for changing a column's nullability -- batch mode (copy-and-
    # move) is required, same as dcdef4f896b2. A manual transaction (H2, COR-5) has no source
    # email at all; NULL here *is* the "this was added manually" marker (no separate boolean
    # column, one source of truth per fact).
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.alter_column("email_message_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.alter_column("email_message_id", existing_type=sa.Integer(), nullable=False)
