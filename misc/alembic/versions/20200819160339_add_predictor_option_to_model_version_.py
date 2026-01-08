"""add predictor_option to model_version table

Revision ID: 622cf706d846
Revises: c60d629a263e
Create Date: 2020-08-19 16:03:39.007681

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "622cf706d846"
down_revision = "c60d629a263e"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("model_version", sa.Column("predictor_option", sa.JSON))
    op.execute(
        "update model_version set predictor_option=(select predictor_option from mold where mold.id=model_version.mold);"
    )


def downgrade():
    op.drop_column("model_version", "predictor_option")
