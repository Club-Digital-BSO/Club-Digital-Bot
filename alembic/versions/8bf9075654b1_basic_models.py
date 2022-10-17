"""basic models

Revision ID: 8bf9075654b1
Revises: 
Create Date: 2022-10-17 18:29:31.238483

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8bf9075654b1'
down_revision = None
branch_labels = None
depends_on = None


def upgrade(engine_name: str) -> None:
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name: str) -> None:
    globals()["downgrade_%s" % engine_name]()





def upgrade_engine1() -> None:
    pass


def downgrade_engine1() -> None:
    pass


def upgrade_engine2() -> None:
    pass


def downgrade_engine2() -> None:
    pass

