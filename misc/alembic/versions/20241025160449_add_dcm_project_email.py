"""add_dcm_project_email

Revision ID: bf0b015ed97a
Revises: a09e64768533
Create Date: 2024-10-25 16:04:49.053150

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "bf0b015ed97a"
down_revision = "a09e64768533"
branch_labels = None
depends_on = None

# Table names as variables
DCM_PROJECT = "dcm_project"


def upgrade():
    op.add_column(DCM_PROJECT, sa.Column("email_host", sa.String(255)))
    op.add_column(DCM_PROJECT, sa.Column("email_address", sa.String(255)))
    op.add_column(DCM_PROJECT, sa.Column("email_password", sa.String(255)))
    op.add_column(DCM_PROJECT, sa.Column("fill_status", sa.String(255)))


def downgrade():
    op.drop_column(DCM_PROJECT, "email_host")
    op.drop_column(DCM_PROJECT, "email_address")
    op.drop_column(DCM_PROJECT, "email_password")
    op.drop_column(DCM_PROJECT, "fill_status")
