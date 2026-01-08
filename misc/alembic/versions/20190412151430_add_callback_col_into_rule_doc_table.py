"""add callback col into rule_doc table

Revision ID: 38ad35144921
Revises: 0d668179ea9a
Create Date: 2019-04-12 15:14:30.069349

"""

import sqlalchemy as sa
from alembic import op

from remarkable.db import IS_MYSQL

# revision identifiers, used by Alembic.
revision = "38ad35144921"
down_revision = "0d668179ea9a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("rule_doc", sa.Column("callback", sa.String(500) if IS_MYSQL else sa.Text))
    op.create_index("ix_fid_did_callback", "rule_doc", ["fid", "doclet_id", "callback"], unique=True)
    op.drop_index("ix_rule_doc_aid", "rule_doc")


def downgrade():
    op.drop_column("rule_doc", "callback")
    # op.drop_index('ix_fid_did_callback', 'rule_doc')  # index dropped when drop the column
    op.create_index("ix_rule_doc_aid", "rule_doc", ["aid"])
