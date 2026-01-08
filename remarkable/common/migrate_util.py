import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.elements import TextClause

from remarkable.db import IS_MYSQL


def create_timestamp_field(field_name: str, typ: type, server_default: TextClause | None = None, **kwargs):
    if IS_MYSQL:
        if server_default is not None and field_name != "deleted_utc":
            server_default = sa.text("(UNIX_TIMESTAMP(CURRENT_TIMESTAMP()))")
    return sa.Column(field_name, typ, server_default=server_default, **kwargs)


def create_array_field(field_name: str, typ: sa.ARRAY, server_default: TextClause | None = None, **kwargs):
    if IS_MYSQL:
        typ = sa.JSON
        if server_default is not None:
            server_default = None
    return sa.Column(field_name, typ, server_default=server_default, **kwargs)


def create_jsonb_field(field_name: str, server_default: TextClause | None = None, **kwargs):
    if IS_MYSQL:
        typ = sa.JSON
        server_default = None
    else:
        typ = postgresql.JSONB
    return sa.Column(field_name, typ, server_default=server_default, **kwargs)


def op_drop_index_if_exists(op, idx, table):
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    for index in inspector.get_indexes(table):
        if index["name"] == idx:
            op.drop_index(idx, table)
            break
