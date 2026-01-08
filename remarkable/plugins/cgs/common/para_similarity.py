import difflib
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from itertools import zip_longest

from remarkable.common.convert_number_util import DateUtil, NumberUtil, PercentageUtil
from remarkable.plugins.cgs.common.enum_utils import ConvertContentEnum
from remarkable.plugins.cgs.common.lcs import get_lcs
from remarkable.plugins.cgs.common.patterns_util import (
    P_BASE_SIMILARITY_PATTERNS,
    P_DATE,
    P_IGNORE_TEXT,
    P_NEGATIVE_PREFIX,
    P_NUMBER,
    P_NUMBERING,
    P_PERCENTAGE,
    P_PERFECTLY_NUMBER,
)
from remarkable.plugins.cgs.common.utils import convert_table_to_sentences_by_row, get_outlines
from remarkable.plugins.predict.common import is_table_elt

# https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/959#note_237823
# JUNK_CHARS = set('《》<>()（）{}[]【】［］」「〗〖』『〉〈»«＞＜〕〕〔〔\n')
R_PUNCTUATION = r',.．、？?，。！!“"：:”\'‘’ ;；'
PUNCTUATION_CHARS = set(R_PUNCTUATION)
SYMBOL_BRACKETS_LEFT_CHARS = set(r"[《<(（{【［「〖『〈«＜〔〔")
SYMBOL_BRACKETS_RIGHT_CHARS = set(r"]》>)）}】］」〗』〉»＞〕〕")
SYMBOL_BRACKETS_CHARS = list(SYMBOL_BRACKETS_LEFT_CHARS) + list(SYMBOL_BRACKETS_RIGHT_CHARS)
JUNK_CHARS = set(list(PUNCTUATION_CHARS) + SYMBOL_BRACKETS_CHARS + ["\n"])

P_SUB_PUNCTUATION = re.compile(rf"^[{R_PUNCTUATION}]*|[{R_PUNCTUATION}]*$")

JUNK_CHARS_DOT = set("。;；？:：")

# 拆分diff结果相等场景，按左右划分，仅用做处理近义词时拆分模板，处理完统一为“DIFF_EQUAL”
DIFF_L_EQUAL = "l"
DIFF_R_EQUAL = "r"
DIFF_EQUAL = " "
DIFF_COMMON_EQUALS = (DIFF_EQUAL, DIFF_L_EQUAL, DIFF_R_EQUAL)
DIFF_DELETE = "-"
DIFF_INSERT = "+"

SPECIAL_REPLACE_CHAR = "❤"

SENTENCE_TYPE_PARA = "PARAGRAPH"
SENTENCE_TYPE_TABLE = "TABLE"


@dataclass
class Sentence:
    index: int
    sentence_index: int
    text: str
    chars: list | None
    origin: str
    cleaned_text: str
    para_index: int
    index_mapping: dict = field(default_factory=dict)
    ends: str = field(default="")
    ignore_dot: bool = field(default=False)
    type: str = field(default=SENTENCE_TYPE_PARA)
    row_index: int = field(default=0)

    P_SPLIT = re.compile(r"[。;；？:：\n]+")

    @property
    def origin_text(self):
        return f"{self.text}{self.ends}"

    @classmethod
    def create_sentences(cls, paragraphs, ignore_numbering=True, split=True):
        res = []
        total = 0
        table_indexes = set()
        for index, item in enumerate(paragraphs):
            if isinstance(item, str):
                pack_data = {
                    "text": item,
                    "chars": [],
                    "para_index": index,
                    "origin": None,
                }
            elif is_table_elt(item):
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2132
                # 表格需按行拆分为段落
                if item["syllabus"] in table_indexes:
                    continue
                table_indexes.add(item["syllabus"])
                for row in convert_table_to_sentences_by_row(item):
                    pack_data = {
                        "text": row["text"],
                        "chars": row["chars"],
                        "para_index": row["table_index"],
                        "row_index": row["row"],
                        "origin": row,
                    }
                    total, sentences = cls.init_sentences(
                        pack_data,
                        total=total,
                        ignore_numbering=ignore_numbering,
                        split=split,
                        sentence_type=SENTENCE_TYPE_TABLE,
                    )
                    res.extend(sentences)
                continue
            else:
                pack_data = {
                    "text": item["text"],
                    "chars": item["chars"],
                    "para_index": item["index"],
                    "origin": item,
                }

            total, sentences = cls.init_sentences(
                pack_data, total=total, ignore_numbering=ignore_numbering, split=split
            )
            res.extend(sentences)
        return res

    @classmethod
    def init_sentences(cls, pack_data, total=0, ignore_numbering=True, split=True, sentence_type=SENTENCE_TYPE_PARA):
        res = []
        prev = 0
        text = pack_data["text"]
        para_index = pack_data["para_index"]
        origin = pack_data["origin"]
        chars = pack_data["chars"]
        count = len(text)
        sentence_index = 0
        row_index = 0 if sentence_type == SENTENCE_TYPE_PARA else pack_data["row_index"]
        if split:
            for dot_index, dot in enumerate(cls.P_SPLIT.finditer(text)):
                sentence_text = text[prev : dot.start()]
                ignore_dot = ignore_numbering and not sentence_index
                index_mapping, cleaned_text = Sentence.delete_punctuation_from_text(sentence_text, ignore_dot)
                res.append(
                    Sentence(
                        index=total,
                        text=sentence_text,
                        sentence_index=dot_index,
                        index_mapping=index_mapping,
                        cleaned_text=cleaned_text,
                        para_index=para_index,
                        ends=dot.group(),
                        chars=chars[prev : dot.start()] if chars else None,
                        origin=origin,
                        ignore_dot=ignore_dot,
                        type=sentence_type,
                        row_index=row_index,
                    )
                )
                total += 1
                prev = dot.end()
                sentence_index += 1

        if prev < count - 1 or not split:
            sentence_text = text[prev:]
            ignore_dot = ignore_numbering and not sentence_index
            index_mapping, cleaned_text = Sentence.delete_punctuation_from_text(sentence_text, ignore_dot, not split)
            res.append(
                Sentence(
                    index=total,
                    text=sentence_text,
                    sentence_index=sentence_index + 1,
                    index_mapping=index_mapping,
                    cleaned_text=cleaned_text,
                    para_index=para_index,
                    ends="",
                    chars=chars[prev:] if chars else None,
                    origin=origin,
                    ignore_dot=ignore_dot,
                    type=sentence_type,
                    row_index=row_index,
                )
            )
            total += 1

        return total, res

    @classmethod
    def find_sentences_by_range(cls, sentences, start, end):
        res = []
        for item in sorted(sentences, key=lambda x: x.index):
            if end > item.index > start:
                res.append(item)
        return res

    @classmethod
    def create_sentence_without_brackets(cls, origin_sentence, ignore_numbering=True) -> "Sentence":
        index_mapping, cleaned_text = cls.delete_punctuation_from_text(
            origin_sentence.text,
            ignore_numbering=ignore_numbering,
            ignore_dot=origin_sentence.ignore_dot,
            junk_chars=PUNCTUATION_CHARS,
        )
        return cls(
            index=origin_sentence.index,
            text=origin_sentence.text,
            sentence_index=origin_sentence.sentence_index,
            index_mapping=index_mapping,
            cleaned_text=cleaned_text,
            para_index=origin_sentence.para_index,
            ends=origin_sentence.ends,
            chars=origin_sentence.chars,
            origin=origin_sentence.origin,
            ignore_dot=origin_sentence.ignore_dot,
        )

    @classmethod
    def delete_punctuation_from_text(cls, text, ignore_numbering=True, ignore_dot=False, junk_chars=None):
        chars = []
        junk_chars = junk_chars or JUNK_CHARS
        index_mapping = {}
        new_index = 0
        start = 0
        if ignore_numbering:
            matched = P_NUMBERING.nexts(text)
            date_res = P_DATE.nexts(text)
            # 首位非日期
            if matched and not (date_res and matched.end() in date_res.span()):
                start = matched.end(0)

        index_mapping[0] = start
        prev_char = ""
        for index, char in enumerate(text[start:], start=start):
            if (char not in junk_chars and (not ignore_dot or char not in JUNK_CHARS_DOT)) or (
                index < len(text) and P_PERFECTLY_NUMBER.nexts(f"{prev_char}{char}")
            ):
                chars.append(char)
                prev_char = char
                index_mapping[new_index] = index
                new_index += 1

        return index_mapping, "".join(chars)

    def get_origin_by_range(self, start, end=0):
        text_len = len(self.cleaned_text)
        if not end:
            end = text_len
        if end and end >= text_len:
            if start == 0:
                return self.origin_text
        end = min(text_len - 1, end)
        if end == -1:
            end = 0 if text_len == 0 else text_len - 1
        start = max(0, start)
        if start == 0:
            origin_start = 0
        else:
            origin_start = self.index_mapping[start]
        return self.origin_text[origin_start : self.index_mapping[end] + 1]


@dataclass
class ConvertText:
    clean_text: str
    convert_types: list | None
    _convert_text: str = field(default="")
    _convert_mapping: dict = field(default_factory=dict)

    def format_text_by_convert_types(self):
        if not self.convert_types:
            return

        convert_vals = []
        if ConvertContentEnum.DATE.value in self.convert_types:
            convert_vals.extend([(ConvertContentEnum.DATE, res) for res in P_DATE.finditer(self.clean_text)])
        if ConvertContentEnum.PERCENTAGE.value in self.convert_types:
            convert_vals.extend(
                [(ConvertContentEnum.PERCENTAGE, res) for res in P_PERCENTAGE.finditer(self.clean_text)]
            )
        # filter duplicate number match
        if ConvertContentEnum.NUMBER.value in self.convert_types:
            for res in P_NUMBER.finditer(self.clean_text):
                start, end = res.span()
                if any(
                    p_res.start() < start < p_res.end() or p_res.start() < end < p_res.end()
                    for _, p_res in convert_vals
                ):
                    continue
                convert_vals.append((ConvertContentEnum.NUMBER, res))

        if not convert_vals:
            return

        convert_vals = sorted(convert_vals, key=lambda x: x[-1].end())
        convert_mapping, convert_text = self.format_text_with_convert(convert_vals, self.clean_text)
        self.convert_mapping = convert_mapping
        self.convert_text = convert_text
        return

    @classmethod
    def format_text_with_convert(cls, convert_vals, cleaned_text):
        convert_mapping = {}
        offset = 0
        for convert_type, res in convert_vals:
            start, end = offset + res.start(), offset + res.end()
            text = cleaned_text[start:end]
            if hasattr(cls, f"convert_{convert_type.value}_text"):
                convert_text = getattr(cls, f"convert_{convert_type.value}_text", None)(text)
                cleaned_text = cleaned_text[:start] + convert_text + cleaned_text[end:]
                offset += len(convert_text) - len(text)
                convert_mapping[f"{start}_{start + len(convert_text)}"] = {
                    "origin_val": text,
                    "format_val": convert_text,
                }

        return convert_mapping, cleaned_text

    @classmethod
    def convert_number_text(cls, text):
        cleaned_text = P_NEGATIVE_PREFIX.sub("", text)
        number = NumberUtil.cn_number_2_digit(cleaned_text)
        if P_NEGATIVE_PREFIX.nexts(text):
            number = f"-{str(number)}" if number else ""
        return str(number) or text

    @classmethod
    def convert_date_text(cls, text):
        number = DateUtil.convert_2_human_date(text)
        return number or text

    @classmethod
    def convert_percentage_text(cls, text):
        cleaned_text = P_NEGATIVE_PREFIX.sub("", text)
        number = PercentageUtil.convert_2_division_str(cleaned_text)
        if P_NEGATIVE_PREFIX.nexts(text):
            number = f"-{number}" if number else ""
        return number or text

    @property
    def convert_mapping(self):
        return self._convert_mapping

    @property
    def convert_text(self):
        return self._convert_text or self.clean_text

    @convert_mapping.setter
    def convert_mapping(self, value: dict):
        self._convert_mapping = value

    @convert_text.setter
    def convert_text(self, value: str):
        self._convert_text = value


@dataclass
class DiffResult:
    left: Sentence | None
    right: Sentence | None
    diff: list
    ratio: float

    TEMPLATES = {
        DIFF_INSERT: "<u>{}</u>",
        DIFF_DELETE: "<s>{}</s>",
    }

    @property
    def right_content(self):
        if self.right:
            return self.right.origin_text
        return ""

    @property
    def left_content(self):
        if self.left:
            return self.left.origin_text
        return ""

    @property
    def is_matched(self):
        return self.ratio > 0

    @property
    def is_full_matched(self):
        return math.isclose(self.ratio, 1.0, abs_tol=10e-6)

    @classmethod
    def format_template(cls, op, texts):
        template = cls.TEMPLATES.get(op)
        if template:
            return template.format("".join(texts))
        return "".join(texts)

    @property
    def text_diff_content(self):
        return "".join([f"{op}{text}" for op, text in self.diff])

    @property
    def html_diff_content(self):
        buffer = []
        prev_op = ""
        html = []
        for op, text in self.diff:
            if op != prev_op:
                if buffer:
                    html.append(self.format_template(prev_op, buffer))
                buffer = []
            prev_op = op
            buffer.append(text)

        if buffer:
            html.append(self.format_template(prev_op, buffer))

        return "".join(html)


class ParagraphSimilarity:
    MIN_RATIO = 0.5

    def __init__(
        self,
        paragraphs_left,
        paragraphs_right,
        ratio=0.7,
        ignore_numbering=True,
        fill_paragraph=False,
        max_width=20,
        similarity_patterns=None,
        ignore_extra_para=False,
        convert_types=None,
        split_sentence=True,
    ):
        self.split_sentence = split_sentence
        self.similarity_patterns = similarity_patterns or P_BASE_SIMILARITY_PATTERNS
        self.sentences_left = Sentence.create_sentences(paragraphs_left, ignore_numbering, split=split_sentence)
        self.sentences_right = Sentence.create_sentences(paragraphs_right, ignore_numbering, split=split_sentence)
        self.fill_paragraph = fill_paragraph
        self.ignore_extra_para = ignore_extra_para
        self.convert_types = convert_types
        self.ratio = ratio
        self.max_width = max_width
        self.results = self._diff_paragraphs()
        self.grouped_results = self._group_results()

    def _group_results(self):
        return self._group_results_by_paragraph(self.results, self.ignore_extra_para)

    @classmethod
    def _group_results_by_paragraph(cls, results, ignore_extra_para=False):
        res = []
        children = []
        prev_result = None
        for result in results:
            if result.right:
                if prev_result and cls._is_same_sentence(prev_result.right, result.right):
                    children.append(result)
                elif any(
                    cls._is_same_sentence(prev_item.right, result.right) for prev_item in children if prev_item.right
                ):
                    children.append(result)
                # 左侧段落的子句与当前是相同段落，且子句均无与右侧匹配的对象
                elif (
                    result.left
                    and any(
                        cls._is_same_sentence(prev_item.left, result.left) for prev_item in children if prev_item.left
                    )
                    and all(not prev_item.right for prev_item in children)
                ):
                    children.append(result)
                elif children:
                    res.append(children)
                    children = [result]
                else:
                    children.append(result)
                prev_result = result
            else:
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/959#note_244439
                if (
                    result.left
                    and prev_result
                    and prev_result.left
                    and not cls._is_same_sentence(prev_result.left, result.left)
                ) or (
                    children
                    and all(
                        not cls._is_same_sentence(prev_item.left, result.left)
                        for prev_item in children
                        if prev_item.left
                    )
                ):
                    res.append(children)
                    children = [result]
                else:
                    children.append(result)
                prev_result = None
        if children:
            res.append(children)

        # 剔除段落内参杂的其他非匹配段落, 忽略头尾
        if ignore_extra_para and len(res) > 2:
            pre_diff = None
            for diffs in res[::-1]:
                if not pre_diff or any(_diff.ratio > 0 for _diff in diffs):
                    pre_diff = diffs
                    continue
                if not any(DIFF_INSERT != val[0] for _diff in diffs for val in _diff.diff if val):
                    res.remove(diffs)
        return res

    @staticmethod
    def _is_same_sentence(prev_sentence: Sentence, current_sentence: Sentence):
        if prev_sentence.type == current_sentence.type == SENTENCE_TYPE_PARA:
            return prev_sentence.para_index == current_sentence.para_index
        elif prev_sentence.type == current_sentence.type == SENTENCE_TYPE_TABLE:
            return (
                prev_sentence.para_index == current_sentence.para_index
                and prev_sentence.row_index == current_sentence.row_index
            )
        return False

    @property
    def right_outlines(self):
        paragraphs = []
        unique_key = "{type}_{para_index}_{index}"
        mapping = {
            unique_key.format(type=item.type, para_index=item.para_index, index=item.index): item
            for item in self.sentences_right
        }
        for item in self.results:
            if not item.right:
                continue
            key = unique_key.format(type=item.right.type, para_index=item.right.para_index, index=item.right.index)
            if key in mapping:
                if origin := mapping[key].origin:
                    paragraphs.append(origin)

        return get_outlines(paragraphs)

    @property
    def left_outlines(self):
        paragraphs = []
        mapping = {item.para_index: item for item in self.sentences_left}
        for item in self.results:
            if item.left and item.left.para_index in mapping:
                if mapping[item.left.para_index].origin:
                    paragraphs.append(mapping[item.left.para_index].origin)

        return get_outlines(paragraphs)

    @classmethod
    def compare_two_text(cls, left, right):
        sentences_left = Sentence.create_sentences([left], True, False)[0]
        sentences_right = Sentence.create_sentences([right], True, False)[0]
        left_sentence = Sentence.create_sentence_without_brackets(sentences_left)
        right_sentence = Sentence.create_sentence_without_brackets(sentences_right)
        matcher = difflib.SequenceMatcher(a=left_sentence.cleaned_text, b=right_sentence.cleaned_text)
        compare_result, _ = cls._gen_origin_diff_result(left_sentence, right_sentence, cls._compare(matcher))

        return DiffResult(
            left=sentences_left,
            right=sentences_right,
            ratio=matcher.ratio(),
            diff=[(item[0], item[-1]) for item in compare_result],
        )

    @property
    def valid_sentences_count(self):
        match_sentence_count = 0
        for diff_results in self.grouped_results:
            match_sentence_count += sum(1 for item in diff_results if item.left and item.right)
        return match_sentence_count

    @property
    def max_ratio(self):
        return self.weighted_average_ratio

    @property
    def average_ratio(self):
        if not self.grouped_results:
            return 0
        ratio = 0
        for diff_results in self.grouped_results:
            ratio += sum(item.ratio for item in diff_results) / len(diff_results)
        return ratio / len(self.grouped_results)

    @property
    def weighted_average_ratio(self):
        return self.calc_weighted_average_ratio(self.grouped_results)

    @classmethod
    def calc_weighted_average_ratio(cls, grouped_results):
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2223
        # 针对每组计算加权平均数，再求平均数
        if not grouped_results:
            return 0
        ratio = 0
        count = len(grouped_results)
        for diff_results in grouped_results:
            ratio += cls.calc_weighted_ratio(diff_results)
        return ratio / count if count != 0 else 0

    @staticmethod
    def calc_weighted_ratio(diff_results: list[DiffResult]):
        # 加权平均数
        if not diff_results:
            return 0
        ratio = sum(item.ratio * len(item.diff) for item in diff_results)
        chars_count = sum(len(item.diff) for item in diff_results)
        return ratio / chars_count if chars_count != 0 else 0

    @property
    def simple_results(self):
        diff_html = []
        index = 0
        for items in self.grouped_results:
            _type = "match"

            add_count = 0
            del_count = 0
            match_count = 0
            count = len(items)
            left = []
            right = []
            for item in items:
                if not item.left and not item.ratio:
                    add_count += 1
                elif not item.right and not item.ratio:
                    del_count += 1
                elif item.left and item.right and not math.isclose(item.ratio, 1, abs_tol=1e-06):
                    match_count += 1
                if item.left:
                    left.append(item.left.origin_text)
                if item.right:
                    right.append(item.right.origin_text)

            if add_count == count:
                _type = "add"
            elif del_count == count:
                _type = "del"
                index += 1
            elif add_count == 0 and del_count == 0 and not match_count:
                index += 1
                _type = "equal"
            else:
                index += 1

            diff_html.append(
                {
                    "html": "".join([item.html_diff_content for item in items]),
                    "type": _type,
                    "left": "".join(left),
                    "right": "".join(right) if _type != "equal" else None,
                }
            )
        return diff_html

    @classmethod
    def _get_group_sentences(cls, sentences):
        mapping = defaultdict(list)
        for sentence in sorted(sentences, key=lambda x: x.index):
            mapping[sentence.para_index].append(sentence)
        return mapping

    @property
    def is_matched(self):
        return self.judge_is_matched(self.results)

    @staticmethod
    def judge_is_matched(results: list[DiffResult]):
        if not results:
            return False
        for item in results:
            if item.is_matched:
                return True
        return False

    @property
    def is_full_matched(self):
        return self.judge_is_full_matched(self.results)

    @staticmethod
    def judge_is_full_matched(results: list[DiffResult]):
        if not results:
            return False
        for item in results:
            if not item.is_full_matched:
                return False
        return True

    @property
    def is_full_matched_or_contain(self):
        if not self.results:
            return False

        prev_index = None
        for index, item in enumerate(self.results):
            if item.is_full_matched:
                if prev_index is not None and prev_index + 1 != index:
                    return False
                prev_index = index
            elif item.is_matched:
                return False
            elif item.right is None:
                return False

        return prev_index is not None

    @property
    def is_full_matched_without_extra_para(self):
        if not self.grouped_results:
            return False

        for group_items in self.grouped_results:
            if any(not item.is_full_matched for item in group_items):
                return False
        return True

    @property
    def right_content(self):
        texts = []
        for items in self.grouped_results:
            texts.append("".join([item.right_content for item in items]))
        return "\n".join(texts)

    @property
    def left_content(self):
        texts = []
        for items in self.grouped_results:
            texts.append("".join([item.left.origin_text for item in items if item.left]))
        return "\n".join(texts)

    def print_result(self):
        for item in self.results:
            print("-" * 30)
            print(f"max ratio: {item.ratio}")
            print(f"diff: {item.html_diff_content}")
            if item.left:
                print(f"----L: {item.left.text} ")
            if item.right:
                print(f"----R: {item.right.text} ")

        print("group by paragraph", "-" * 30)

        for item in self.simple_results:
            print(item)

    @classmethod
    def _compare(cls, matcher):
        diff = difflib.Differ()
        for tag, alo, ahi, blo, bhi in matcher.get_opcodes():
            if tag == "replace":
                gen = diff._fancy_replace(matcher.a, alo, ahi, matcher.b, blo, bhi)
            elif tag == "delete":
                gen = diff._dump(DIFF_DELETE, matcher.a, alo, ahi)
            elif tag == "insert":
                gen = diff._dump(DIFF_INSERT, matcher.b, blo, bhi)
            elif tag == "equal":
                gen = diff._dump(DIFF_EQUAL, matcher.a, alo, ahi)
            else:
                raise ValueError("unknown tag %r" % (tag,))

            yield from gen

    @classmethod
    def _remove_untrusted_item(cls, diff_mapping, max_width):
        # 对于开头和末尾的孤立句子， 删掉超过限制范围的
        items = sorted(diff_mapping.keys(), key=lambda x: x[1])
        count = len(items)
        if count < 2:
            return diff_mapping

        if items[1][1] - items[0][1] > max_width:
            diff_mapping.pop(items[0])

        if count == 2:
            return diff_mapping

        if items[-1][1] - items[-2][1] > max_width:
            diff_mapping.pop(items[-1])

        return diff_mapping

    @classmethod
    def group_sentences(cls, sentences_left, sentences_right, diff_mapping):
        lcs = get_lcs(sentences_left, sentences_right, diff_mapping)
        prev_index_right = None
        prev_index_left = None
        result = []
        for item in lcs:
            if prev_index_left is not None and item.left.index > prev_index_left + 1:
                sentences = Sentence.find_sentences_by_range(sentences_left, start=prev_index_left, end=item.left.index)
                for sentence in sentences:
                    operator = DIFF_DELETE if sentence.cleaned_text else DIFF_EQUAL
                    result.append(
                        DiffResult(
                            left=sentence, right=None, ratio=0, diff=[f"{operator}{ch}" for ch in sentence.origin_text]
                        )
                    )

            if prev_index_right is not None and item.right.index > prev_index_right + 1:
                sentences = Sentence.find_sentences_by_range(
                    sentences_right, start=prev_index_right, end=item.right.index
                )
                for sentence in sentences:
                    operator = DIFF_INSERT if sentence.cleaned_text else DIFF_EQUAL
                    result.append(
                        DiffResult(
                            left=None, right=sentence, ratio=0, diff=[f"{operator}{ch}" for ch in sentence.origin_text]
                        )
                    )
            result.append(item)
            prev_index_right = item.right.index
            prev_index_left = item.left.index

        if prev_index_left is not None and sentences_left:
            sentences = Sentence.find_sentences_by_range(
                sentences_left, start=prev_index_left, end=sentences_left[-1].index + 1
            )
            for sentence in sentences:
                operator = DIFF_DELETE if sentence.cleaned_text else DIFF_EQUAL
                result.append(
                    DiffResult(
                        left=sentence, right=None, ratio=0, diff=[f"{operator}{ch}" for ch in sentence.origin_text]
                    )
                )

        return result

    @classmethod
    def fix_miss_right_sentences(cls, sentences_right, results):
        mapping = defaultdict(list)
        for sentence in sentences_right:
            mapping[sentence.para_index].append(sentence)

        right_sentences = [item.right for item in results if item.right]
        first = []
        last = []
        if right_sentences:
            for sentence in mapping[right_sentences[0].para_index]:
                if sentence.sentence_index < right_sentences[0].sentence_index:
                    operator, ratio = cls.get_operator(DIFF_INSERT, sentence.cleaned_text)
                    first.append(
                        DiffResult(
                            left=None,
                            right=sentence,
                            ratio=ratio,
                            diff=[(operator, ch) for ch in sentence.origin_text],
                        )
                    )
            for sentence in mapping[right_sentences[-1].para_index]:
                if sentence.sentence_index > right_sentences[-1].sentence_index:
                    operator, ratio = cls.get_operator(DIFF_INSERT, sentence.cleaned_text)
                    last.append(
                        DiffResult(
                            left=None,
                            right=sentence,
                            ratio=ratio,
                            diff=[(operator, ch) for ch in sentence.origin_text],
                        )
                    )
        return first, last

    @classmethod
    def get_operator(cls, operator, cleaned_text):
        if cleaned_text:
            return operator, 0.0
        return DIFF_EQUAL, 1.0

    @classmethod
    def fix_miss_left_sentences(cls, sentences_left, results):
        left_sentences = [item.left for item in results if item.left]
        first = []
        last = []
        if left_sentences:
            for sentence in sentences_left:
                if sentence.index < left_sentences[0].index:
                    operator, ratio = cls.get_operator(DIFF_DELETE, sentence.cleaned_text)
                    first.append(
                        DiffResult(
                            left=sentence,
                            right=None,
                            ratio=ratio,
                            diff=[(operator, ch) for ch in sentence.origin_text],
                        )
                    )
                if sentence.index > left_sentences[-1].index:
                    operator, ratio = cls.get_operator(DIFF_DELETE, sentence.cleaned_text)
                    last.append(
                        DiffResult(
                            left=sentence,
                            right=None,
                            ratio=ratio,
                            diff=[(operator, ch) for ch in sentence.origin_text],
                        )
                    )
        else:
            for sentence in sentences_left:
                operator, ratio = cls.get_operator(DIFF_DELETE, sentence.cleaned_text)
                first.append(
                    DiffResult(
                        left=sentence, right=None, ratio=ratio, diff=[(operator, ch) for ch in sentence.origin_text]
                    )
                )

        return first, last

    @classmethod
    def _render_diff_result(cls, sentence_left, sentences_right, results, fill_paragraph=True):
        first_right, last_right = [], []
        if fill_paragraph:
            first_right, last_right = cls.fix_miss_right_sentences(sentences_right, results)

        first_left, last_left = cls.fix_miss_left_sentences(sentence_left, results)
        return first_left + first_right + results + last_right + last_left

    @classmethod
    def _ignore_similar_diff_result(cls, diff_list: list[str], similarity_patterns=None) -> list[str]:
        # 分别记录左侧、右侧文本在diff中位置
        # 如同义词需要替换，则该同义词在左右两侧出现位置也基本一致，
        # 根据左右两侧文本匹配到的pos，在原始文本中找起始位置，左侧需要-1，包含前置字符，
        # 如位置相同，则在原始文本中前后必出现一处共同点
        # 以右侧文本为准，左侧特殊字符替换，后面过滤
        if not diff_list:
            return []
        right_mapping, left_mapping = cls._split_diff_mapping(diff_list, exclude_ignore_punctuation=True)
        left_diff_str = "".join([diff_list[idx][-1] for idx in left_mapping.values()])
        right_diff_str = "".join([diff_list[idx][-1] for idx in right_mapping.values()])
        for _pattern in similarity_patterns or P_BASE_SIMILARITY_PATTERNS:
            left_spans = [_m.span() for _m in _pattern.finditer(left_diff_str)]
            right_spans = [_m.span() for _m in _pattern.finditer(right_diff_str)]
            if not (left_spans and right_spans):
                continue
            # 向前移一位，example：
            # 1. left: 报酬的外包, right:报酬的基金服务， 外包与基金服务前一位相同，后面词相似
            # 2. left: 管理人托管人, right:私募基金管理人， 首位相同，后面词相似
            left_spans = [
                [(idx == -1 and -1) or left_mapping[idx] for idx in range(start - 1, end)] for start, end in left_spans
            ]
            right_spans = [
                [(idx == -1 and -1) or right_mapping[idx] for idx in range(start - 1, end)]
                for start, end in right_spans
            ]
            # 相似词语位置，前后必须有一处匹配点
            match_spans = [
                (l_match, r_match)
                for l_match in left_spans
                for r_match in right_spans
                if l_match[-1] == r_match[-1] or l_match[0] == r_match[0] or l_match[1] == r_match[1]
            ]
            for l_pos, r_pos in match_spans:
                for idx in l_pos[1:]:
                    # 首位匹配，但该词不属于右侧近义词，则该词置为+
                    if diff_list[idx][0] in DIFF_COMMON_EQUALS and idx == r_pos[0]:
                        diff_list[idx] = f"{DIFF_INSERT}{diff_list[idx][-1]}"
                        continue
                    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/959#note_244413
                    # example left:基金投资者 right：基金份投资者,  相同的部分跳过
                    if idx in r_pos[1:] or diff_list[idx][0] in DIFF_COMMON_EQUALS:
                        continue
                    diff_list[idx] = f"{diff_list[idx][:-1]}{SPECIAL_REPLACE_CHAR}"
                for idx in r_pos[1:]:
                    diff_list[idx] = f"{DIFF_EQUAL}{diff_list[idx][-1]}"

        return [item for item in diff_list if item[-1] != SPECIAL_REPLACE_CHAR]

    @classmethod
    def _gen_origin_diff_result(
        cls, sentence_left, sentence_right, result, similarity_patterns=None, convert_types=None
    ):
        res = []
        index = 0
        old_index = 0
        prev_old_index = -1
        equal_index = 0
        prev_del_index = -1
        prev_equal_index = -1
        prev_repair_index = 0
        diff_list = list(result)
        for item in diff_list:
            diff_type = item[0]
            if diff_type in [DIFF_EQUAL, DIFF_INSERT]:
                if diff_type == DIFF_EQUAL:
                    equal_index += 1
                    old_equal_index = sentence_left.index_mapping[equal_index - 1]
                    if prev_del_index != -1:
                        res.extend(
                            [f"{DIFF_DELETE}{ch}" for ch in sentence_left.text[prev_del_index + 1 : old_equal_index]]
                        )
                        prev_del_index = old_equal_index
                    prev_equal_index = old_equal_index
                old_index = sentence_right.index_mapping[index]
                index += 1
                if old_index > prev_old_index + 1:
                    res.extend([f"{DIFF_INSERT}{ch}" for ch in sentence_right.text[prev_old_index + 1 : old_index]])
                # 每次遍历到相同diff处, 取上一处与当前内所有diff数据,以范文为基准, 修正同位置符号diff数据
                if diff_type == DIFF_EQUAL and (len(res) > prev_repair_index):
                    res = res[:prev_repair_index] + cls._repair_abnormal_diff(
                        diff_list, res[prev_repair_index:], item[-1], is_head=prev_repair_index == 0
                    )
                    prev_repair_index = len(res)
                res.append(item)
                prev_old_index = old_index
            else:
                equal_index += 1
                old_equal_index = sentence_left.index_mapping[equal_index - 1]
                res.extend(
                    [f"{DIFF_DELETE}{ch}" for ch in sentence_left.text[prev_equal_index + 1 : old_equal_index + 1]]
                )
                prev_equal_index = old_equal_index
                prev_del_index = old_equal_index
            if diff_type == DIFF_EQUAL and len(res) == prev_repair_index + 1:
                prev_repair_index = len(res)

        # 还原左侧文本尾部剩余字符（忽略比较的符号）
        tail_del_text = sentence_left.text[prev_equal_index + 1 :]
        if tail_del_text:
            if tail_del_text[-1] in PUNCTUATION_CHARS:
                tail_del_text = tail_del_text[:-1]
            res.extend([f"{DIFF_DELETE}{ch}" for ch in tail_del_text])
        if old_index != len(sentence_right.text) - 1:
            res.extend([f"{DIFF_R_EQUAL}{ch}" for ch in sentence_right.text[prev_old_index + 1 :]])

        # prev_repair_index之后，左右均存在符号
        left, right = False, False
        for item in res[prev_repair_index:]:
            if item[-1] in JUNK_CHARS:
                if item[0] == DIFF_DELETE:
                    left = True
                else:
                    right = True
            if right and left:
                break
        if left and right:
            res = res[:prev_repair_index] + cls._repair_abnormal_diff(diff_list, res[prev_repair_index:])

        if sentence_right.ends:
            res.append(f"{DIFF_R_EQUAL}{sentence_right.ends}")

        res = cls._ignore_similar_diff_result(res, similarity_patterns=similarity_patterns)
        res = cls._unify_diff_types(res)
        res = cls._ignore_bracket_diff_result(res)
        # fix：标点符号前后均相等，且该符号存在差异，改为equal
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2218
        cls.fix_abnormal_diff(res)
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2385#note_345286
        res = cls._remove_empty_diff_result(res)
        if not convert_types:
            return res, None
        # 数值、日期转换为阿拉伯数字格式，最简化，重新diff
        return cls.convert_result_by_diff_result(res, convert_types)

    @classmethod
    def _remove_empty_diff_result(cls, diff_list: list[str]):
        return [diff for diff in diff_list if diff[-1] != " "]

    @classmethod
    def fix_abnormal_diff(cls, diff_list, format_type="str"):
        diff_end_index = len(diff_list) - 1
        for idx, diff in enumerate(diff_list):
            if diff[0] in DIFF_COMMON_EQUALS or diff[-1] not in PUNCTUATION_CHARS:
                continue
            check_diffs = []
            if 0 < idx < diff_end_index:
                check_diffs = [diff_list[idx - 1], diff_list[idx + 1]]
            elif idx == 0 and idx < diff_end_index:
                check_diffs = [diff_list[idx + 1]]
            elif idx == diff_end_index:
                check_diffs = [diff_list[idx - 1]]
            if all(item[0] in DIFF_COMMON_EQUALS and item[-1] not in PUNCTUATION_CHARS for item in check_diffs):
                if format_type == "tuple":
                    diff_list[idx] = (DIFF_EQUAL, diff[-1])
                else:
                    diff_list[idx] = f"{DIFF_EQUAL}{diff[-1]}"

    @classmethod
    def _unify_diff_types(cls, diff_list):
        res = []
        for _diff in diff_list:
            _type = _diff[0]
            if _diff[0] in (DIFF_R_EQUAL, DIFF_L_EQUAL):
                _type = DIFF_EQUAL
            res.append(f"{_type}{_diff[-1]}")
        return res

    @classmethod
    def _ignore_bracket_diff_result(cls, diff_list):
        for first_brackets, second_brackets in (
            (SYMBOL_BRACKETS_LEFT_CHARS, SYMBOL_BRACKETS_RIGHT_CHARS),
            (SYMBOL_BRACKETS_RIGHT_CHARS, SYMBOL_BRACKETS_LEFT_CHARS),
        ):
            diff_list = cls._move_bracket_to_equal_position(diff_list, first_brackets)
            diff_list = cls._fix_bracket_diff_results(diff_list, second_brackets)
            diff_list.reverse()
        return diff_list

    @classmethod
    def _fix_bracket_diff_results(cls, diff_list, brackets):
        prev = None
        prev_idx = -1
        is_equal = False
        for idx, diff in enumerate(diff_list):
            if diff[-1] not in SYMBOL_BRACKETS_CHARS:
                if diff[0] == DIFF_EQUAL and prev:
                    is_equal = True
                continue

            if not prev:
                prev = diff
                prev_idx = idx
                is_equal = False
                continue
            if diff[-1] in brackets:
                if is_equal:
                    for _idx in range(prev_idx, idx):
                        if diff_list[_idx][-1] in SYMBOL_BRACKETS_CHARS:
                            diff_list[_idx] = f"{DIFF_EQUAL}{diff_list[_idx][-1]}"
                prev = None
                prev_idx = -1
        if is_equal and prev_idx > 0:
            diff_list[prev_idx] = f"{DIFF_EQUAL}{diff_list[prev_idx][-1]}"

        return diff_list

    @classmethod
    def _move_bracket_to_equal_position(cls, diff_list, brackets):
        """
        向右移动括号至首次非delete位置
        https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1879
        """
        prev = None
        prev_idx = -1
        right_mapping, left_mapping = cls._split_diff_mapping(diff_list)
        right_mapping = {val: key for key, val in right_mapping.items()}
        left_mapping = {val: key for key, val in left_mapping.items()}
        for idx, diff in enumerate(diff_list):
            char = diff[-1]
            diff_type = diff[0]
            if char in brackets:
                if prev:
                    prev = None
                    prev_idx = -1
                if not prev:
                    prev = diff
                    prev_idx = idx
                continue
            if not prev:
                continue
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2065
            # 非brackets，且该字符在对应文本中的位置在prev后面
            if char not in brackets:
                # 如果括号为equal,则应与当前字符在同一个mapping查找位置
                diff_type = prev[0] if diff_type == DIFF_EQUAL else diff_type
                prev_type = diff_type if prev[0] == DIFF_EQUAL else prev[0]
                if diff_type != prev_type:
                    continue
                origin_pos = left_mapping[idx] if diff_type == DIFF_DELETE else right_mapping[idx]
                prev_origin_idx = left_mapping[prev_idx] if prev_type == DIFF_DELETE else right_mapping[prev_idx]
                if origin_pos > prev_origin_idx:
                    diff_list.insert(idx, prev)
                    del diff_list[prev_idx]
                    prev = None
                    prev_idx = -1
        return diff_list

    @classmethod
    def convert_result_by_diff_result(cls, diff_list, convert_types):
        # 标记需要转换的内容
        right_mapping, left_mapping = cls._split_diff_mapping(diff_list)

        left_diff_str = "".join([diff_list[idx][-1] for idx in left_mapping.values()])
        right_diff_str = "".join([diff_list[idx][-1] for idx in right_mapping.values()])
        left = ConvertText(left_diff_str, convert_types)
        right = ConvertText(right_diff_str, convert_types)
        left.format_text_by_convert_types()
        right.format_text_by_convert_types()
        if not (left.convert_mapping or right.convert_mapping):
            return diff_list, None
        matcher = difflib.SequenceMatcher()
        matcher.set_seq1(left.convert_text)
        matcher.set_seq2(right.convert_text)
        # 复原已转换内容
        return cls.restore_diff_results(left, right, list(cls._compare(matcher))), matcher.ratio()

    @classmethod
    def restore_diff_results(
        cls, left_convert: ConvertText, right_convert: ConvertText, diff_list: list[str]
    ) -> list[str]:
        diff_list = list(diff_list)
        convert_mapping = cls.merge_convert_mapping(left_convert, right_convert, diff_list)
        for (p_start, p_end), value_dict in sorted(convert_mapping.items(), key=lambda x: x[0][0], reverse=True):
            left_dict = value_dict.get("left")
            right_dict = value_dict.get("right")
            diff_vals = []
            if left_dict and right_dict:
                # 左右值相等，直接用原文
                # 左右值不等或该位置内仅存在一方内容，则还原对应原内容
                if left_dict["format_val"] == right_dict["format_val"]:
                    diff_vals = [f"{DIFF_EQUAL}{char}" for char in right_dict["origin_val"]]
                else:
                    diff_vals = [f"{DIFF_DELETE}{char}" for char in left_dict["origin_val"]]
                    diff_vals += [f"{DIFF_INSERT}{char}" for char in right_dict["origin_val"]]
            elif left_dict:
                diff_vals = [f"{DIFF_DELETE}{char}" for char in left_dict["origin_val"]]
            elif right_dict:
                diff_vals = [f"{DIFF_INSERT}{char}" for char in right_dict["origin_val"]]
            diff_list = cls.restore_diff_list_by_pos(diff_list, diff_vals, p_start, p_end)
        return diff_list

    @classmethod
    def restore_diff_list_by_pos(cls, diff_list, diff_val, start, end):
        if not diff_val:
            return diff_list
        return diff_list[:start] + diff_val + diff_list[end + 1 :]

    @classmethod
    def merge_convert_mapping(cls, left_convert: ConvertText, right_convert: ConvertText, diff_list: list[str]):
        """
        需还原位置的内容根据diff出现的顺序进行排序，左右两侧如属于同位置，则diff结果一致
        位置可能不完全一致，如果左右两侧diff的位置存在交集，则认定两处位置最大区间（并集）为需要合并处理的位置
        key为前后闭区间
        """
        right_mapping, left_mapping = cls._split_diff_mapping(diff_list)
        convert_mapping = defaultdict(dict)
        for pos, val_dict in left_convert.convert_mapping.items():
            start, end = map(int, pos.split("_"))
            convert_mapping[(left_mapping[start], left_mapping[end - 1])]["left"] = val_dict
        for pos, val_dict in right_convert.convert_mapping.items():
            start, end = map(int, pos.split("_"))
            start, end = right_mapping[start], right_mapping[end - 1]
            # merge conflict content
            for (p_start, p_end), value_dict in sorted(convert_mapping.items(), key=lambda x: x[0][0], reverse=True):
                if (p_start <= start <= p_end or p_start <= end <= p_end) or (
                    start <= p_start <= end or start <= p_end <= end
                ):
                    del convert_mapping[(p_start, p_end)]
                    key = (min(p_start, start), max(end, p_end))
                    convert_mapping[key]["left"] = value_dict["left"]
                    convert_mapping[key]["right"] = val_dict
                    break
            else:
                convert_mapping[(start, end)]["right"] = val_dict

        return convert_mapping

    @staticmethod
    def _split_diff_mapping(diff_list, exclude_ignore_punctuation=False):
        right_mapping, left_mapping = {}, {}
        right_index, left_index = 0, 0
        for idx, item in enumerate(diff_list):
            diff_type = item[0]
            if diff_type in DIFF_COMMON_EQUALS:
                is_match_pos = False
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2145
                # 仅在处理近义词场景下, 排除因忽略标点符号等特殊符号差异导致左右内容互相混淆
                if exclude_ignore_punctuation:
                    if diff_type == DIFF_L_EQUAL:
                        is_match_pos = True
                        left_mapping[left_index] = idx
                        left_index += 1
                    if diff_type == DIFF_R_EQUAL:
                        is_match_pos = True
                        right_mapping[right_index] = idx
                        right_index += 1
                if not is_match_pos:
                    right_mapping[right_index] = idx
                    left_mapping[left_index] = idx
                    right_index += 1
                    left_index += 1
            elif diff_type == DIFF_INSERT:
                right_mapping[right_index] = idx
                right_index += 1
            else:
                left_mapping[left_index] = idx
                left_index += 1
        return right_mapping, left_mapping

    @classmethod
    def _repair_abnormal_diff(cls, origin_diff_list, diff_list, next_word=None, is_head=False):
        # 取相同diff中间的差异块, 忽略同位置的符号差异
        # example: left: 私募，托管人 right:哈私募,、托管人,
        # diff: 私募<s>,、</s><u>，</u><s>哈</s>私募   --> 私募<s>,、</s><s>哈</s>私募
        if not diff_list:
            return diff_list
        if all(_val[0] == DIFF_DELETE for _val in diff_list):
            if all(_val[-1] in PUNCTUATION_CHARS for _val in diff_list):
                return []
            return diff_list

        right_mapping, left_mapping = cls._split_diff_mapping(diff_list)

        left_diff_str = "".join([diff_list[idx][-1] for idx in left_mapping.values()])
        right_diff_str = "".join([diff_list[idx][-1] for idx in right_mapping.values()])
        l_start, r_start = 0, 0
        if is_head:
            l_start = cls._repair_number_from_text(
                origin_diff_list, diff_list, left_mapping, left_diff_str, is_left=True
            )
            r_start = cls._repair_number_from_text(origin_diff_list, diff_list, right_mapping, right_diff_str)

        # 左侧或右侧无文本，则该段在忽略段首序号差异后，其余差异保留
        if not (left_diff_str and right_diff_str) and any(
            char not in PUNCTUATION_CHARS for char in (left_diff_str or right_diff_str)
        ):
            return diff_list

        # 数值中的符号保留差异
        left_range, right_range = [], []
        if next_word:
            left_num_matcher = P_NUMBER.nexts(left_diff_str + next_word)
            right_num_matcher = P_NUMBER.nexts(right_diff_str + next_word)
            left_range = list(range(left_num_matcher.start(), left_num_matcher.end())) if left_num_matcher else []
            right_range = list(range(right_num_matcher.start(), right_num_matcher.end())) if right_num_matcher else []

        right_datas = cls._split_text_by_symbol_chars(right_diff_str, right_mapping, right_range, r_start)
        left_datas = cls._split_text_by_symbol_chars(left_diff_str, left_mapping, left_range, l_start)
        insert_mapping = defaultdict(list)
        for left_indexes, right_indexes in reversed(list(zip_longest(left_datas, right_datas, fillvalue=[]))):
            if not right_indexes:
                continue
            insert_pos = min(right_indexes + left_indexes, key=lambda x: x[1])[1]
            for _, idx in left_indexes + right_indexes:
                diff_list[idx] = f"{diff_list[idx][0]}{SPECIAL_REPLACE_CHAR}"
            insert_mapping[insert_pos].append(right_indexes)
        for pos, index_list in sorted(insert_mapping.items(), reverse=True):
            for r_indexes in index_list:
                for char, _ in r_indexes[::-1]:
                    diff_list.insert(pos, f"{DIFF_R_EQUAL}{char}")

        return [item for item in diff_list if item[-1] != SPECIAL_REPLACE_CHAR]

    @classmethod
    def _split_text_by_symbol_chars(cls, text, char_mapping, exclude_pos: list, start_pos=0):
        # 根据需要忽略比较的字符进行拆分，多个字符连续拆为一组
        split_indexes = []
        match_indexes = []
        for idx in range(start_pos, len(text)):
            char = text[idx]
            if char in PUNCTUATION_CHARS and (not NumberUtil.P_DOT.search(char) or idx not in exclude_pos):
                match_indexes.append((char, char_mapping[idx]))
                continue
            if not match_indexes:
                continue
            split_indexes.append(match_indexes)
            match_indexes = []
        if match_indexes:
            split_indexes.append(match_indexes)
        return split_indexes

    @classmethod
    def _repair_number_from_text(cls, origin_diff_list, diff_list, diff_mapping, diff_text, is_left=False):
        # 头部可能会出现
        # ["- 6", "- .", "+ 6", "+ .", "- 测"] -> ["  6", "  .","- 测"]
        # ["- 6", "- .", "- 测"] -> ["  6", "  .","- 测"]
        # ["- 6", "- .", "+ 6", "+ 1", "+ .", "- 测"] -> ["  6", "  1","  .", "- 测"]
        # ["- 6", "- .", "- 测"] -> ["- 测"]
        # ["- 测", "- 试", "- 6"] -> ["- 测"]
        end = 0
        match = P_NUMBERING.nexts(diff_text)
        if match:
            # 判断当前序号是否为日期，是则跳过
            right_mapping, left_mapping = cls._split_diff_mapping(origin_diff_list)
            left_diff_str = "".join([origin_diff_list[idx][-1] for idx in left_mapping.values()])
            right_diff_str = "".join([origin_diff_list[idx][-1] for idx in right_mapping.values()])
            origin_diff_text = left_diff_str if is_left else right_diff_str
            include_head = origin_diff_text.startswith(diff_text)
            start, end = match.span()
            # diff_text可能为补充的词，origin中已剔除，不包含则无需检查序号是否为日期
            if include_head:
                date_res = P_DATE.nexts(origin_diff_text)
                if date_res and (
                    date_res.start() <= start <= date_res.end() or date_res.start() <= end <= date_res.end()
                ):
                    return 0
            match_indexes = [diff_mapping[idx] for idx in range(start, end)]
            if is_left:
                # 左侧首位序号忽略,以右侧为主
                for idx in match_indexes:
                    if diff_list[idx][0] == DIFF_EQUAL:
                        continue
                    diff_list[idx] = f"{diff_list[idx][0]}{SPECIAL_REPLACE_CHAR}"
            else:
                # 右侧首位的序号数据前置,删除在diff列表中偏后的旧数据,不会影响原始数据长度
                temp_list = []
                for idx in match_indexes:
                    temp_list.append(f"{DIFF_EQUAL}{diff_list[idx][-1]}")
                for idx in match_indexes[::-1]:
                    diff_list.pop(idx)
                for val in temp_list[::-1]:
                    diff_list.insert(0, val)
        return end

    @staticmethod
    def _find_seq_matched(diff_mapping, sentences_left, sentences_right):
        # AABB  AABBXXXXXBB  连续的句子都找到了 就算找到了
        min_right = len(sentences_right)
        max_right = 0

        for (_, right_index), item in diff_mapping.items():
            if item.right.index < min_right:
                min_right = right_index
            if item.right.index > max_right:
                max_right = right_index + 1

        if not max_right:
            return None

        left_len = len(sentences_left)
        record = [[[0, 0] for i in range(max_right + 1)] for j in range(left_len + 1)]
        max_len = 0
        left_end = 0
        right_end = 0
        max_ratio = 0

        for i in range(left_len):
            for j in range(min_right, max_right):
                if diff := diff_mapping.get((i, j)):
                    prev_record = record[i][j]
                    current_record = record[i + 1][j + 1]
                    current_record[0] = prev_record[0] + diff.ratio
                    current_record[1] = prev_record[1] + 1
                    if current_record[0] > max_ratio:
                        max_ratio = current_record[0]
                        max_len = current_record[1]
                        left_end = i + 1
                        right_end = j + 1

        #  对于存在完整匹配的情况（包括多个完整匹配） 直接取序列连续部分
        if max_len == left_len:
            return [diff_mapping[index, right_end - max_len + index] for index in range(left_end - max_len, left_end)]

        return None

    def _diff_paragraphs(self):
        diff_mapping = self.search_all_sentences(
            self.sentences_left,
            self.sentences_right,
            self.ratio,
            similarity_patterns=self.similarity_patterns,
            convert_types=self.convert_types,
        )

        if self.max_width:
            diff_mapping = self._remove_untrusted_item(diff_mapping, self.max_width)

        seq_matched = self._find_seq_matched(diff_mapping, self.sentences_left, self.sentences_right)
        if seq_matched:
            diff_results = self._render_diff_result(
                self.sentences_left,
                self.sentences_right,
                seq_matched,
                self.fill_paragraph,
            )
        else:
            diff_results = self._render_diff_result(
                self.sentences_left,
                self.sentences_right,
                self.group_sentences(self.sentences_left, self.sentences_right, diff_mapping),
                self.fill_paragraph,
            )
        return self.merge_diff_results_by_break_sentence(diff_results)

    @classmethod
    def merge_diff_results_by_break_sentence(cls, diff_results):
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2140#note_325297
        # 仅处理前后段落连续，且一处为全部+或全部-，另一处尾部或头部的类型与之相反
        # e.g [
        #    "[('-', '其'), ('-', '中'), ('-', '，'), ('-', '合')]"
        #    "[('+', '其'), ('+', '中'), (' ', '，'), ('+', '合'), (' ', '约'), (' ', '面'), (' ', '值')]"
        # ]
        prev_diff = None
        for diff in diff_results:
            if not any(_diff_val[0] != DIFF_EQUAL for _diff_val in diff.diff):
                prev_diff = None
                continue
            if not prev_diff:
                prev_diff = diff
                continue
            if cls.merge_diff_results(prev_diff, diff) or cls.merge_diff_results(diff, prev_diff):
                prev_diff = None
            elif cls.merge_equal_diff_results(prev_diff, diff):
                prev_diff = None
            else:
                prev_diff = diff

        for diff in diff_results:
            if not diff.diff:
                diff_results.remove(diff)
        return diff_results

    @staticmethod
    def merge_diff_results(single_diff: DiffResult, multi_diff: DiffResult):
        diff_types = {_diff_val[0] for _diff_val in single_diff.diff}
        if len(diff_types) != 1 or diff_types == {
            DIFF_EQUAL,
        }:
            return False

        opposite_diffs = [diff_val[-1] for diff_val in single_diff.diff]
        multi_diff_vals = [diff_val[-1] for diff_val in multi_diff.diff]
        index = "".join(multi_diff_vals).find("".join(opposite_diffs))

        if index != -1 and (index == 0 or index + len(opposite_diffs) == len(multi_diff_vals)):
            # 除括号、标点符号外的字符 diff类型相反
            for left, right in zip(single_diff.diff, multi_diff.diff[index : len(single_diff.diff)]):
                if left[-1] in JUNK_CHARS:
                    continue
                if left[0] == right[0]:
                    return False
            single_diff.diff = [(DIFF_EQUAL, diff_val[-1]) for diff_val in single_diff.diff]
            multi_diff.diff = multi_diff.diff[0:index] + multi_diff.diff[index + len(single_diff.diff) :]
            single_diff.ratio = 1.0
            if multi_diff.diff:
                multi_diff.ratio = len([1 for diff_val in multi_diff.diff if diff_val[0] == DIFF_EQUAL]) / len(
                    multi_diff.diff
                )
            else:
                multi_diff.ratio = 0
            return True
        return False

    @classmethod
    def merge_equal_diff_results(cls, prev_diff: DiffResult, current_diff: DiffResult):
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2262
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2263
        # prev最后连续相同类型的差异字符与current_diff开始连续相同类型的差异字符
        # 类型相反,内容去除标点符号之后相同
        prev_group_results = cls.split_diff_result_by_diff_type(prev_diff)
        current_group_results = cls.split_diff_result_by_diff_type(current_diff)
        prev_start, prev_content, prev_end_results = prev_group_results[-1]
        current_start, current_content, current_start_results = current_group_results[0]
        prev_content = P_SUB_PUNCTUATION.sub("", prev_content)
        current_content = P_SUB_PUNCTUATION.sub("", current_content)
        if prev_content != current_content:
            return False
        prev_diff_types = {diff_val[0] for diff_val in prev_end_results}
        current_diff_types = {diff_val[0] for diff_val in current_start_results}
        if len(prev_diff_types) != 1 or len(current_diff_types) != 1:
            return False
        if (
            any(DIFF_EQUAL in diff_types for diff_types in (prev_diff_types, current_diff_types))
            or prev_diff_types == current_diff_types
        ):
            return False

        prev_end = len(prev_diff.diff)
        current_end = len(current_diff.diff) if len(current_group_results) < 2 else current_group_results[1][0]

        if prev_diff_types == {
            DIFF_INSERT,
        }:
            prev_diff.diff = prev_diff.diff[0:prev_start] + [
                (DIFF_EQUAL, diff[-1]) for diff in prev_diff.diff[prev_start:prev_end]
            ]
            current_diff.diff = current_diff.diff[current_end:]
        else:
            prev_diff.diff = prev_diff.diff[0:prev_start]
            current_diff.diff = [
                (DIFF_EQUAL, diff[-1]) for diff in current_diff.diff[current_start:current_end]
            ] + current_diff.diff[current_end:]
        cls.fix_abnormal_diff(prev_diff.diff, format_type="tuple")
        cls.fix_abnormal_diff(current_diff.diff, format_type="tuple")

        prev_diff.ratio = (
            (len([diff for diff in prev_diff.diff if diff[0] == DIFF_EQUAL]) / len(prev_diff.diff))
            if prev_diff.diff
            else 0
        )
        current_diff.ratio = (
            (len([diff for diff in current_diff.diff if diff[0] == DIFF_EQUAL]) / len(current_diff.diff))
            if current_diff.diff
            else 0
        )
        return True

    @staticmethod
    def split_diff_result_by_diff_type(diff_result: DiffResult):
        group_results = defaultdict(list)
        pos = 0
        prev_diff = None
        for idx, diff in enumerate(diff_result.diff):
            if not prev_diff:
                prev_diff = diff
                group_results[pos].append(diff)
                continue
            if diff[0] != prev_diff[0]:
                prev_diff = diff
                pos = idx
            group_results[pos].append(diff)
        return [
            (pos, "".join(diff[-1] for diff in diffs), diffs)
            for pos, diffs in group_results.items()
            if any(diff[-1] not in PUNCTUATION_CHARS for diff in diffs)
        ]

    @classmethod
    def search_sentences(cls, paragraphs_left, paragraphs_right, min_ratio=0.7):
        sentences_left = Sentence.create_sentences(paragraphs_left, split=False)
        sentences_right = Sentence.create_sentences(paragraphs_right, split=False)

        assert len(sentences_left) == 1

        return list(cls.search_all_sentences(sentences_left, sentences_right, min_ratio).values())

    @classmethod
    def search_split_sentences(
        cls, paragraphs_left, paragraphs_right, min_ratio=0.7
    ) -> list[tuple[int, list[DiffResult]]]:
        sentences_left = Sentence.create_sentences(paragraphs_left, split=True)
        sentences_right = Sentence.create_sentences(paragraphs_right, split=True)

        assert len(paragraphs_left) == 1

        diff_mapping = cls.search_all_sentences(sentences_left, sentences_right, min_ratio)

        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2371
        seq_matched = cls._find_seq_matched(diff_mapping, sentences_left, sentences_right)
        if seq_matched:
            diff_results = cls._render_diff_result(
                sentences_left,
                sentences_right,
                seq_matched,
                False,
            )
        else:
            diff_results = cls._render_diff_result(
                sentences_left,
                sentences_right,
                list(diff_mapping.values()),
                False,
            )

        group_results = cls._group_results_by_paragraph(diff_results)
        return [
            (right_idx[0], child_results)
            for child_results in group_results
            if (right_idx := [diff.right.para_index for diff in child_results if diff.right])
        ]

    @classmethod
    def search_all_sentences(
        cls, sentences_left, sentences_right, min_ratio, similarity_patterns=None, convert_types=None
    ):
        matcher = difflib.SequenceMatcher()
        diff_mapping = {}
        left_count = len(sentences_left)
        left_mapping = {}
        for sentence_right in sentences_right:
            if P_IGNORE_TEXT.search(sentence_right.text):
                continue
            matcher.set_seq2(sentence_right.cleaned_text)
            right_text_len = len(sentence_right.cleaned_text)
            right = None
            new_matcher = None

            for sentence_left in sentences_left:
                left_text_len = len(sentence_left.cleaned_text)
                if left_text_len == 0:
                    continue
                start_index = sentence_right.cleaned_text.find(sentence_left.cleaned_text)
                if (
                    start_index > -1
                    and sentence_left.index == 0
                    and start_index + left_text_len == right_text_len
                    and (
                        start_index == 0
                        or sentence_right.text[sentence_right.index_mapping[start_index] - 1] in JUNK_CHARS
                    )
                ):
                    # 左侧在右侧中部匹配,且为一句话,左侧模板可在右侧找到,且匹配末尾的下一个字符是需要忽略的,则直接返回
                    diff_mapping[(sentence_left.index, sentence_right.index)] = DiffResult(
                        left=sentence_left,
                        right=sentence_right,
                        ratio=1.0,
                        diff=[
                            (DIFF_EQUAL, item)
                            for item in sentence_right.get_origin_by_range(start_index, start_index + left_text_len)
                        ],
                    )
                elif (
                    sentence_left.index == left_count - 1
                    and start_index == 0
                    and (
                        start_index + left_text_len == right_text_len
                        or sentence_right.text[sentence_right.index_mapping[start_index + left_text_len] - 1]
                        in JUNK_CHARS
                    )
                ):
                    # 左右头部匹配,且为一句话,左侧模板可在右侧找到,且匹配末尾的下一个字符是需要忽略的,则直接返回
                    diff_mapping[(sentence_left.index, sentence_right.index)] = DiffResult(
                        left=sentence_left,
                        right=sentence_right,
                        ratio=1.0,
                        diff=[
                            (DIFF_EQUAL, item)
                            for item in sentence_right.get_origin_by_range(start_index, start_index + left_text_len - 1)
                        ],
                    )
                else:
                    # 长度比例小于最小相似度阈值，直接跳过
                    _min_ratio = min(cls.MIN_RATIO, min_ratio)
                    numerator, denominator = (
                        (left_text_len, right_text_len)
                        if left_text_len < right_text_len
                        else (right_text_len, left_text_len)
                    )
                    if numerator / denominator < _min_ratio:
                        continue

                    matcher.set_seq1(sentence_left.cleaned_text)
                    if min(matcher.real_quick_ratio(), matcher.quick_ratio()) < _min_ratio:
                        continue
                    if not new_matcher:
                        new_matcher = difflib.SequenceMatcher()
                        right = Sentence.create_sentence_without_brackets(sentence_right)
                        new_matcher.set_seq2(right.cleaned_text)

                    if not (left := left_mapping.get(sentence_left.index)):
                        left = Sentence.create_sentence_without_brackets(sentence_left)
                        left_mapping[left.index] = left
                    new_matcher.set_seq1(left.cleaned_text)

                    compare_result, ratio = cls._gen_origin_diff_result(
                        left,
                        right,
                        cls._compare(new_matcher),
                        similarity_patterns=similarity_patterns,
                        convert_types=convert_types,
                    )
                    ratio = ratio or new_matcher.ratio()
                    if ratio < min_ratio:
                        continue
                    ratio = 1.0 if all(item[0] == DIFF_EQUAL for item in compare_result) else ratio
                    diff_mapping[(sentence_left.index, sentence_right.index)] = DiffResult(
                        left=sentence_left,
                        right=sentence_right,
                        ratio=ratio,
                        diff=[(item[0], item[-1]) for item in compare_result],
                    )
        return diff_mapping

    @property
    def result_text(self):
        return "\n".join(["".join((item.text_diff_content for item in group)) for group in self.grouped_results])


if __name__ == "__main__":
    _para_a = ["好好学习天天向上", "学习强国"]
    _para_b = [
        "天天向上好好学习",
        "好好学习天天向下",
        "123",
        "学习强国",
        "好好学习天天向上11111",
        "好好学习天天学习向上",
        "这个完全不一样，看你怎么diff",
        "好",
    ]
    ss = ParagraphSimilarity(_para_a, _para_b)
    ss.print_result()
