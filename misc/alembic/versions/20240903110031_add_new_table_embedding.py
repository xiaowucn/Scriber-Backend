"""add new table embedding

Revision ID: 0cd100623ad7
Revises: ace0d163721c
Create Date: 2024-09-03 11:00:31.859628

"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy.vector import VECTOR

from remarkable.config import get_config

# revision identifiers, used by Alembic.
revision = "0cd100623ad7"
down_revision = "ace0d163721c"
branch_labels = None
depends_on = None


def upgrade():
    if get_config("client.name") != "scriber":
        return
    op.execute("create extension if not exists vector;")
    op.create_table(
        "embedding",
        sa.Column("id", sa.Integer, autoincrement=True, primary_key=True),
        sa.Column("file_id", sa.Integer, nullable=False),
        sa.Column("index", sa.Integer, nullable=False),
        sa.Column("text", sa.String(2000), nullable=False),
        sa.Column("embedding", VECTOR),
        sa.Column("created_utc", sa.Integer, server_default=sa.text("extract(epoch from now())::int")),
    )
    op.create_index("idx_embedding_file_id_index_position", "embedding", ["file_id", "index"], unique=True)


def downgrade():
    op.drop_table("embedding")
