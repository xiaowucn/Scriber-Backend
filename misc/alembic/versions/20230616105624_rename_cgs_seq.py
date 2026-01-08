"""rename cgs seq

Revision ID: 152b41b74636
Revises: 0267a3a5e25b
Create Date: 2023-06-16 10:56:24.655691

"""

from alembic import op

from remarkable.db import IS_MYSQL

from remarkable.db import IS_MYSQL

# revision identifiers, used by Alembic.
revision = "152b41b74636"
down_revision = "0267a3a5e25b"
branch_labels = None
depends_on = None


def upgrade():
    # GaussDB does not support rename sequence function
    # op.execute("ALTER SEQUENCE cgs_answer_data_id_seq RENAME TO answer_data_id_seq;")
    # So we have to choose a complicated way to rename the sequence
    if IS_MYSQL:
        pass
    else:
        op.execute(
            """
        CREATE SEQUENCE answer_data_id_seq;
        SELECT setval('answer_data_id_seq', (SELECT last_value FROM cgs_answer_data_id_seq));
        ALTER TABLE answer_data ALTER COLUMN id SET DEFAULT nextval('answer_data_id_seq');
        DROP SEQUENCE cgs_answer_data_id_seq;
        """
        )


def downgrade():
    pass
