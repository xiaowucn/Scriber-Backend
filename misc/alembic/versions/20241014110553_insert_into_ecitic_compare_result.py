"""insert_into_ecitic_compare_result

Revision ID: 8adb5c65ca25
Revises: cf59ca6ae537
Create Date: 2024-10-14 11:05:53.522394

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8adb5c65ca25"
down_revision = "cf59ca6ae537"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        "ecitic_compare_record_result_ref",
        column_name="compare_result_result_id",
        new_column_name="compare_result_id",
        existing_type=sa.Integer,
    )
    conn = op.get_bind()
    count = conn.execute("select count(*) from ecitic_compare_record").fetchone()[0]
    if count > 0:
        op.execute(
            """
            insert into ecitic_compare_result (deleted_utc, is_diff, question, std_question)
            select id, is_diff, question, std_question from ecitic_compare_record order by id;
            """
        )

        op.execute(
            """
            insert into ecitic_compare_record_result_ref (compare_record_id, compare_result_id)
            select r.id, s.id from ecitic_compare_record r join ecitic_compare_result s on r.id = s.deleted_utc;
            """
        )

    op.execute(
        """
        update ecitic_compare_result set deleted_utc = 0 where deleted_utc != 0;

        """
    )

    op.drop_column("ecitic_compare_record", "is_diff")
    op.drop_column("ecitic_compare_record", "question")
    op.drop_column("ecitic_compare_record", "std_question")
    op.drop_column("ecitic_compare_record", "external_source")


def downgrade():
    op.alter_column(
        "ecitic_compare_record_result_ref",
        column_name="compare_result_id",
        new_column_name="compare_result_result_id",
        existing_type=sa.Integer,
    )

    op.add_column("ecitic_compare_record", sa.Column("is_diff", sa.Boolean, server_default=sa.text("true"), index=True))
    op.add_column("ecitic_compare_record", sa.Column("question", sa.JSON, nullable=False))
    op.add_column("ecitic_compare_record", sa.Column("std_question", sa.JSON, nullable=False))
    op.add_column("ecitic_compare_record", sa.Column("external_source", sa.String(255)))
