"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""

import sqlalchemy as sa
from alembic import op
${imports if imports else ""}
% if "create" in message and "table" in message:
from remarkable.common.migrate_util import create_timestamp_field
% endif
# revision identifiers, used by Alembic.
revision = "${up_revision}"
down_revision = "${down_revision}"
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}
<%
    if "create" in message and "index" in message:
        customer_names = ["index_name", "table_name", "columns"]
        upgrades = """op.create_index(index_name, table_name, columns)"""
        downgrades = """op.drop_index(index_name, table_name)"""
    elif "add" in message and ("column" in message or "field" in message):
        customer_names = ["table_name", "column_name"]
        upgrades = """op.add_column(table_name, sa.Column(column_name, sa.String(255)))"""
        downgrades = """op.drop_column(table_name, column_name)"""
    elif "drop" in message and ("column" in message or "field" in message):
        customer_names = ["table_name", "column_name"]
        upgrades = """op.drop_column(table_name, column_name)"""
        downgrades = """op.add_column(table_name, sa.Column(column_name, sa.String(255)))"""
    elif "create" in message and "table" in message:
        customer_names = ["table_name"]
        upgrades = """op.create_table(
        table_name,
        sa.Column("id", sa.Integer, primary_key=True),
        create_timestamp_field("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        # create_timestamp_field("updated_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
        # sa.Column("deleted_utc", sa.Integer, server_default=sa.text("0")),
        # sa.Column("user_id", sa.Integer, nullable=False),
        # sa.Column("updated_by_id", sa.Integer),
    )"""
        downgrades = """op.drop_table(table_name)"""
    else:
        customer_names = []
        upgrades = downgrades = ""
%>
% if customer_names:
% for name in customer_names:
${name} = ""
% endfor
% endif


def upgrade():
    ${upgrades if upgrades else "pass"}


def downgrade():
    ${downgrades if downgrades else "pass"}
