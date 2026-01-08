"""add column mold to accuracy_record

Revision ID: 863fe4eedfa0
Revises: 19130ed7c980
Create Date: 2018-12-07 15:19:16.479896

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "863fe4eedfa0"
down_revision = "19130ed7c980"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("accuracy_record", sa.Column("mold", sa.Integer, nullable=False))


def downgrade():
    op.drop_column("accuracy_record", "mold")
