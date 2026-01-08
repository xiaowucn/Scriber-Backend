# -*- coding: utf-8 -*-

from sqlalchemy import Column, Integer, MetaData, String, Table, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import mapper, sessionmaker
from sqlalchemy.schema import Sequence

from remarkable.common.util import generate_timestamp

BaseModel = declarative_base()
metadata = MetaData()


def create_db_session(dsn_url):
    engine = create_engine(dsn_url, echo=False)
    session_maker = sessionmaker(engine)
    return session_maker()


record_table = Table(
    "record",
    metadata,
    Column("id", Integer, Sequence("record_id_seq"), primary_key=True),
    Column("key", String(length=64)),
    Column("filename", String(length=256)),
    Column("filemeta", String(length=256)),
    Column("schema", Text),
    Column("result_version", String(length=64)),
    Column("created_utc", Integer, default=generate_timestamp),
    Column("updated_utc", Integer, default=generate_timestamp, onupdate=generate_timestamp),
)

Record = type("Record", (object,), {})
mapper(Record, record_table)
