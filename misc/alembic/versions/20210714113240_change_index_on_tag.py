"""change index on tag

Revision ID: efc5e7a4d7b4
Revises: 1eb2ccde9a12
Create Date: 2021-07-14 11:32:40.742901

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "efc5e7a4d7b4"
down_revision = "1eb2ccde9a12"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index("uix_tag", "tag")
    op.create_index("uix_tag", "tag", ["name", "tag_type"])
    op.create_index("uix_tag_relation", "tag_relation", ["tag_id", "relational_id"])


def downgrade():
    op.drop_index("uix_tag", "tag")
    op.create_index("uix_tag", "tag", ["name"])
    op.drop_index("uix_tag_relation", "tag_relation")
