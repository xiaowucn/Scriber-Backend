"""adjust_ecitic_table_columns

Revision ID: 798d1e80a1a6
Revises: 8adb5c65ca25
Create Date: 2024-10-15 11:44:55.742660

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON, JSONB

from remarkable.common.migrate_util import create_timestamp_field
from remarkable.db import IS_MYSQL

# revision identifiers, used by Alembic.
revision = "798d1e80a1a6"
down_revision = "8adb5c65ca25"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("ecitic_compare_record", "updated_utc")
    op.drop_column("ecitic_compare_record", "deleted_utc")
    op.add_column("ecitic_compare_record", sa.Column("external_source", sa.String(255)))

    op.drop_column("ecitic_compare_result", "updated_utc")
    op.drop_column("ecitic_compare_result", "deleted_utc")

    op.drop_column("ecitic_compare_record_result_ref", "created_utc")

    if not IS_MYSQL:
        op.execute(
            """
        update ecitic_compare_result set question = question->'answer' where (question->'answer') is not null;
        """
        )
    op.alter_column("ecitic_compare_result", column_name="question", new_column_name="answer", existing_type=sa.JSON)
    if not IS_MYSQL:
        op.alter_column("ecitic_compare_result", column_name="answer", type_=JSONB, postgresql_using="answer::jsonb")
        op.execute(
            """
        update ecitic_compare_result set std_question = std_question->'answer' where (std_question->'answer') is not null;
        """
        )
    op.alter_column(
        "ecitic_compare_result", column_name="std_question", new_column_name="std_answer", existing_type=sa.JSON
    )
    if not IS_MYSQL:
        op.alter_column(
            "ecitic_compare_result", column_name="std_answer", type_=JSONB, postgresql_using="std_answer::jsonb"
        )


def downgrade():
    op.add_column(
        "ecitic_compare_record",
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )
    op.add_column("ecitic_compare_record", sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")))
    op.drop_column("ecitic_compare_record", "external_source")

    op.add_column(
        "ecitic_compare_result",
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )
    op.add_column("ecitic_compare_result", sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")))

    op.add_column(
        "ecitic_compare_record_result_ref",
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )

    if not IS_MYSQL:
        op.alter_column("ecitic_compare_result", column_name="answer", type_=JSON, postgresql_using="answer::json")
    op.alter_column("ecitic_compare_result", column_name="answer", new_column_name="question", existing_type=sa.JSON)
    if not IS_MYSQL:
        op.alter_column(
            "ecitic_compare_result", column_name="std_answer", type_=JSON, postgresql_using="std_answer::json"
        )
    op.alter_column(
        "ecitic_compare_result", column_name="std_answer", new_column_name="std_question", existing_type=sa.JSON
    )
