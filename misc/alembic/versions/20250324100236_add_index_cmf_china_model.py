"""add_index_cmf_china_model

Revision ID: 623958a63595
Revises: d5cddf48a1e2
Create Date: 2025-03-24 10:02:36.095038

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "623958a63595"
down_revision = "d5cddf48a1e2"
branch_labels = None
depends_on = None

CMF_CHINA_MODEL = "cmf_china_model"


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    indices = {"ix_cmf_china_model_name", "cmf_china_model_name_key", "cmf_china_model_address_key"}
    # drop unique constraint
    for constraint in inspector.get_unique_constraints(CMF_CHINA_MODEL):
        if constraint["name"] == "cmf_china_model_address_key":
            op.drop_constraint(constraint["name"], CMF_CHINA_MODEL, type_="unique")
            indices.remove(constraint["name"])
    # drop index
    for index in inspector.get_indexes(CMF_CHINA_MODEL):
        if index["name"] in indices:
            op.drop_index(index["name"], CMF_CHINA_MODEL)
    op.create_index("cmf_china_model_name_address_key", CMF_CHINA_MODEL, ["name", "address"], unique=True)


def downgrade():
    op.create_index("cmf_china_model_name_key", CMF_CHINA_MODEL, ["name"], unique=True)
    op.create_index("cmf_china_model_address_key", CMF_CHINA_MODEL, ["address"], unique=True)
    op.drop_index("cmf_china_model_name_address_key", CMF_CHINA_MODEL)
