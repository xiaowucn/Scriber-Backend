"""update question ai status

Revision ID: 4a77bf575cd7
Revises: 7731221ae540
Create Date: 2020-03-13 10:53:15.955995

"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


# revision identifiers, used by Alembic.
revision = "4a77bf575cd7"
down_revision = "7731221ae540"
branch_labels = None
depends_on = None


def upgrade():
    # op.execute(
    #     f"""
    #     update question
    #     set ai_status = {AIStatus.NO_MODEL.value}
    #     where id in (select q.id
    #                  from question q
    #                           inner join file f on q.id = f.qid
    #                  where f.mold isnull);
    # """
    # )
    pass


def downgrade():
    pass
