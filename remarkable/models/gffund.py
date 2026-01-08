from peewee import SQL, CharField, IntegerField
from playhouse.postgres_ext import ArrayField

from remarkable.pw_models.base import BaseModel


class GFFundFaxMapping(BaseModel):
    class Meta:
        table_name = "gffund_fax_mapping"

    model_name = ArrayField(constraints=[SQL("DEFAULT ARRAY[]::string[]")], field_class=CharField)
    fax = CharField(unique=True, index=True, help_text="fax number or email address)")
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
