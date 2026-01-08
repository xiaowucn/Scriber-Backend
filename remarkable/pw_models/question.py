from importlib import import_module
from typing import Self

from peewee import SQL, BigIntegerField, CharField, ForeignKeyField, IntegerField
from speedy.peewee_plus.field import EnumField

from remarkable.answer.common import update_manual_tag
from remarkable.common.constants import (
    AIStatus,
    ConflictTreatmentType,
    FillInStatus,
    LLMStatus,
    MoldType,
    QuestionStatus,
)
from remarkable.common.util import generate_timestamp
from remarkable.config import get_config
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import ADMIN, NewAdminUser
from remarkable.pw_models.base import BaseModel
from remarkable.pw_models.model import (
    MoldWithFK,
    NewAnswer,
    NewCCXIContract,
    NewChinaStockAnswer,
    NewExtractMethod,
    NewMold,
)
from remarkable.pw_orm import field
from remarkable.service.model import ModelVersionService
from remarkable.utils.answer_util import AnswerUtil, UserAnswer


class _Question(BaseModel):
    ai_status = IntegerField(constraints=[SQL("DEFAULT '-1'::integer")], null=True)
    llm_status: LLMStatus = EnumField(LLMStatus, null=True)
    exclusive_status = IntegerField(constraints=[SQL("DEFAULT '-1'::integer")], null=True)
    compare_status = IntegerField(default=0)
    answer = field.JSONField(json_type="json", null=True)
    checksum = CharField()
    confirmed_answer = field.JSONField(json_type="json", null=True)
    created_utc = BigIntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])
    crude_answer = field.JSONField(json_type="json", null=True)
    data = field.JSONField(json_type="json")
    data_updated_utc = IntegerField(null=True)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    did = IntegerField(index=True, null=True)
    diff_detail = field.JSONField(json_type="json", null=True)
    fill_in_status = IntegerField(null=True)
    fill_in_user = CharField(null=True)
    health = IntegerField(constraints=[SQL("DEFAULT 1")])
    mark_uids = field.ArrayField(field_class=IntegerField, default=list)
    mark_users = field.ArrayField(field_class=CharField, default=list)
    name = CharField(null=True)
    num = CharField(index=True, null=True)
    origin_health = IntegerField(null=True)
    preset_answer = field.JSONField(json_type="json", null=True)
    preset_answer_version = CharField(null=True)
    priority = IntegerField(constraints=[SQL("DEFAULT 100")], index=True, null=True)
    progress = CharField(null=True)
    status = IntegerField(constraints=[SQL("DEFAULT 0")])
    updated_utc = BigIntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")])

    class Meta:
        table_name = "question"
        indexes = ((("name", "num", "fill_in_status"), False),)

    @staticmethod
    def gen_checksum(fid, mold):
        return f"{fid}-{mold}"

    @classmethod
    async def reset_predict_status(cls, questions):
        for question in questions:
            mold_ins = await NewMold.find_by_id(question.mold)
            exclusive_status = await cls._initialize_ai_status(mold_ins)
            await pw_db.update(
                question,
                ai_status=exclusive_status,
                exclusive_status=exclusive_status,
                llm_status=LLMStatus.SKIP_PREDICT if question.llm_status == LLMStatus.SKIP_PREDICT else LLMStatus.TODO,
                updated_utc=generate_timestamp(),
            )

    @staticmethod
    async def _initialize_ai_status(mold_ins: NewMold):
        # from remarkable.models.model_version import NewModelVersion

        enable_preset_answer = get_config("web.preset_answer") or False
        if not enable_preset_answer:
            return AIStatus.SKIP_PREDICT
        if mold_ins.mold_type == MoldType.LLM:
            return AIStatus.TODO
        if mold_ins.predictor_option["framework_version"] == "1.0":
            return AIStatus.TODO
        has_predictor_config = True
        try:
            utils_module_from_code = import_module("remarkable.predictor")
            utils_module_from_code.load_prophet_config(mold_ins)
        except ModuleNotFoundError:
            has_predictor_config = False
        enable_version_id = await ModelVersionService.get_enabled_version(mold_ins.id)
        if not has_predictor_config and not enable_version_id:
            return AIStatus.DISABLE
        return AIStatus.TODO

    @classmethod
    async def find_by_fid_mid(cls, fid: int, mold_id: int, for_update=False) -> Self | None:
        return await pw_db.first(cls.select(for_update=for_update).filter(fid=fid, mold=mold_id))

    @classmethod
    async def find_by_fid(cls, fid: int) -> list[Self]:
        return await cls.find_by_kwargs(fid=fid, delegate="all")

    @classmethod
    async def create_by_mold(cls, fid: int, mold: int, name: str | None = None, num: str | None = None):
        health = get_config("web.default_question_health") or 1
        mold_ins = await NewMold.find_by_id(mold)
        exclusive_status = await cls._initialize_ai_status(mold_ins)
        if mold_ins.mold_type == MoldType.COMPLEX.value or exclusive_status != AIStatus.TODO:
            llm_status = LLMStatus.SKIP_PREDICT
        else:
            llm_status = LLMStatus.TODO
        meta = {
            "data": {"file_id": fid},
            "checksum": cls.gen_checksum(fid, mold),
            "fid": fid,
            "health": health,
            "origin_health": health,
            "status": QuestionStatus.TODO.value,
            "ai_status": exclusive_status,
            "exclusive_status": exclusive_status,
            "llm_status": llm_status,
            "name": name,
            "num": num,
            "fill_in_status": FillInStatus.TODO.value,
            "mold": mold,
        }

        question = await cls.find_by_fid_mid(fid, mold)
        if not question:
            question = await pw_db.create(cls, **meta)
        return question

    @classmethod
    async def delete_by_mold(cls, fid: int, mold: int):
        question = await cls.find_by_fid_mid(fid, mold)
        if question:
            await pw_db.execute(NewCCXIContract.delete().where(NewCCXIContract.qid == question.id))
            await pw_db.execute(NewChinaStockAnswer.delete().where(NewChinaStockAnswer.qid == question.id))
            await pw_db.delete(question)

    @classmethod
    async def get_master_question(cls, fid: int, *fields):
        """
        当前一个file只会有一个master_question
        :param fid:
        :return:
        """
        return await pw_db.first(
            cls.select(*fields)
            .join(NewMold, on=cls.mold == NewMold.id)
            .where(
                NewMold.master.is_null(),
                cls.fid == fid,
            )
            .order_by(NewMold.id)
        )

    @classmethod
    async def list_by_range(
        cls,
        mold=None,
        start=None,
        end=None,
        question_status=None,
        tree_l=None,
        have_preset_answer=None,
        have_crude_answer=None,
        project=None,
        special_cols=None,
        files_ids=None,
    ) -> list[Self]:
        conditions = []
        if mold is not None:
            conditions.append(cls.mold == int(mold))
        if start is not None:
            conditions.append(NewFile.id >= int(start))
        if end is not None:
            conditions.append(NewFile.id <= int(end))
        if question_status:
            conditions.append(cls.status.in_(question_status))
        if tree_l:
            conditions.append(NewFile.tree_id.in_(tree_l))
        if files_ids:
            conditions.append(NewFile.id.in_(files_ids))
        if have_preset_answer is True:
            conditions.append(cls.preset_answer.is_null(False))
        elif have_preset_answer is False:
            conditions.append(cls.preset_answer.is_null(True))
        if have_crude_answer is True:
            conditions.append(cls.crude_answer.is_null(False))
        elif have_crude_answer is False:
            conditions.append(cls.crude_answer.is_null(True))

        if project is not None:
            conditions.append(NewFile.pid == int(project))
        columns = []  # By default all fields will be queried if columns is a empty list
        if special_cols:
            columns = [getattr(cls, col) for col in special_cols if hasattr(cls, col)]

        questions = await pw_db.execute(
            cls.select(*columns)
            .join(NewFile, on=(cls.fid == NewFile.id))
            .where(*conditions)
            .order_by(NewFile.id.desc())
        )
        return questions

    async def collect_answers(self, include_preset_answer=False) -> list[UserAnswer]:
        user_answers = await NewAnswer.get_answers_by_qid(self.id)
        standard_answers = [a for a in user_answers if a.standard]
        answers_data = []
        if standard_answers:
            for answer in standard_answers:
                user = await NewAdminUser.find_by_id(answer.uid)
                answers_data.append(
                    UserAnswer._make([answer.uid, user.name if user else "dummy", update_manual_tag(answer.data)])
                )
        else:
            for answer in user_answers:
                user = await NewAdminUser.find_by_id(answer.uid)
                answers_data.append(
                    UserAnswer._make([answer.uid, user.name if user else "dummy", update_manual_tag(answer.data)])
                )
            if include_preset_answer and self.preset_answer:
                answers_data.append(UserAnswer._make([ADMIN.id, ADMIN.name, self.preset_answer]))
        conflict_type = get_config("web.mode_conflict_treatment", ConflictTreatmentType.MERGED.value)
        if conflict_type == ConflictTreatmentType.MANUAL.value:
            # TODO: 先检查有无冲突，若答案冲突则不合并
            answers_data = answers_data[-1:]
        elif conflict_type == ConflictTreatmentType.LATEST.value:
            answers_data = answers_data[:1]
        return answers_data

    async def update_record(self, mold, exclusive_status=None, llm_status=None, **kwargs):
        if mold.mold_type not in [MoldType.LLM, MoldType.HYBRID]:
            await self.update_(ai_status=exclusive_status, **kwargs)
            return

        params = {
            "exclusive_status": self.exclusive_status,
            "llm_status": self.llm_status,
        }
        if exclusive_status is not None:
            params["exclusive_status"] = exclusive_status
        if llm_status is not None:
            params["llm_status"] = llm_status

        if mold.mold_type == MoldType.LLM:
            ai_status = params.get("llm_status")
        elif params.get("exclusive_status") in (
            AIStatus.DISABLE,
            AIStatus.SKIP_PREDICT,
            AIStatus.UNCORRELATED,
        ):
            ai_status = params.get("exclusive_status")
        elif params.get("exclusive_status") == AIStatus.TODO or params.get("llm_status") == LLMStatus.TODO:
            ai_status = AIStatus.TODO
        elif params.get("exclusive_status") == AIStatus.DOING or params.get("llm_status") == LLMStatus.DOING:
            ai_status = AIStatus.DOING
        elif params.get("exclusive_status") == AIStatus.FAILED or params.get("llm_status") == LLMStatus.FAILED:
            ai_status = AIStatus.FAILED
        else:
            ai_status = AIStatus.FINISH
        await self.update_(ai_status=ai_status, **params, **kwargs)


class NewQuestion(_Question):
    class Meta:
        table_name = "question"
        indexes = ((("name", "num", "fill_in_status"), False),)

    fid = IntegerField()
    mold = IntegerField()

    @staticmethod
    def answer_items(answer, key="userAnswer"):
        return answer.get(key, {}).get("items", [])

    async def fetch_metadata(self):
        extract_methods = await NewExtractMethod.find_by_kwargs(mold=self.mold)
        meta = {
            "confirmed_answer": self.confirmed_answer,
            "extract_methods": extract_methods,
        }
        return meta

    async def set_answer(self):
        """
        应该且只应该在 保存答案&预测答案 之后调用
        :return:
        """
        answers_data = await self.collect_answers(include_preset_answer=True)
        schema = await NewMold.find_by_id(self.mold)
        self.answer = AnswerUtil.merge_answers(answers_data, schema_data=schema.data, base_answer=self.answer)
        await self.update_(answer=self.answer)
        return self.answer

    @classmethod
    async def find_by_fid_mids(cls, fid: int, mold_ids: list[int]):
        return await pw_db.execute(cls.select().where(cls.fid == fid, cls.mold.in_(mold_ids)))

    async def get_user_merged_answer(self):
        """
        合并后的标注答案
        :return:
        """
        schema = await NewMold.find_by_id(self.mold)
        answers_data = await self.collect_answers(include_preset_answer=False)
        return AnswerUtil.merge_answers(answers_data, schema_data=schema.data)

    async def update_record(self, exclusive_status=None, llm_status=None, **kwargs):
        mold = await NewMold.find_by_id(self.mold)

        await super().update_record(mold, exclusive_status=exclusive_status, llm_status=llm_status, **kwargs)


class QuestionWithFK(_Question):
    class Meta:
        table_name = "question"
        indexes = ((("name", "num", "fill_in_status"), False),)

    file: NewFile | None = ForeignKeyField(NewFile, column_name="fid", backref="questions")
    mold: MoldWithFK | None = ForeignKeyField(MoldWithFK, column_name="mold", backref="questions")

    async def set_answer(self):
        """
        应该且只应该在 保存答案&预测答案 之后调用
        :return:
        """
        answers_data = await self.collect_answers(include_preset_answer=True)
        self.answer = AnswerUtil.merge_answers(answers_data, schema_data=self.mold.data, base_answer=self.answer)
        await self.update_(answer=self.answer)
        return self.answer

    async def update_record(self, exclusive_status=None, llm_status=None, **kwargs):
        mold = await NewMold.find_by_id(self.mold.id)

        await super().update_record(mold, exclusive_status=exclusive_status, llm_status=llm_status, **kwargs)
