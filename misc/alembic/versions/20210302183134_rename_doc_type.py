"""Rename doc type

Revision ID: 935fa0752f8c
Revises: c272d0ff0a76
Create Date: 2021-03-02 18:31:34.854269

"""

from alembic import op

from remarkable.common.constants import SZSE_RULE_MAP

# revision identifiers, used by Alembic.
revision = "935fa0752f8c"
down_revision = "c272d0ff0a76"
branch_labels = None
depends_on = None

table = "file_meta"
col_name = "doc_type"


def upgrade():
    for k, v in SZSE_RULE_MAP.items():
        op.execute(f"update {table} set {col_name} = '{v}' where {col_name} = '{k}'")


def downgrade():
    for k, v in SZSE_RULE_MAP.items():
        op.execute(f"update {table} set {col_name} = '{k}' where {col_name} = '{v}'")
