from peewee import SQL, CharField, ForeignKeyField, IntegerField, fn

from remarkable.common.constants import CommonStatus, ModelType
from remarkable.db import pw_db
from remarkable.models.new_model_answer import ModelAnswer
from remarkable.pw_models.base import BaseModel
from remarkable.pw_models.model import MoldWithFK
from remarkable.pw_orm import field


class _ModelVersion(BaseModel):
    name = CharField()
    model_type = IntegerField(db_column="type")
    status = IntegerField(default=0)
    dirs = field.ArrayField()
    files = field.ArrayField()
    enable = IntegerField(default=0)
    predictors = field.JSONField(json_type="json", null=True)
    predictor_option = field.JSONField(json_type="json", null=True)

    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")])

    @classmethod
    async def enable_model(cls, vid):
        """
        同一时间只能有一个版本的模型启用
        """
        model_version = await cls.find_by_id(vid)
        query = cls.update(enable=CommonStatus.INVALID.value).where(
            cls.mold == model_version.mold, cls.enable == CommonStatus.VALID.value
        )
        await cls.manager().execute(query)
        model_version.enable = CommonStatus.VALID.value
        await cls.manager().update(model_version)

    @classmethod
    async def disable_model(cls, vid):
        query = cls.update(enable=CommonStatus.INVALID.value).where(cls.id == vid)
        await cls.manager().execute(query)

    @classmethod
    async def get_enabled_version(cls, mold: int, only_developed=False):
        """
        获取当前启用的模型版本
        """
        cond = cls.mold == mold
        cond &= cls.model_type != ModelType.PROMPTER.value
        cond &= cls.enable == CommonStatus.VALID.value
        cond &= cls.deleted_utc == 0

        if only_developed:
            cond &= cls.model_type == ModelType.DEVELOP.value

        query = cls.select(cls.id).where(cond).order_by(cls.created_utc.desc()).limit(1)
        with cls.manager().allow_sync():
            # TODO: use async query when we completely drop the gino orm.
            return query.scalar() or 0

    @classmethod
    async def get_last_with_model_answer(cls, mold_id, enable_vid):
        """
        获取上一个有ModelAnswer的定制模型
        :param mold_id:
        :param enable_vid:
        :return:
        """
        from remarkable.pw_models.question import NewQuestion

        last_vid_query = ModelAnswer.select(fn.MAX(ModelAnswer.vid))
        last_vid_query = last_vid_query.join(NewQuestion, on=(ModelAnswer.qid == NewQuestion.id))
        last_vid_query = last_vid_query.join(
            NewModelVersion, on=(NewModelVersion.id == ModelAnswer.vid), include_deleted=True
        )

        cond = (NewQuestion.mold == mold_id) & (ModelAnswer.vid != enable_vid)
        cond &= NewModelVersion.model_type == ModelType.DEVELOP.value
        cte = last_vid_query.where(cond).cte("cte")

        query = (
            NewModelVersion.select(include_deleted=True).join(cte, on=(NewModelVersion.id == cte.c.max)).with_cte(cte)
        )
        version = await pw_db.first(query)
        return version


class NewModelVersion(_ModelVersion):
    class Meta:
        table_name = "model_version"

    mold = IntegerField()


class ModelVersionWithFK(_ModelVersion):
    class Meta:
        table_name = "model_version"

    mold = ForeignKeyField(MoldWithFK, db_column="mold", backref="model_versions")
