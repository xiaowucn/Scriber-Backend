"""add_column_to_cmf_china_email_file_info

Revision ID: d2890c68da3e
Revises: 1ac4443bc202
Create Date: 2025-05-26 16:43:07.245247

"""

import sqlalchemy as sa
from alembic import op

from remarkable.common.migrate_util import create_array_field

# revision identifiers, used by Alembic.
revision = "d2890c68da3e"
down_revision = "1ac4443bc202"
branch_labels = None
depends_on = None


table_name = "cmf_china_email_file_info"


def upgrade():
    # 发送时间
    op.add_column(table_name, sa.Column("sent_at", sa.Integer, nullable=True))
    # 发件人
    op.add_column(table_name, create_array_field("from_", sa.ARRAY(sa.String)))
    # 接件人
    op.add_column(table_name, create_array_field("to", sa.ARRAY(sa.String)))
    # 抄送人
    op.add_column(table_name, create_array_field("cc", sa.ARRAY(sa.String)))
    # 邮件主题
    op.add_column(table_name, sa.Column("subject", sa.Text))
    # 是否是正文文件
    op.add_column(table_name, sa.Column("is_content", sa.Boolean, server_default=sa.text("false")))


def downgrade():
    op.drop_column(table_name, "sent_at")
    op.drop_column(table_name, "from_")
    op.drop_column(table_name, "to")
    op.drop_column(table_name, "cc")
    op.drop_column(table_name, "subject")
    op.drop_column(table_name, "is_content")
