"""remove dept_id from file_project

Revision ID: 9ff57621aa88
Revises: 1cda4a8e0b0c
Create Date: 2024-03-28 10:39:53.490010

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9ff57621aa88"
down_revision = "0d41b614d5c8"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("file_project", "dept_id")


def downgrade():
    op.add_column("file_project", sa.Column("dept_id", sa.Integer, nullable=True, index=True))
