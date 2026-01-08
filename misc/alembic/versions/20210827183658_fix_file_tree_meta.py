"""fix file_tree.meta

Revision ID: 34b3977dcd23
Revises: aa4caad00967
Create Date: 2021-08-27 18:36:58.324526

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "34b3977dcd23"
down_revision = "aa4caad00967"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""update file_tree set meta = '{}' where meta = '"{}"' or meta is null;""")
    op.execute("""update file_project set meta = '{}' where meta = '"{}"' or meta is null;""")


def downgrade():
    pass
