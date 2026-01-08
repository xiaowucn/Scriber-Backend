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


class FieldConsistency(Rule):
    def check(
        self, answer: AnswerNode, pdfinsight: PdfinsightReader, meta: defaultdict[str, list[NewFileMeta]]
    ) -> list[InspectItem]:
        ret = []
        checkers = [
            SimpleCheck("产品全称", pdfinsight),
            SimpleCheck("存续期限", pdfinsight),
            RemoveDecorateCheck("投资范围", pdfinsight),
            RemoveDecorateCheck("投资目标", pdfinsight),
            ContactInformationCheck("联系人电话", pdfinsight),
            ContactInformationCheck("联系人姓名", pdfinsight),
            ContactInformationCheck("联系人邮箱", pdfinsight),
        ]
        for checker in checkers:
            data_set = checker.prepare_dataset(answer)
            inspect_item = checker.check(data_set)
            ret.append(inspect_item)
        return ret


@attr.s
class ConsistencyCheckBase:
    column: str = attr.ib()
    pdfinsight: PdfinsightReader = attr.ib()

    def prepare_dataset(self, answer):
        plain_texts = []
        schema_cols = []
        x_paths = []
        schema_answer = answer[self.column]
        for item in schema_answer.values():
            schema_cols.append(item.data["key"])
            for data_item in item.data.data:
                box_text = data_item.get("text")
                if box_text:
                    plain_texts.append(data_item["text"])
                for box in data_item["boxes"]:
                    x_paths.extend(get_xpath(self.pdfinsight, box=box))
                    if not box_text:
                        plain_texts.append(box["text"])

        return {
            "schema_cols": schema_cols,
            "plain_texts": plain_texts,
            "x_paths": x_paths,
        }

    def check(self, data_set):
        raise NotImplementedError


class SimpleCheck(ConsistencyCheckBase):
    SPECIAL_WORDS = PatternCollection(
        [
            r"[\s【】（）\(\)。]",
        ]
    )

    def clean_box_texts(self, box_text):
        box_text = self.SPECIAL_WORDS.sub("", box_text)
        return clean_txt(box_text)

    def check(self, data_set):
        plain_texts = data_set["plain_texts"]
        clean_texts = {self.clean_box_texts(i) for i in plain_texts}
        compare_result = len(clean_texts)
        check_results = ComplianceStatus.COMPLIANCE if compare_result == 1 else ComplianceStatus.NONCOMPLIANCE
        comment = "与文档内其它位置一致" if compare_result == 1 else "与文档内其它位置不一致"
        detail = {
            "comment_detail": plain_texts,
        }
        head = InspectItem.new(
            schema_cols=data_set["schema_cols"],
            result=check_results,
            comment=comment,
            second_rule=self.column,
            detail=detail,
            comment_pos={"xpath": data_set["x_paths"]},
        )
        return head


class RemoveDecorateCheck(SimpleCheck):
    HEAD_PATTERN = PatternCollection(
        [
            r"^[（(]二[)）]\s?投资范围\s?：",
            r"^投资于\s?：",
            r"^[（(]一[)）]\s?投资目标\s?：",
        ]
    )

    TAIL_PATTERN = PatternCollection([r"本基金成立后备案完成前.*?货币市场基金等中国证监会认可的现金管理工具。$"])

    def clean_box_texts(self, box_text):
        box_text = self.HEAD_PATTERN.sub("", box_text)
        box_text = self.TAIL_PATTERN.sub("", box_text)
        return clean_txt(box_text)


class ContactInformationCheck(ConsistencyCheckBase):
    parent_col = "联系人（基本情况）"
    anthor_parent_col = "联系人（业务联系表）"

    def prepare_dataset(self, answer):
        plain_texts = []
        anthor_plain_texts = []
        schema_cols = []
        x_paths = []
        schema_answer = answer.get(self.parent_col, defaultval={})
        for item in schema_answer.values():
            for key, value in item.items():
                if self.column == key[0]:
                    schema_cols.append(value.data["key"])
                    for data_item in value.data.data:
                        box_text = data_item.get("text")
                        if box_text:
                            plain_texts.append(data_item["text"])
                        for box in data_item["boxes"]:
                            x_paths.extend(get_xpath(self.pdfinsight, box))
                            if not box_text:
                                plain_texts.append(clean_txt(box["text"]))

        schema_answer = answer.get(self.anthor_parent_col, defaultval={})
        for item in schema_answer.values():
            for key, value in item.items():
                if self.column == key[0]:
                    schema_cols.append(value.data["key"])
                    for data_item in value.data.data:
                        box_text = data_item.get("text")
                        if box_text:
                            anthor_plain_texts.append(data_item["text"])
                        for box in data_item["boxes"]:
                            x_paths.extend(get_xpath(self.pdfinsight, box))
                            if not box_text:
                                anthor_plain_texts.append(clean_txt(box["text"]))

        return {
            "schema_cols": schema_cols,
            "plain_texts": plain_texts,
            "anthor_plain_texts": anthor_plain_texts,
            "x_paths": x_paths,
        }

    def check(self, data_set):
        plain_texts = data_set["plain_texts"]
        anthor_plain_texts = data_set["anthor_plain_texts"]
        if plain_texts:
            compare_result = plain_texts[0] in set(anthor_plain_texts)
        else:
            compare_result = False
        check_results = ComplianceStatus.COMPLIANCE if compare_result == 1 else ComplianceStatus.NONCOMPLIANCE
        comment = "与文档内其它位置一致" if compare_result == 1 else "与文档内其它位置不一致"
        comment_detail = plain_texts + anthor_plain_texts
        if not anthor_plain_texts:
            comment_detail = plain_texts + ["未提取到结果"]
        detail = {
            "comment_detail": comment_detail,
        }
        head = InspectItem.new(
            schema_cols=data_set["schema_cols"],
            result=check_results,
            comment=comment,
            second_rule=self.column,
            detail=detail,
            comment_pos={"xpath": data_set["x_paths"]},
        )
        return head
