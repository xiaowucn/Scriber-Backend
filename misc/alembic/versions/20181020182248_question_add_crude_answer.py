"""question_add_crude_answer

Revision ID: dea97658a66e
Revises: b8a834465a57
Create Date: 2018-10-20 18:22:48.453196

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "dea97658a66e"
down_revision = "b8a834465a57"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("question", sa.Column("crude_answer", sa.JSON, nullable=True))


def downgrade():
    op.drop_column("question", "crude_answer")
