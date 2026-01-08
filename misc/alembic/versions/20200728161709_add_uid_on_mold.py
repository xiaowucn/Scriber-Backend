"""add uid on mold

Revision ID: ab87d7eefb48
Revises: c9c14a55e3e5
Create Date: 2020-07-28 16:17:09.628979

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from remarkable.db import IS_MYSQL

# revision identifiers, used by Alembic.

revision = "ab87d7eefb48"
down_revision = "c9c14a55e3e5"
branch_labels = None
depends_on = None

Session = sessionmaker()
Base = declarative_base()


def upgrade():
    op.add_column("mold", sa.Column("uid", sa.Integer))

    class Mold(Base):
        __tablename__ = "mold"
        id = sa.Column(sa.Integer, primary_key=True)
        name = sa.Column(sa.String(255))
        uid = sa.Column(sa.Integer)

    class History(Base):
        __tablename__ = "history"
        id = sa.Column(sa.Integer, primary_key=True)
        uid = sa.Column(sa.Integer)
        action = sa.Column(sa.Integer)
        meta = sa.Column(sa.JSON)

    bind = op.get_bind()
    session = Session(bind=bind)
    for mold in session.query(Mold).order_by(Mold.id).all():
        cond = sa.cast(History.meta.op("->>")("mold_id"), sa.Integer) == mold.id
        if IS_MYSQL:
            cond = sa.cast(History.meta["mold_id"], sa.Integer) == mold.id
        record = session.query(History).filter(cond).first()
        mold.uid = record.uid if record else 1
    session.commit()


def downgrade():
    op.drop_column("mold", "uid")
