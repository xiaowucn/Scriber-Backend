import re

from remarkable.common.util import clean_txt
from remarkable.predictor.base_prophet import BaseProphet
from remarkable.predictor.predictor import EnumPredictor, JudgeByRegex
from remarkable.predictor.utils import (
    contribution_method,
    guarantee_method,
    guarantee_type,
    is_chinese_address,
    is_correlation,
    is_overseas_assets,
    item_category,
    subject_type,
    vote,
    whether_or_not,
    whether_review,
)


class PurchaseAssetEnumPredictor(EnumPredictor):
    connected_transaction_pattern = re.compile(r"交易构成关联交易")

    def predict(self, predictor_result, schema):
        if schema.name == "是否属于境外资产":
            return is_overseas_assets(predictor_result.text)
        elif schema.name == "交易对手方与公司是否有关联关系":
            return self.is_connected_transaction(predictor_result.text)
        elif schema.name == "出售或购买的标的类别":
            return self.get_asset_category(predictor_result.text)
        else:
            return None

    def is_connected_transaction(self, content):
        if self.connected_transaction_pattern.search(content):
            return "是"
        else:
            return "否"

    def get_asset_category(self, content):
        if "股权" in content:
            return "股权"
        else:
            return "资产"


class ArBlowdownEnumPredictor(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "是否排污":
            return self.is_blowdown(predictor_result.text)
        else:
            return None

    @staticmethod
    def is_blowdown(content):
        if re.search(r"重点排污单位之外的公司的环保情况说明\n?.*?√不适用", content):
            return "否"
        if re.search(r"排[污放]信息", content):
            return "是"
        return "是"


class DisclosureTipsEnumPredictor(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "增持或减持":
            return is_increase(predictor_result.text)
        elif schema.name == "是否触及要约收购":
            return whether_or_not(predictor_result.text)
        elif schema.name == "变动是否使公司控股股东及实际控制人发生变化":
            return whether_or_not(predictor_result.text)
        return None


def is_increase(content):
    if re.search(r"增持", content):
        return "增持"
    return "减持"


class ControlChangeEnumPredictor(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "增持或减持":
            return is_increase(predictor_result.text)
        elif schema.name == "是否触及要约收购":
            return self.has_tender_offer(predictor_result.text)
        elif schema.name == "变动是否使公司控股股东及实际控制人发生变化":
            return self.is_change_holder(predictor_result.text)
        return None

    @staticmethod
    def has_tender_offer(content):
        if re.search(r"[不无未否]|免于", content):
            return "否"
        return "是"

    @staticmethod
    def is_change_holder(content):
        if not isinstance(content, str):
            content = "_".join([each.text for each in content.element_results])
        if re.search(r"变更为|发生变|变更未导致", content):
            return "是"
        return "否"


class OtherGuaranteeEnumPredictor(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "被担保人是否是关联方及关联关系":
            return is_correlation(predictor_result.text)
        elif schema.name == "是否有反担保":
            return whether_or_not(predictor_result.text)
        elif schema.name == "担保类型":
            return guarantee_type(predictor_result.text, multi=True)
        elif schema.name == "担保方式":
            return guarantee_method(predictor_result.text, multi=True)
        return None


class DailyContractEnumPredictor(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "合同类型":
            return self.contract_type(predictor_result.text)
        elif schema.name == "合同对方是否为关联方":
            return whether_or_not(predictor_result.text)
        elif schema.name == "审议程序情况（是否要上股东大会决议）":
            return whether_or_not(predictor_result.text)
        else:
            return None

    @staticmethod
    def contract_type(content):
        """
        合同：项目中标/买卖/货物运输
        """
        val_patterns = [
            ("项目中标", [r"项目中标"]),
            ("工程建设", [r"工程建设"]),
            ("采购合同", [r"采购"]),
            ("补充协议", [r"补充"]),
            ("销售合同", [r"销售"]),
            ("项目/产品/技术开发", [r"开发"]),
            ("合作协议", [r"合作"]),
        ]
        enum_value = None
        for val, patterns in val_patterns:
            if any(re.search(reg, content) for reg in patterns):
                enum_value = val
                break
        return enum_value


class ReceiveFinancialSupportEnumPredictor(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "审议程序（是否要上股东大会决议）":
            return whether_or_not(predictor_result.text)
        elif schema.name == "是否属于境外资产":
            return is_overseas_assets(predictor_result.text)
        else:
            return None


class ShareholdersIncreaseAnnouncementEnumPredictor(EnumPredictor):
    ratio_p = re.compile(r"(?P<dst>\d+\.?\d*?)%")

    @classmethod
    def gen_shareholder_type(cls, content):
        """股东类型
        除非明确说明为控股股东，否则需要按照持股比例判断，低于5%为其他，高于5%为重要股东
        """
        if re.search(r"控股股东", content):
            return "控股股东及其一致行动人"

        match = cls.ratio_p.search(content)
        if not match:
            return None

        ratio = float(match.group("dst"))
        return "重要股东" if ratio >= 5 else "其他"

    @classmethod
    def placard_or_not(cls, content):
        """是否举牌
        增持比例为5%整数倍，选是，否则选否
        """
        match = cls.ratio_p.search(content)
        if not match:
            return None
        ratio = float(match.group("dst"))
        return "否" if ratio % 5 else "是"

    def predict(self, predictor_result, schema):
        if schema.name == "股东类型":
            return self.gen_shareholder_type(predictor_result.text)
        if schema.name == "是否举牌":
            return self.placard_or_not(predictor_result.text)
        return None


class FakeRE:
    col_pattern_map = {
        "主体类型_持股5%以上股东": (r"(?P<dst>\d+\.?\d*?)%", 5),
        "业绩预告类别_净利润与上年同期相比上升50%以上": (r"[升上涨增加长\+](?P<dst>\d+\.?\d*?)%", 50),
        "业绩预告类别_净利润与上年同期相比下降50%以上": (r"[降下跌减少\-](?P<dst>\d+\.?\d*?)%", 50),
    }

    def __init__(self, col):
        self.col = col

    def greater_than(self, text):
        pattern, threshold = self.col_pattern_map.get(self.col) or ("", 0)
        if not pattern:
            return None
        match = re.search(pattern, text)
        if not match:
            return None
        return match if float(match.group("dst")) >= threshold else None

    def search(self, text):
        if self.col == "是否属于境外资产_否":
            return is_chinese_address(text)
        return self.greater_than(text)


class ReportOnChangesInEquityEnumPredictor(JudgeByRegex):
    col_patterns = {
        "主体类型": {
            "控股股东": [re.compile(r"控股股东")],
            "一致行动人": [re.compile(r"一致行动人")],
            "持股5%以上股东": [FakeRE("主体类型_持股5%以上股东")],
            "其他": [re.compile(r".*")],
        },
        "股份变动性质": {
            "增持": [re.compile(r"增")],
            "减持": [re.compile(r"减")],
        },
    }


class ChangesAccountingPoliciesPredictor(JudgeByRegex):
    col_patterns = {
        "说明类型": {
            "会计差错": [re.compile(r"差错")],
            "会计政策": [re.compile(r"政策")],
            "会计估计变更": [re.compile(r"估计")],
        },
    }


class SummaryDraftEquityIncentivePlanPredictor(JudgeByRegex):
    # TODO: 限制性股票单元 vs 普通限制性股票?
    col_patterns = {
        "激励方式": {
            "限制性股票单元": [re.compile(r"限制性.*二类")],
            "股票期权": [re.compile(r"期权")],
            "普通限制性股票": [re.compile(r"限制性")],
        },
    }


class PerformanceForecastCorrection(JudgeByRegex):
    col_patterns = {
        "业绩预告类别": {
            "净利润为负": [re.compile(r"净利润为负")],
            "净利润与上年同期相比上升50%以上": [FakeRE("业绩预告类别_净利润与上年同期相比上升50%以上")],
            "净利润与上年同期相比下降50%以上": [FakeRE("业绩预告类别_净利润与上年同期相比下降50%以上")],
            "实现扭亏为盈": [re.compile(r"扭亏为盈")],
            "因上市规则12.4.2被实施退市风险警示": [re.compile(r"12\.4\.2")],
            "其他": [re.compile(r".*")],
        },
    }


class EquityIncentivePlanShareRepurchase(JudgeByRegex):
    col_patterns = {
        "回购方式": {
            "集中竞价": [r"集中竞价"],
            "要约方式": [r".*"],
        },
        "公告类型": {
            "方案": [r"方案"],
            "进展": [r"开始"],
            "变更": [r"变更"],
            "终止": [r"终止"],
        },
    }


class SellAssets(JudgeByRegex):
    col_patterns = {
        "交易事项": {
            "出售": [r"[出售卖]"],
            "购买": [r"[买入购]"],
        },
        "交易对手方与公司是否有关联关系": {
            "否": [r"[不无未否]"],
            "是": [r".*"],
        },
        "是否属于境外资产": {
            "否": FakeRE("是否属于境外资产_否"),
            "是": [r".*"],
        },
    }


class AnnualGuarantee(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "担保方式":
            return guarantee_method(predictor_result.text, multi=True)
        elif schema.name == "担保类型":
            return is_overseas_assets(predictor_result.text)
        elif schema.name == "是否有反担保":
            return whether_or_not(predictor_result.text)
        else:
            return None


class GuaranteeSubsidiary(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "担保方式":
            return guarantee_method(predictor_result.text, multi=True)
        elif schema.name == "担保类型":
            return is_overseas_assets(predictor_result.text)
        elif schema.name == "是否有反担保":
            return whether_or_not(predictor_result.text)
        else:
            return None


class DailyConnectedTransaction(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "审议程序":
            return whether_or_not(predictor_result.text)
        else:
            return None


class EntrustAssociatesEnumPredictor(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "审议程序（是否要上股东大会决议）":
            return whether_or_not(predictor_result.text)
        elif schema.name == "是否属于境外资产":
            return is_overseas_assets(predictor_result.text)
        else:
            return None


class SharePledgedEnumPredictor(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "公告类型":
            return "质押"
        elif schema.name in [
            "出质人是否是控股股东及其一致行动人",
            "质押股份是否为限售流通股",
            "质押股份是否负担业绩补偿义务",
        ]:
            return whether_or_not(predictor_result.text)
        else:
            return None


class ShareFreezeEnumPredictor(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "公告类型":
            return "冻结"
        elif schema.name == "冻结股份是否为限售流通股":
            return whether_or_not(predictor_result.text)
        else:
            return None

    @classmethod
    def is_restricted_shares(cls, content):
        if re.search(r"无限", content):
            return "否"
        else:
            return "是"


class SharePledgedTerminationEnumPredictor(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "公告类型":
            return "解质"
        else:
            return None


class SplitStockEnumPredictor(EnumPredictor):
    reduce_stock_pattern = re.compile(r"(无|不).*?(增减|增持或减持).*?股份")
    audit_pattern = re.compile(r"[预|议]案.*?(需|提交).*?审议")

    def predict(self, predictor_result, schema):
        if schema.name == "是否有减持计划":
            return self.is_reduction(predictor_result)
        elif schema.name == "高送转提议人":
            return self.get_proposer(predictor_result.text)
        elif schema.name == "审议程序":
            return self.is_need_audit(predictor_result.text)
        else:
            return None

    def is_reduction(self, answer_result):
        is_reduction = True
        for content in answer_result.text.split("\n"):
            if self.reduce_stock_pattern.search(content):
                is_reduction = False
                break

        if is_reduction:
            return "是"
        else:
            return "否"

    @staticmethod
    def get_proposer(content):
        return "股东" if "股东" in content else "董事会"

    def is_need_audit(self, content):
        return "是" if self.audit_pattern.search(content) else "否"


class AssociationArticlesModifyAnnouncementEnumPredictor(EnumPredictor):
    def predict(self, predictor_result, schema):
        return self.is_director_involved(predictor_result.text)

    def is_director_involved(self, content):
        if content and "董事会" in content:
            return "是"
        else:
            return "否"


class TransactionWithAssociates(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "审议程序（是否要上股东大会决议）":
            return whether_or_not(predictor_result.text)
        elif schema.name == "是否属于境外资产":
            return is_overseas_assets(predictor_result.text)
        else:
            return None


class ConnectedTransactionPrompter(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "审议程序（是否要上股东大会决议）":
            return whether_or_not(predictor_result.text)
        elif schema.name == "是否属于境外资产":
            return is_overseas_assets(predictor_result.text)
        else:
            return None


class ConnectedTransactionProgress(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "审议程序（是否要上股东大会决议）":
            return whether_or_not(predictor_result.text)
        elif schema.name == "是否属于境外资产":
            return is_overseas_assets(predictor_result.text)
        else:
            return None


class ConnectedTransactionCompletion(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "审议程序（是否要上股东大会决议）":
            return whether_or_not(predictor_result.text)
        elif schema.name == "是否属于境外资产":
            return is_overseas_assets(predictor_result.text)
        else:
            return None


class OverweightPlan(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "主体类型":
            return subject_type(predictor_result.text)
        else:
            return None


class OverweightProgress(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "主体类型":
            return subject_type(predictor_result.text)
        else:
            return None


class OverweightCompletion(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "主体类型":
            return subject_type(predictor_result.text)
        else:
            return None


class ReductionPlan(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "主体类型":
            return subject_type(predictor_result.text)
        else:
            return None


class ReductionProgress(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "主体类型":
            return subject_type(predictor_result.text)
        else:
            return None


class NewProject(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "审议程序（是否要上股东大会决议）":
            return whether_or_not(predictor_result.text)
        elif schema.name == "是否是关联交易":
            return whether_or_not(predictor_result.text)
        elif schema.name == "是否是重大资产重组":
            return whether_or_not(predictor_result.text)
        else:
            return None


class AssociateGuarantee(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "担保方式":
            return guarantee_method(predictor_result.text, multi=True)
        elif schema.name == "担保类型":
            return guarantee_type(predictor_result.text, multi=True)
        elif schema.name == "是否有反担保":
            return whether_or_not(predictor_result.text)
        else:
            return None


class StrategicFrameworkAgreement(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "审议程序":
            return whether_or_not(predictor_result.text)
        else:
            return None


class AssociateFinancialSupport(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "审议程序":
            return whether_or_not(predictor_result.text)
        elif schema.name == "是否关联交易":
            return whether_or_not(predictor_result.text)
        elif schema.name == "是否是重大资产重组":
            return whether_or_not(predictor_result.text)
        else:
            return None


class RepurchaseProgramEnumPredictor(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "公告类型":
            return announcement_type(predictor_result.text)
        elif schema.name == "回购方式":
            return repurchase_type(predictor_result.text)
        return None


class RepurchaseImplementationPredictor(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "公告类型":
            return announcement_type(predictor_result.text)
        elif schema.name == "回购方式":
            return repurchase_type(predictor_result.text)
        return None


def announcement_type(content):
    for i in ["方案", "进展", "变更", "终止"]:
        if i in content:
            return i
    return "方案"


def repurchase_type(content):
    ret = []
    if "集中" in content:
        ret.append("集中竞价")
    if "要约" in content:
        ret.append("要约方式")
    return ret or None


class RepurchaseResultPredictor(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "是否有差异":
            content = "_".join([each.text for each in predictor_result.element_results])
            if re.search(r"不存在差异|均符合", content):
                return "否"
            if re.search(r"存在差异", content):
                return "是"
        return None


class PurchaseRelatedAssetsPredictor(EnumPredictor):
    def predict(self, predictor_result, schema):
        content = "_".join([each.text for each in predictor_result.element_results])
        if schema.name == "交易事项":
            return transaction_type(content)
        elif schema.name == "出售或购买的标的类别":
            return None
        elif schema.name == "是否属于境外资产":
            return "资产"
        elif schema.name == "交易对手方与公司是否有关联关系":
            return is_related(content)
        elif schema.name == "投票情况":
            return None
        return None


def transaction_type(content):
    if "购买" in content:
        return "购买"
    return "出售"


def is_related(content):
    if re.search(r"[构购]成.*?关联交易", content):
        return "是"
    elif whether_or_not(content):
        return "否"
    return None


class SaleRelatedAssetsPredictor(EnumPredictor):
    def predict(self, predictor_result, schema):
        content = "_".join([each.text for each in predictor_result.element_results])
        if schema.name == "交易事项":
            return transaction_type(content)
        elif schema.name == "出售或购买的标的类别":
            return None
        elif schema.name == "是否属于境外资产":
            return is_overseas_assets(content)
        elif schema.name == "交易对手方与公司是否有关联关系":
            return is_related(content)
        elif schema.name == "投票情况":
            return None
        return None


class QuityIncentiveTermination(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "是否涉及回购注销":
            if re.search(r"回购注销", predictor_result.text):
                return "是"
            else:
                return "否"
        return None


class ShareIncentiveGrant(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "股权激励方式":
            share_types = ["第一类", "第二类", "期权"]
            for share_type in share_types:
                if share_type in predictor_result.text:
                    return share_type
            return None
        elif schema.name == "是否存在以下情况：激励对象为董事、高管的，在限制性股票授予日前6个月卖出公司股份":
            if whether_or_not(predictor_result.text):
                return "否"
            else:
                return "是"
        return None


class ConvertibleDebtPayment(EnumPredictor):
    def predict(self, predictor_result, schema):
        content = "_".join([each.text for each in predictor_result.element_results])
        if schema.name == "事项类别":
            return item_category(content)
        elif schema.name == "所得税代扣代缴方式":
            if re.search(r"付息", predictor_result.text):
                return "券商代扣代缴"
            else:
                return "其他"
        return None


class ProfitDistribution(EnumPredictor):
    def predict(self, predictor_result, schema):
        content = "_".join([each.text for each in predictor_result.element_results])
        if schema.name == "审议程序情况（是否要上股东大会决议）":
            return whether_or_not(content)
        return None


class ConvertibleDebtProspectus(EnumPredictor):
    def predict(self, predictor_result, schema):
        content = "_".join([each.text for each in predictor_result.element_results])
        if schema.name == "是否存在老股东优先配售":
            return whether_or_not(content)
        elif schema.name == "是否有担保":
            return whether_or_not(content)
        return None


class ApplyBankruptcySchemaEnumPredictor(EnumPredictor):
    def predict(self, predictor_result, schema):
        if schema.name == "实际控制人或控股股东是否涉及破产清算":
            if re.search(r"实际控制人|控股股东", predictor_result.text):
                return "是"
            return "否"
        return None


class AssetDisposal(EnumPredictor):
    def predict(self, predictor_result, schema):
        content = "_".join([each.text for each in predictor_result.element_results])
        if schema.name == "是否构成重大资产重组":
            return whether_or_not(content)
        return None


class LastRaiseFunds(EnumPredictor):
    def predict(self, predictor_result, schema):
        content = "_".join([each.text for each in predictor_result.element_results])
        if schema.name == "是否存在变更":
            return whether_or_not(content)
        return None


class CooperationInvestment(EnumPredictor):
    def predict(self, predictor_result, schema):
        content = "_".join([each.text for each in predictor_result.element_results])
        if schema.name == "出资方式":
            return contribution_method(content)
        return None


class RaiseFundsReport(EnumPredictor):
    def predict(self, predictor_result, schema):
        content = "_".join([each.text for each in predictor_result.element_results])
        if schema.name == "差异的原因和情况":
            return whether_or_not(content)
        elif schema.name == "是否存在变更":
            return whether_or_not(content)
        return None


class RaiseFundsUsage(EnumPredictor):
    def predict(self, predictor_result, schema):
        content = "_".join([each.text for each in predictor_result.element_results])
        if schema.name == "股东大会审议情况":
            return whether_review(content)
        elif schema.name == "董事大会反对情况":
            if re.search(r"[0零]票", content):
                return "无"
            else:
                return "反对"
        elif schema.name == "董事大会弃权情况":
            if re.search(r"[0零]票", content):
                return "无"
            else:
                return "反对"
        return None


class RaiseFundsReplacement(EnumPredictor):
    def predict(self, predictor_result, schema):
        content = "_".join([each.text for each in predictor_result.element_results])
        if schema.name == "股东大会审议情况":
            return whether_review(content)
        return None


class InvestWithAssociates(EnumPredictor):
    def predict(self, predictor_result, schema):
        content = "_".join([each.text for each in predictor_result.element_results])
        if schema.name == "审议程序（是否要上股东大会决议）":
            return whether_review(content)
        elif schema.name == "投票情况":
            return vote(content)
        elif schema.name == "是否是关联交易":
            return whether_or_not(content)
        elif schema.name == "是否是重大资产重组":
            return whether_or_not(content)
        return None


class AssociatesEntrustInvestment(EnumPredictor):
    def predict(self, predictor_result, schema):
        content = "_".join([each.text for each in predictor_result.element_results])
        if schema.name == "审议程序（是否要上股东大会决议）":
            return whether_review(content)
        elif schema.name == "投票情况":
            return vote(content)
        elif schema.name == "是否是关联交易":
            return whether_or_not(content)
        elif schema.name == "是否是重大资产重组":
            return whether_or_not(content)
        return None


class AssociatesEntrustLoan(EnumPredictor):
    def predict(self, predictor_result, schema):
        content = "_".join([each.text for each in predictor_result.element_results])
        if schema.name == "审议程序（是否要上股东大会决议）":
            return whether_review(content)
        elif schema.name == "投票情况":
            return vote(content)
        elif schema.name == "是否是关联交易":
            return whether_or_not(content)
        elif schema.name == "是否是重大资产重组":
            return whether_or_not(content)
        return None


class AssetSeizureFreezeEnumPredictor(JudgeByRegex):
    col_patterns = {
        "资产类型": {
            "股权": [r"股权"],
            "土地及地上附着物": [r"土?地"],
            "银行账户": [r"银行账户"],
        },
        "变动情况": {
            "新增冻结": [r"新增冻结"],
            "解除冻结": [r"解除冻结"],
            "账户资金增加": [r"账户资金增加"],
            "账户资金减少": [r"账户资金减少"],
        },
        "公司名称": {
            "被冻结股权的公司名称": [r"公司"],
            "土地所有人": [r"土地所有人"],
            "被冻结单位名称": [r"被冻结单位名称"],
        },
    }


class IntellectualropertyEnumPredictor(JudgeByRegex):
    col_patterns = {
        "问题类别": {
            "获得授权": [r"授权"],
            "获得认证": [r"认证"],
            "无效宣告": [r"无效"],
            "变更": [r"变更"],
            "转让": [r"转让"],
            "纠纷": [r"纠纷"],
        }
    }


class SupervisorMeetingEnumPredictor(JudgeByRegex):
    col_patterns = {"是否通过": {"是": [r"通过|同意"], "否": [r"不通过"]}}


class _NaturalPersonJudge:
    col = "自然人"

    @classmethod
    def search(cls, text):
        text = clean_txt(text)
        return (
            None if re.search(r"合伙|法人|公司|有限|独资", text) or re.search(r"[^\u4e00-\u9fa5]+", text) else cls.col
        )


class SSEPoc(JudgeByRegex):
    col_patterns = {
        "是否拥有永久境外居留权（自然人）": {"否": [r"无|没有"], "是": [r".*"]},
        "股东类型": {"合伙企业": [r"合伙"], "法人": [r"有限|法人"], "自然人": [_NaturalPersonJudge]},
        "是否关联方": {"否": [r"无|没有|否"], "是": [r".*"]},
        "注释内容": {"关联情况": [r"关联"], "其他": [r".*"]},
    }


class Prophet(BaseProphet):
    def parse_enum_value(self, predictor_result, schema):
        if self.enum_predictor:
            return self.enum_predictor.predict(predictor_result, schema)
        return None

    def get_enum_predictor(self):
        enum_classes = {
            "01 资产处置公告": AssetDisposal,
            "04 监事会决议公告": SupervisorMeetingEnumPredictor,
            "0401 购买资产": PurchaseAssetEnumPredictor,
            "14 年报-排污": ArBlowdownEnumPredictor,
            "0603 其他对外担保": OtherGuaranteeEnumPredictor,
            "0604 提供反担保": OtherGuaranteeEnumPredictor,
            "0419 签订日常经营合同": DailyContractEnumPredictor,
            "0509 接受关联人财务资助": ReceiveFinancialSupportEnumPredictor,
            "07 股东增持公告": ShareholdersIncreaseAnnouncementEnumPredictor,
            "08 申请破产清算公告": ApplyBankruptcySchemaEnumPredictor,
            "20 权益变动报告": ReportOnChangesInEquityEnumPredictor,
            "21 资产查封冻结公告": AssetSeizureFreezeEnumPredictor,
            "23 临时公告-知识产权": IntellectualropertyEnumPredictor,
            "0512 委托关联人管理资产和业务": EntrustAssociatesEnumPredictor,
            "1801 回购方案": RepurchaseProgramEnumPredictor,
            "1805 回购实施进展": RepurchaseImplementationPredictor,
            "1809 回购实施结果暨股份变动": RepurchaseResultPredictor,
            "2101 股权激励计划草案摘要": SummaryDraftEquityIncentivePlanPredictor,
            "2401 股份被质押": SharePledgedEnumPredictor,
            "2402 股份被冻结": ShareFreezeEnumPredictor,
            "2403 股份质押解除": SharePledgedTerminationEnumPredictor,
            "0902 董事会审议高送转": SplitStockEnumPredictor,
            "2710 变更会计政策或者会计估计": ChangesAccountingPoliciesPredictor,
            "1213 因股东披露权益变动报告书或收购报告书的提示": DisclosureTipsEnumPredictor,
            "1214 控股股东或实际控制人发生变动的提示": ControlChangeEnumPredictor,
            "03 公司章程公告-关于修改公司章程的公告": AssociationArticlesModifyAnnouncementEnumPredictor,
            "0527 与关联人财务公司的交易": TransactionWithAssociates,
            "0528 关联交易的提示": ConnectedTransactionPrompter,
            "0529 关联交易的进展": ConnectedTransactionProgress,
            "0530 关联交易的完成": ConnectedTransactionCompletion,
            "1222 股东增持计划": OverweightPlan,
            "1223 股东增持进展": OverweightProgress,
            "1224 股东增持计划完成": OverweightCompletion,
            "1220 股东减持计划": ReductionPlan,
            "1221 股东减持进展": ReductionProgress,
            "0421 新建项目": NewProject,
            "0502 向关联人提供担保或反担保": AssociateGuarantee,
            "0425 签订战略框架协议": StrategicFrameworkAgreement,
            "0508 向关联人提供财务资助": AssociateFinancialSupport,
            "0507 向关联人委托贷款": AssociatesEntrustLoan,
            "0801 预盈": PerformanceForecastCorrection,
            "0803 预亏": PerformanceForecastCorrection,
            "0804 业绩大幅提升": PerformanceForecastCorrection,
            "0805 业绩大幅下降": PerformanceForecastCorrection,
            "0809 业绩预告更正": PerformanceForecastCorrection,
            "2106 股权激励计划股份回购开始": EquityIncentivePlanShareRepurchase,
            "0402 出售资产": SellAssets,
            "0601 年度担保预计": AnnualGuarantee,
            "0503 向关联人购买资产": PurchaseRelatedAssetsPredictor,
            "0504 向关联人出售资产": SaleRelatedAssetsPredictor,
            "0505 与关联人共同投资": InvestWithAssociates,
            "0506 向关联人委托理财": AssociatesEntrustInvestment,
            "0602 为控股子公司提供担保": GuaranteeSubsidiary,
            "0501 日常关联交易": DailyConnectedTransaction,
            "2105 股权激励计划终止": QuityIncentiveTermination,
            "2108 股权激励计划授予": ShareIncentiveGrant,
            "1906 可转债付息": ConvertibleDebtPayment,
            "0901 实施利润分配和资本公积金转增": ProfitDistribution,
            "1921 可转债募集说明书摘要": ConvertibleDebtProspectus,
            "0702 超募资金/结余募集资金的使用（KCB数据）": RaiseFundsUsage,
            "0705 用募集资金置换预先投入的自筹资金（KCB数据）": RaiseFundsReplacement,
            "0708 募集资金存放与使用情况报告": RaiseFundsReport,
            "0709 前次募集资金使用情况报告": LastRaiseFunds,
            "0426 与私募基金合作投资": CooperationInvestment,
            "上交所合规检查POC2": SSEPoc,
        }
        if predictor := (enum_classes.get(self._mold.name) or enum_classes.get(clean_txt(self._mold.name))):
            return predictor()
