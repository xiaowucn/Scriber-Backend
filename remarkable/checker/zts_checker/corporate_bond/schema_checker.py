import dataclasses
import logging
from dataclasses import dataclass

from remarkable.checker.answers import Answer
from remarkable.checker.base import BaseChecker
from remarkable.checker.zts_checker.utils import get_number_value, get_schema_result, percentage_to_float
from remarkable.common.constants import ZTS_DOC_TYPES_SEMI, ZTSDocType
from remarkable.converter.szse.cyb_conv import AnswerNodeCalculator
from remarkable.plugins.cgs.schemas.reasons import ResultItem

logger = logging.getLogger(__name__)


@dataclass
class CheckField:
    field: str
    doc_type: str
    multi: bool = False
    answers: list[Answer] = dataclasses.field(default_factory=list)

    @property
    def first_answer(self):
        if self.answers:
            return self.answers[0]
        return None


class CorporateBondChecker(BaseChecker):
    SCHEMA_NAME = ""  # 深交所企业债/上交所企业债 两个schema共用
    NAME = ""
    LABEL = ""
    RELATED_NAME = ""

    def __init__(self, reader, file, manager, mold=None, labels=None, doc_types=None, answer_reader=None):
        super().__init__(reader, file, manager, mold.id, labels, answer_reader)
        self.mold = mold
        self.doc_types = doc_types

    @property
    def latest_doc_type(self):
        """
        最新的文档类型: 本期年报 or 本期半年报
        :return:
        """
        if self.doc_types == ZTS_DOC_TYPES_SEMI:
            return ZTSDocType.SEMI.value
        return ZTSDocType.ANNUAL.value

    def fill_answer(self, check_field: CheckField) -> CheckField:
        check_field.answers = []  # 避免读到旧的answers
        if check_field.multi:
            answers = self.manager[check_field.doc_type].get_multi(check_field.field)
            check_field.answers = answers
        else:
            answer = self.manager[check_field.doc_type].get(check_field.field)
            if answer and answer.value:
                check_field.answers = [answer]
        return check_field

    def get_schema_results(self, check_field: CheckField, answer: Answer, include_peers: bool = False) -> list[dict]:
        schema_results = [get_schema_result(self.mold.name, check_field.doc_type, check_field.field, answer)]
        if include_peers:
            peers = self.manager[check_field.doc_type].get_peers(answer)
            for peer in peers:
                schema_results.append(get_schema_result(self.mold.name, check_field.doc_type, peer.name, peer))
        return schema_results

    def simple_formula_check(self):
        results = []
        if self.latest_doc_type not in self.SCHEMA_FIELDS:
            return results
        schema_fields = self.SCHEMA_FIELDS[self.latest_doc_type]

        is_compliance = False
        schema_results = []
        all_node_valid = True
        formula_check_fields = {}
        formula_ret = None
        for node, check_field in schema_fields.items():
            self.fill_answer(check_field)
            formula_check_fields[node] = check_field
            include_peers = "-" in check_field.field
            schema_results.extend(self.get_schema_results(check_field, check_field.first_answer, include_peers))

            if not check_field.answers:
                all_node_valid = False

        if all_node_valid:
            formula_list = []
            for item in self.FORMULA:
                if AnswerNodeCalculator.is_operator(item):
                    formula_list.append(item)
                else:
                    formula_check_field = formula_check_fields[item]
                    formula_list.append(get_number_value(formula_check_field.first_answer.value))
            formula_ret = AnswerNodeCalculator.calc(formula_list)
            try:
                is_compliance = percentage_to_float(formula_ret) <= self.THRESHOLD
            except Exception as exp:
                logger.exception(exp)

        result = ResultItem(
            name=self.NAME,
            related_name=self.RELATED_NAME,
            is_compliance=is_compliance,
            schema_id=self.schema_id,
            reasons={"formula_ret": formula_ret},
            label=self.LABEL,
            fid=self.file.id,
            schema_results=schema_results,
        )
        results.append(result)
        return results


class ConsistencyChecker(CorporateBondChecker):
    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/5737
    NAME = "一致性比对"

    def check(self):
        raise NotImplementedError


class ConsistencyCompareChecker(ConsistencyChecker):
    SCHEMA_FIELDS = ["信息披露负责人信息-姓名", "会计师事务所-会计师事务所名称"]

    def check(self):
        check_doc_types = (
            (ZTSDocType.SEMI.value, ZTSDocType.PREVIOUS_ANNUAL.value)
            if self.doc_types == ZTS_DOC_TYPES_SEMI
            else (ZTSDocType.ANNUAL.value, ZTSDocType.PREVIOUS_ANNUAL.value)
        )

        results = []
        for field in self.SCHEMA_FIELDS:
            if self.doc_types == ZTS_DOC_TYPES_SEMI and field == "会计师事务所-会计师事务所名称":
                continue

            check_field_0 = self.fill_answer(CheckField(field, check_doc_types[0]))
            check_field_1 = self.fill_answer(CheckField(field, check_doc_types[1]))
            answer_0 = check_field_0.first_answer
            answer_1 = check_field_1.first_answer
            is_compliance = False
            if answer_0 and answer_1:
                is_compliance = answer_0.value == answer_1.value
            result = ResultItem(
                name=self.NAME,
                related_name=self.RELATED_NAME,
                is_compliance=is_compliance,
                schema_id=self.schema_id,
                reasons=[],
                label=field,
                fid=self.file.id,
                schema_results=[
                    *self.get_schema_results(check_field_0, answer_0),
                    *self.get_schema_results(check_field_1, answer_1),
                ],
            )
            results.append(result)
        return results


class RestrictedFundsChecker(CorporateBondChecker):
    NAME = "资产受限"

    def check(self):  # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/5732
        raise NotImplementedError


class RestrictedFundsFormula1Checker(RestrictedFundsChecker):
    LABEL = "公式1.1"
    FORMULA = "单项资产受限-受限金额 / 所有者权益金额"
    THRESHOLD = 0.1
    SCHEMA_FIELDS = {
        "本期年报": [
            CheckField("单项资产受限", ZTSDocType.ANNUAL.value, multi=True),
            CheckField("所有者权益金额", ZTSDocType.PREVIOUS_ANNUAL.value),
        ],
        "本期半年报": [
            CheckField("单项资产受限", ZTSDocType.SEMI.value, multi=True),
            CheckField("所有者权益金额", ZTSDocType.PREVIOUS_ANNUAL.value),
        ],
    }

    def check(self):
        results = []
        schema_fields = self.SCHEMA_FIELDS[self.latest_doc_type]
        restricted_assets = schema_fields[0]
        answer_nodes = self.answer_reader[restricted_assets.doc_type].find_nodes([restricted_assets.field])
        restricted_assets.answers = sorted(answer_nodes, key=lambda x: x.idx)
        owner_equity = self.fill_answer(schema_fields[1])
        if not restricted_assets.answers:
            schema_results = []
            for answer in owner_equity.answers:
                schema_results.extend(self.get_schema_results(owner_equity, answer))

            schema_results.append(
                get_schema_result(self.mold.name, restricted_assets.doc_type, "单项资产受限-受限金额", None)
            )
            schema_results.append(
                get_schema_result(self.mold.name, restricted_assets.doc_type, "单项资产受限-受限资产类别", None)
            )

            result = ResultItem(
                name=self.NAME,
                related_name=self.RELATED_NAME,
                is_compliance=None,
                schema_id=self.schema_id,
                reasons={"formula_ret": None},
                label=self.LABEL,
                fid=self.file.id,
                schema_results=schema_results,
            )
            results.append(result)
            return results
        owner_equity_answer = owner_equity.first_answer
        for restricted_assets_answer in restricted_assets.answers:
            is_compliance = False
            schema_results = []
            schema_results.extend(self.get_schema_results(owner_equity, owner_equity_answer))
            restricted_assets_value = None
            for _, node in restricted_assets_answer.items():
                answer = Answer(node.data.to_dict(), None, None)
                field = node.namepath.replace("_", "-")
                schema_results.append(get_schema_result(self.mold.name, restricted_assets.doc_type, field, answer))
                if node.name == "受限金额":
                    restricted_assets_value = get_number_value(node.data.plain_text)

            owner_equity_value = get_number_value(owner_equity_answer.value if owner_equity_answer else None)
            formula_list = [restricted_assets_value, "/", owner_equity_value]
            ret = AnswerNodeCalculator.calc(formula_list)
            try:
                is_compliance = percentage_to_float(ret) <= self.THRESHOLD
            except Exception as exp:
                logger.exception(exp)
            result = ResultItem(
                name=self.NAME,
                related_name=self.RELATED_NAME,
                is_compliance=is_compliance,
                schema_id=self.schema_id,
                reasons={"formula_ret": ret},
                label=self.LABEL,
                fid=self.file.id,
                schema_results=schema_results,
            )
            results.append(result)

        return results


class RestrictedFundsFormula2Checker(RestrictedFundsChecker):
    LABEL = "公式1.1"
    FORMULA = ["(", "资产受限金额合计3", "-", "资产受限金额合计1", ")", "/", "所有者权益金额"]
    THRESHOLD = 0.3
    SCHEMA_FIELDS = {
        "本期年报": {
            "资产受限金额合计3": CheckField("资产受限金额合计-受限金额", ZTSDocType.ANNUAL.value),
            "资产受限金额合计1": CheckField("资产受限金额合计-受限金额", ZTSDocType.PREVIOUS_ANNUAL.value),
            "所有者权益金额": CheckField("所有者权益金额", ZTSDocType.PREVIOUS_ANNUAL.value),
        },
        "本期半年报": {
            "资产受限金额合计3": CheckField("资产受限金额合计-受限金额", ZTSDocType.SEMI.value),
            "资产受限金额合计1": CheckField("资产受限金额合计-受限金额", ZTSDocType.PREVIOUS_ANNUAL.value),
            "所有者权益金额": CheckField("所有者权益金额", ZTSDocType.PREVIOUS_ANNUAL.value),
        },
    }

    def check(self):
        return self.simple_formula_check()


class BorrowingChecker(CorporateBondChecker):
    NAME = "新增借款"

    def check(self):  # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/5735
        raise NotImplementedError


class BorrowingFundsFormula1Checker(BorrowingChecker):
    LABEL = "公式2.1"
    FORMULA = ["(", "报告期末有息债务余额2", "-", "报告期末有息债务余额1", ")", "/", "所有者权益金额"]
    THRESHOLD = 0.5
    SCHEMA_FIELDS = {
        "本期年报": {
            "报告期末有息债务余额2": CheckField("报告期末有息债务余额", ZTSDocType.ANNUAL.value),
            "报告期末有息债务余额1": CheckField("报告期末有息债务余额", ZTSDocType.PREVIOUS_ANNUAL.value),
            "所有者权益金额": CheckField("所有者权益金额", ZTSDocType.PREVIOUS_ANNUAL.value),
        },
        "本期半年报": {
            "报告期末有息债务余额2": CheckField("报告期末有息债务余额", ZTSDocType.SEMI.value),
            "报告期末有息债务余额1": CheckField("报告期末有息债务余额", ZTSDocType.PREVIOUS_ANNUAL.value),
            "所有者权益金额": CheckField("所有者权益金额", ZTSDocType.PREVIOUS_ANNUAL.value),
        },
    }

    def check(self):
        return self.simple_formula_check()


class BorrowingFundsFormula2Checker(BorrowingChecker):
    LABEL = "公式2.2"
    FORMULA = ["(", "报告期末有息债务余额2", "-", "报告期初有息债务余额", ")", "/", "所有者权益金额"]
    THRESHOLD = 0.5
    SCHEMA_FIELDS = {
        "本期年报": {
            "报告期末有息债务余额2": CheckField("报告期末有息债务余额", ZTSDocType.ANNUAL.value),
            "报告期初有息债务余额": CheckField("报告期初有息债务余额", ZTSDocType.ANNUAL.value),
            "所有者权益金额": CheckField("所有者权益金额", ZTSDocType.PREVIOUS_ANNUAL.value),
        },
        "本期半年报": {
            "报告期末有息债务余额2": CheckField("报告期末有息债务余额", ZTSDocType.SEMI.value),
            "报告期初有息债务余额": CheckField("报告期初有息债务余额", ZTSDocType.SEMI.value),
            "所有者权益金额": CheckField("所有者权益金额", ZTSDocType.PREVIOUS_ANNUAL.value),
        },
    }

    def check(self):
        return self.simple_formula_check()


class GuaranteeChecker(CorporateBondChecker):
    NAME = "对外担保"

    def check(self):  # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/5736
        raise NotImplementedError


class GuaranteeFormula1Checker(GuaranteeChecker):
    LABEL = "公式3.1"
    FORMULA = ["(", "报告期末对外担保余额2", "-", "报告期末对外担保余额1", ")", "/", "所有者权益金额"]
    THRESHOLD = 0.5
    SCHEMA_FIELDS = {
        "本期年报": {
            "报告期末对外担保余额2": CheckField("报告期末对外担保余额", ZTSDocType.ANNUAL.value),
            "报告期末对外担保余额1": CheckField("报告期末对外担保余额", ZTSDocType.PREVIOUS_ANNUAL.value),
            "所有者权益金额": CheckField("所有者权益金额", ZTSDocType.PREVIOUS_ANNUAL.value),
        },
        "本期半年报": {
            "报告期末对外担保余额2": CheckField("报告期末对外担保余额", ZTSDocType.SEMI.value),
            "报告期末对外担保余额1": CheckField("报告期末对外担保余额", ZTSDocType.PREVIOUS_ANNUAL.value),
            "所有者权益金额": CheckField("所有者权益金额", ZTSDocType.PREVIOUS_ANNUAL.value),
        },
    }

    def check(self):
        return self.simple_formula_check()


class GuaranteeFormula2Checker(GuaranteeChecker):
    LABEL = "公式3.2"
    FORMULA = ["(", "报告期末对外担保余额2", "-", "报告期初对外担保余额", ")", "/", "所有者权益金额"]
    THRESHOLD = 0.5
    SCHEMA_FIELDS = {
        "本期年报": {
            "报告期末对外担保余额2": CheckField("报告期末对外担保余额", ZTSDocType.ANNUAL.value),
            "报告期初对外担保余额": CheckField("报告期初对外担保余额", ZTSDocType.ANNUAL.value),
            "所有者权益金额": CheckField("所有者权益金额", ZTSDocType.PREVIOUS_ANNUAL.value),
        },
        "本期半年报": {
            "报告期末对外担保余额2": CheckField("报告期末对外担保余额", ZTSDocType.SEMI.value),
            "报告期初对外担保余额": CheckField("报告期初对外担保余额", ZTSDocType.SEMI.value),
            "所有者权益金额": CheckField("所有者权益金额", ZTSDocType.PREVIOUS_ANNUAL.value),
        },
    }

    def check(self):
        return self.simple_formula_check()
