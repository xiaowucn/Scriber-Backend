import logging
import re
from collections import defaultdict
from enum import IntEnum, unique
from itertools import groupby

import attr

from remarkable.common.constants import SSEAuditStatus
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.plugins.predict.answer import AnswerNode
from remarkable.predictor.schema_answer import CharResult
from remarkable.pw_models.model import NewFileMeta
from remarkable.rule.rule import InspectItem, Rule, revise_answer


def revise_amount(second_rule: str, answer):
    res_item = InspectItem.new(second_rule=second_rule, position={"data": answer.data.get("data", [])})
    # 币种: 人民币|数值: 10,000.00|单位: 万元 -> 10,000.00万元
    res_item.comment = "".join([t.split(":")[-1].strip() for t in answer.data.plain_text.split("|")[1:]])
    return res_item


@unique
class InfoType(IntEnum):
    STATEMENT = 1  # 报表注释
    SEGMENT = 2  # 分部信息


@attr.s
class IncomeItem:
    name: InspectItem = attr.ib()
    income: InspectItem = attr.ib()
    src: int = attr.ib()


class MainBusiness(Rule):
    total_operating_income = None  # 营业收入合计
    businesses = defaultdict(InspectItem)  # 主营业务概览
    business_detail: dict[str, IncomeItem] = {}  # 主营业务详情

    def clean_cache(self):
        self.businesses = defaultdict(InspectItem)
        self.business_detail = {}

    def is_in(self, item):
        item_text = clean_txt(item.name.comment)
        for text in self.businesses:
            if text in item_text or item_text in text:
                return True
        return False

    def load_answer(self, answer: AnswerNode):
        self.clean_cache()
        self.total_operating_income = (
            revise_amount("营业收入", revise_answer(answer["营业收入"])) if "营业收入" in answer else None
        )
        for path in "主营业务-分行业", "主营业务-分产品":
            if path not in answer:
                continue
            for node in [n for _, n in answer[path].items() if not n.isleaf()]:
                for key in ("行业", "产品"):
                    if key in node:
                        ans = revise_answer(node[key])
                        if not clean_txt(ans.data.plain_text):
                            continue
                        self.businesses.setdefault(
                            clean_txt(ans.data.plain_text),
                            InspectItem.new(
                                position={"data": ans.data.get("data", [])},
                                second_rule=ans.name,
                                comment=ans.data.plain_text,
                            ),
                        )

        attr_amount_map = {
            "营业收入-主营业务": "主营业务收入金额",
            "营业收入-其他业务收入": "其他业务收入金额",
            "营业收入-所有细分业务收入": "细分业务收入金额",
            "附注-分部信息": "分部业务收入金额",
        }
        for _attr, amount in attr_amount_map.items():
            if _attr not in answer:
                continue
            for node in [n for _, n in answer[_attr].items() if not n.isleaf()]:
                if "业务名称" not in node or amount not in node:
                    continue
                item = revise_answer(node["业务名称"])
                if not clean_txt(item.data.plain_text):
                    continue
                income = revise_amount("收入", revise_answer(node[amount]))
                if income.amount == 0:
                    # 跳过零收入(单元格无内容)
                    continue
                self.business_detail.setdefault(
                    item.data.plain_text,
                    IncomeItem(
                        InspectItem.new(
                            position={"data": item.data.get("data", [])},
                            second_rule=item.name,
                            comment=item.data.plain_text,
                        ),
                        income,
                        InfoType.SEGMENT if _attr.endswith("分部信息") else InfoType.STATEMENT,
                    ),
                )

    def check(
        self, answer: AnswerNode, pdfinsight: PdfinsightReader, meta: defaultdict[str, list[NewFileMeta]]
    ) -> list[InspectItem]:
        self.load_answer(answer)
        ret = InspectItem.new(result=SSEAuditStatus.COMP_0, second_rule="经营情况与财务报告披露一致", comment="合规")
        cond_item = InspectItem.new(second_rule="经营情况-主营业务", comment="")
        income_item = InspectItem.new(second_rule="财务报表-业务收入", comment="")
        statement_item = InspectItem.new(second_rule="财务报表-报表注释", comment="")
        segment_item = InspectItem.new(second_rule="分部-财务信息", comment="")
        if self.total_operating_income:
            income_item.comment = ""
            income_item.detail["sub_cols"].append(
                InspectItem.new(
                    result=SSEAuditStatus.COMP_0,
                    position=self.total_operating_income.detail["position"],
                    comment=self.total_operating_income.comment,
                    second_rule="营业收入",
                )
            )
            income_item.detail["position"] = self.total_operating_income.detail["position"]
        else:
            logging.error("!!!未提取到营业收入, 请检查提取逻辑!!!")

        for item in self.business_detail.values():
            sub_item = InspectItem.new(
                result=SSEAuditStatus.COMP_0,
                position=item.income.detail["position"],
                comment=item.income.comment,
                second_rule=item.name.comment,
            )
            if self.total_operating_income:
                percentage = item.income.amount / self.total_operating_income.amount
                if item.src == InfoType.STATEMENT and percentage > 0.1 and not self.is_in(item):
                    # 占比高于10%但没有披露为"主营业务"的, 不合规
                    sub_item.result = ret.result = SSEAuditStatus.NON_COMP_0
                    statement_item.detail["extra_cols"].append(item.name.comment)
                    ret.second_rule = "经营情况与财务报告披露不一致"
                    ret.comment = "不合规"
                if item.src == InfoType.SEGMENT and percentage > 0.1:
                    # 分部信息不参与经营情况的比较, 仅高亮超过10%的项目
                    sub_item.result = SSEAuditStatus.NON_COMP_1
                sub_item.detail["percentage"] = round(percentage * 100, 2).to_eng_string() + "%"
            else:
                ret.result = SSEAuditStatus.UNCERTAIN
                ret.second_rule = "未能提取到营业收入"
                ret.comment = "待分析"
                sub_item.detail["percentage"] = "-"
            if item.src == InfoType.STATEMENT:
                statement_item.detail["sub_cols"].append(sub_item)
            else:
                segment_item.detail["sub_cols"].append(sub_item)
                segment_item.comment = ""

        if statement_item.detail["extra_cols"]:
            statement_item.comment = "、".join(statement_item.detail["extra_cols"]) + "未在经营情况披露"
            statement_item.detail.pop("extra_cols")

        for key, group in groupby(self.businesses.values(), key=lambda x: x.second_rule):
            for idx, item in enumerate(group, 1):
                cond_item.detail["sub_cols"].append(
                    InspectItem.new(
                        position=item.detail["position"],
                        comment=item.comment,
                        second_rule=f"分{key}{idx}",
                    )
                )

        if not self.business_detail:
            ret.result = SSEAuditStatus.NON_COMP_2
            ret.second_rule = "财务注释与分部均未详细披露"
            ret.comment = "不合规"
        elif not statement_item.detail["sub_cols"] and segment_item.detail["sub_cols"]:
            # 未披露财务注释但披露了分部财务信息
            ret.result = SSEAuditStatus.UNCERTAIN
            ret.second_rule = "披露分部财务信息，需进一步分析"
            ret.comment = "待分析"

        # 默认定位到第一个子项目位置
        if statement_item.detail["sub_cols"] and statement_item.detail["sub_cols"][0].detail["position"]:
            statement_item.detail["position"] = statement_item.detail["sub_cols"][0].detail["position"]
        if segment_item.detail["sub_cols"] and segment_item.detail["sub_cols"][0].detail["position"]:
            segment_item.detail["position"] = segment_item.detail["sub_cols"][0].detail["position"]
        if cond_item.detail["sub_cols"] and cond_item.detail["sub_cols"][0].detail["position"]:
            cond_item.detail["position"] = cond_item.detail["sub_cols"][0].detail["position"]

        if not income_item.detail["sub_cols"]:
            income_item.comment = "业务收入未披露"
        if not statement_item.detail["sub_cols"]:
            statement_item.comment = "报表注释未披露"
            statement_item.detail["position"] = self.get_syl_pos(
                pdfinsight, [re.compile("营业收入和营业成本")], "报表注释"
            )
        if not segment_item.detail["sub_cols"]:
            segment_item.comment = "分部财务信息未披露"
            segment_item.detail["position"] = self.get_syl_pos(
                pdfinsight, [re.compile("报告分部的财务信息")], "分部财务信息"
            )

        return [ret, cond_item, income_item, statement_item, segment_item]

    @classmethod
    def get_syl_pos(cls, pdfinsight, patterns, label):
        pos = {}
        syllabuses = pdfinsight.find_sylls_by_pattern(patterns, clean_func=clear_syl_title)
        if not syllabuses:
            return pos
        aimed_item = syllabuses[0]
        _, elt = pdfinsight.find_element_by_index(aimed_item["element"])
        pos["data"] = [CharResult(elt, elt["chars"]).to_answer()]
        pos["label"] = label
        return pos
