"""add default_mold col in file_project table

Revision ID: 7756a52ff32f
Revises: b7fba2b32ffa
Create Date: 2019-08-30 18:20:30.491906

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7756a52ff32f"
down_revision = "b7fba2b32ffa"
branch_labels = None
depends_on = None
table = "file_project"


def upgrade():
    op.add_column(table, sa.Column("default_mold", sa.Integer))


def downgrade():
    op.drop_column(table, "default_mold")
