"""change autodoc callback url

Revision ID: 8c6f4d3f8e2c
Revises: 6c7dc78e4672
Create Date: 2019-04-23 18:29:45.290568

"""

import hashlib

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

revision = "8c6f4d3f8e2c"
down_revision = "38ad35144921"
branch_labels = None
depends_on = None

Session = sessionmaker()
Base = declarative_base()
table = "rule_doc"


class RuleDoc(Base):
    __tablename__ = table
    id = sa.Column(sa.Integer, primary_key=True)
    fid = sa.Column(sa.Integer)
    doclet_id = sa.Column(sa.Integer)
    callback = sa.Column(sa.Text)
    hash_tmp = sa.Column(sa.String(255))


def upgrade():
    # 先取消unique index
    op.drop_index("ix_fid_did_callback", table)
    op.add_column(table, sa.Column("hash_tmp", sa.String(255)))

    # 替换callback
    sql = """
        UPDATE rule_doc
        SET callback = 'http://bj.cheftin.com:55778/api/v1/callback/rule_item/doclet'
        WHERE callback = 'http://bj.cheftin.com:55978/api/v1/callback/rule_item/doclet';
    """
    op.execute(sql)

    # hash
    bind = op.get_bind()
    session = Session(bind=bind)
    for doc in session.query(RuleDoc):
        doc.hash_tmp = hashlib.md5("{}{}{}".format(doc.fid, doc.doclet_id, doc.callback).encode()).hexdigest()
    session.commit()

    # 根据hash去重, 留较新的
    sql = """
        DELETE FROM rule_doc rd
        WHERE NOT EXISTS (
            SELECT 1
            FROM (
                SELECT MIN(id) AS min_id
                FROM rule_doc
                GROUP BY hash_tmp
            ) AS grouped_ids
            WHERE grouped_ids.min_id = rd.id
        );
    """
    op.execute(sql)

    # 删临时表, 恢复index
    op.drop_column(table, "hash_tmp")
    op.create_index("ix_fid_did_callback", table, ["fid", "doclet_id", "callback"], unique=True)


def downgrade():
    sql = """
        UPDATE rule_doc
        SET callback = 'http://bj.cheftin.com:55978/api/v1/callback/rule_item/doclet'
        WHERE callback = 'http://bj.cheftin.com:55778/api/v1/callback/rule_item/doclet';
    """
    op.execute(sql)
