"""remove duplicate doclet_id and fid

Revision ID: 0d668179ea9a
Revises: 3bcd23e18964
Create Date: 2019-04-12 00:25:10.506200

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "0d668179ea9a"
down_revision = "3bcd23e18964"
branch_labels = None
depends_on = None


def upgrade():
    sql = """
        DELETE
        FROM rule_doc rd
        WHERE NOT EXISTS (
            SELECT 1
            FROM (
                SELECT MAX(id) AS max_id
                FROM rule_doc
                GROUP BY {}
            ) AS max_ids
            WHERE max_ids.max_id = rd.id
        );
    """
    for dup_col in "fid", "doclet_id":
        op.execute(sql.format(dup_col))


def downgrade():
    pass
