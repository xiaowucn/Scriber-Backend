from collections import defaultdict

import attr

from remarkable.answer.node import AnswerNode
from remarkable.common.constants import ComplianceStatus
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.pw_models.model import NewFileMeta
from remarkable.rule.common import get_xpath
from remarkable.rule.rule import InspectItem, Rule


class FieldCompliance(Rule):
    def check(
        self, answer: AnswerNode, pdfinsight: PdfinsightReader, meta: defaultdict[str, list[NewFileMeta]]
    ) -> list[InspectItem]:
        ret = []
        checkers = [
            RiskLevelCheck("风险登记描述"),
        ]
        for checker in checkers:
            plain_texts = []
            schema_cols = []
            x_paths = []
            schema_answer = answer[checker.column]
            for item in schema_answer.values():
                schema_cols.append(item.data["key"])
                for data_item in item.data.data:
                    for box in data_item["boxes"]:
                        box_text = data_item.get("text")
                        if box_text:
                            plain_texts.append(data_item["text"])
                        else:
                            plain_texts.append(box["text"])
                        x_paths.extend(get_xpath(pdfinsight, box=box))

            inspect_item = checker.check(schema_cols, plain_texts, x_paths)
            ret.append(inspect_item)
        return ret


@attr.s
class ComplianceCheckBase:
    column: str = attr.ib()

    def check(self, schema_cols, plain_texts, x_paths):
        raise NotImplementedError


class RiskLevelCheck(ComplianceCheckBase):
    risk_map = {
        "R1": ["C1", "C2", "C3", "C4", "C5"],
        "R2": ["C2", "C3", "C4", "C5"],
        "R3": ["C3", "C4", "C5"],
        "R4": ["C4", "C5"],
        "R5": ["C5"],
    }
    RISK_PATTERNS = PatternCollection([r"(?P<dst>R[1-5])"])
    TOLERANCE_PATTERNS = PatternCollection([r"(?P<dst>C[1-5])"])

    @staticmethod
    def clean_box_texts(box_text):
        return clean_txt(box_text)

    def get_risk_level(self, plain_texts):
        risk_level = None
        for text in plain_texts:
            if self.RISK_PATTERNS.nexts(text):
                risk_level = text
                break
        return risk_level

    def get_tolerance_level(self, plain_texts):
        tolerance_levels = []
        for text in plain_texts:
            matchers = self.TOLERANCE_PATTERNS.finditer(text)
            for matcher in matchers:
                if not matcher:
                    continue
                tolerance_levels.append(matcher.group("dst"))
        return tolerance_levels

    def check(self, schema_cols, plain_texts, x_paths):
        clean_texts = {self.clean_box_texts(i) for i in plain_texts}
        risk_level = self.get_risk_level(clean_texts)
        tolerance_levels = self.get_tolerance_level(clean_texts)
        tolerances = self.risk_map.get(risk_level, [])
        compare_result = all(i in tolerances for i in tolerance_levels)
        check_results = ComplianceStatus.COMPLIANCE if compare_result == 1 else ComplianceStatus.NONCOMPLIANCE
        comment = "风险等级合规" if compare_result == 1 else "风险等级不合规"
        detail = {
            "comment_detail": [
                f"本基金产品风险等级为{risk_level}，适合风险承受能力等级为{'、'.join(tolerance_levels)}的合格投资者"
            ],
        }
        head = InspectItem.new(
            schema_cols=schema_cols,
            result=check_results,
            comment=comment,
            second_rule=self.column,
            detail=detail,
            comment_pos={"xpath": x_paths},
        )
        return head
