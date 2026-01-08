"""adjust_ecitic__dcm_table_index

Revision ID: db3ad876238b
Revises: c6c4c0b7142a
Create Date: 2024-10-22 16:32:42.034429

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "db3ad876238b"
down_revision = "c6c4c0b7142a"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    # drop unique constraint
    for index_name, tablename in (
        ("dcm_bond_order_project_id_key", "dcm_bond_order"),
        ("dcm_bond_limit_project_id_key", "dcm_bond_limit"),
    ):
        constraints = inspector.get_unique_constraints(tablename)
        if index_name in constraints:
            op.drop_constraint(index_name, tablename, type_="unique")
        else:
            op.drop_index(index_name, tablename)

    op.create_index("ix_bond_order", "dcm_bond_order", ["project_id", "order_no", "interest_rate"])
    op.create_index("ix_bond_limit", "dcm_bond_limit", ["project_id", "order_no", "interest_rate"])


def downgrade():
    op.create_index("dcm_bond_order_project_id_key", "dcm_bond_order", ["project_id"], unique=True)
    op.create_index("dcm_bond_limit_project_id_key", "dcm_bond_limit", ["project_id"], unique=True)

    op.drop_index("ix_bond_order", "dcm_bond_order")
    op.drop_index("ix_bond_limit", "dcm_bond_limit")
