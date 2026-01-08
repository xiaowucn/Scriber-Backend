# CYC: build-with-nuitka
import logging
import re

from remarkable.predictor.predictor import T_ENUM_ANSWERS

logger = logging.getLogger(__name__)


def judge_product_type(answers: T_ENUM_ANSWERS, text: str) -> str | list[str] | None:
    contract_type = answers.get('["富国基金", "基金合同类型"]')
    if not contract_type:
        logger.warning("基金合同类型枚举值为空")
        return None
    if contract_type == "FOF":
        return "基金类"
    elif contract_type == "联接型":
        return "基金类"
    elif contract_type == "ETF":
        return "股票类" if re.search(r"(成[份分]股|股票)[^,，。]*?(占比|比例)不得?低于", text) else "基金类"
    elif contract_type == "债券型":
        return "债券类"
    elif contract_type == "股票型":
        return "股票类"
    elif contract_type == "混合型":
        return "混合类"
    elif contract_type == "货币型":
        # TODO: 规则不确定，需要确认
        return "公募货币基金" if "公募" in text else "现金管理类"
    elif contract_type == "QDII":
        return "QDII类"
    # TODO:
    # 权益类：投资到除A股之外（包括新三板、区域性股权市场等）权益资产百分之八十以上的产品
    # 衍生品类：投资于衍生品资产百分之八十以上的产品
    # 非标类：投资于非标准化资产（包括但不限于信托计划、委托贷款、银行理财、资产收益权、票据、股票质押、非上市股权）百分之八十以上的产品，
    #   管理人发行的资产证券化产品也计为非标类
    return "其他类"
