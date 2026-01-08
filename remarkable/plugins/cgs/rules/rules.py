import copy
import re
from itertools import chain

from remarkable.common.constants import RuleType
from remarkable.common.util import clean_txt
from remarkable.plugins.cgs.common.utils import is_empty
from remarkable.plugins.cgs.rules.calculator import ExprCalculator, Token
from remarkable.plugins.cgs.schemas.suggestion import SuggestionManager


class BaseRule:
    def __init__(self, obj):
        self.obj = obj

    @property
    def detail(self):
        return self.obj.detail or {}

    @property
    def message(self):
        raise NotImplementedError

    def is_valid(self):
        raise NotImplementedError

    def validate(self, mapping):
        raise NotImplementedError

    @property
    def content(self):
        raise NotImplementedError

    @property
    def schema_fields(self):
        raise NotImplementedError

    @property
    def reason(self):
        raise NotImplementedError

    @classmethod
    def get_expr_empty_message(cls, expr, mapping):
        reason = None
        message = None
        emtpy_fields = [
            item["name"]
            for item in expr
            if isinstance(item, dict) and "name" in item and not mapping.get(item["name"]).value
        ]
        if emtpy_fields:
            fields = "、".join(set(emtpy_fields))
            reason = f"{fields}为空"
            message = SuggestionManager.get_suggestion_by_fields(emtpy_fields)
        return reason, message


class RegexRule(BaseRule):
    """
    {
        "regex": "公司",
        "field": {"name": "公司注册资本", "schema_path": "测试｜公司注册资本", "schema_id": 1234},
        "message": "公司注册资本 < 1万元 ",
    }
    """

    @property
    def field(self):
        return self.detail.get("field") or {}

    @property
    def message(self):
        return self.detail.get("message") or f"不满足规则:{self.content}"

    @property
    def reason(self):
        return self.detail.get("reason") or f"不满足规则:{self.content}"

    def is_valid(self):
        try:
            re.compile(self.content)
        except (TypeError, re.error):
            return False
        return True

    def validate(self, mapping):
        res = {"result": False, "detail": "正则未匹配成功", "message": self.message, "reason": self.reason}

        schema_item = mapping.get(self.field.get("name"))
        if not schema_item.value:
            res["reason"] = f'{self.field.get("name")}为空'
            res["message"] = SuggestionManager.get_suggestion_by_fields(self.field.get("name"))
            return res

        matched = re.compile(self.content).search(schema_item.value)
        if matched:
            res.update({"result": True, "detail": f"匹配到字符串: {matched.group(0)}", "message": None, "reason": None})
        return res

    @property
    def content(self):
        return self.detail.get("regex")

    @property
    def schema_fields(self):
        name = self.field.get("name")
        if not name:
            return []
        return [name]


class ExprRule(BaseRule):
    """
    {
        "expr": [{"name": "公司注册资本"}, ">=", "1万元"],
        "unique": false
        "message": "公司注册资本 < 1万元 ",
    }
    """

    @property
    def message(self):
        return self.detail.get("message")

    @property
    def reason(self):
        return self.detail.get("reason")

    @classmethod
    def operators(cls):
        return list(Token.OPS.keys())

    def is_valid(self):
        expr = self.detail.get("expr") or []
        return ExprCalculator(copy.deepcopy(expr)).run(only_validate=True)

    def validate(self, mapping):
        res = {"result": False, "message": self.message, "reason": self.reason}

        expr = self.detail.get("expr") or []
        expr = copy.deepcopy(expr)

        reason, message = self.get_expr_empty_message(expr, mapping)
        if reason:
            res.update({"reason": reason, "message": message})
            return res
        for item in expr:
            if isinstance(item, dict):
                if "name" in item:
                    schema_item = mapping.get(item["name"])
                    item["value"] = clean_txt(schema_item.value)

        result = ExprCalculator(expr, {"unique": self.detail.get("unique")}).run()
        if result.value:
            return {"result": True, "message": None, "reason": None}
        message, reason = ExprCalculator.render_message_by_result(result)
        res["message"] = self.message or message
        res["reason"] = self.reason or reason
        return res

    def get_text_expr(self):
        return ExprCalculator(self.detail.get("expr")).expr_text

    @property
    def content(self):
        return self.get_text_expr()

    @property
    def schema_fields(self):
        res = []
        expr = self.detail.get("expr") or []
        for item in expr:
            if isinstance(item, dict):
                if "name" in item:
                    res.append(item["name"])
        return list(set(res))


class EmptyRule(BaseRule):
    """
    {
        "field": {"name": "公司名称", "schema_path": "测试｜公司名称", "schema_id": 1234}
        "message": "公司名称不能为空",
    }
    """

    @property
    def message(self):
        schema_name = self.field.get("name")
        return self.detail.get("message") or SuggestionManager.get_suggestion_by_fields(schema_name)

    @property
    def reason(self):
        schema_name = self.field.get("name")
        return self.detail.get("reason") or f"{schema_name} 不能为空"

    @property
    def field(self):
        return self.detail.get("field") or {}

    def is_valid(self):
        return self.field and self.field.get("name")

    def validate(self, mapping):
        value = mapping.get(self.field["name"]).value
        flag = not is_empty(value)
        return {
            "result": flag,
            "message": self.message if not flag else None,
            "reason": self.reason if not flag else None,
        }

    @property
    def content(self):
        schema_name = self.field.get("name")
        return f"{schema_name} 是否为空"

    @property
    def schema_fields(self):
        name = self.field.get("name")
        if not name:
            return []
        return [name]


class ConditionRule(BaseRule):
    """
    {
        "conditions": [
            {
                "expr_if": {
                    "expr": [{"name": "公司注册资本"}, ">=", "1万元"],
                    "unique": false
                },
                "expr_then": {
                    "expr": [{"name": "公司注册余额"}, ">=", "0.5万元"],
                    "unique": false
                },
                "message": "xxxx",
                "reason": "xxx"
            }
        ],
    }
    """

    @property
    def message(self):
        return self.detail.get("message") or f"不满足: {self.content}"

    @property
    def reason(self):
        return self.detail.get("reason") or f"不满足: {self.content}"

    @property
    def default_reason(self):
        res = []
        for condition in self.detail.get("conditions") or []:
            res.append(ExprCalculator(condition["expr_if"]["expr"]).reversed_expr_text)
        return ";".join(res)

    @classmethod
    def operators(cls):
        return list(Token.OPS.keys()) + [Token.OP_NULL]

    def is_valid(self):
        conditions = self.detail.get("conditions") or []
        if not conditions:
            return False
        for condition in conditions:
            ExprCalculator(condition["expr_if"]["expr"]).run(only_validate=True)
            ExprCalculator(condition["expr_then"]["expr"]).run(only_validate=True)
        return True

    @classmethod
    def validate_expr(cls, expr, mapping, options):
        for item in expr:
            if isinstance(item, dict):
                if "name" in item:
                    schema_item = mapping.get(item["name"])
                    item["value"] = clean_txt(schema_item.value) if schema_item.value else schema_item.value
        return ExprCalculator(expr, options).run()

    @classmethod
    def has_null_op(cls, expr):
        for item in expr:
            if not isinstance(item, dict) and item == Token.OP_NULL:
                return True
        return False

    def validate(self, mapping):
        res = {"result": None, "message": None, "reason": "不符合任一条件"}

        for condition in self.detail.get("conditions") or []:
            expr_if = copy.deepcopy(condition["expr_if"]["expr"])
            expr_then = copy.deepcopy(condition["expr_then"]["expr"])
            expr_if_result = self.validate_expr(expr_if, mapping, {"unique": condition["expr_if"].get("unique")})
            if expr_if_result.value:
                if not self.has_null_op(expr_then):
                    reason, message = self.get_expr_empty_message(expr_then, mapping)
                    if reason:
                        res.update({"reason": reason, "message": message, "matched": False})
                        return res

                expr_then_result = self.validate_expr(
                    expr_then, mapping, {"unique": condition["expr_then"].get("unique")}
                )
                if expr_then_result.value:
                    return {
                        "result": True,
                        "message": None,
                        "reason": None,
                        "expr_if": expr_if,
                        "expr_then": expr_then,
                    }

                reversed_expr_text = ExprCalculator(expr_if).expr_text
                message, reason = ExprCalculator.render_message_by_result(expr_then_result, reversed_expr_text)
                res.update(
                    {
                        "result": False,
                        "expr_if": expr_if,
                        "expr_then": expr_then,
                        "message": condition.get("message") or message,
                        "reason": condition.get("reason") or reason,
                    }
                )
                return res
        return res

    @classmethod
    def get_text_expr(cls, expr):
        return ExprCalculator(expr).expr_text

    @classmethod
    def get_text_then(cls, condition):
        return cls.get_text_expr(condition["expr_then"]["expr"])

    @classmethod
    def get_text_if(cls, condition):
        return cls.get_text_expr(condition["expr_if"]["expr"])

    @property
    def content(self):
        res = []
        for index, condition in enumerate(self.detail.get("conditions") or [], start=1):
            text_if = self.get_text_if(condition)
            text_then = self.get_text_then(condition)
            res.append(f"条件{index}: {text_if}, 则 {text_then}")
        return "\n".join(res)

    @property
    def schema_fields(self):
        res = []
        for condition in self.detail.get("conditions") or []:
            for item in chain(condition["expr_if"]["expr"], condition["expr_then"]["expr"]):
                if "name" in item:
                    res.append(item["name"])
        return list(set(res))


class UnknownRule(BaseRule):
    @property
    def message(self):
        return ""

    def is_valid(self):
        return False

    def validate(self, mapping):
        return None

    @property
    def content(self):
        return "未知规则"

    @property
    def schema_fields(self):
        return []

    @property
    def reason(self):
        return ""


RULE_MAPPING = {
    RuleType.REGEX.value: RegexRule,
    RuleType.EXPR.value: ExprRule,
    RuleType.EMPTY.value: EmptyRule,
    RuleType.CONDITION.value: ConditionRule,
}


def get_rule(rule_type):
    return RULE_MAPPING.get(rule_type) or UnknownRule
