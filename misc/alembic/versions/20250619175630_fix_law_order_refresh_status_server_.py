"""fix law_order refresh_status server default

Revision ID: 5b3de4ad2921
Revises: 65193c454a43
Create Date: 2025-06-19 17:56:30.682073

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "5b3de4ad2921"
down_revision = "65193c454a43"
branch_labels = None
depends_on = None


table_name = "law_order"
column_name = "refresh_status"


def upgrade():
    op.alter_column(table_name, column_name, server_default="0")


def downgrade():
    pass
