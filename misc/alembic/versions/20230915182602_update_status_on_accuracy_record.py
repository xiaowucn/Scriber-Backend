"""update_status_on_accuracy_record

Revision ID: c6902b72220c
Revises: 67ff4da56196
Create Date: 2023-09-15 18:26:02.605228

"""

import sqlalchemy as sa
from alembic import op

from remarkable.db import IS_MYSQL

# revision identifiers, used by Alembic.
revision = "c6902b72220c"
down_revision = "67ff4da56196"
branch_labels = None
depends_on = None
table = "accuracy_record"


def upgrade():
    op.alter_column(table, "status", server_default=sa.text("''"))
    if not IS_MYSQL:
        op.execute(
            """
            UPDATE accuracy_record
            SET status = CASE
                WHEN length(data::text) > 2 THEN 'done'
                    ELSE 'failed'
                END;
        """
        )


def downgrade():
    pass
