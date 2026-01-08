"""drop_abandoned_utc

Revision ID: 4e2853667d69
Revises: 33d6332107dd
Create Date: 2023-02-27 18:43:34.914026

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "4e2853667d69"
down_revision = "33d6332107dd"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("file", "abandoned_utc")
    op.drop_column("file_tree", "abandoned_utc")


def downgrade():
    pass
