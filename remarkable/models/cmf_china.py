from peewee import BooleanField, CharField, DecimalField, ForeignKeyField, IntegerField, TextField
from playhouse.postgres_ext import BinaryJSONField, JSONField

from remarkable.common.constants import CmfFiledStatus, CmfInterfacePresetStatus, CommonStatus
from remarkable.db import pw_db
from remarkable.models.new_user import NewAdminUser
from remarkable.pw_models.base import BaseModel
from remarkable.pw_models.model import MoldWithFK, NewMoldField
from remarkable.pw_orm import field
from remarkable.pw_orm.field import EncryptedCharField


class CmfModel(BaseModel):
    class Meta:
        table_name = "cmf_china_model"

    name = CharField()
    user: NewAdminUser | None = ForeignKeyField(NewAdminUser, column_name="uid")
    address = CharField()
    intro = CharField(null=True)
    usage = CharField(null=True)
    metadata = BinaryJSONField(default=dict)

    created_utc = IntegerField()
    updated_utc = IntegerField()

    def can_predict(self, alias: str):
        schema_aliases = self.metadata.get("schema_aliases", {})
        return schema_aliases.get(alias, False)

    @property
    def schema_aliases(self):
        return (self.metadata or {}).get("schema_aliases", {})


class CmfModelFileRef(BaseModel):
    class Meta:
        table_name = "cmf_model_file_ref"

    model: CmfModel = ForeignKeyField(CmfModel, null=False, column_name="model_id", backref="models")
    fid = IntegerField()

    # 当没有关联场景时,调用接口预测的结果
    answer = JSONField(null=True)
    status = IntegerField(default=CmfInterfacePresetStatus.WAIT)
    created_utc = IntegerField()


class CmfFiledFileInfo(BaseModel):
    class Meta:
        table_name = "cmf_filed_file_info"

    fid = IntegerField()
    status = IntegerField(default=CmfFiledStatus.WAIT)
    fail_info = CharField(null=True)


class CmfMoldModelRef(BaseModel):
    class Meta:
        table_name = "cmf_mold_model_ref"

    mold: MoldWithFK = ForeignKeyField(MoldWithFK, null=False, column_name="mold_id", backref="model_versions")
    model: CmfModel = ForeignKeyField(CmfModel, null=False, column_name="model_id", backref="models")
    enable = BooleanField(default=False)

    created_utc = IntegerField()
    updated_utc = IntegerField()

    async def enable_model(self):
        """
        同一时间只能有一个模型启用
        """
        query = CmfMoldModelRef.update(enable=CommonStatus.INVALID.value).where(
            CmfMoldModelRef.mold == self.mold, CmfMoldModelRef.enable == CommonStatus.VALID.value
        )
        await pw_db.execute(query)
        self.enable = CommonStatus.VALID.value
        await pw_db.update(self)

    @classmethod
    async def get_enabled_model(cls, mold: int):
        """
        获取当前启用的模型
        """
        query = cls.select().where(cls.mold == mold, cls.enable).order_by(cls.id.desc())
        cmf_mold_model_ref = await pw_db.prefetch_one(query, CmfModel.select())
        if cmf_mold_model_ref and cmf_mold_model_ref.model:
            return cmf_mold_model_ref.model
        return None


class CmfFiledScript(BaseModel):
    class Meta:
        table_name = "cmf_filed_script"

    filename = CharField()
    context = TextField()
    created_utc = IntegerField()
    updated_utc = IntegerField()


class CmfChinaEmail(BaseModel):
    class Meta:
        table_name = "cmf_china_email"

    host = CharField()
    account = CharField()
    password = EncryptedCharField()
    mold_id = IntegerField()
    pid = IntegerField()
    uid = IntegerField()

    created_utc = IntegerField()
    updated_utc = IntegerField()

    def to_dict(self, exclude=(password,), **kwargs):
        return super().to_dict(exclude=exclude, **kwargs)


class CmfChinaEmailFileInfo(BaseModel):
    class Meta:
        table_name = "cmf_china_email_file_info"

    host = CharField()
    account = CharField()
    email_id = IntegerField()
    fid = IntegerField()
    sent_at = IntegerField()
    from_ = field.ArrayField()
    to = field.ArrayField()
    cc = field.ArrayField()
    subject = CharField()
    is_content = BooleanField(default=False)

    created_utc = IntegerField()


class CmfFileReviewed(BaseModel):
    """文件复核"""

    class Meta:
        table_name = "cmf_china_file_reviewed"

    uid = IntegerField()
    file_id = IntegerField()
    reviewed_count = IntegerField(default=1)

    created_utc = IntegerField()


class CmfUserCheckFields(BaseModel):
    """全景列表字段选项"""

    class Meta:
        table_name = "cmf_china_user_check_fields"

    uid = IntegerField()
    mold_field: NewMoldField = ForeignKeyField(
        NewMoldField, null=False, column_name="mold_field_id", backref="mold_fields"
    )
    check = BooleanField(default=True)

    created_utc = IntegerField()


class CmfModelUsageCount(BaseModel):
    """模型调用统计"""

    class Meta:
        table_name = "cmf_china_model_usage_count"

    model_id = IntegerField()
    date = IntegerField()
    success_count = IntegerField(default=0)
    failure_count = IntegerField(default=0)


class CmfModelAuditAccuracy(BaseModel):
    class Meta:
        table_name = "cmf_model_audit_accuracy"

    model_id = IntegerField(null=False)
    date = IntegerField(null=False)
    molds_rate = BinaryJSONField(null=False)

    created_utc = IntegerField()
    updated_utc = IntegerField()


class CmfSharedDisk(BaseModel):
    class Meta:
        table_name = "cmf_shared_disk"

    file_id = IntegerField(null=False)
    path = CharField()

    created_utc = IntegerField()


class CmfABCompare(BaseModel):
    class Meta:
        table_name = "cmf_ab_compare"

    mold_id = IntegerField(null=False)
    # AB 比对推送地址
    url = CharField()
    # 是否使用LLM
    use_llm = BooleanField(default=False)
    # 提示词
    prompt = TextField(default="")

    created_utc = IntegerField()


class CmfMoldFieldRef(BaseModel):
    class Meta:
        table_name = "cmf_mold_field_ref"

    mold_field: NewMoldField = ForeignKeyField(
        NewMoldField, null=False, column_name="mold_field_id", backref="mold_fields"
    )
    probability = DecimalField(default=0.9)

    created_utc = IntegerField()
