"""add size tu_hash col

Revision ID: abf751032f6c
Revises: db77cb0b07a2
Create Date: 2018-12-06 23:52:19.004216

"""

import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from remarkable.common.storage import localstorage

# revision identifiers, used by Alembic.
revision = "abf751032f6c"
down_revision = "db77cb0b07a2"
branch_labels = None
depends_on = None

table = "hkex_file"
storage = localstorage.mount("hkex_files")
Session = sessionmaker()
Base = declarative_base()


class HKEXFile(Base):
    __tablename__ = table
    id = sa.Column(sa.Integer, primary_key=True)
    url = sa.Column(sa.String(500))
    type = sa.Column(sa.String(50))
    hash = sa.Column(sa.String(64))
    tu_hash = sa.Column(sa.String(64))
    size = sa.Column(sa.Integer)


def upgrade():
    pass


def downgrade():
    pass
