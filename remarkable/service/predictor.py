import itertools
import logging
import os
import re
import string
import tempfile
from collections import Counter, OrderedDict
from math import ceil
from pathlib import Path
from subprocess import Popen

import rjieba as jieba

from remarkable import config
from remarkable.common.util import clean_txt
from remarkable.config import project_root
from remarkable.pdfinsight.reader import PdfinsightReader

match_cache = {}
MAX_CHAR_LENGTH = 10
P_SPLIT = re.compile(r"[。！!]")


class PatternString:
    translate = str.maketrans("", "", string.punctuation + "“”，。；（）？！")
    featured_words = OrderedDict(
        [
            ("PERCENTAGE", re.compile(r"^\-?\d+(?:\.\d+)?%$")),
            ("YEAR", re.compile(r"^(?:18|19|20|21)\d{2}$")),
            ("NUMBER", re.compile(r"^\-?\d+(?:,\d+)*(?:\.\d+)?$")),
            ("NOTENO", re.compile(r"^\((?:[a-z]|\d+|[iv]+)$|^(?:[a-z]|\d{1,2}|[iv]+)[\)\.]$|^[•–]$")),
        ]
    )

    def __init__(self, text, sub_texts=None):
        self.text = text
        self.pretreatment(sub_texts)

    def __str__(self):
        return self.text

    def __len__(self):
        return len(self.text)

    def pretreatment(self, sub_texts):
        self.words = []
        if not sub_texts:
            self.words = list(jieba.cut(self.text))
        else:
            for text in sub_texts:
                self.words.extend(list(jieba.cut(text)))
        self.normalized_words = [PatternString.normalize_word(w) for w in self.words]

    @property
    def normalized_text(self):
        return "".join(self.normalized_words)

    @staticmethod
    def normalize_word(word):
        # word = word.rstrip('.,:;')
        for featured_word, regex in PatternString.featured_words.items():
            if regex.match(word):
                return featured_word
        # word = word.strip(string.punctuation)

        # lower_translated = word.lower().translate(PatternString.translate)
        # return lower_translated if lower_translated not in stopwords.words["english"] else ""
        return word.replace(" ", "")

    def match_vmsp_pattern(self, pattern, direction=None):
        if not pattern:
            return not self.words
        if direction == "left":
            # 意为答案左边的部分
            _words = self.normalized_words[MAX_CHAR_LENGTH * -1 :]
        elif direction == "right":
            _words = self.normalized_words[:MAX_CHAR_LENGTH]
        else:
            _words = self.normalized_words
        if "".join(_words) == "".join(pattern):
            return True
        match_key = "_".join(_words + ["|||"] + pattern)
        result = match_cache.get(match_key)
        if result is None:
            cursor = 0
            for word in _words:
                if pattern[cursor] == word:
                    cursor += 1
                if cursor >= len(pattern):
                    result = True
                    break
            else:
                result = False
            match_cache[match_key] = result
        return result

    def vmsp_input(self, side="right", max_words=20):
        words = self.normalized_words
        res = []
        if side == "ends":
            if len(words) <= max_words:
                res = words
            else:
                left_part = words[: int(max_words / 2)]
                right_part = words[len(left_part) - max_words :]
                res = left_part + right_part
        elif side == "left":
            res = words[-max_words:]
        else:
            # 取目标右侧的一部分文字，先去掉句首逗号/分号
            res = words[:max_words]

        # 过滤掉空字符串（由 normalize_word 生成的）
        return [w for w in res if w]


def match_pattern(pattern, ptext, direction=None):
    return ptext.match_vmsp_pattern(pattern, direction=direction)


def match_length(ptext, distribute):
    _len = len(ptext.text)
    _total = sum(distribute.values())
    _meet = sum(distribute[_len + i] for i in range(-2, 3))
    return _meet / _total >= 0.01


def generate_texts_around(pattern, words):
    texts_around = (None, None)
    match = re.search(re.escape(pattern), words)
    if match:
        texts_around = (words[: match.span()[0]], words[match.span()[-1] :])
    return texts_around


re_sentece_stops = re.compile(r"[\.\?!\,] ")


def get_answer_text_parts(para, answer_boxes):
    left_chars = []
    answer_chars = []
    right_chars = []
    # answer_region = False
    for char in para.get("chars", []):
        if not any(PdfinsightReader.box_in_box(char["box"], box["box"]) for box in answer_boxes):
            if not answer_chars:
                left_chars.append(char)
            else:
                right_chars.append(char)
        else:
            answer_chars.append(char)

    # _pstr = PatternString("".join(c["text"] for c in left_chars + answer_chars + right_chars))
    left, answer, right = [
        "".join([c["text"] for c in chars]).strip() for chars in (left_chars, answer_chars, right_chars)
    ]
    return left, answer, right


def get_all_answer_text_parts(para, answer_boxes):
    # 拆为单句
    left, answer, right = get_answer_text_parts(para, answer_boxes)
    res = [(left, answer, right)]
    left_texts = P_SPLIT.split(left)
    right_texts = P_SPLIT.split(right, maxsplit=1)
    if left != left_texts[-1] or right != right_texts[0]:
        res.append((left_texts[-1], answer, right_texts[0]))
    return res


def get_result_of_vmsp(input_str, minsup=0.1):
    """
    Mining Frequent Maximal Sequential Patterns Using The VMSP Algorithm
    https://philippe-fournier-viger.com/spmf/VMSP.php
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        spmf_path = os.path.join(config.project_root, "data/jar/spmf.jar")
        input_path = Path(os.path.join(tmpdir, "vmsp_in.txt"))
        output_path = Path(os.path.join(tmpdir, "vmsp_out.txt"))
        input_path.write_text(input_str, encoding="utf-8")
        cmd = [
            "java",
            f"-Djava.util.prefs.systemRoot={tmpdir}",
            f"-Djava.util.prefs.userRoot={tmpdir}",
            "-Xmx1024m",
            "-jar",
            spmf_path,
            "run",
            "VMSP",
            input_path,
            output_path,
            str(minsup),
            "1000",
            "1000",
            "true",
        ]
        with Popen(cmd) as process:
            process.wait(1800)

        patterns_list = []
        with open(output_path, encoding="utf-8") as fp_pattern:
            for line in fp_pattern:
                if patterns := [p for p in line.rstrip().split(" | ")[:-1] if p]:
                    patterns_list.append(patterns)
        return patterns_list


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
            vmsp_input = text.vmsp_input(cut_side, max_words=max_chars)
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
        accepted_patterns = [
            p for p in patterns if len(p) >= min_length or (len(p) == 1 and p[0] in PatternString.featured_words)
        ]
        return accepted_patterns

    def dynamic_vmsp_configs(texts):
        sample_count = len(texts)
        average_length = sum(len(t.words) for t in texts) / (sample_count + 1)
        need_single_word = len([t for t in texts if len(t.words) == 1]) / (sample_count + 1) >= 0.1
        minsup_levels = [0.5, 0.4, 0.3, 0.2, 0.1]
        _minsup = 0.05
        while _minsup * len(texts) >= 4:
            minsup_levels.append(_minsup)
            _minsup /= 2
        length_levels = []
        _length = min(ceil(average_length), MAX_CHAR_LENGTH)
        while _length > 1:
            if _length not in length_levels:
                length_levels.append(_length)
            _length = ceil(_length / 2)
        length_levels = length_levels or [1]
        if need_single_word and 1 not in length_levels:
            length_levels.append(1)
        return [
            (s, 2, MAX_CHAR_LENGTH, left) for left, s in itertools.product(length_levels, minsup_levels)
        ]  # + [(1 / (sample_count + 1), 2, max_char_length, 1)]

    patterns = []
    if [t for t in text_list if not t.words] and allow_empty:
        patterns.append([])
    text_list = [t for t in text_list if t.words]

    # last_minsup = 1 / (len(text_list) + 1)
    vmsp_configs = dynamic_vmsp_configs(text_list)
    vmsp_configs_idx = 0
    while text_list:
        if vmsp_configs_idx >= len(vmsp_configs):
            logging.warning("%s items not recall", len(text_list))
            break
        sequence_config = vmsp_configs[vmsp_configs_idx]
        _patterns = run_vmsp(text_list, *sequence_config)
        text_left = []
        for text in text_list:
            if not any(text.match_vmsp_pattern(p, direction=cut_side) for p in _patterns):
                text_left.append(text)
        if _patterns:
            patterns.extend(_patterns)
            text_list = text_left
        else:
            vmsp_configs_idx += 1

    return patterns


def generate_texts_inside_pattern(texts):
    return generate_vmsp_pattern([p[1] for p in texts], cut_side="ends", allow_empty=False)


def generate_answer_boundary(inputs):
    _groups = {}
    for _left, _answer, _right in inputs:
        _boundary = (
            _left.normalized_words[-1] if _left.normalized_words else "",
            _right.normalized_words[0] if _right.normalized_words else "",
        )
        _group = _groups.setdefault("|||".join(_boundary), {"boundary": _boundary, "inputs": []})
        _group["inputs"].append((_left, _answer, _right))
    return sorted(_groups.values(), key=lambda g: len(g["inputs"]), reverse=True)


def answer_length_counter(answers):
    counter = Counter([len(clean_txt(t.text)) for t in answers])
    return counter


def _split_text_by_boundary(text, boundary, side="left"):
    if boundary:
        # TODO: 分词可能会和 boundary 不一致，从而无法提取
        # 对国长虹给予警告 => '对国', '长虹', '给予', '警告'
        # jieba.add_word(boundary)
        pairs = []
        ptext = PatternString(text)
        for idx, word in enumerate(ptext.normalized_words):
            if word == boundary:
                if side == "left":
                    pairs.append(("".join(ptext.words[: idx + 1] + [""]), "".join(ptext.words[idx + 1 :])))
                elif side == "right":
                    pairs.append(("".join(ptext.words[:idx]), "".join([""] + ptext.words[idx:])))
        return pairs

    if side == "left":
        return (("", text),)

    return ((text, ""),)


def _batch_split_text_by_boundary(text, boundary, side="left"):
    if boundary:
        # jieba.add_word(boundary)  # TODO A字段的boundary更新进停止词可能会对B字段的分词产生影响
        pairs = []
        if feature_pattern := PatternString.featured_words.get(boundary):
            pattern = feature_pattern.pattern
            if side == "left":
                pattern = pattern[:-1]  # 去除正则中的 $
            else:
                pattern = pattern[1:]  # 去除正则中的 ^
            sub_texts = re.split(rf"({pattern})", text)
        else:
            sub_texts = re.split(rf"({re.escape(boundary)})", text)
        ptext = PatternString(text, sub_texts=sub_texts)
        for idx, word in enumerate(ptext.normalized_words):
            if word == boundary:
                if side == "left":
                    pairs.append(("".join(ptext.words[: idx + 1] + [""]), "".join(ptext.words[idx + 1 :])))
                elif side == "right":
                    pairs.append(("".join(ptext.words[:idx]), "".join([""] + ptext.words[idx:])))
        return pairs

    if side == "left":
        return [
            ("", text),
        ]

    return [
        (text, ""),
    ]


def pattern_escape(text):
    # re.escape will add \\ to each cn char
    return re.sub(r"([.?+*^$|{}()\[\]\\-])", r"\\\1", text)


def _split_text_by_left_boundary(text, boundary):
    """
    根据左边界切分文本，返回 pairs = [(left_text, other_text), ...]
    eg:
    ('会议于2020年以投票表决方式召开', '于') => [('会议于', '2020年以投票表决方式召开'), ]
    """
    pairs = []
    if boundary:
        boundary = pattern_escape(boundary)
        for each in re.finditer(boundary, text):
            start, end = each.span()
            left_part = text[:end]
            other_part = text[end:]
            pairs.append((left_part, other_part))
    else:
        pairs = [("", text)]
    return pairs


def _split_text_by_right_boundary(text, boundary):
    """
    在左边界的切分基础上，根据右边界切分文本，返回 pairs = [(answer_text, right_text), ...]
    eg:
    ('2020年以投票表决方式召开', '以') => [('2020年', '以投票表决方式召开'), ]
    """
    pairs = []
    if boundary:
        boundary = pattern_escape(boundary)
        for each in re.finditer(boundary, text):
            start, end = each.span()
            answer_text = text[:start]
            right_part = text[start:]
            pairs.append((answer_text, right_part))
    else:
        pairs = [(text, "")]
    return pairs


def iter_split_text_by_boundary(text, boundary):
    lword, rword = boundary
    for _left_text, _other_text in _split_text_by_left_boundary(text, lword):
        for _answer_text, _right_text in _split_text_by_right_boundary(_other_text, rword):
            yield (_left_text, _answer_text, _right_text)


def match_around_pattern(texts, pattern):
    (_left_vmsp, _left_boundary), (_right_vmsp, _right_boundary) = pattern
    (prev_text, answer, after_text) = texts
    if match_pattern(_left_vmsp, prev_text, direction="left") and match_pattern(
        _right_vmsp, after_text, direction="right"
    ):
        return True
    return False


def range_lock(selected, start, end):
    for _start, _end in selected:
        if _start <= start <= _end or _start <= end <= _end:
            return False
    selected.append((start, end))
    return True


def is_paragraph_elt(elt):
    return elt.get("class") in ["PARAGRAPH", "PAGE_HEADER", "PAGE_FOOTER"]


def extract_feature_by_group(group):
    left_patterns = generate_vmsp_pattern([p[0] for p in group["inputs"]], cut_side="left", allow_empty=True) or [[]]
    answer_patterns = generate_vmsp_pattern([p[1] for p in group["inputs"]], cut_side="ends", allow_empty=False)
    right_patterns = generate_vmsp_pattern([p[2] for p in group["inputs"]], cut_side="right", allow_empty=True) or [[]]
    length_distribute = answer_length_counter(p[1] for p in group["inputs"])
    return {
        "boundary": group["boundary"],
        "answer_patterns": answer_patterns,
        "answer_length": length_distribute,
        "left_patterns": left_patterns,
        "right_patterns": right_patterns,
        "score": len(group["inputs"]),
    }


def predictor_model_path(name):
    return os.path.join(project_root, "data", "model", "%s_predictor.zip" % name)


PREDICTOR_MODEL_FILES = ("predictors/",)
