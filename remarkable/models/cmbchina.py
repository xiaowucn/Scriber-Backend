import peewee
from playhouse.postgres_ext import BinaryJSONField

from remarkable.pw_models.base import BaseModel


class AuditAnswer(BaseModel):
    fid = peewee.IntegerField()
    product_code = peewee.TextField()
    answer = BinaryJSONField()
    created_utc = peewee.IntegerField()
    updated_utc = peewee.IntegerField()

    class Meta:
        table_name = "cmbchina_answer"
