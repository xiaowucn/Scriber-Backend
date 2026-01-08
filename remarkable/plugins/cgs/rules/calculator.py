"""
计算自定义表达式，
输入 自定义表达式，如
    [{'value': "12", 'name': '冷静期'}, '>', {'value': "24"},
    "或", {"value": "12.3333", "name": "公司余额"}, '<', {'value': '13.3'}]
输出 True, False
"""

import logging
import math
import re

from remarkable.common.exceptions import CGSException
from remarkable.plugins.cgs.common.utils import append_suggestion, is_empty


class ExpressionError(CGSException):
    MESSAGE = "合规公式缺少表达式，请检查后重试"

    def __init__(self, tokens, token):
        self.token = token
        self.tokens = tokens

    @property
    def message(self):
        return (
            self.detail + f"表达式 {self.content} 在位置{self.token.index + 1}， "
            f"{self.token.type_name} {self.token.name} 处发现错误。"
            f"请检查后重试。"
        )

    def to_dict(self):
        return {"content": self.content, "index": self.token.index, "name": self.token.name}

    @property
    def content(self):
        return self.expression_text(self.tokens)

    @property
    def detail(self):
        return ""

    @classmethod
    def expression_text(cls, tokens):
        return " ".join([token.name for token in tokens])

    def __str__(self):
        return self.message


class UnknownOperatorError(ExpressionError):
    @property
    def detail(self):
        return f"未知的{self.token.type_name}。"


class MissLeftValueError(ExpressionError):
    @property
    def detail(self):
        return f"{self.token.type_name} {self.token.name} 处缺少左值。"

    @property
    def message(self):
        return self.MESSAGE


class MissRightValueError(ExpressionError):
    @property
    def detail(self):
        return f"{self.token.type_name} {self.token.name} 处缺少右值。"

    @property
    def message(self):
        return self.MESSAGE


class MissOperatorError(ExpressionError):
    @property
    def detail(self):
        return f"{self.token.type_name} {self.token.name} 缺少操作符。"

    @property
    def message(self):
        return self.MESSAGE


class InvalidValueError(ExpressionError):
    @property
    def detail(self):
        return "运算类操作符只能处理数值或者schema字段"

    @property
    def message(self):
        return "表达式校验不通过，请确认后再次提交"


class ExprCalcError(ExpressionError):
    @property
    def detail(self):
        values = ""
        if isinstance(self.token, ValueToken):
            values = self.token.value
            if not values:
                values = "为空"
        return f"{self.token.type_name} {self.token.name} 处的值{values}无法计算。"


class Operator:
    ABS_TOL = 0.01

    @classmethod
    def add(cls, value1, value2):
        return (value1.number or 0) + (value2.number or 0)

    @classmethod
    def sub(cls, value1, value2):
        return (value1.number or 0) - (value2.number or 0)

    @classmethod
    def div(cls, value1, value2):
        return (value1.number or 0) / (value2.number or 0)

    @classmethod
    def mul(cls, value1, value2):
        return (value1.number or 0) * (value2.number or 0)

    @classmethod
    def contain(cls, value1, value2):
        return value1.value and value2.value and value2.value in value1.value

    @classmethod
    def not_contain(cls, value1, value2):
        return not value1.value or not value2.value or value2.value not in value1.value

    @classmethod
    def gt(cls, value1, value2):
        number1 = value1.number
        number2 = value2.number
        if number1 is None or number2 is None:
            return False

        return number1 > number2

    @classmethod
    def lt(cls, value1, value2):
        number1 = value1.number
        number2 = value2.number
        if number1 is None or number2 is None:
            return False

        return number1 < number2

    @classmethod
    def gte(cls, value1, value2):
        return cls.gt(value1, value2) or cls.eq(value1, value2)

    @classmethod
    def lte(cls, value1, value2):
        return cls.lt(value1, value2) or cls.eq(value1, value2)

    @classmethod
    def eq(cls, value1, value2):
        if value1.value == value2.value:
            return True

        if value1.value == "NULL":
            return is_empty(value2.value)
        if value2.value == "NULL":
            return is_empty(value1.value)

        number1 = value1.number
        number2 = value2.number
        if number1 is None or number2 is None:
            return False

        return math.isclose(number1, number2, abs_tol=cls.ABS_TOL)

    @classmethod
    def not_eq(cls, value1, value2):
        return not cls.eq(value1, value2)

    @classmethod
    def or_(cls, value1, value2):
        return value1.value or value2.value

    @classmethod
    def and_(cls, value1, value2):
        return value1.value and value2.value


class Token:
    OPS = {
        # 名字: {逆运算, 优先级, 操作符号}
        "+": (None, 100, Operator.add),
        "-": (None, 100, Operator.sub),
        "×": (None, 100, Operator.mul),
        "÷": (None, 100, Operator.div),
        ">": ("≤", 90, Operator.gt),
        "<": ("≥", 90, Operator.lt),
        "≥": ("<", 90, Operator.gte),
        "≤": (">", 90, Operator.lte),
        "=": ("≠", 90, Operator.eq),
        "==": ("≠", 90, Operator.eq),
        "≠": ("==", 90, Operator.not_eq),
        "包含": ("不包含", 90, Operator.contain),
        "不包含": ("包含", 90, Operator.not_contain),
        "或": ("且", 70, Operator.or_),
        "且": ("或", 70, Operator.and_),
    }

    SAME_OPS_MAPPING = {
        "!=": "≠",
        "不等于": "≠",
        "/": "÷",
        "x": "×",
        "*": "×",
        ">=": "≥",
        "<=": "≤",
        "||": "或",
        "&&": "且",
    }

    BOOL_OPS = {">", "<", "≥", "≤", "=", "==", "≠", "包含", "不包含"}
    NUMBER_OPS = {"+", "-", "×", "÷", ">", "<", "≥", "≤", "="}

    OP_NULL = "NULL"

    def __init__(self, token, index):
        self.token = token
        if isinstance(token, str) and token in self.SAME_OPS_MAPPING:
            self.token = self.SAME_OPS_MAPPING[token]
        self.index = index

    @classmethod
    def is_operator(cls, token):
        return isinstance(token, str) and token != cls.OP_NULL and token in cls.OPS

    @classmethod
    def is_value(cls, token):
        return isinstance(token, dict)

    @classmethod
    def create(cls, token, index):
        if cls.is_value(token):
            return ValueToken(token, index)
        if cls.is_operator(token):
            return OperatorToken(token, index)
        return UnknownToken(token, index)

    @property
    def name(self):
        return self.token

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.name

    @property
    def type_name(self):
        return "值"

    @property
    def reversed_name(self):
        return self.token.get("reversed_name") or self.name

    @property
    def suggestion(self):
        return self.token.get("suggestion")


class ValueToken(Token):
    P_VALUE_RATE = re.compile(r"([+-]?[0-9.]+)%")
    P_CN_RATE = re.compile(r"百分之(.*)$")
    P_UNIT = re.compile(
        r"(?P<number>[-+]?[0-9一二三四五六七八九十百千万亿零〇.,]+)\s*(?P<unit>年|月|天|日|周|个|人|个?小时|分钟?|秒|时|h|H|(人民币)?元(/股)?|.*?)?$"
    )
    P_NUMBER_UNIT = re.compile(r"(?P<number>[-+]?[0-9.,]+)\s*(?P<unit>[十百千万亿]+)?")
    P_IS_NUMBER = re.compile(r"^[+-]?[0-9.]+$")
    UNIT_RATE = {
        "年": 12,
        "月": 1.0,
        "日": 1 / 30,
        "天": 1 / 30,
        "周": 1 / 4,
        "分": 1 / 60,
        "分钟": 1 / 60,
        "秒": 1 / 3600,
        "万": 10000,
        "亿": 100000000,
        "百": 100,
        "千": 1000,
        "十": 10,
        "萬": 10000,
        "億": 100000000,
        "仟": 1000,
        "佰": 100,
        "拾": 10,
    }

    @property
    def real_name(self):
        return self.token.get("name")

    @property
    def type_name(self):
        if self.token.get("name"):
            return "schema字段"
        return "输入值"

    @property
    def name(self):
        if self.token == self.OP_NULL:
            return "NULL"

        name = self.token.get("name")
        if name:
            return name
        return str(self.token.get("value"))

    @property
    def is_rate(self):
        return self.value and ("%" in self.value or "百分之" in self.value)

    @classmethod
    def convert_number(cls, value):
        if isinstance(value, (int, float)):
            return value
        if "." not in value:
            return int(value)
        return float(value)

    @classmethod
    def convert_cn(cls, value):
        from remarkable.converter.utils import cn2digit

        return cn2digit(value)

    @classmethod
    def convert_rate(cls, value):
        matched = cls.P_VALUE_RATE.search(value)
        if matched:
            return float(matched.group(1)) / 100.0

        matched = cls.P_CN_RATE.search(value)
        if matched:
            return float(cls.convert_cn(matched.group(1))) / 100.0
        raise ValueError

    @classmethod
    def convert_unit(cls, value):
        matched = cls.P_UNIT.search(value)
        if not matched:
            raise ValueError

        if not matched.group("number"):
            raise ValueError

        number = matched.group("number").replace(",", "")

        #   拆分数值 和 百万亿
        number_matched = cls.P_NUMBER_UNIT.search(number)
        if number_matched:
            number = number_matched.group("number")
            number = cls.convert_number(number)
            unit = number_matched.group("unit")
            if unit:
                for item in unit:
                    if item not in cls.UNIT_RATE:
                        continue
                    number *= cls.UNIT_RATE[item]
        else:
            number = cls.convert_cn(number)
            number = cls.convert_number(number)
        unit_rate = cls.UNIT_RATE.get(matched.group("unit"))
        if unit_rate:
            number *= unit_rate
        return number

    @property
    def is_schema_field(self):
        return bool(self.real_name)

    @property
    def is_number(self):
        if not self.value:
            return False
        value = str(self.value)
        return bool(self.P_IS_NUMBER.search(value))

    @property
    def number(self):
        converted_value = None
        if not self.value:
            return None

        value = self.value
        if isinstance(self.value, str):
            value = self.value.replace(",", "")
        for func in [self.convert_number, self.convert_rate, self.convert_unit]:
            try:
                converted_value = func(value)
            except (ValueError, TypeError):
                pass
            else:
                break

        return converted_value

    @property
    def value(self):
        return self.token.get("value")

    @property
    def left(self):
        return self.token.get("left")

    @property
    def right(self):
        return self.token.get("right")

    @property
    def parent_operator(self):
        return self.token.get("operator")


class OperatorToken(Token):
    CONVERT_ALIAS = {"包含": "补充", "不包含": "删除"}

    @property
    def level(self):
        return self.OPS[self.token][1]

    def operate(self, value1, value2):
        return self.OPS[self.token][2](value1, value2)

    @property
    def type_name(self):
        return "操作符"

    @classmethod
    def convert_alias(cls, name):
        for key, alias in cls.CONVERT_ALIAS.items():
            if key == name:
                return alias
        return None

    @property
    def reversed_name(self):
        if self.token in self.OPS:
            operator = self.OPS[self.token][0]
            if operator is not None:
                return operator
        return self.name

    @property
    def is_bool_operator(self):
        return self.token in self.BOOL_OPS

    @property
    def is_number_operator(self):
        return self.token in self.NUMBER_OPS


class UnknownToken(Token):
    pass


class ExprCalculator:
    DEFAULT_OPTIONS = {"unique": False}

    def __init__(self, expression, options=None, validate_number_operator=False):
        self.expression = expression
        self.tokens = [Token.create(item, index) for index, item in enumerate(expression)]
        self.options = options
        self.validate_number_operator = validate_number_operator

    def get_options(self, key):
        return (self.options or {}).get(key) or self.DEFAULT_OPTIONS.get(key)

    def _convert(self, sub_tokens):
        operator = [item for item in sub_tokens if isinstance(item, OperatorToken) and item.name == "包含"]
        if (
            len(sub_tokens) <= 3 or not operator
        ):  # field 包含 value, 小于等于3个的 没必要处理,没有包含操作符的 没必要处理
            return sub_tokens

        field = sub_tokens[0]
        values = [item for item in sub_tokens if isinstance(item, ValueToken) and item.real_name != field.real_name]
        operator = operator[0]

        missed_tokens = []
        matched_tokens = []
        for value in values:
            try:
                result = self.operate(value, field, operator)
                if result:
                    matched_tokens.append(value)
                else:
                    missed_tokens.append(value)
            except (ZeroDivisionError, TypeError, ValueError) as e:
                logging.exception(e)
                raise ExprCalcError(self.tokens, field) from e

        flag = len(matched_tokens) == 1
        op_name = "唯一包含" if flag else "未唯一包含"
        suggestion_op = ""
        if not flag:
            text = "或".join(v.name for v in values)
            if len(missed_tokens) == len(values):
                suggestion_op = f"请在“{field.name}”内补充“{text}”"
            else:
                suggestion_op = f"请在“{field.name}”内删除“{text}”"

        return [
            Token.create(
                {
                    "value": flag,
                    "name": f"{field.name} 唯一包含 {values}",
                    "left": field,
                    "right": None,
                    "operator": operator,
                    "detail": {"matched_tokens": matched_tokens},
                    "reversed_name": f"{field.name} {op_name} {values}",
                    "suggestion": suggestion_op,
                },
                index=operator.index,
            )
        ]

    def convert_contain_once(self, tokens):
        # 对于连续对同一个字段的 或包含 进行预处理，转换为一个新的计算符  唯一包含
        temp_arr = []
        result = []
        operators = {"包含", "或"}
        for token in tokens:
            if isinstance(token, OperatorToken):
                if token.name in operators:
                    temp_arr.append(token)
                else:
                    result.extend(self._convert(temp_arr))
                    result.append(token)
                    temp_arr = []
            elif token.real_name:
                if not temp_arr:
                    temp_arr.append(token)
                elif token.real_name == temp_arr[0].real_name:
                    temp_arr.append(token)
                else:
                    last_operator = []
                    if temp_arr:
                        last_operator = [temp_arr.pop()]
                    result.extend(self._convert(temp_arr))
                    result.extend(last_operator)
                    temp_arr = [token]
            else:
                temp_arr.append(token)
        if temp_arr:
            result.extend(self._convert(temp_arr))
        return result

    @property
    def expr_text(self):
        return " ".join([item.name for item in self.tokens])

    @property
    def reversed_expr_text(self):
        return " ".join([item.reversed_name for item in self.tokens])

    @classmethod
    def gen_suffix_expr(cls, tokens):
        operator_stack = []
        expr_stack = []

        for token in tokens:
            if isinstance(token, ValueToken):
                expr_stack.append(token)
            elif isinstance(token, OperatorToken):
                if not operator_stack:
                    operator_stack.append(token)
                else:
                    for top in operator_stack[::-1]:
                        if top.level >= token.level:
                            expr_stack.append(top)
                            operator_stack.pop()
                        else:
                            operator_stack.append(token)
                            break

                    if not operator_stack:
                        operator_stack.append(token)
            else:
                raise UnknownOperatorError(tokens, token)

        expr_stack.extend(reversed(operator_stack))
        return expr_stack

    @classmethod
    def search_result_tree(cls, node):
        result = []

        def search(_node, _result):
            if not _node:
                return
            if (not _node.parent_operator or _node.parent_operator.name not in {"或", "且"}) and not _node.value:
                _result.append(_node)
            else:
                search(_node.left, _result)
                search(_node.right, _result)

        search(node, result)
        if not result:
            result.append(node)
        return result

    def run(self, only_validate=False):
        tokens = self.tokens
        if not only_validate and self.get_options("unique") and len(tokens) > 2:
            tokens = self.convert_contain_once(tokens)
            if len(tokens) == 1:
                return tokens[0]

        suffix_expr = self.gen_suffix_expr(tokens)
        print("suffix expression: {}".format(suffix_expr))

        stack = []
        if len(suffix_expr) == 1:
            if isinstance(suffix_expr[0], ValueToken):
                raise MissOperatorError(self.tokens, suffix_expr[0])
            raise MissLeftValueError(self.tokens, suffix_expr[0])

        for token in suffix_expr:
            if isinstance(token, ValueToken):
                stack.append(token)
            else:
                if not stack:
                    raise MissLeftValueError(self.tokens, token)
                token1 = stack.pop()
                if not stack:
                    raise MissRightValueError(self.tokens, token)
                token2 = stack.pop()

                if not only_validate:
                    try:
                        result = self.operate(token1, token2, token)
                    except (ZeroDivisionError, TypeError, ValueError) as e:
                        logging.exception(e)
                        raise ExprCalcError(self.tokens, token1) from e
                else:
                    if self.validate_number_operator and token.is_number_operator:
                        if not token1.is_number and not token1.is_schema_field and not token1.parent_operator:
                            raise InvalidValueError(token=token1, tokens=self.tokens)
                        if not token2.is_number and not token2.is_schema_field and not token2.parent_operator:
                            raise InvalidValueError(token=token2, tokens=self.tokens)

                    result = True

                stack.append(
                    Token.create(
                        {
                            "value": result,
                            "name": f"{token2} {token} {token1}",
                            "left": token2,
                            "right": token1,
                            "operator": token,
                            "reversed_name": f"{token2.reversed_name} {token.reversed_name} {token1.reversed_name}",
                            "suggestion": self.render_node_suggestion(token, token1, token2),
                        },
                        index=token.index,
                    )
                )

        if len(stack) >= 2:
            raise MissOperatorError(self.tokens, stack[0])
        return stack[0]

    @classmethod
    def render_node_suggestion(cls, token, token1, token2):
        op_name = OperatorToken.convert_alias(token.name)
        if op_name:
            suggestion = f"请在“{token2}”内{op_name}“{token1}”"
        else:
            suggestion = f"{token2} {token} {token1}"
        return suggestion

    @classmethod
    def operate(cls, value1, value2, operator):
        if operator.is_bool_operator:
            # 如 a < b == c > d != 4 转换为 a < b && b == c && c > d && d != 4
            if value2.parent_operator and value2.parent_operator.is_bool_operator:
                return value2.value and operator.operate(value2.right, value1)
            if value1.parent_operator and value1.parent_operator.is_bool_operator:
                pass  # 在没有括号情况下，不会出现
        return operator.operate(value2, value1)

    @classmethod
    def render_message_by_result(cls, result, addition_reason=None):
        message = None
        reason_text = None or addition_reason

        if result.value:
            return message, reason_text

        nodes = cls.search_result_tree(result)
        if nodes:
            for node in nodes:
                _reason_text = node.reversed_name
                _message = node.suggestion
                if node.left and node.right and node.right.value == "NULL":
                    if node.parent_operator:
                        if node.parent_operator.name == "≠":
                            _reason_text = f"{node.left.name} 为空"
                            _message = f"请补充{node.name}内容"
                        elif node.parent_operator.name in ("=", "=="):
                            _reason_text = f"{node.left.name} 不为空"

                message = append_suggestion(message, _message)
                reason_text = append_suggestion(reason_text, _reason_text, separator="\n")

        return message, reason_text


if __name__ == "__main__":
    # exp = [
    #     {'value': "24", 'name': '冷静期'},
    #     '>',
    #     {'value': "24"},
    #     "或",
    #     {"value": "133", "name": "公司余额"},
    #     '<',
    #     {'value': '13.3'},
    # ]
    # res = ExprCalculator(exp).run().value
    # print(res)
    # print(ExprCalculator([{'value': 12}, '<']).run())
    # print(ExprCalculator([{'value': 12}, '>', '<']).run())
    # print(ExprCalculator([{'value': 12}]).run())
    # print(ExprCalculator(['<']).run())
    # print(ExprCalculator([{'value': 12}, {'value': 12}, {'value': 12},'<']).run())
    exp = [{"name": "冷静期", "value": "26"}, ">", {"value": "25"}, ">", {"value": "24"}, "<", {"value": 27}]
    res = ExprCalculator(exp).run().value
    print(res)
