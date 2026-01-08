"""add col name for model_version

Revision ID: f923170dab2e
Revises: e77239064967
Create Date: 2022-04-07 12:37:21.194298

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f923170dab2e"
down_revision = "e77239064967"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("model_version", sa.Column("name", sa.String(255)))
    op.execute("update model_version set name = id where name is null;")
    op.create_index("model_version_schema_name", "model_version", ["mold", "name"], unique=True)


def downgrade():
    op.drop_index("model_version_schema_name", "model_version")
    op.drop_column("model_version", "name")
