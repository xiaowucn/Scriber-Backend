"""add new table chinaamc_project_info

Revision ID: 5916e6f75d62
Revises: 9ff57621aa88
Create Date: 2024-03-28 11:28:01.829275

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field, create_timestamp_field
from remarkable.config import get_config
from remarkable.common.migrate_util import create_array_field, create_timestamp_field

# revision identifiers, used by Alembic.
revision = "5916e6f75d62"
down_revision = "9ff57621aa88"
branch_labels = None
depends_on = None

table = "chinaamc_project_info"


def upgrade():
    op.create_table(
        table,
        sa.Column("id", sa.Integer, nullable=False, primary_key=True),
        sa.Column("pid", sa.Integer, nullable=False, unique=True),
        sa.Column("source", sa.Integer, nullable=False),
        create_array_field("dept_ids", sa.ARRAY(sa.Text), nullable=False, server_default=sa.text("'{}'::text[]")),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )

    if get_config("client.name") == "chinaamc":
        op.execute(
            """
            insert into chinaamc_project_info (pid, source)
            select id, source::integer from file_project where not visible and source in ('0', '1');
        """
        )
    op.drop_column("file_project", "source")


def downgrade():
    op.drop_table(table)
    op.add_column("file_project", sa.Column("source", sa.String(255)))
