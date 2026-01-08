from peewee import SQL, CharField, IntegerField

from remarkable.pw_models.base import BaseModel


class Role(BaseModel):
    name = CharField()
    description = CharField()
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])
