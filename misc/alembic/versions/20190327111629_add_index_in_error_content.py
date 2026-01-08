"""add_index_in_error_content

Revision ID: c32162744c79
Revises: 348d87b8d188
Create Date: 2019-03-27 11:16:29.124302

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "c32162744c79"
down_revision = "348d87b8d188"
branch_labels = None
depends_on = None


def upgrade():
    sql = """
        DELETE FROM error_content ec
        WHERE NOT EXISTS (
            SELECT 1
            FROM (
                SELECT MAX(id) AS max_id
                FROM error_content
                GROUP BY uid, fid, rule_result_id
            ) AS max_ids
            WHERE max_ids.max_id = ec.id
        );
        """
    op.execute(sql)
    op.create_index("error_content_uid_fid_rid_key", "error_content", ["uid", "fid", "rule_result_id"], unique=True)


def downgrade():
    op.drop_index("error_content_uid_fid_rid_key", "error_content")
