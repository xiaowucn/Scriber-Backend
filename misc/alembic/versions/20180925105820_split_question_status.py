"""split question status

Revision ID: 8c3c1ec8e62f
Revises: fcdb529a1781
Create Date: 2018-09-25 10:58:20.572645

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "8c3c1ec8e62f"
down_revision = "723e8d943441"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        UPDATE question
        SET status = 0
        WHERE status = 1
        AND id NOT IN ( SELECT qid FROM answer );
    """
    )


def downgrade():
    op.execute("""UPDATE question SET status=1 WHERE status=0;""")
