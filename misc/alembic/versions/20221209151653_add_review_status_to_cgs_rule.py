"""add_review_status_to_cgs_rule

Revision ID: 8ce5a303d5d5
Revises: 9da0ec60ae4e
Create Date: 2022-12-09 15:16:53.285424

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field
from remarkable.db import IS_MYSQL

# revision identifiers, used by Alembic.
revision = "8ce5a303d5d5"
down_revision = "9da0ec60ae4e"
branch_labels = None
depends_on = None
table = "cgs_rule"


def upgrade():
    op.add_column(table, sa.Column("review_status", sa.Integer))
    op.execute("update cgs_rule set review_status=3;")
    op.add_column(table, sa.Column("not_pass_reason", sa.String(255)))
    op.add_column(table, sa.Column("uid", sa.Integer))
    op.add_column(table, sa.Column("user", sa.String(255)))
    op.add_column(
        table, create_array_field("review_uids", sa.ARRAY(sa.Integer), server_default=sa.text("array[]::integer[]"))
    )
    if IS_MYSQL:
        op.execute("update cgs_rule set review_uids = '[]' where review_uids is null;")
    else:
        op.execute("update cgs_rule set review_uids = ARRAY[]::integer[] where review_uids is null;")
    op.add_column(
        table,
        create_array_field("review_users", sa.ARRAY(sa.String(255)), server_default=sa.text("array[]::varchar[]")),
    )
    if IS_MYSQL:
        op.execute("update cgs_rule set review_users = '[]' where review_users is null;")
    else:
        op.execute("update cgs_rule set review_users = ARRAY[]::varchar[] where review_users is null;")
    op.add_column(table, sa.Column("handle_uid", sa.Integer))
    op.add_column(table, sa.Column("handle_user", sa.String(255)))


def downgrade():
    op.drop_column(table, "review_status")
    op.drop_column(table, "not_pass_reason")
    op.drop_column(table, "uid")
    op.drop_column(table, "user")
    op.drop_column(table, "review_uids")
    op.drop_column(table, "review_users")
    op.drop_column(table, "handle_uid")
    op.drop_column(table, "handle_user")
