import logging
import re
from collections import defaultdict
from copy import deepcopy
from itertools import chain
from typing import Generator

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.predictor.fullgoal_predictor.models.product_abb import get_depend_predictors
from remarkable.predictor.models.partial_text import PartialText
from remarkable.predictor.schema_answer import PredictorResult

logger = logging.getLogger(__name__)

P_TITLE_PATTERN = PatternCollection(r"(?P<dst>[A-Z][类级]?((份额)?(基金)?(份额)?)?)$")
P_SPLIT_PUNCTUATION = PatternCollection(
    [
        r"。",
        r"[;；]",
        r"[，,]",
    ]
)


class Subscription(PartialText):
    def train(self, dataset, **kwargs):
        pass

    @property
    def splits(self):
        return PatternCollection(self.get_config("splits", [r"[。；;](?![）)])"]))

    @property
    def skip_syllabus(self):
        return self.get_config("skip_syllabus", False)

    @property
    def split_punctuation(self):
        return PatternCollection(
            self.get_config("split_punctuation", [r"。", r"[;；]", r"[，,]投资者通过", r"[，,](?!\d)"])
        )

    @property
    def para_regs(self):
        return PatternCollection(self.get_config("para_regs", []))

    @property
    def neglect_patterns(self):
        return PatternCollection(self.get_config("neglect_patterns", []))

    @property
    def main_column(self):
        return self.get_config("main_column", "")

    @property
    def main_column_regs(self):
        if self.main_column:
            return PatternCollection(self.get_config("regs", [], self.main_column))
        return PatternCollection([])

    @property
    def need_distinct(self) -> bool:
        """是否需要对答案去重"""
        return self.get_config("need_distinct", False)

    @property
    def bracket_regs(self):
        return PatternCollection(r"[（(]")

    @property
    def bracket_content_regs(self):
        return PatternCollection(self.get_config("bracket_content_regs", []))

    @property
    def parallel_connectors(self):
        # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/9465?projectId=6&treeId=16&fileId=326&schemaId=5&schemaKey=%E5%8D%95%E7%AC%94%E8%AE%A4%E8%B4%AD%E4%B8%8B%E9%99%90
        return PatternCollection(self.get_config("parallel_connectors", [r"(或|与|及|以及|或者|也可以)(?!其整数倍)"]))

    def get_paragraph_text_chars(self, element, exclude_indices):
        if element["index"] in exclude_indices:
            return "", []
        chars = []
        if page_merged_paragraph := element.get("page_merged_paragraph"):
            if indices := page_merged_paragraph["paragraph_indices"]:
                exclude_indices.update(indices)
            paragraph_text = page_merged_paragraph.get("text")
            for index in indices:
                _, elt = self.pdfinsight.find_element_by_index(index)
                chars.extend(elt.get("chars", []))
        else:
            paragraph_text = element.get("text")
            chars = element.get("chars", [])

        paragraph_text = self.mosaic_text(paragraph_text)

        return paragraph_text, chars

    def mosaic_text(self, paragraph_text):
        # 抹去某些字符
        patterns = [
            re.compile(r"(?P<dst>（通过本基金管理人基金网上交易系统等特定交易方式申购本基金暂不受此限制）)"),
            re.compile(r"基金管理人(?P<dst>调整A类、B类基金份额最低申购金额)，将本基金A类基金份额单笔最低"),
            re.compile(r"(?P<dst>（含申购费.下同）)"),
        ]
        for pattern in patterns:
            if match := pattern.search(paragraph_text):
                paragraph_text = self.replace_multiple_named_groups_with_stars(
                    pattern, paragraph_text, match.groupdict()
                )
                break

        return paragraph_text

    @staticmethod
    def replace_multiple_named_groups_with_stars(pattern, text, group_names):
        """
        将正则表达式中多个指定命名分组匹配的内容替换为等长的星号(*)
        """

        def replace_callback(match):
            # 获取整个匹配的字符串
            full_match = match.group(0)

            # 收集每个分组的位置和替换后的字符串
            replacements = []
            for group_name in group_names:
                group_content = match.group(group_name)
                if group_content is not None:
                    start = match.start(group_name) - match.start(0)  # 相对于整个匹配的起始位置
                    end = match.end(group_name) - match.start(0)
                    stars = "*" * len(group_content)
                    replacements.append((start, end, stars))

            # 按照从后往前的顺序替换，这样前面的位置不会受到影响
            replacements.sort(key=lambda x: x[0], reverse=True)
            result = full_match
            for start, end, stars in replacements:
                result = result[:start] + stars + result[end:]

            return result

        return re.sub(pattern, replace_callback, text)

    def matchers_deduplication(self, match_results, column):
        fix_match_results = []
        for matcher in match_results:
            # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/11197?projectId=36&treeId=59&fileId=903&schemaId=2
            if not (value := matcher.group()):
                continue
            # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/9471?projectId=6&treeId=16&fileId=320&schemaId=5
            if any(i for i in ["不受直销", "如果销售机构", "各场外"] if i in value):
                continue

            if neglect_answer_patterns := self.get_config("neglect_answer_patterns", column=column):
                if PatternCollection(neglect_answer_patterns).nexts(clean_txt(value)):
                    continue

            if not fix_match_results:
                fix_match_results.append(matcher)
                continue
            is_find = False
            for fix_matcher in fix_match_results:
                if (
                    matcher.span("dst")[0] >= fix_matcher.span("dst")[0]
                    and matcher.span("dst")[0] <= fix_matcher.span("dst")[1]
                ) or (
                    matcher.span("dst")[1] >= fix_matcher.span("dst")[0]
                    and matcher.span("dst")[1] <= fix_matcher.span("dst")[1]
                ):
                    is_find = True
                    break
            if not is_find:
                fix_match_results.append(matcher)

        return fix_match_results

    def filter_parallel_phrases(self, parallel_results):
        """
        过滤并列短语，只保留每个并列组中的第一个匹配项。
        :param parallel_results: List of matcher objects
        :return: Filtered list of matcher objects
        """
        if not parallel_results:
            return parallel_results
        filtered_results = []
        processed_spans = []
        for matcher in parallel_results:
            current_span = matcher.span("dst")
            # 如果是第一个结果，直接添加
            if not filtered_results:
                filtered_results.append(matcher)
                processed_spans.append(current_span)
                continue

            # 检查是否与已有结果构成并列关系
            is_parallel = False
            for processed_span in processed_spans:
                end_pos = max(current_span[0], processed_span[0])
                start_pos = min(current_span[1], processed_span[1])
                # 判断位置是否接近（假设距离小于 50 个字符）
                if end_pos - start_pos < 50:
                    # 检查两个匹配之间的文本是否包含并列连接词
                    between_text = matcher.string[start_pos:end_pos]
                    if self.parallel_connectors.nexts(between_text):
                        is_parallel = True
                        logging.info(f"{between_text} exists parallel phrases")
                        break

            # 如果不是并列关系，添加到结果中
            if not is_parallel:
                filtered_results.append(matcher)
                processed_spans.append(current_span)

        return filtered_results

    def gen_column_result(self, element, chars, paragraph_text, match_result, column) -> list[PredictorResult]:
        column_result = []
        if match_result:
            value = match_result.groupdict().get("dst", None)
            dst_chars = self.get_chars(paragraph_text, value, chars, match_result.span("dst"))
            split_pattern = self.get_config("split_pattern", column=column)
            element_results = self.create_content_result(element, dst_chars, split_pattern)
            for element_result in element_results:
                column_result.append(self.create_result([element_result], column=column))

        return column_result

    def gen_depend_answers(self, predictors) -> Generator[PredictorResult, None, None]:
        for predictor in predictors:
            if predictor.answer_groups:
                for answers in predictor.answer_groups.values():
                    for answer in answers:
                        yield answer
            else:
                elements = self.predictor.get_candidate_elements(predictor.schema.path[1:])
                for answers in predictor.predict_answer_from_models(elements) or []:
                    for answer in (a for ans in answers.values() for a in ans):
                        yield answer

    def extract_by_column(self, element, paragraph_text, chars, fund_name_result, main_column_result):
        start_index = 0
        group_answers = []

        for match in chain(self.splits.finditer(paragraph_text), (None,)):
            start, end = match.span() if match else (len(paragraph_text), 0)
            if not (sub_text := paragraph_text[start_index:start]):
                start_index = end
                continue
            if self.neglect_patterns and self.neglect_patterns.nexts(clean_txt(sub_text)):
                start_index = end
                continue
            if self.para_regs and not self.para_regs.nexts(clean_txt(sub_text)):
                start_index = end
                continue
            sub_chars = chars[start_index:start]
            answer = defaultdict(list)
            for column in self.columns:
                if column == "基金名称" and fund_name_result:
                    answer[column].append(deepcopy(fund_name_result))
                    continue
                if column == self.main_column and all(main_column_result):
                    answer[column].append(deepcopy(main_column_result))
                    continue
                if not (regex_pattern := PatternCollection(self.get_config("regs", [], column))):
                    continue
                column_matchers = self.matchers_deduplication(regex_pattern.finditer(clean_txt(sub_text)), column)
                for column_matcher in column_matchers:
                    value = column_matcher.groupdict().get("dst", None)
                    if neglect_answer_patterns := self.get_config("neglect_answer_patterns", {}).get(column):
                        if PatternCollection(neglect_answer_patterns).nexts(value):
                            continue
                    dst_chars = self.get_chars(sub_text, value, sub_chars, column_matcher.span("dst"))
                    answer[column].append(
                        [
                            self.create_result(
                                self.create_content_result(element, dst_chars, None),
                                column=column,
                            )
                        ]
                    )
                    if not self.get_config("multi_config", False, column) or fund_name_result:
                        break
                    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/6738
                    duplication = self.get_config("duplication", False, column)
                    if duplication:
                        if PatternCollection(duplication).nexts(column_matcher.group(0)):
                            answer[column].append(deepcopy(answer[column][-1]))
            if answer:
                for index in range(max(len(results) for results in answer.values())):
                    result = {}
                    for column, answer_results in answer.items():
                        if len(answer_results) > index:
                            result[column] = answer_results[index]
                        elif answer_results:
                            result[column] = deepcopy(answer_results[-1])
                    group_answers.append(result)
            start_index = end
        return group_answers

    def _split_paragraph_generic(
        self, element, split_pattern_index, paragraph_text, chars, fund_name_result, pattern, recursive_split_func
    ):
        group_answers = []
        start_index = 0
        for match in chain(pattern.finditer(paragraph_text), (None,)):
            start, end = match.span() if match else (len(paragraph_text), 0)
            if not (sub_text := paragraph_text[start_index:start]):
                start_index = end
                continue

            clean_text = clean_txt(sub_text)
            if self._should_skip_text(clean_text):
                start_index = end
                continue

            sub_chars = chars[start_index:start]
            match_results = self.matchers_deduplication(self.main_column_regs.finditer(clean_text), self.main_column)
            match_results = self.filter_parallel_phrases(match_results)

            if len(match_results) >= 2 and self.bracket_content_regs and self.bracket_content_regs.nexts(clean_text):
                group_answers.extend(recursive_split_func(element, sub_text, sub_chars, fund_name_result))
            elif len(match_results) <= 1 or split_pattern_index == len(self.split_punctuation.pattern_objects) - 1:
                main_column_result = self._get_main_column_result(element, sub_chars, sub_text, match_results)
                group_answers.extend(
                    self.extract_by_column(element, sub_text, sub_chars, fund_name_result, main_column_result)
                )
            else:
                group_answers.extend(
                    self.split_paragraph(element, split_pattern_index + 1, sub_text, sub_chars, fund_name_result)
                )

            start_index = end

        return group_answers

    def _should_skip_text(self, clean_text):
        return (self.neglect_patterns and self.neglect_patterns.nexts(clean_text)) or (
            self.para_regs and not self.para_regs.nexts(clean_text)
        )

    def _get_main_column_result(self, element, sub_chars, sub_text, match_results) -> list:
        if len(match_results) >= 1:
            return self.gen_column_result(element, sub_chars, sub_text, match_results[0], self.main_column)
        return [None]

    def split_paragraph(self, element, split_pattern_index, paragraph_text, chars, fund_name_result):
        return self._split_paragraph_generic(
            element,
            split_pattern_index,
            paragraph_text,
            chars,
            fund_name_result,
            self.split_punctuation.pattern_objects[split_pattern_index],
            self.split_paragraph_with_bracket,
        )

    def split_paragraph_with_bracket(self, element, paragraph_text, chars, fund_name_result):
        return self._split_paragraph_generic(
            element,
            0,  # Reset split pattern index for recursive calls
            paragraph_text,
            chars,
            fund_name_result,
            self.bracket_regs,
            self.split_paragraph_with_bracket,
        )

    def gen_group_answers(self, element, paragraph_text, chars, fund_name_result=None):
        group_answers = []
        match_results = self.matchers_deduplication(
            self.main_column_regs.finditer(clean_txt(paragraph_text)), self.main_column
        )
        if len(match_results) <= 1:
            # 一个/沒有 主属性
            main_column_result = []
            if len(match_results) == 1:
                main_column_result = self.gen_column_result(
                    element, chars, paragraph_text, match_results[0], self.main_column
                )
            for predictor_result in main_column_result or [None]:
                group_answers.extend(
                    self.extract_by_column(element, paragraph_text, chars, fund_name_result, [predictor_result])
                )
        else:
            # 多个主属性
            # 依次以句号、分号、逗号分割，直到句子中只有一个主属性
            group_answers.extend(self.split_paragraph(element, 0, paragraph_text, chars, fund_name_result))
        return group_answers

    def extract_by_paragraphs(self, elements):
        exclude_indices = set()
        group_answers = []
        for elt in elements:
            paragraph_text, chars = self.get_paragraph_text_chars(elt, exclude_indices)
            if not paragraph_text or not chars:
                continue
            if self.para_regs and not self.para_regs.nexts(clean_txt(paragraph_text)):
                continue
            group_answers.extend(self.gen_group_answers(elt, paragraph_text, chars, None))
        if self.need_distinct:
            return self.distinct_answer(group_answers)
        return group_answers

    def distinct_answer(self, group_answers):
        new_group_answers = []
        for group_answer in group_answers:
            exist = False
            for new_group_answer in new_group_answers:
                if self.is_same_text_answer(group_answer, new_group_answer):
                    exist = True
                    break
                if self.is_same_primary_result(group_answer, new_group_answer):
                    exist = True
                    break
            if not exist:
                new_group_answers.append(group_answer)
        return new_group_answers

    def is_same_text_answer(self, answer1: dict[str, list[PredictorResult]], answer2: dict[str, list[PredictorResult]]):
        if answer1.keys() != answer2.keys():
            return False
        for key, ans_list1 in answer1.items():
            ans_list2 = answer2[key]
            if not self.is_same_predictor_results(ans_list1, ans_list2):
                return False
        return True

    @staticmethod
    def is_same_predictor_results(results1: list[PredictorResult], results2: list[PredictorResult]):
        if len(results1) != len(results2):
            return False
        for idx, val1 in enumerate(results1):
            val2 = results2[idx]
            if val1.text != val2.text:
                return False
        return True

    def is_same_primary_result(
        self, answer1: dict[str, list[PredictorResult]], answer2: dict[str, list[PredictorResult]]
    ):
        """
        primary_key 的result内容相同
        非primary_key 的key相同
        则返回True
        :param answer1:
        :param answer2:
        :return:
        """
        for field in self.primary_key:
            if not self.is_same_predictor_results(answer1.get(field, []), answer2.get(field, [])):
                return False

        other_keys_1 = {x for x in answer1.keys() if x not in self.primary_key}
        other_keys_2 = {x for x in answer2.keys() if x not in self.primary_key}
        if other_keys_1 != other_keys_2:
            return False

        return True

    def extract_by_syllabus(self, elements):
        exclude_indices = set()
        group_answers = []
        fund_name_result = None
        for elt in elements:
            paragraph_text, chars = self.get_paragraph_text_chars(elt, exclude_indices)
            if not paragraph_text or not chars:
                continue
            if (matcher := P_TITLE_PATTERN.nexts(clean_txt(paragraph_text))) and not self.skip_syllabus:
                fund_name_result = self.gen_column_result(elt, chars, paragraph_text, matcher, "基金名称")
            else:
                group_answers.extend(self.gen_group_answers(elt, paragraph_text, chars, fund_name_result))
        return group_answers

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        if depends := self.get_config("depends", []):
            depend_predictors = get_depend_predictors(self.predictor.prophet.predictors, depends)
            depend_answer = next(self.gen_depend_answers(depend_predictors), None)
            if not depend_answer:
                return []

            elements = self.get_elements_from_answer_results([depend_answer])
        if not elements:
            return []
        syllabuses = sorted(
            self.pdfinsight.syllabus_reader.find_by_elt_index(elements[0]["index"]), key=lambda x: x["index"]
        )
        if syllabuses and P_TITLE_PATTERN.nexts(clear_syl_title(syllabuses[-1]["title"])):
            _, elt = self.pdfinsight.find_element_by_index(syllabuses[-1]["element"])
            if elt not in elements:
                elements.insert(0, elt)
            return self.extract_by_syllabus(elements)
        return self.extract_by_paragraphs(elements)
