"""add dept_id to file_project

Revision ID: 1cda4a8e0b0c
Revises: c0d9fe6e85f8
Create Date: 2024-03-27 09:56:24.689636

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1cda4a8e0b0c"
down_revision = "c0d9fe6e85f8"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("file_project", sa.Column("dept_id", sa.Integer, nullable=True, index=True))


def downgrade():
    op.drop_column("file_project", "dept_id")
