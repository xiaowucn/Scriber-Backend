"""support multi molds

Revision ID: 8862369e9654
Revises: 04162510f259
Create Date: 2021-04-21 15:03:11.256801

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field
from remarkable.db import IS_MYSQL

# revision identifiers, used by Alembic.
revision = "8862369e9654"
down_revision = "04162510f259"
branch_labels = None
depends_on = None


def upgrade():
    # file
    op.add_column(
        "file",
        create_array_field("molds", sa.ARRAY(sa.Integer), server_default=sa.text("array[]::integer[]"), nullable=False),
    )
    if IS_MYSQL:
        op.execute("update file set molds=json_array(mold)")
    else:
        op.execute("update file set molds=array[mold] where mold is NOT NULL")

    # question
    op.add_column("question", sa.Column("mold", sa.Integer, nullable=False))
    op.execute("update question set mold=(select mold from file where qid = question.id)")
    op.add_column("question", sa.Column("fid", sa.Integer))
    op.execute("update question set fid=(select id from file where qid = question.id)")
    op.execute("delete from question where mold is null or fid is null")
    op.alter_column("question", "mold", nullable=False, existing_type=sa.Integer)
    op.alter_column("question", "fid", nullable=False, existing_type=sa.Integer)

    op.add_column("question", sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")))
    op.execute("update question set deleted_utc=(select deleted_utc from file where qid = question.id)")

    op.execute("update question set progress=(select progress from file where qid = question.id)")
    op.add_column(
        "question",
        create_array_field(
            "mark_uids", sa.ARRAY(sa.Integer), server_default=sa.text("array[]::integer[]"), nullable=False
        ),
    )
    op.add_column(
        "question",
        create_array_field(
            "mark_users", sa.ARRAY(sa.String), server_default=sa.text("array[]::varchar[]"), nullable=False
        ),
    )

    if IS_MYSQL:
        op.execute("""
            update question q, file f
            set q.mark_uids=coalesce(f.mark_uids, '[]'),
                q.mark_users=coalesce(f.mark_users, '[]')
            where q.fid = f.id;
        """)
    else:
        op.execute(
            "update question set mark_uids=(select coalesce(mark_uids, array[]::integer[]) from file where id = question.fid)"
        )
        op.execute(
            "update question set mark_users=(select coalesce(mark_users, array[]::varchar[]) from file where id = question.fid)"
        )

    # file_tree
    op.add_column(
        "file_tree",
        create_array_field(
            "default_molds", sa.ARRAY(sa.Integer), server_default=sa.text("array[]::integer[]"), nullable=False
        ),
    )
    if IS_MYSQL:
        op.execute("update file_tree set default_molds=json_array(default_mold) where default_mold is NOT NULL")
    else:
        op.execute("update file_tree set default_molds=array[default_mold] where default_mold is NOT NULL")

    # file_project
    op.add_column(
        "file_project",
        create_array_field(
            "default_molds", sa.ARRAY(sa.Integer), server_default=sa.text("array[]::integer[]"), nullable=False
        ),
    )
    if IS_MYSQL:
        op.execute("update file_project set default_molds=json_array(default_mold) where default_mold is NOT NULL")
    else:
        op.execute("update file_project set default_molds=array[default_mold] where default_mold is NOT NULL")

    op.drop_column("file", "qid")
    op.drop_column("file", "mold")
    op.drop_column("file", "progress")
    op.drop_column("file", "mark_users")
    op.drop_column("file", "mark_uids")
    op.drop_column("file", "last_mark_utc")
    op.drop_column("file_tree", "default_mold")
    op.drop_column("file_project", "default_mold")
    op.drop_column("training_data", "from_id")
    op.drop_column("training_data", "to_id")
    op.drop_index("uix_question", "question")


def downgrade():
    op.add_column("file", sa.Column("mold", sa.Integer))
    op.execute("update file set mold=molds[1] where molds[1] is NOT NULL")
    op.add_column("file", sa.Column("qid", sa.Integer))
    op.execute(
        "update file set qid=(select id from question where question.mold = file.mold and question.fid = file.id)"
    )
    op.add_column("file", sa.Column("progress", sa.String(50)))
    op.execute(
        "update file set progress=(select progress from question where question.mold = file.mold and question.fid = file.id)"
    )
    op.add_column("file", create_array_field("mark_uids", sa.ARRAY(sa.Integer)))
    op.add_column("file", create_array_field("mark_users", sa.ARRAY(sa.String)))
    op.add_column("file", sa.Column("last_mark_utc", sa.Integer))

    op.add_column("file_tree", sa.Column("default_mold", sa.Integer))
    op.execute("update file_tree set default_mold=default_molds[1] where default_molds[1] is NOT NULL")

    op.add_column("file_project", sa.Column("default_mold", sa.Integer))
    op.execute("update file_project set default_mold=default_molds[1] where default_molds[1] is NOT NULL")

    op.drop_column("question", "mold")
    op.drop_column("question", "fid")
    op.drop_column("question", "deleted_utc")
    op.drop_column("question", "mark_users")
    op.drop_column("question", "mark_uids")

    op.drop_column("file", "molds")
    op.drop_column("file_tree", "default_molds")
    op.drop_column("file_project", "default_molds")

    op.add_column("training_data", sa.Column("from_id", sa.Integer))
    op.add_column("training_data", sa.Column("to_id", sa.Integer))
