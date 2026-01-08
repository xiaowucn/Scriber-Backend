import re
from decimal import Decimal

from remarkable.checker.answers import Answer

P_NUMBER = re.compile(r"^[\d.,%％]+")


def get_schema_result(mold_name: str, doc_type: str, field: str, answer: Answer):
    ret = {
        "name": field,
        "full_key_path": [mold_name, *field.split("-")],
        "matched": False,
        "doc_type": doc_type,
    }
    if answer and answer.value:
        ret.update(**{"text": answer.value, "answer": answer.answer})
    return ret


def percentage_to_float(percentage_string):
    """
    将百分比字符串转换为浮点数
    """
    if not percentage_string:
        return None
    try:
        return float(Decimal(percentage_string.replace(",", "").rstrip("%")) / Decimal(100))
    except ValueError:
        return None


def get_number_value(data: str):
    """
    提取时已将单位统一处理过,此处只取数值
    :param data:
    :return:
    """
    if not data:
        return data
    match = P_NUMBER.match(data)
    if match:
        return match.group()
    return data
