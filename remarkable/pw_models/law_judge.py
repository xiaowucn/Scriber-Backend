from enum import IntEnum

from peewee import BooleanField, ForeignKeyField, SmallIntegerField, TextField, fn

from remarkable.common.constants import EnumMixin
from remarkable.db import pw_db
from remarkable.models.new_file import NewFile
from remarkable.models.new_user import NewAdminUser
from remarkable.pw_models.audit_rule import BaseAuditResult
from remarkable.pw_models.base import BaseUTCModel
from remarkable.pw_models.law import LawCheckPoint, LawOrder, LawRule


class JudgeStatusEnum(EnumMixin, IntEnum):
    TODO = 0
    DOING = 5
    SUCCESS = 10
    PARTIAL = -5  # 多个状态, 部分成功
    FAILED = -10
    MISSING = -20


class LawJudgeResult(BaseAuditResult, BaseUTCModel):
    file = ForeignKeyField(NewFile, index=True)
    law_order = ForeignKeyField(LawOrder)
    rule = ForeignKeyField(LawRule)
    cp = ForeignKeyField(LawCheckPoint)
    judge_status = SmallIntegerField(default=JudgeStatusEnum.TODO.value)

    class Meta:
        table_name = "law_judge_result"

    @property
    def unique_id(self):
        return f"law_{self.id}"

    @property
    def law_order_name(self):
        return self.law_order.name

    @property
    def is_template(self):
        return self.law_order.is_template

    @property
    def cp_name(self):
        return self.cp.cp_name

    @classmethod
    async def get_judge_results(cls, file_id: int, only_incompliance: bool = False):
        cond = [cls.file_id == int(file_id), cls.law_order_id.is_null(False)]

        if only_incompliance:
            cond.append(~cls.is_compliance)

        results = await pw_db.prefetch(
            cls.select().where(*cond).order_by(cls.order_key, cls.rule_id.desc()),
            LawOrder.select(LawOrder.id, LawOrder.name, LawOrder.is_template, include_deleted=True),
            (
                LawCheckPoint.select(
                    LawCheckPoint.id,
                    fn.COALESCE(LawCheckPoint.alias_name, LawCheckPoint.name).alias("cp_name"),
                    include_deleted=True,
                ),
                cls,
            ),
        )
        return results

    @classmethod
    async def reset_judge_results(cls, file_id: int):
        cond = cls.file_id == file_id
        await pw_db.execute(cls.delete().where(cond))

    @classmethod
    def _user_info(cls, user):
        return {"user_id": user.id}

    @classmethod
    async def bulk_insert_records(cls, records):
        await cls.records.rel_model.bulk_insert(records)

    @classmethod
    def display_status_by_counter(cls, counter):
        has_success = JudgeStatusEnum.SUCCESS.value in counter
        has_failed = JudgeStatusEnum.FAILED.value in counter

        if JudgeStatusEnum.DOING.value in counter:
            return JudgeStatusEnum.DOING
        if JudgeStatusEnum.TODO.value in counter:
            if has_success or has_failed:
                return JudgeStatusEnum.DOING
            return JudgeStatusEnum.TODO
        if has_success and has_failed:
            return JudgeStatusEnum.PARTIAL
        if has_success:
            return JudgeStatusEnum.SUCCESS
        if has_failed:
            return JudgeStatusEnum.FAILED
        if JudgeStatusEnum.MISSING.value in counter:
            return JudgeStatusEnum.MISSING
        return None


class LawJudgeResultRecord(BaseUTCModel):
    result = ForeignKeyField(LawJudgeResult, index=True, backref="records")
    user = ForeignKeyField(NewAdminUser)
    is_compliance_from = BooleanField(null=True)
    is_compliance_to = BooleanField(null=True)
    suggestion = TextField(null=True)
    user_reason = TextField(null=True)

    class Meta:
        table_name = "law_judge_result_record"

    @property
    def user_name(self):
        if isinstance(self.user, NewAdminUser):
            return self.user.name
        return ""

    @classmethod
    async def get_last_modified_users(cls, result_ids: list[int]):
        if not result_ids:
            return {}
        cte = (
            cls.select(
                cls.result_id,
                NewAdminUser.name.alias("user_name"),
                fn.ROW_NUMBER().over(partition_by=[cls.result_id], order_by=[cls.id.desc()]).alias("rnk"),
            )
            .where(cls.result_id.in_(result_ids))
            .join(NewAdminUser)
            .cte("subq")
        )
        query = cte.select_from(cte.c.result_id, cte.c.user_name).where(cte.c.rnk == 1).with_cte(cte).tuples()
        ret = dict(await pw_db.execute(query))
        return ret
