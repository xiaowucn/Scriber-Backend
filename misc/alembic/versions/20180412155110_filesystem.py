"""filesystem

Revision ID: 4ea9158f33bf
Revises: 078439197444
Create Date: 2018-04-12 15:51:10.622075

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "4ea9158f33bf"
down_revision = "078439197444"
branch_labels = None
depends_on = None

fields = (
    create_timestamp_field(
        "created_utc", sa.Integer, index=True, server_default=sa.text("extract(epoch from now())::int")
    ),
    create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
)


def upgrade():
    op.create_table(
        "file_project",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("rtree_id", sa.Integer, nullable=False),
        create_array_field("default_tags", sa.ARRAY(sa.Integer)),
        *fields,
    )

    op.create_table(
        "file_tree",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("ptree_id", sa.Integer, nullable=False),
        sa.Column("pid", sa.Integer, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        *fields,
    )

    op.create_table(
        "file",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tree_id", sa.Integer, nullable=False),
        sa.Column("pid", sa.Integer, nullable=False),
        sa.Column("name", sa.String(1024), nullable=False),
        sa.Column("hash", sa.String(32), nullable=False),
        sa.Column("pdf", sa.String(32)),
        sa.Column("pdf_flag", sa.Integer),
        create_array_field("tags", sa.ARRAY(sa.Integer)),
        sa.Column("qid", sa.Integer),
        sa.Column("size", sa.Integer),
        sa.Column("page", sa.Integer),
        *fields,
    )

    op.create_table(
        "file_tag",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        create_array_field("columns", sa.ARRAY(sa.String)),
        *fields,
    )


def downgrade():
    op.drop_table("file_project")
    op.drop_table("file_tree")
    op.drop_table("file")
    op.drop_table("file_tag")
