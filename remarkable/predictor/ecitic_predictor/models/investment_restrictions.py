import copy
import logging
import re
from difflib import SequenceMatcher
from itertools import chain
from typing import Any

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt, index_in_space_string
from remarkable.predictor.common_pattern import R_COLON, R_SEMICOLON
from remarkable.predictor.ecitic_predictor.models.splitter_mixin import ParaSplitterMixin
from remarkable.predictor.models.middle_paras import MiddleParas
from remarkable.predictor.models.syllabus_elt_v2 import SyllabusEltV2
from remarkable.predictor.models.table_tuple import TupleTable
from remarkable.predictor.schema_answer import CharResult, TableResult

logger = logging.getLogger(__name__)

R_SPLIT_SYMBOL = rf"{R_COLON}{R_SEMICOLON}。"
R_CONTINUED_PREFIX = r"^(其中|包括|例如)"

R_CIRCLE_NUMBER = r"①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮"

R_NUM_PUNCTUATION = r",\.．，、\s"
R_LEFT_BRACKET = r"\{〔【（\("
R_RIGHT_BRACKET = r"\)）】〕\}"

R_DIGITAL_SERIAL_NUMBER = rf"[{R_LEFT_BRACKET}]?\d+[{R_RIGHT_BRACKET}{R_NUM_PUNCTUATION}]"

R_LEFT_DOUBLE_QUOTES = r"[“\"]"
R_RIGHT_DOUBLE_QUOTES = r"[”\"]"

# http://100.64.0.9:55816/scriber/#/project/remark/11316?projectId=130&treeId=165&fileId=2389&schemaId=129
R_END_NOTE = r"([（\(].*[）\)])"

P_CONTENT = PatternCollection(
    [
        rf"^{R_LEFT_DOUBLE_QUOTES}?{R_DIGITAL_SERIAL_NUMBER}\s*.*[{R_SEMICOLON}。]{R_END_NOTE}?{R_RIGHT_DOUBLE_QUOTES}?$",
        rf"^\s*{R_LEFT_DOUBLE_QUOTES}?[{R_LEFT_BRACKET}]?\s*[➢0-9一二三四五六七八九十]+\s*[{R_NUM_PUNCTUATION}]*[{R_RIGHT_BRACKET}]?\s*.*[{R_SEMICOLON}。]{R_END_NOTE}?{R_RIGHT_DOUBLE_QUOTES}?$",
    ]
)
P_CONTENT_TITLE = PatternCollection([rf"{R_DIGITAL_SERIAL_NUMBER}"])
P_CONTENT_SPECIAL = PatternCollection([rf"^[（(].*[）)][{R_SEMICOLON}。]$"])
P_CONTENT_SUB = PatternCollection(rf"{R_DIGITAL_SERIAL_NUMBER}*.*[{R_COLON}]$")
P_CONTENT_SUB_TEXT = PatternCollection(
    rf"^(\d+[{R_RIGHT_BRACKET}]|[{R_CIRCLE_NUMBER}]|{R_CONTINUED_PREFIX}|^基金因未平仓).*[{R_SEMICOLON}。]$"
)
P_FORBIDDEN_ACTIONS = PatternCollection(
    [
        r"[\s:、:）)]*禁止行为\s*$",
    ]
)
P_IGNORE_PATTERN = PatternCollection(
    [
        r"应遵循以下限制[:：]$",
    ]
)
P_SENTENCE_END = PatternCollection(rf"[{R_SEMICOLON}]")
P_SENTENCE_INTERPRETER = PatternCollection(rf"[{R_SEMICOLON}]")
P_SUB_SENTENCE = PatternCollection(rf"[{R_SPLIT_SYMBOL}]([{R_LEFT_BRACKET}{R_RIGHT_BRACKET}](?![\d][\)）]))?")
P_SUB_NO = PatternCollection(
    [
        r"[（(]?\d+[）)]",
        rf"[{R_CIRCLE_NUMBER}]",
    ]
)

P_NO = PatternCollection(
    rf"^\s*([{R_LEFT_BRACKET}]?\d+[{R_RIGHT_BRACKET}{R_NUM_PUNCTUATION}]?|[{R_CIRCLE_NUMBER}]|[(（【]?\s*[➢0-9一二三四五六七八九十]+\s*[{R_NUM_PUNCTUATION}]+[)）】]?)"
)

P_BUILDING = PatternCollection(
    r"基金管理人(应当)?自(本基金成立|基金合同生效)之日起?(\s?\d\s?个月内)?使本?基金的投资组合比例符合本?(基金)?(合同的|上述|上款)?的?(有关)?约定。"
)
P_DISCLAIMER = PatternCollection(
    [
        r"基金委托人已经知晓且确认：以上第.*项投资限制由基金管理人自行监控，基金托管人不承担投资监督职责。",
        r"以上投资限制中，如果?涉及.*监控事项的?，由基金管理人自行监控，基金托管人不承担投资监督职责。",
    ]
)
P_ADJUST = PatternCollection(
    r"(\s?除(上述|第).*外，|\s?对于除.*项外的其他比例?限制，)?\s?因?\s?证券[、/]?(期货)?市场波动、.*等基金管理人之外的(因素|原因)(致|导致|致使|使).*不符合.*(比例|限制)?的?，基金管理人(应当)?在?\s?\d+\s?个交易日内(进行)?调整[^,，。;]*"
)

P_NO_LIST = {
    "0": re.compile(r"^\s*\d+[、\.]"),
    "1": re.compile(r"^\s*[（(]\d+[）)]"),
    "2": re.compile(r"^\s*\d+[）)]"),
    "3": re.compile(rf"^\s*[{R_CIRCLE_NUMBER}]"),
    "4": re.compile(rf"^\s*[(（【]?\s*[➢0-9一二三四五六七八九十]+\s*[{R_NUM_PUNCTUATION}]+[)）】]?"),
}

P_NO_SPLIT = PatternCollection(r"投向AA级及以下信用债.*其余品种按持仓市值计算")

FIXED_SENTENCE_END = [
    "本基金新增场外期权合约、收益互换合约及存续合约晨期的，在场外投资划救指令到达基金托管人时，基金托管人对基金净资产规模是否符合本条要求进行事中审核",
    "其中，国债、中央银行票据、政策性金融债、地方政府债券、可转换债券、可交换债券、资产支持证券、资产支持票据、同业存单不受本条限制",
]


class RestrictionsSplitter:
    """投资限制拆分器"""

    @staticmethod
    def merge_content(content_list, flag, index, matched_list_set, predict_element, skip_index):
        if flag and content_list:
            boxs = []
            no_box = []
            for element_index, element in enumerate(content_list):
                if element_index == 0 and element.get("text", "").endswith("；"):
                    no_box = get_no(element.get("text"), no_box, element)
                    matched_list_set.extend([(element, element["chars"])])
                else:
                    if element.get("text", "").endswith("；") and element_index != len(content_list) - 1:
                        matched_list_set.extend([(element, no_box + element["chars"])])
                    else:
                        boxs.extend(element["chars"])
            if boxs:
                matched_list_set.extend([(predict_element, no_box + boxs)])
        skip_index = index + len(content_list) - 1
        return skip_index

    def run(self, predict_elements: list):
        sub_content_chars, matched_list_set = [], []  # 子段落开头表述box
        other_patterns = [
            {"pattern": P_BUILDING, "matched": False},
            {"pattern": P_ADJUST, "matched": False},
            {"pattern": P_DISCLAIMER, "matched": False},
        ]
        max_length = len(predict_elements) - 1
        skip_index = -1
        pre_main_no_regex_index = None
        for index, predict_element in enumerate(predict_elements):
            if not (paragraph_text := predict_element.get("text")):
                continue
            paragraph_clean_text = clean_txt(paragraph_text)
            if index == skip_index or not paragraph_clean_text or P_IGNORE_PATTERN.nexts(paragraph_clean_text):
                continue
            if P_FORBIDDEN_ACTIONS.nexts(paragraph_clean_text):
                break
            # 标准段落 获取所有
            special_index = index + 1
            next_paragraph_text = ""
            if special_index < max_length:
                next_paragraph_text = predict_elements[special_index].get("text", "")
                next_paragraph_text = next_paragraph_text.strip()
            if (no_index := get_no_regex_index(paragraph_clean_text)) and sub_content_chars:
                if no_index == pre_main_no_regex_index or no_index == "0":
                    pre_main_no_regex_index = no_index
                    sub_content_chars = []

            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/5428
            if no_index == "0" and P_CONTENT_SUB.nexts(paragraph_clean_text):
                continue

            if match := P_CONTENT.nexts(paragraph_clean_text):
                if next_paragraph_text:
                    if P_CONTENT.nexts(next_paragraph_text):
                        matched_list_set.extend(split_by_semicolon(match, sub_content_chars, predict_element))
                    elif P_CONTENT_TITLE.nexts(next_paragraph_text) or not P_CONTENT_SUB.nexts(paragraph_clean_text):
                        matched_list_set.extend(split_by_semicolon(match, sub_content_chars, predict_element))
                    else:
                        flag, content_list = False, []  # flag 是下一个能按规则提取的位置标志位
                        for index_, predict_element_ in enumerate(predict_elements[index:]):
                            paragraph_text_ = predict_element_.get("text")
                            if P_FORBIDDEN_ACTIONS.nexts(paragraph_text_):
                                break
                            if index_ != 0 and P_CONTENT.nexts(paragraph_text_):
                                flag = True
                                break
                            content_list.append(predict_element_)
                        # 合并一些不在规则中的描述，然后按照分号拆分
                        skip_index = self.merge_content(
                            content_list, flag, index, matched_list_set, predict_element, skip_index
                        )
                    continue
                else:
                    matched_list_set.extend(split_by_semicolon(match, sub_content_chars, predict_element))
            else:
                # 根据固定段落匹配相似度
                if any(SequenceMatcher(None, a, paragraph_clean_text).ratio() >= 0.8 for a in FIXED_SENTENCE_END):
                    matched_list_set.extend([(predict_element, predict_element["chars"])])
                    continue

            # 有子段落 获取子段落开头的表述 这个表述要插入到每个子段落之前
            if index != 0 and P_CONTENT_SUB.nexts(paragraph_clean_text):
                pre_main_no_regex_index = get_no_regex_index(paragraph_clean_text)
                sub_content_chars = predict_element["chars"]
                continue

            # 特殊处理（xxx;）为单独段落的情况
            if next_paragraph_text and P_CONTENT_SPECIAL.nexts(next_paragraph_text):
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4400#note_499556
                # 当前的序号和下一句的序号是同一类则拆分为一条
                if get_no_regex_index(next_paragraph_text) == no_index:
                    matched_list_set.extend([(predict_element, predict_element["chars"])])
                else:
                    end_chars = predict_element["chars"] + predict_elements[special_index]["chars"]
                    matched_list_set.extend([(predict_element, end_chars)])
                    skip_index = special_index
                continue

            # 有子段落 获取子段落
            if match := P_CONTENT_SUB_TEXT.nexts(paragraph_clean_text):
                matched_list_set.extend(split_by_semicolon(match, sub_content_chars, predict_element))
            else:
                # 其他三种表述 https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2848
                matched_list_set.extend(extracting_other_rules(paragraph_text, predict_element, other_patterns))
        return matched_list_set

    def split(self, predict_elements: list):
        fix_elements = []
        for ele in predict_elements:
            if page_merged_paragraph := ele.get("page_merged_paragraph"):
                fix_element = copy.deepcopy(ele)
                fix_element["text"] = page_merged_paragraph.get("text")
                for idx in page_merged_paragraph["paragraph_indices"]:
                    if idx == ele["index"]:
                        continue
                    _, para = self.pdfinsight.find_element_by_index(idx)
                    if para:
                        fix_element["chars"].extend(filter(lambda x: x not in fix_element["chars"], para["chars"]))
                fix_elements.append(fix_element)
            else:
                fix_elements.append(ele)
        return [
            CharResult(
                element=predict_element,
                chars=contend_box,
            )
            for predict_element, contend_box in self.run(fix_elements)
        ]


def extracting_other_rules(paragraph_text: str, predict_element: dict[str, Any], patterns: list[dict]) -> list:
    content_box_list = []
    for pattern_ in patterns:
        if not pattern_["matched"] and (content_match := pattern_["pattern"].nexts(clean_txt(paragraph_text))):
            pattern_["matched"] = True
            start, end = content_match.span()
            sp_start, sp_end = index_in_space_string(paragraph_text, (start, end))
            content_box_list.append(predict_element["chars"][sp_start:sp_end])
    return [(predict_element, content_box) for content_box in content_box_list] if content_box_list else []


def split_by_semicolon(
    match: re.Match, sub_content_chars: list[dict[str, Any]], predict_element: dict[str, Any]
) -> list:
    current_chars = predict_element["chars"]
    element_text = predict_element["text"]
    content = match.group()[:-1]
    no_box = []
    matched_list = []

    if not P_SUB_SENTENCE.nexts(content) or P_NO_SPLIT.nexts(content):
        matched_list.append((predict_element, sub_content_chars + current_chars))
        return matched_list
    no_box = get_no(content, no_box, predict_element)
    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4400
    start_no_index = get_no_regex_index("".join(s["text"] for s in no_box))
    start = 0
    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2874#note_374116
    temp_sub_context = []
    if (
        not sub_content_chars
        and (match_sub_no := P_SUB_NO.nexts(content))
        and not P_SENTENCE_INTERPRETER.nexts(content)
    ):
        if match_sub_no.start() != 0:
            sp_start, sp_end = index_in_space_string(element_text, (start, start + match_sub_no.start()))
            temp_sub_context = current_chars[sp_start:sp_end]
    next_pos = 0
    for link_res in chain(P_SUB_SENTENCE.finditer(content), (None,)):
        start, end = link_res.span() if link_res else (len(content), 0)
        if next_pos == start:
            continue
        sp_start, sp_end = index_in_space_string(element_text, (next_pos, start))
        split_content_chars = current_chars[sp_start:sp_end]
        split_content = content[next_pos:start]
        if next_pos == 0:
            dst_chars = sub_content_chars + split_content_chars
        elif match := P_NO.nexts(split_content.strip()):
            # 子句有序号
            sub_no_index = get_no_regex_index(split_content.strip()[match.start() : match.end()])
            if start_no_index is not None and sub_no_index is not None and sub_no_index != start_no_index:
                # 子句序号和主句序号不是同一类
                dst_chars = (
                    sub_content_chars + no_box + split_content_chars
                    if sub_content_chars
                    else temp_sub_context + no_box + split_content_chars
                )
            else:
                dst_chars = (
                    sub_content_chars + split_content_chars
                    if sub_content_chars
                    else temp_sub_context + split_content_chars
                )
        elif content[start:end] in R_COLON and link_res:
            # 以冒号结尾的时候，此句添加到序号序列中
            sp_start, sp_end = index_in_space_string(element_text, (next_pos, end))
            no_box = sub_content_chars + no_box + current_chars[sp_start:sp_end]
            dst_chars = []
        else:
            dst_chars = sub_content_chars + no_box + split_content_chars

        next_pos = end
        if dst_chars:
            matched_list.append((predict_element, dst_chars))
    return matched_list


def get_no(content, no_box, predict_element):
    if match_no := P_NO.nexts(content):
        s_index, e_index = match_no.span()
        no_box = predict_element["chars"][s_index:e_index]
    return no_box


def get_no_regex_index(context: str) -> str | None:
    for key, val in P_NO_LIST.items():
        if val.match(context):
            return key
    return None


class InvestmentRestrictionsSyllabus(ParaSplitterMixin, SyllabusEltV2, RestrictionsSplitter):
    pass


class InvestmentRestrictionsMiddle(ParaSplitterMixin, MiddleParas, RestrictionsSplitter):
    pass


class InvestmentRestrictionsTupleTable(TupleTable, RestrictionsSplitter):
    def predict_schema_answer(self, elements):
        parent_answers = super().predict_schema_answer(elements)
        if not parent_answers:
            return parent_answers
        predict_elements = []
        for answer_result in parent_answers:
            if not isinstance(answer_result, dict):
                continue
            for answers in answer_result.values():
                for answer in answers:
                    for results in answer.element_results:
                        if isinstance(results, TableResult):
                            predict_elements.extend([results.element["cells"][key] for key in results.cells])
            break
        if not (element_results := self.split(predict_elements)):
            return parent_answers
        answer_results = [self.create_result(element_results, column="拆分")]
        for parent_answer in parent_answers:
            if isinstance(parent_answer, dict):
                answer_results.extend(parent_answer.get("原文", []))
            elif parent_answer.schema.name == "原文":
                answer_results.append(parent_answer)
                break
        return answer_results
