import logging
from typing import TYPE_CHECKING, Self

import attr
from peewee import SQL, BooleanField, CharField, IntegerField, TextField, fn
from speedy.peewee_plus.orm import or_

from remarkable.common.constants import RuleID, RuleReviewStatus, RuleType
from remarkable.common.enums import AuditAnswerType
from remarkable.common.exceptions import CGSException, CustomError
from remarkable.common.util import generate_timestamp
from remarkable.db import pw_db
from remarkable.plugins.cgs.rules.rules import get_rule
from remarkable.pw_models.base import BaseModel
from remarkable.pw_models.model import NewAuditResultRecord
from remarkable.pw_orm import field

if TYPE_CHECKING:
    from remarkable.plugins.cgs.schemas.reasons import ResultItem


class NewAuditRule(BaseModel):
    created_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], index=True, null=True)
    deleted_utc = IntegerField(constraints=[SQL("DEFAULT 0")], null=True)
    detail = field.JSONField(null=True)
    handle_uid = IntegerField(null=True)
    handle_user = CharField(null=True)
    is_compliance_tip = BooleanField(null=True)
    is_noncompliance_tip = BooleanField(null=True)
    name = CharField(index=True)
    not_pass_reason = CharField(null=True)
    origin_content = TextField(null=True)
    review_status = IntegerField(null=True, default=RuleReviewStatus.NOT_REVIEWED)
    review_uids = field.ArrayField(field_class=IntegerField, null=True)
    review_users = field.ArrayField(field_class=CharField, null=True)
    rule_type = CharField(index=True, null=True)
    schema_id = IntegerField(null=True)
    tip_content = TextField(null=True)
    uid = IntegerField(null=True)
    updated_utc = IntegerField(constraints=[SQL("DEFAULT (EXTRACT(epoch FROM now()))::integer")], null=True)
    user = CharField(null=True)
    validate_bond_info = BooleanField(null=False)
    validate_company_info = BooleanField(null=False)
    public = BooleanField(null=True)

    fields = field.ArrayField(field_class=TextField, null=False)  # 关联字段

    field_ids = field.ArrayField(field_class=IntegerField, null=False)  # 关联字段ID

    class Meta:
        table_name = "cgs_rule"

    _rule = None

    @classmethod
    async def get_by_id_and_user(cls, pk_id: int, is_admin: bool, user_id: int) -> Self | None:
        cond = NewAuditRule.id == pk_id
        if not is_admin:
            cond &= NewAuditRule.public | (NewAuditRule.uid == user_id)
        rule = await pw_db.first(NewAuditRule.select().where(cond))

        return rule

    @property
    def label(self):
        return f"custom_{self.id}"

    @property
    def schema_fields(self):
        return self.rule.schema_fields

    def reset_type(self):
        self._rule = None

    @property
    def rule(self):
        if not self._rule:
            self._rule = get_rule(self.rule_type)(self)
        return self._rule

    @property
    def rule_content(self):
        return self.rule.content

    @property
    def is_valid(self):
        return self.rule.is_valid()

    def validate(self, mapping):
        result = {"result": False, "message": self.rule.message, "reason": "规则处理失败"}
        try:
            result = self.rule.validate(mapping)
        except CGSException as e:
            logging.exception(e)
        return result

    def to_dict(self, **kwargs):
        result = super().to_dict(**kwargs)
        result["rule_content"] = self.rule_content
        return result

    @classmethod
    async def list_reviewing_rules(cls, mold_id: int, only_review_passed: bool = False):
        cond = cls.schema_id == mold_id
        if only_review_passed:
            cond &= cls.review_status == RuleReviewStatus.PASS
        return await pw_db.execute(cls.select().where(cond))

    async def update_rule(self, **kwargs):
        for key, val in kwargs.items():
            if val is None:
                continue
            setattr(self, key, val)
        self.reset_type()

        if not self.is_valid:
            raise CustomError("不合法的规则，请检查后再试")
        await pw_db.update(self)


class BaseAuditResult(BaseModel):
    name = CharField(index=True)  # 界面中原文位置在: reasons + schema_results
    is_compliance = BooleanField(null=True)  # 是否合规(最终) None值表示`不适用`
    is_compliance_ai = BooleanField(null=True)  # ai设置的 (和最终结果相反时表示`人工确认`)
    is_compliance_user = BooleanField(null=True)  # 用户设置的
    is_edited = BooleanField(default=False, null=True)
    is_compliance_tip = BooleanField(null=True)  # 人工确认后tip图标(合规时), 内容为`tip_content`
    is_noncompliance_tip = BooleanField(null=True)  # 人工确认后tip图标(不合规时), 内容为`tip_content`
    tip_content = TextField(null=True)  # compliance_tip的content
    order_key = CharField(null=True)  # get_first_position
    # 一致性检查可能有多个原文和法规  name后tip的提示内容
    origin_contents = field.ArrayField(field_class=CharField, null=True)
    contract_content = TextField(null=True)  # 合同指引内容
    reasons = field.JSONField(null=True)  # 一致性检查 会有多个范文，法规，导致有多个原因
    related_name = TextField(null=True)
    rule_type = CharField(null=True)  # 一致性检查：rule_type === RuleType.TEMPLATE
    # [{"name": "xxx", "boxes": [{"text": "xxx", "page": xx, "outlines": [xxx], "xpath": "xxx"}]}]
    schema_results = field.JSONField(null=True)
    suggestion = TextField(null=True)  # 建议(最终)
    suggestion_ai = TextField(null=True)  # ai设置的
    suggestion_user = TextField(null=True)  # 用户设置的
    user_reason = TextField(null=True)

    @property
    def comment(self):
        return f"修改意见: {self.suggestion}"

    @classmethod
    def sorted_schema_results(cls, schema_results):
        if schema_results:
            if any("cells" in item or not item.get("outlines") for item in schema_results):
                return
            for item in sorted(
                (item for item in schema_results if item.get("matched")),
                key=lambda x: (x["page"], x["outlines"][str(x["page"])][0][1], x["outlines"][str(x["page"])][0][0]),
            ):
                yield item

    @classmethod
    def gen_outline_items(cls, schema_results=None, reasons=None):
        if not schema_results:
            for item in reasons or []:
                if "outlines" in item:
                    yield item
        else:
            yield from cls.sorted_schema_results(schema_results)

    @classmethod
    def get_first_position(cls, schema_results, reasons):
        min_position = None
        for item in cls.gen_outline_items(schema_results, reasons):
            if not item["outlines"] or item["page"] is None:
                continue

            outline = item["outlines"][str(item["page"])]
            position = (item["page"], outline[0][1], outline[0][0])
            if not min_position or position < min_position:
                min_position = position

        if not min_position:
            return None

        return "".join([str(int(item)).zfill(4) for item in min_position])

    @classmethod
    def _user_info(cls, user) -> dict:
        raise NotImplementedError

    @classmethod
    async def bulk_insert_records(cls, records):
        raise NotImplementedError

    @classmethod
    async def batch_update_user_result(cls, results, user):
        async with pw_db.atomic():
            records = []
            for result in results:
                result["is_edited"] = True

                compliance_from = result["is_compliance"]
                compliance_to = result["is_compliance"]

                if "is_compliance_user" in result:
                    result["is_compliance"] = result["is_compliance_user"]
                    compliance_to = result["is_compliance"]
                if "suggestion_user" in result:
                    result["suggestion"] = result["suggestion_user"]

                result_id = result.pop("result_id")
                user_reason = result.get("user_reason")
                suggestion_user = result.get("suggestion_user")
                record = {
                    "result_id": result_id,
                    **cls._user_info(user),
                    "is_compliance_from": compliance_from,
                    "is_compliance_to": compliance_to,
                    "user_reason": "内容被删除" if user_reason == "" else user_reason,
                    # CgsResultRecord.suggestion 即用户的建议
                    "suggestion": "内容被删除" if suggestion_user == "" else suggestion_user,
                }

                records.append(record)
                await cls.update_by_pk(result_id, **result)

            await cls.bulk_insert_records(records)


class NewAuditResult(BaseAuditResult):
    created_utc = IntegerField(index=True, null=True, default=generate_timestamp)
    deleted_utc = IntegerField(null=True, default=0)
    fid = IntegerField(index=True, null=True)
    is_builtin = BooleanField(default=True, null=True)
    label = CharField(null=True)
    # 一致性检查可能有多个原文和法规  name后tip的提示内容
    qid = IntegerField(index=True, null=True)
    rule_id = IntegerField(null=True)
    schema_id = IntegerField(null=True)
    updated_utc = IntegerField(default=generate_timestamp, null=True)
    answer_type = IntegerField(default=AuditAnswerType.final_answer)

    class Meta:
        table_name = "cgs_result"

    @property
    def unique_id(self):
        return f"cgs_{self.id}"

    @classmethod
    async def get_results(
        cls, fid: int, schema_ids: list[int], is_admin: bool, user_id: int, only_incompliance: bool = False
    ):
        cond = [cls.fid == int(fid), cls.schema_id.in_(schema_ids), cls.answer_type == AuditAnswerType.final_answer]

        user_cond = [] if is_admin else [or_(NewAuditRule.uid == user_id, NewAuditRule.public)]
        cond.append(
            or_(
                fn.EXISTS(
                    NewAuditRule.select().where(
                        cls.rule_id == NewAuditRule.id,
                        *user_cond,
                    )
                ),
                # 外部决策回调的审核结果rule_id为-1, 研发规则的审核结果rule_id为null
                cls.rule_id == RuleID.EXTERNAL_ID,
                cls.rule_id.is_null(),
            )
        )

        if only_incompliance:
            cond.append(~cls.is_compliance)

        results = await pw_db.execute(cls.select().where(*cond).order_by(cls.order_key, cls.rule_id.desc()))
        return results

    def to_result_item(self):
        return {
            "title": self.title,
            "name": self.name,
            "tip_content": self.tip_content,
            "is_compliance": self.is_compliance,
            "is_compliance_ai": self.is_compliance_ai,
            "is_compliance_user": self.is_compliance_user,
            "reasons": [self.user_reason]
            if self.user_reason
            else [item["reason_text"] for item in self.reasons if not item["matched"]],
            "suggestion": self.suggestion,
            "origin_contents": self.origin_contents,
            "contract_content": self.contract_content,
            "id": self.id,
        }

    @property
    def title(self):
        schema_results = list(self.sorted_schema_results(self.schema_results))
        if schema_results and schema_results[0]["chapters"]:
            return schema_results[0]["chapters"][-1]["title"]
        return ""

    @classmethod
    async def get_results_by_fid(cls, fid, schema_id):
        query = (
            cls.select()
            .where(
                cls.fid == int(fid), cls.schema_id == int(schema_id), cls.answer_type == AuditAnswerType.final_answer
            )
            .order_by(cls.order_key)
        )
        return pw_db.execute(query)

    @classmethod
    def _user_info(cls, user):
        return {"user_id": user.id, "user_name": user.name}

    @classmethod
    async def bulk_insert_records(cls, records):
        await NewAuditResultRecord.bulk_insert(records)

    def to_row(self):
        result = super().to_dict()
        if "id" in result:
            result.pop("id")
        return result

    @property
    def schema_fields(self):
        res = []
        for item in self.schema_results or []:
            if item.get("name"):
                res.append(item["name"])
        return res

    @classmethod
    async def reset_results(cls, fid: int, schema_id: int, is_preset_answer: bool = False):
        cond = (cls.fid == fid) & (cls.schema_id == schema_id)
        if is_preset_answer:
            cond &= cls.answer_type == AuditAnswerType.preset_answer
        else:
            cond &= cls.answer_type == AuditAnswerType.final_answer
        await pw_db.execute(cls.delete().where(cond))

    @classmethod
    async def update_results(cls, labels: dict[str, int], items: list[Self]):
        record_by_id: dict[int, dict] = {}
        for item in items:
            record_by_id[labels[item.label]] = item.to_dict(exclude=[cls.id])
        audit_results = await pw_db.execute(cls.select().where(cls.id.in_(list(record_by_id.keys()))))
        for audit_result in audit_results:
            update_params = record_by_id[audit_result.id]
            await audit_result.update_(**update_params)

    @classmethod
    def from_inspect_result(
        cls,
        question_id: int,
        result_item: "ResultItem",
        is_template_rule: bool = True,
    ):
        reasons = attr.asdict(result_item)["reasons"]
        show_tip = bool(result_item.tip)
        default_rule_type = RuleType.TEMPLATE.value if is_template_rule else RuleType.SCHEMA.value
        return cls(
            name=result_item.name,
            related_name=result_item.related_name,
            is_compliance_ai=result_item.is_compliance_real,
            is_compliance=result_item.is_compliance_real,
            rule_id=None,
            is_builtin=True,
            qid=question_id,
            origin_contents=result_item.origin_contents,
            suggestion=result_item.suggestion,
            suggestion_ai=result_item.suggestion,
            rule_type=result_item.rule_type or default_rule_type,
            reasons=reasons,
            tip_content=result_item.tip if is_template_rule else None,
            fid=result_item.fid,
            is_compliance_tip=show_tip if is_template_rule else False,
            is_noncompliance_tip=show_tip if is_template_rule else False,
            schema_id=result_item.schema_id,
            schema_results=result_item.schema_results,
            order_key=cls.get_first_position(None, reasons),
            label=result_item.label,
            contract_content=result_item.contract_content,
        )
