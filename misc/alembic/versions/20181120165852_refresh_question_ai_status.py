"""refresh question.ai_status

Revision ID: 33593585bb7c
Revises: 28d196beac1f
Create Date: 2018-11-20 16:58:52.577778

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "33593585bb7c"
down_revision = "28d196beac1f"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("update question set ai_status=3 where preset_answer is not null and ai_status is null")
    op.execute("update question set ai_status=-1 where ai_status is null")
    op.execute("alter table question alter column ai_status set default -1")


def downgrade():
    op.execute("alter table question alter column ai_status set default null")
    op.execute("update question set ai_status=null where ai_status=-1")
