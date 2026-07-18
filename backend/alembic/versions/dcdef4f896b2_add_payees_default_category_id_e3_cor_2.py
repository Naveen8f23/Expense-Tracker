"""add payees.default_category_id (E3, COR-2)

Revision ID: dcdef4f896b2
Revises: e5aa5f25c7b3
Create Date: 2026-07-19 00:37:25.249649

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dcdef4f896b2'
down_revision: Union[str, None] = 'e5aa5f25c7b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite has no ALTER support for adding constraints -- batch mode (copy-and-move) is
    # required, unlike the plain op.add_column used by earlier migrations that didn't add a FK.
    with op.batch_alter_table("payees") as batch_op:
        batch_op.add_column(sa.Column("default_category_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_payees_default_category_id_categories", "categories", ["default_category_id"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("payees") as batch_op:
        batch_op.drop_constraint("fk_payees_default_category_id_categories", type_="foreignkey")
        batch_op.drop_column("default_category_id")
