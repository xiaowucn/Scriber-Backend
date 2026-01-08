"""split question status

Revision ID: caf98f4af2a0
Revises: d624e5b432f6
Create Date: 2018-10-29 15:24:31.000252

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "caf98f4af2a0"
down_revision = "b8a834465a57"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        UPDATE question
        SET status = 10
        WHERE question.id IN (
                SELECT qid
                FROM answer
                WHERE standard = 1
            )
            AND question.status = 5
    """
    )


def downgrade():
    op.execute(
        """
        UPDATE question
        SET status = 5
        WHERE status = 10
    """
    )
