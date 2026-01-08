import logging
from enum import Enum

from marshmallow import Schema
from marshmallow.validate import OneOf
from webargs import fields

from remarkable.common.constants import RuleReviewStatus, RuleType
from remarkable.common.exceptions import FormException
from remarkable.models.query_helper import AsyncPagination, PaginationSchema


class AuditStatusType(Enum):
    TODO = 0  # 默认状态:数据库中无记录时的初始状态,系统新增插入新状态,读取最新记录
    PROCESS = 1
    FAILED = 2
    DONE = 3

    REMOTE_REQUEST_FAILED = 20
    WAITING_CALLBACK = 21
    CALLBACK_PROCESSING = 22
    CALLBACK_PROCESSING_FAILED = 23
    CALLBACK_PROCESSING_DONE = 24


pagination_schema = {
    "field": fields.String(required=False, load_default=None),
    "keyword": fields.String(required=False, load_default=None),
    **AsyncPagination.web_args,
}


class RulesSchema(PaginationSchema):
    mold_id = fields.Int(load_default=None)
    name = fields.Str(load_default="")
    rule_type = fields.Str(load_default=None, validate=OneOf(RuleType.member_values()))
    review_status = fields.Int(load_default=0, validate=OneOf(RuleReviewStatus.member_values()))


class RuleStatusSchema(Schema):
    review_status = fields.Int(required=True)


class RuleSchema(Schema):
    schema_id = fields.Int(required=True)
    name = fields.String(required=True)
    validate_company_info = fields.Boolean(required=True)
    validate_bond_info = fields.Boolean(required=True)
    tip_content = fields.String(required=False, load_default=None)
    is_compliance_tip = fields.Boolean(required=True)
    is_noncompliance_tip = fields.Boolean(required=True)
    origin_content = fields.String(required=False, load_default=None)
    rule_type = fields.String(required=True)
    detail = fields.Dict(required=True)


def validate_rules(rules):
    from remarkable.pw_models.audit_rule import NewAuditRule

    errors = {}
    for index, rule_item in enumerate(rules):
        data = RuleSchema().validate(rule_item)
        if data:
            errors[index] = {"validate_error": True, "data": data, "message": "提交参数错误"}
            continue

        try:
            rule = NewAuditRule(**rule_item)
            flag = rule.is_valid
            if not flag:
                errors[index] = {"message": "不合法的规则"}
        except Exception as e:
            message = str(e)
            logging.exception(e)
            if hasattr(e, "message"):
                message = e.message

            errors[index] = {"message": message}
    if errors:
        raise FormException(errors=errors, content="存在不合法的规则，请检查修改后重试")


rules_schema = {"rules": fields.List(fields.Dict(), validate=validate_rules)}

mapping_schema = {"mapping": fields.Dict()}
