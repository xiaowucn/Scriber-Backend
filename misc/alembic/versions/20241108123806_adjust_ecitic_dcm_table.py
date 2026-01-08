"""adjust_ecitic_dcm_table

Revision ID: f0f72bef6653
Revises: 1e697d01c76c
Create Date: 2024-11-08 12:38:06.560905

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f0f72bef6653"
down_revision = "1e697d01c76c"
branch_labels = None
depends_on = None

# Table names as variables
DCM_BOND_ORDER = "dcm_bond_order"
DCM_UNDER_WRITE_RATE = "dcm_under_write_rate"
DCM_FILE_INFO = "dcm_file_info"
DCM_BOND_LIMIT = "dcm_bond_limit"


def upgrade():
    op.add_column(DCM_BOND_ORDER, sa.Column("orderapply_id", sa.String(255), nullable=False))
    op.create_index("dcm_bond_order_orderapply_id_key", DCM_BOND_ORDER, ["orderapply_id"], unique=True)
    op.add_column(DCM_BOND_ORDER, sa.Column("order_id", sa.String(255), nullable=False))

    op.add_column(DCM_UNDER_WRITE_RATE, sa.Column("underwritegroup_id", sa.String(255), nullable=False))
    op.create_index(
        "dcm_under_write_rate_underwritegroup_id_key", DCM_UNDER_WRITE_RATE, ["underwritegroup_id"], unique=True
    )
    op.add_column(DCM_UNDER_WRITE_RATE, sa.Column("order_id", sa.String(255), nullable=False))

    op.add_column(DCM_FILE_INFO, sa.Column("email_content", sa.String(255)))

    conn = op.get_bind()
    inspector = sa.inspect(conn)
    index_name = "dcm_under_write_rate_project_id_key"

    constraints = inspector.get_unique_constraints(DCM_UNDER_WRITE_RATE)
    if index_name in constraints:
        op.drop_constraint(index_name, DCM_UNDER_WRITE_RATE, type_="unique")
    else:
        op.drop_index(index_name, DCM_UNDER_WRITE_RATE)
    op.create_index("dcm_bond_limit_limit_id_key", DCM_BOND_LIMIT, ["limit_id"], unique=True)


def downgrade():
    op.drop_column(DCM_BOND_ORDER, "orderapply_id")
    op.drop_column(DCM_BOND_ORDER, "order_id")
    op.drop_column(DCM_UNDER_WRITE_RATE, "underwritegroup_id")
    op.drop_column(DCM_UNDER_WRITE_RATE, "order_id")
    op.drop_column(DCM_FILE_INFO, "email_content")

    op.drop_index("dcm_bond_limit_limit_id_key", DCM_BOND_LIMIT)
    op.create_check_constraint("dcm_under_write_rate_project_id_key", "dcm_under_write_rate", "true")
