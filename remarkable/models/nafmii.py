from enum import IntEnum

from peewee import CharField, ForeignKeyField, IntegerField, TextField

from remarkable.models.new_file import NewFile
from remarkable.pw_models.base import BaseModel
from remarkable.pw_models.model import NafmiiUser
from remarkable.pw_orm import field


class TaskFlag(IntEnum):
    default = 0  # 识别且推送
    skip_push = 1  # 只重新识别
    only_push = 2  # 只重新推送


class NafmiiSystem(BaseModel):
    name = CharField(null=False)
    registry = CharField(null=False)
    partner_id = CharField(null=False)

    created_utc = IntegerField(null=False)
    updated_utc = IntegerField(null=False)

    class Meta:
        table_name = "nafmii_system"


class NafmiiFileInfo(BaseModel):
    sys = ForeignKeyField(NafmiiSystem)
    file = ForeignKeyField(NewFile, null=False, backref="file_info")
    ext_id = CharField(null=True)
    ext_path = CharField(null=True)
    status = IntegerField(null=False, default=0)
    confirm_status = IntegerField(null=False, default=0)
    task_types = field.ArrayField(TextField, null=True)
    keywords = field.ArrayField(TextField, null=True)
    org_name = CharField(null=True)
    org_code = CharField(null=True)

    revise_file_path = CharField(null=True)

    flag = IntegerField(null=False, default=TaskFlag.default)
    push_answer_at = IntegerField(null=False, default=0)

    created_utc = IntegerField(null=False)
    updated_utc = IntegerField(null=False)
    deleted_utc = IntegerField()


class FileAnswer(BaseModel):
    file = ForeignKeyField(NewFile, null=False, column_name="fid", backref="answers")
    status = IntegerField(default=0)
    diff = field.JSONField(default=list)
    sensitive_word = field.JSONField(default=list)
    keyword = field.JSONField(default=list)

    created_utc = IntegerField(null=False)
    updated_utc = IntegerField(null=False)
    deleted_utc = IntegerField(null=False)

    class Meta:
        table_name = "nafmii_file_answer"


class WordType(BaseModel):
    name = CharField(null=False)
    created_utc = IntegerField(null=False)

    class Meta:
        table_name = "nafmii_word_type"


class SensitiveWord(BaseModel):
    sys = ForeignKeyField(NafmiiSystem)
    user = ForeignKeyField(NafmiiUser)
    type = ForeignKeyField(WordType)

    name = CharField(null=False)

    created_utc = IntegerField(null=False)

    class Meta:
        table_name = "nafmii_sensitive_word"


class Knowledge(BaseModel):
    class Meta:
        table_name = "nafmii_knowledge"

    type = IntegerField(null=False)
    name = CharField(null=False)
    user = ForeignKeyField(NafmiiUser)

    created_utc = IntegerField(null=False)
    updated_utc = IntegerField(null=False)
    deleted_utc = IntegerField(null=False)


class KnowledgeDetail(BaseModel):
    knowledge = ForeignKeyField(Knowledge, backref="details")
    type = IntegerField(null=False)
    title = CharField(null=False)
    content = CharField(null=False)
    filename = CharField(null=False)
    file_path = CharField(null=False)

    created_utc = IntegerField(null=False)
    updated_utc = IntegerField(null=False)
    deleted_utc = IntegerField(null=False)

    class Meta:
        table_name = "nafmii_knowledge_detail"
