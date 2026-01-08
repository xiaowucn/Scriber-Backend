from peewee import SQL, BooleanField, CharField, ForeignKeyField, IntegerField
from playhouse.postgres_ext import ArrayField, BinaryJSONField

from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.pw_models.base import BaseModel


class EciticParaMap(BaseModel):
    category = CharField()
    field = CharField()
    label = CharField()
    group_name = CharField()
    values = ArrayField(field_class=CharField)
    to_value = CharField()

    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")])


class EciticTemplate(BaseModel):
    name = CharField()
    business_group = CharField()
    mold = IntegerField()
    fields = BinaryJSONField()
    uid = IntegerField()
    is_default = BooleanField()

    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")])

    @classmethod
    async def keep_unique_default(cls, business_group, mold):
        query = cls.update(is_default=False).where(cls.mold == mold, cls.business_group == business_group)
        await pw_db.execute(query)


class EciticPush(BaseModel):
    template = IntegerField()
    system = CharField()
    function = CharField()
    email = CharField()
    push_address = CharField()
    uid = IntegerField()
    enabled = BooleanField()  # 自动推送

    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")])


class EciticPushRecord(BaseModel):
    fid = IntegerField()
    task_type = IntegerField()
    push_type = IntegerField()
    uid = IntegerField()
    status = IntegerField()
    data = BinaryJSONField()
    external_source = CharField()
    visible = BooleanField()
    compare_record = IntegerField()

    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)


class EciticCompareRecord(BaseModel):
    qid = IntegerField()
    std_qid = IntegerField()
    mold = IntegerField()
    trigger_type = IntegerField()
    uid = IntegerField()
    external_source = CharField()

    created_utc = IntegerField()


class EciticCompareResult(BaseModel):
    is_diff = BooleanField()
    answer = BinaryJSONField()
    std_answer = BinaryJSONField()
    external_source = CharField()

    created_utc = IntegerField()


class EciticCompareRecordResultRef(BaseModel):
    compare_record_id = IntegerField()
    compare_result = ForeignKeyField(EciticCompareResult, backref="compare_result_refs")


class EciticFile(NewFile):
    class Meta:
        table_name = "file"

    @property
    def file_info(self):
        return self.file_infos[0]


class EciticFileInfo(BaseModel):
    version = CharField(null=True)
    group_name = CharField(null=True)
    batch_no = CharField(null=True)
    templates = ArrayField(IntegerField, default=list)
    is_new_file = BooleanField(default=False)
    need_stat = BooleanField(default=False)
    stat_after_push = BooleanField(default=True)
    external_source = CharField(null=True)

    file = ForeignKeyField(EciticFile, null=False, backref="file_infos")

    class Meta:
        table_name = "ecitic_file_info"

    @classmethod
    async def get_by_file_id(cls, file_id):
        file_info = await pw_db.first(cls.select().where(cls.file == file_id))
        return file_info
