"""set unique to false in admin_user and mold

Revision ID: 04162510f259
Revises: 54e66509d704
Create Date: 2021-05-08 17:59:11.498185

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "04162510f259"
down_revision = "54e66509d704"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("admin_user_name_key", "admin_user", type_="unique")
    op.drop_constraint("mold_name_key", "mold", type_="unique")


def downgrade():
    op.create_unique_constraint("admin_user_name_key", "admin_user", ["name"])
    op.create_unique_constraint("mold_name_key", "mold", ["name"])
