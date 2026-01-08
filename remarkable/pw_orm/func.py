import peewee
from peewee import fn

from remarkable.db import IS_MYSQL

if IS_MYSQL:
    ARRAY_AGG = fn.JSON_ARRAYAGG
    JSONB_BUILD_OBJECT = fn.JSON_OBJECT
else:
    ARRAY_AGG = fn.ARRAY_AGG
    JSONB_BUILD_OBJECT = fn.JSONB_BUILD_OBJECT


def any_in(array_field, field):
    if IS_MYSQL:
        return fn.JSON_CONTAINS(array_field, field.cast("json"), "$")
    else:
        return field == fn.ANY(array_field)


def build_array(*args):
    if IS_MYSQL:
        return fn.JSON_ARRAY(*args)
    return peewee.Value(list(args), unpack=False)


def _sum(*args):
    if IS_MYSQL:
        return fn.Convert(fn.SUM(*args), peewee.SQL("SIGNED"))
    return fn.SUM(*args)
