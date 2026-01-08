"""段落中文本内容提取"""

import itertools
import re
from collections import Counter
from functools import reduce

import rjieba as jieba

from remarkable.common.util import clean_txt, cut_words, index_in_space_string, is_none_or_whitespace
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.plugins.predict.models.model_base import SPECIAL_ATTR_PATTERNS, PredictModelBase
from remarkable.predictor.predict import CharResult, ResultOfPredictor
from remarkable.service.predictor import get_result_of_vmsp, is_paragraph_elt


def match_pattern(pattern, text, max_gap=99):
    if not pattern:
        return text == ""
    return re.search(vmsp2regex(pattern), text) is not None


def generate_texts_around(pattern, words):
    texts_around = (None, None)
    match = re.search(re.escape(pattern), words)
    if match:
        texts_around = (words[: match.span()[0]], words[match.span()[-1] :])
    return texts_around


def get_answer_text_parts(para, answer_boxes):
    left_chars = []
    answer_chars = []
    right_chars = []
    for char in para.get("chars", []):
        if not any(PdfinsightReader.box_in_box(char["box"], box["box"]) for box in answer_boxes):
            if not answer_chars:
                left_chars.append(char)
            else:
                right_chars.append(char)
        else:
            answer_chars.append(char)

    return ["".join([c["text"] for c in chars]) for chars in (left_chars, answer_chars, right_chars)]


def text2pattern(text):
    text = re.sub(r"\s+", "", pattern_escape(text))
    text = re.sub(SPECIAL_ATTR_PATTERNS["number"][0], r"\d+", text)
    text = re.sub(r"[(（【]+", r"[(（[【]+", text)
    text = re.sub(r"[)）】]+", r"[)）\]】]+", text)
    text = re.sub(r"[:：]+", r"[:：]+", text)
    return text


GREEK_MAP = {"δ": SPECIAL_ATTR_PATTERNS["number"][0], "∵": r"[(（【]+", "∴": r"[)）】]+", "⊕": r"[:：]+"}


def greek_encode_text(text):
    text = re.sub(r"\s+", "", text)
    for char, reg in GREEK_MAP.items():
        text = re.sub(reg, char, text)
    return text


def greek_decode_text(text):
    # text = re.sub(r"δ", r"\d+", text)
    for char, reg in GREEK_MAP.items():
        text = re.sub(char, reg, text)
    return text


def vmsp2regex(pattern, max_gap=99):
    return ".*".join([pattern_escape(t) for t in pattern])


def pattern_escape(text):
    # re.escape will add \\ to each cn char
    return re.sub(r"([.?+*^$|{}()\[\]\\-])", r"\\\1", text)


def generate_vmsp_pattern(text_list, cut_side="right", allow_empty=True):
    """
    , minsup=0.1, max_groups=2, max_chars=20, min_length=1
    """

    def run_vmsp(texts, minsup, max_groups, max_chars, min_length):
        inputs = []
        input_str = []
        words_dict = {}
        convert_str = "@CONVERTED_FROM_TEXT\n"
        for text in texts:
            vmsp_input = cut_words(text, cut_side, max_words=max_chars)
            for word in vmsp_input:
                if word not in words_dict:
                    words_dict[word] = len(words_dict)
                    convert_str += "@ITEM={}={}\n".format(words_dict[word], word)
            if vmsp_input:
                vmsp_input_str = " -1 ".join([str(words_dict[word]) for word in vmsp_input]) + " -1 -2\n"
                inputs.append(vmsp_input_str)
                input_str.append(vmsp_input)
        convert_str += "@ITEM=-1=|\n"
        patterns = get_result_of_vmsp(convert_str + "".join(inputs), minsup=minsup)
        return [p for p in patterns if len(p) >= min_length]

    patterns = []
    if "" in text_list:
        if allow_empty:
            patterns.append("")
        text_list = [t for t in text_list if t]

    last_minsup = 1 / (len(text_list) + 1)
    vmsp_configs = [(0.5, 2, 10, 1), (0.2, 2, 10, 2), (0.1, 2, 10, 2), (last_minsup, 2, 10, 2), (last_minsup, 2, 10, 1)]
    vmsp_configs_idx = 0
    while text_list:
        if vmsp_configs_idx >= len(vmsp_configs):
            print("%s items not recall" % len(text_list))
            break
        config = vmsp_configs[vmsp_configs_idx]
        _patterns = run_vmsp(text_list, *config)
        text_left = []
        for text in text_list:
            if not any(match_pattern(p, text) for p in _patterns):
                text_left.append(text)
        if _patterns:
            patterns.extend(_patterns)
            text_list = text_left
        else:
            vmsp_configs_idx += 1

    return patterns


def generate_texts_around_pattern(texts_around):
    """
    left: (vmsp, boundary)
    right: (vmsp, boundary)
    """
    before_patterns = []
    for _pattern in generate_vmsp_pattern([texts[0] for texts in texts_around], cut_side="left") or [""]:
        _boundary = Counter()
        # for _left, _, _ in texts_around:
        #     if match_pattern(_pattern, _left):
        #         _words = list(jieba.cut(_left))
        #         _boundary.update([_words[-1] if _words else ""])
        before_patterns.append((_pattern, [c[0] for c in _boundary.most_common()]))

    after_patterns = []
    for _pattern in generate_vmsp_pattern([texts[2] for texts in texts_around], cut_side="right") or [""]:
        _boundary = Counter()
        # for _, _, _right in texts_around:
        #     if match_pattern(_pattern, _right):
        #         _words = list(jieba.cut(_right))
        #         _boundary.update([_words[0] if _words else ""])
        after_patterns.append((_pattern, [c[0] for c in _boundary.most_common()]))
    # crude_patterns = list(itertools.product(before_patterns, after_patterns)) + list(
    #     zip(before_patterns, [""] * len(before_patterns))) + list(zip([""] * len(after_patterns), after_patterns))
    crude_patterns = list(itertools.product(before_patterns, after_patterns))
    return crude_patterns


def generate_texts_inside_pattern(texts):
    encoded_answer_texts = [greek_encode_text(t[1]) for t in texts]
    patterns = generate_vmsp_pattern(encoded_answer_texts, cut_side="ends", allow_empty=False)
    answer_regex_patterns = [greek_decode_text(vmsp2regex(p)) for p in patterns]
    return [p for p in answer_regex_patterns if len(p) >= 2]


def generate_answer_boundary(texts):
    boundary = Counter()
    for _left, _, _right in texts:
        _words = list(jieba.cut(_left))
        lword = _words[-1] if _words else ""
        _words = list(jieba.cut(_right))
        rword = _words[0] if _words else ""
        boundary.update(["|||".join([lword, rword])])
    return [p[0].split("|||") for p in boundary.most_common()]


def _split_text_by_boundary(text, boundary, side="left"):
    if boundary:
        parts = text.split(boundary)
    else:
        if side == "right":
            parts = [text, ""]
        else:
            parts = ["", text]
    if len(parts) > 1:
        for i in range(1, len(parts)):
            if side == "left":
                yield (boundary.join(parts[:i] + [""]), boundary.join(parts[i:]))
            elif side == "right":
                yield (boundary.join(parts[:i]), boundary.join([""] + parts[i:]))
            else:
                raise Exception("undefined side")


def split_text_by_around_pattern(text, pattern_pair, use_vmsp=True):
    (_left_vmsp, _left_boundary), (_right_vmsp, _right_boundary) = pattern_pair
    for lword in _left_boundary:
        for _left_text, _other_text in _split_text_by_boundary(text, lword, "left"):
            if use_vmsp and not match_pattern(_left_vmsp, _left_text):
                continue
            for rword in _right_boundary:
                for _answer_text, _right_text in _split_text_by_boundary(_other_text, rword, "right"):
                    if use_vmsp and not match_pattern(_right_vmsp, _right_text):
                        continue
                    yield (_left_text, _answer_text, _right_text)
            if not _right_boundary:
                yield (_left_text, _other_text, "")


def iter_split_text_by_boundary(text, boundary):
    lword, rword = boundary
    for _left_text, _other_text in _split_text_by_boundary(text, lword, "left"):
        for _answer_text, _right_text in _split_text_by_boundary(_other_text, rword, "right"):
            yield (_left_text, _answer_text, _right_text)


def match_around_pattern(texts, pattern):
    (_left_vmsp, _left_boundary), (_right_vmsp, _right_boundary) = pattern
    (prev_text, answer, after_text) = texts
    if match_pattern(_left_vmsp, prev_text) and match_pattern(_right_vmsp, after_text):
        return True
    return False


class PartialTextV2(PredictModelBase):
    model_intro = {
        "doc": """
        段落中文本内容（一句话等）提取
        """,
        "name": "段落文本",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_vmsp = True
        self.use_boundary_words = True

    @classmethod
    def model_template(cls):
        template = {"regs": []}
        default_model_template = cls.default_model_template()
        default_model_template.update(template)
        return default_model_template

    def train(self, dataset, **kwargs):
        model = {}
        for col in self.columns:
            crude_patterns, answer_patterns, answer_boundary = self.extract_feature(col, dataset)
            exact_patterns = self.filter_pattern(col, crude_patterns, answer_patterns, dataset)
            model[col] = {
                "around_patterns": exact_patterns,
                "answer_patterns": answer_patterns,
                "answer_boundary": answer_boundary,
            }
        self.model = model

    def print_model(self):
        print("\n==== model data of %s ====" % self.config["path"])
        for key, item in self.model.items():
            print("\n# %s:" % key)
            print("\n## around patterns:")
            for pair in item.get("around_patterns", []):
                print(pair)
            print("\n## answer patterns:")
            for pair in item.get("answer_patterns", []):
                print(pair)
            print("\n## answer boundary:")
            for pair in item.get("answer_boundary", []):
                print(pair)

    def get_col_regs(self, col):
        regs = self.config.get("regs", [])
        if isinstance(regs, list):
            # 兼容只配置一个的情况
            return regs
        return regs.get(col, [])

    def predict(self, elements, **kwargs):
        answers = []
        elements = elements or []
        for element in elements:
            if not is_paragraph_elt(element):
                continue
            merged_para = element.get("page_merged_paragraph")
            if merged_para:
                content = merged_para.get("text", "")
                chars = []
                for merged_idx in merged_para.get("paragraph_indices", []):
                    ele_typ, _elt = self.pdfinsight.find_element_by_index(merged_idx)
                    if not is_paragraph_elt(element):
                        continue
                    chars.extend(_elt.get("chars", []))
            else:
                content = element.get("text", "")
                chars = element.get("chars", [])
            answer = {}
            clean_content = clean_txt(content)
            for col in self.columns:
                # if col != "大额支付号":
                #     continue
                model = self.model or {}
                col_model = model.get(col, {})
                around_patterns = col_model.get("around_patterns", [])
                answer_patterns = col_model.get("answer_patterns", [])
                answer_boundary = col_model.get("answer_boundary", [])
                config_regex_pattern = self.get_col_regs(col)
                _answer = []
                # print('----------', col)
                # print(content)
                # print('around_patterns', around_patterns)
                # print('answer_patterns', answer_patterns)
                # print('answer_boundary', answer_boundary)

                # 首先根据配置的 regs 取答案
                if config_regex_pattern:
                    # 根据配置的 regs 取内容
                    for kw_pattern in config_regex_pattern:
                        for match in re.finditer(kw_pattern, clean_content):
                            if "dst" in match.groupdict():
                                c_start, c_end = match.span("dst")
                            else:
                                c_start, c_end = match.span()
                            prev_text = clean_content[:c_start]
                            answer_text = clean_content[c_start:c_end]
                            after_text = clean_content[c_end:]
                            if (
                                self.config.get("ignore_around_texts", False)
                                or not around_patterns
                                or all(is_none_or_whitespace(t) for t in (prev_text, after_text))
                            ):
                                sp_start, sp_end = index_in_space_string(content, (c_start, c_end))
                                _text = "".join([char["text"] for char in chars[sp_start:sp_end]])
                                _answer.append(CharResult(chars[sp_start:sp_end], text=_text))
                            else:
                                # 上下文内容匹配
                                for pattern in around_patterns:
                                    if match_around_pattern((prev_text, answer_text, after_text), pattern):
                                        sp_start, sp_end = index_in_space_string(content, (c_start, c_end))
                                        _text = "".join([char["text"] for char in chars[sp_start:sp_end]])
                                        _answer.append(CharResult(chars[sp_start:sp_end], text=_text))
                                        break
                            if _answer:
                                break
                        if _answer:
                            break

                # 其次使用模型
                for _pair in answer_boundary:
                    for _left, _answer_text, _right in iter_split_text_by_boundary(clean_content, _pair):
                        if not any(re.search(p, _answer_text) for p in answer_patterns):
                            continue
                        if not any(match_around_pattern((_left, _answer_text, _right), p) for p in around_patterns):
                            continue
                        c_start, c_end = len(_left), len(_left) + len(_answer_text)
                        sp_start, sp_end = index_in_space_string(content, (c_start, c_end))
                        _text = "".join([char["text"] for char in chars[sp_start:sp_end]])
                        _answer.append(CharResult(chars[sp_start:sp_end], text=_text))
                    # if _answer:
                    #     break

                if _answer:
                    _answer = ResultOfPredictor(_answer)
                    # NOTE: move to ModelGroup
                    # enum_values = self.get_enum_values(self.config['path'][0], col)
                    # if enum_values:  # 补充枚举值
                    #     answer_text = ''.join([x.text for x in _answer.data])
                    #     for val, patterns in self.config.get("enum_pattern", []):
                    #         if any(re.search(pattern, answer_text) for pattern in patterns):
                    #             _answer.value = val
                    answer[col] = _answer
            if answer:
                answers.append(answer)
        return answers

    def extract_feature(self, attr, dataset):
        # For Debug
        # if attr == "账号":
        #     print(attr)
        # else:
        #     return [], [], []
        answer_texts_list = []
        for item in dataset or []:
            # 取标注答案
            answer = None
            leaves = item.answer.get(attr, {}).values() if not self.leaf else [item.answer]
            for leaf in leaves:
                # TODO: 暂不支持三级字段
                if not leaf.data:
                    continue
                for data in leaf.data["data"]:
                    # 此模型实际只处理单元素块的
                    if not data["elements"]:
                        continue
                    answer = "".join([box["text"] for box in data["boxes"]])
                    elt = item.data.get("elements", {}).get(data["elements"][0])
                    if is_paragraph_elt(elt):
                        para = elt.get("page_merged_paragraph") or elt
                        text_parts = get_answer_text_parts(para, data["boxes"])
                        content = text_parts[1]
                        texts_around = (text_parts[0], text_parts[2])
                        if not content:
                            continue
                        if clean_txt(content) != clean_txt(answer):
                            continue
                        answer_texts_list.append((texts_around[0], clean_txt(content), texts_around[1]))

        text_around_patterns = generate_texts_around_pattern(answer_texts_list)
        text_inside_patterns = generate_texts_inside_pattern(answer_texts_list)
        answer_boundary = generate_answer_boundary(answer_texts_list)
        return (
            reduce(lambda x, y: x + [y] if y not in x else x, [[]] + text_around_patterns),
            text_inside_patterns,
            answer_boundary,
        )

    def filter_pattern(self, attr, patterns, answer_patterns, dataset):
        """滤掉正确率低的 pattern"""
        patterns_with_score = [[p, 0] for p in patterns]
        for item in dataset or []:
            # 取标注答案
            leaves = item.answer.get(attr, {}).values() if not self.leaf else [item.answer]
            for leaf in leaves:
                if not leaf.data:
                    continue
                for data in leaf.data["data"]:
                    if not data["elements"]:
                        continue
                    elt = item.data.get("elements", {}).get(data["elements"][0])
                    if not is_paragraph_elt(elt):
                        continue
                    para = elt.get("page_merged_paragraph") or elt
                    text_parts = get_answer_text_parts(para, data["boxes"])
                    content = text_parts[1]
                    texts_around = (text_parts[0], text_parts[2])
                    for p_score in patterns_with_score:
                        if match_around_pattern((texts_around[0], content, texts_around[1]), p_score[0]):
                            p_score[1] += 1
                            print("bingo: ", p_score)
                        else:
                            # p_score[1] -= 1
                            print("miss: ", p_score)
        valid_patterns = [ps[0] for ps in sorted(patterns_with_score, key=lambda p: p[1]) if ps[1] > 0]
        return valid_patterns
