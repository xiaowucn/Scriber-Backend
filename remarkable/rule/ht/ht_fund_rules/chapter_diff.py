from collections import defaultdict

from remarkable.answer.node import AnswerNode
from remarkable.common.constants import ComplianceStatus
from remarkable.common.diff.diff import DiffUtil
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.config import get_config
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.pw_models.model import NewFileMeta
from remarkable.rule.common import get_xpath
from remarkable.rule.ht.ht_fund_rules.common import FundChapterTemplate
from remarkable.rule.rule import InspectItem, Rule

TEMPLATE_PATTERNS = PatternCollection(
    [
        r"\{CS_.*?QC\}",
    ]
)


class ChapterDiff(Rule):
    def __init__(self, name="", custom_config=None, chapters=None):
        super(ChapterDiff, self).__init__(name, custom_config)
        self.chapters = chapters

    def check(
        self, answer: AnswerNode, pdfinsight: PdfinsightReader, meta: defaultdict[str, list[NewFileMeta]]
    ) -> list[InspectItem]:
        ret = []
        if not self.chapters:
            return ret
        checkers = [ChapterChecker(item) for item in self.chapters]
        for checker in checkers:
            inspect_item = checker.check(answer, pdfinsight, meta)
            ret.extend(inspect_item)
        return ret


class ChapterChecker(Rule):
    def check(
        self, answer: AnswerNode, pdfinsight: PdfinsightReader, meta: defaultdict[str, list[NewFileMeta]]
    ) -> list[InspectItem]:
        ret = []
        if self.custom_config:
            column = column_from_custom = self.custom_config["data"]["column"]
            if isinstance(column_from_custom, list):
                column = column_from_custom[-1]
            # 来源于网页端自行配置的模板
            patterns = self.custom_config["data"]["patterns"]
        else:
            column = self.name
            column_from_custom = ["章节对比", column]
            # 待比较的文本使用了合并答案中的plain text 这里将模板合并到一起 与待比较的文本保持一致
            # 开发人员编写的模板
            patterns = ["".join(FundChapterTemplate.get(column, []))]
        schema_cols, paras_from_doc, x_paths = self.get_schema_cols(pdfinsight, answer, column, column_from_custom)
        diff_util = DiffUtil(patterns, paras_from_doc)
        diff_result = diff_util.compare()
        if get_config("ht.ignore_template") and column == "释义":
            self.post_process_diff_result(diff_result)
        compare_result = diff_util.parse_diff_result(diff_result)
        check_results = ComplianceStatus.COMPLIANCE if compare_result == 1 else ComplianceStatus.NONCOMPLIANCE
        comment = "正确" if compare_result == 1 else "有误"
        label_info = "与模板内容一致" if compare_result == 1 else "与模板内容不一致"
        comment_pos = {}
        if x_paths:
            comment_pos = {"xpath": x_paths[:1]}
        detail = {
            "comment_detail": [comment],
            "diff_result": diff_result,
            "patterns": patterns,
            "label_info": label_info,
        }
        inspect_item = InspectItem.new(
            schema_cols=schema_cols,
            result=check_results,
            comment=comment,
            second_rule=column,
            detail=detail,
            comment_pos=comment_pos,
        )
        ret.append(inspect_item)
        return ret

    @staticmethod
    def get_schema_cols(pdfinsight, answer, column, column_from_custom):
        schema_cols = []
        paras_from_doc = []
        x_paths = []
        if column_from_custom and len(column_from_custom) == 2:
            schema_answer = answer[column_from_custom[0]]
            for item in schema_answer.values():
                for key, value in item.items():
                    if column != key[0]:
                        continue
                    schema_cols.append(value.data["key"])
                    # 有可能在界面直接修改标注答案，这里取界面plain_text 但这个是一大段，元素块之间没有分开，
                    # 可能对对比结果产生影响，暂时先使用这种形式
                    paras_from_doc.append(clean_txt(value.data.plain_text))
                    for index in value.relative_element_indexes:
                        _, ele = pdfinsight.find_element_by_index(index)
                        if not ele:
                            continue
                        if ele["class"] != "PARAGRAPH":
                            continue
                        # 从元素块中获取文本 对于对比来说 这里的文本是分段的 暂不使用这种形式
                        # paras_from_doc.append(clean_txt(ele['text']))
                        x_paths.extend(get_xpath(pdfinsight, ele=ele))
        else:
            schema_answer = answer.get(column, {})
            for item in schema_answer.values():
                schema_cols.append(item.data["key"])
                paras_from_doc.append(clean_txt(item.data.plain_text))
                for index in item.relative_element_indexes:
                    _, ele = pdfinsight.find_element_by_index(index)
                    if not ele:
                        continue
                    if ele["class"] != "PARAGRAPH":
                        continue
                    x_paths.extend(get_xpath(pdfinsight, ele=ele))
        return schema_cols, paras_from_doc, x_paths

    @staticmethod
    def post_process_diff_result(diff_result):
        ignore_idx = []
        items = diff_result[0]
        for idx, item in enumerate(items):
            if item["diff"] == "same":
                continue
            if item["diff"] == "lack" and TEMPLATE_PATTERNS.nexts(clean_txt(item["text"])):
                item["diff"] = "same"
                ignore_idx.append(idx)

        for idx in ignore_idx:
            if idx == len(items) - 1:
                break
            item = items[idx + 1]
            item["diff"] = "same"
