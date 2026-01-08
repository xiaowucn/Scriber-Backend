from itertools import chain

from remarkable.common.pattern import PatternCollection
from remarkable.predictor.ecitic_predictor.models.common import R_SPECIAL_TIPS
from remarkable.predictor.ecitic_predictor.models.splitter_mixin import ParaSplitterMixin
from remarkable.predictor.models.middle_paras import MiddleParas
from remarkable.predictor.models.syllabus_elt_v2 import SyllabusEltV2
from remarkable.predictor.schema_answer import CharResult

P_SERIAL_NUMBER = PatternCollection(
    [
        r"^\s*([（(]?\d+[）)、]?|[①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮])",
        r"^\s*[(（【]?\s*[➢0-9一二三四五六七八九十]+\s*[)）】]",
        r"^\s*[(（【]?\s*[➢0-9一二三四五六七八九十]+\s*[,.．，、\s]+[)）】]?\s*",
    ]
)

P_SIGN = PatternCollection([r"[%％]"])

P_SPLITS = PatternCollection([r"[。；;](?![）)])"])

LEFT_BRACKET = r"{〔【（("
RIGHT_BRACKET = r")）】〕}"


def remove_unpaired_paren(chars: list[dict[str, str]]) -> list[dict[str, str]]:
    """移除不匹配的括号，保留配对的括号"""
    if not chars:
        return chars

    # 括号类型映射 - 中英文圆括号可以互相匹配
    BRACKET_PAIRS = {
        "(": ")",
        "（": "）",  # 默认配对
        "【": "】",
        "〔": "〕",
        "{": "}",
    }

    # 使用栈来追踪配对的括号
    stack = []
    paired_indices = set()

    # 第一遍：找到所有配对的括号
    for i, char in enumerate(chars):
        text = char["text"]
        if text in LEFT_BRACKET:
            stack.append((i, text))
        elif text in RIGHT_BRACKET:
            # 从栈顶开始寻找匹配的左括号
            for j in range(len(stack) - 1, -1, -1):
                left_index, left_text = stack[j]
                # 检查是否匹配（中英文圆括号可以互相匹配）
                expected_right = BRACKET_PAIRS.get(left_text)
                if expected_right == text or (
                    # 中英文圆括号互相匹配
                    (left_text == "(" and text in "）)")
                    or (left_text == "（" and text in "）)")
                    or
                    # 其他括号严格匹配
                    (left_text in "〔【{" and expected_right == text)
                ):
                    # 找到配对的左括号
                    paired_indices.add(left_index)
                    paired_indices.add(i)
                    stack.pop(j)
                    break

    # 只保留配对的括号
    return [
        char
        for i, char in enumerate(chars)
        if i in paired_indices or (chars[i]["text"] not in LEFT_BRACKET and chars[i]["text"] not in RIGHT_BRACKET)
    ]


class RatioSplitter:
    """
    投资比例拆分器
    拆分规则：
        1、只处理带有序号、含有%的句子
        2、按。；;拆分
    """

    def split(self, predict_elements: list) -> list:
        element_results = []
        exclude_indices = set()
        for predict_element in predict_elements:
            if predict_element["index"] in exclude_indices:
                continue
            if page_merged_paragraph := predict_element.get("page_merged_paragraph"):
                if indices := page_merged_paragraph["paragraph_indices"]:
                    exclude_indices.update(indices)
                paragraph_text = page_merged_paragraph.get("text")
            else:
                paragraph_text = predict_element.get("text")
            if not paragraph_text:
                continue
            chars = predict_element["chars"]
            if temp_match := R_SPECIAL_TIPS.nexts(paragraph_text):
                # 特别提示，直接按段落展示, 不用拆分
                element_results.append(
                    CharResult(
                        element=predict_element,
                        chars=chars[temp_match.end() :],
                    )
                )
                continue
            match_no = P_SERIAL_NUMBER.nexts(paragraph_text)
            match_sign = P_SIGN.nexts(paragraph_text)
            if not match_no and not match_sign:
                continue

            # 按照拆分符拆分
            start_index = 0
            sub_sentences_chars = []
            for match in chain(P_SPLITS.finditer(paragraph_text), (None,)):
                start, end = match.span() if match else (len(paragraph_text), 0)
                if temp_chars := chars[start_index:start]:
                    temp_chars = remove_unpaired_paren(temp_chars)
                    sub_sentences_chars.append(temp_chars)
                start_index = end
            # 如果有序号，把序号添加到每一个组里面，第一组不需要
            if match_no:
                # 获取序号的chars
                match_no_chars = chars[match_no.start() : match_no.end()]
                for index, sub in enumerate(sub_sentences_chars[1:]):
                    sub_sentences_chars[index + 1] = match_no_chars + sub
            for item in sub_sentences_chars:
                element_results.append(
                    CharResult(
                        element=predict_element,
                        chars=item,
                    )
                )

        return element_results


class InvestmentRatioMiddleParas(ParaSplitterMixin, MiddleParas, RatioSplitter):
    pass


class InvestmentRatioSyllabus(ParaSplitterMixin, SyllabusEltV2, RatioSplitter):
    pass
