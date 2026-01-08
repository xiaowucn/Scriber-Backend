"""add meta to file_tree and file_project

Revision ID: 5c30147b2953
Revises: 75dcb6b35025
Create Date: 2021-06-29 16:10:39.106726

"""

from alembic import op

# revision identifiers, used by Alembic.
from remarkable.common.migrate_util import create_jsonb_field

from remarkable.common.migrate_util import create_jsonb_field

revision = "5c30147b2953"
down_revision = "75dcb6b35025"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("file_tree", create_jsonb_field("meta"))
    op.add_column("file_project", create_jsonb_field("meta"))


def downgrade():
    op.drop_column("file_tree", "meta")
    op.drop_column("file_project", "meta")
