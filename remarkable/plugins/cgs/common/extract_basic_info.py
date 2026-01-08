from remarkable.checker.base import BaseChecker
from remarkable.plugins.cgs.common.patterns_util import P_BOURSE_SH, P_BOURSE_SZ


class ExtractFundBasicInfo:
    @classmethod
    def get_fund_bourse_name(cls, template_checker: BaseChecker):
        bourse_name = template_checker.manager.check_stock_bourse()
        value = (bourse_name and bourse_name[0].value) or ""
        if P_BOURSE_SH.nexts(value):
            return "上海证券交易所"
        if P_BOURSE_SZ.nexts(value):
            return "深圳证券交易所"
        return "上海证券交易所/深圳证券交易所"

    @classmethod
    def get_fund_settlement_name(cls, template_checker: BaseChecker):
        bourse_name = cls.get_fund_bourse_name(template_checker)
        if "上海证券交易所" == bourse_name:
            return "上海证券账户"
        if "深圳证券交易所" == bourse_name:
            return "深圳证券账户"
        return "上海证券账户/深圳证券账户"

    @classmethod
    def get_city_by_bourse(cls, template_checker: BaseChecker):
        bourse_name = cls.get_fund_bourse_name(template_checker)
        if "上海证券交易所" == bourse_name:
            return "上海"
        if "深圳证券交易所" == bourse_name:
            return "深圳"
        return "上海/深圳"

    @classmethod
    def get_fund_name(cls, template_checker: BaseChecker):
        answer = template_checker.manager.get("基金名称")
        return (answer and answer.value) or "XXXXXX"

    @classmethod
    def get_fund_manage_name(cls, template_checker: BaseChecker):
        answer = template_checker.manager.get("基金管理人-名称")
        return (answer and answer.value) or "基金管理人"

    @classmethod
    def get_fund_custodian_name(cls, template_checker: BaseChecker):
        answer = template_checker.manager.get("基金托管人-名称")
        return (answer and answer.value) or "XXXXXX"

    @staticmethod
    def get_fund_bourse_name_with_test(_):
        return "上海"
