from peewee import BooleanField, CharField, ForeignKeyField, IntegerField

from remarkable.pw_models.base import BaseModel
from remarkable.pw_models.model import NewFileProject


class ZTSProjectInfo(BaseModel):
    project = ForeignKeyField(NewFileProject, null=False)
    exchange = CharField()
    record_id = CharField()
    inspected_utc = IntegerField()
    restricted_funds = BooleanField()
    borrowing = BooleanField()
    guarantee = BooleanField()
    consistency = BooleanField()
    created_utc = IntegerField()
    updated_utc = IntegerField()

    class Meta:
        table_name = "zts_project_info"
