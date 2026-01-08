"""段落中文本内容提取"""

import itertools
import re
from collections import Counter
from functools import reduce

from remarkable.common.util import clean_txt, cut_text, index_in_space_string, is_none_or_whitespace
from remarkable.plugins.predict.models.model_base import SPECIAL_ATTR_PATTERNS, PredictModelBase
from remarkable.plugins.sse.sse_answer_formatter import SSEAnswerFormatter
from remarkable.predictor.predict import CharResult, ResultOfPredictor
from remarkable.service.predictor import get_result_of_vmsp, is_paragraph_elt


def generate_texts_around(pattern, words):
    texts_around = ("", "")
    match = re.search(re.escape(pattern), words)
    if match:
        texts_around = (words[: match.span()[0]], words[match.span()[-1] :])
    return texts_around


def text2pattern(text):
    text = re.sub(r"\s+", "", pattern_escape(text))
    # 数字
    text = re.sub(SPECIAL_ATTR_PATTERNS["number"][0], r"\d*", text)
    # 括号
    text = re.sub(r"[(（【]+", r"[(（[【]*", text)
    text = re.sub(r"[)）】]+", r"[)）\]】]*", text)
    text = re.sub(r"[:：]+", r"[:：]*", text)
    return text


def pattern_escape(text):
    # re.escape will add \\ to each cn char
    return re.sub(r"([.?+*^$|{}()\[\]\\-])", r"\\\1", text)


def generate_vmsp_pattern(text_list, cut_side="right"):
    inputs = []
    input_str = []
    convert_str = "@CONVERTED_FROM_TEXT\n"
    for text in text_list:
        vmsp_input = list(cut_text(text, cut_side))
        for char in vmsp_input:
            convert_str += "@ITEM={}={}\n".format(ord(char), char)
        if vmsp_input:
            vmsp_input_str = " -1 ".join([str(ord(c)) for c in vmsp_input]) + " -2\n"
            inputs.append(vmsp_input_str)
            input_str.append(vmsp_input)
    convert_str += "@ITEM=-1=|\n"
    patterns = get_result_of_vmsp(convert_str + "".join(inputs))
    return patterns


def generate_texts_around_pattern(texts_around):
    before_patterns = generate_vmsp_pattern([texts[0] for texts in texts_around], cut_side="left") or [""]
    after_patterns = generate_vmsp_pattern([texts[1] for texts in texts_around], cut_side="right") or [""]
    # crude_patterns = list(itertools.product(before_patterns, after_patterns)) + list(
    #     zip(before_patterns, [""] * len(before_patterns))) + list(zip([""] * len(after_patterns), after_patterns))
    crude_patterns = list(itertools.product(before_patterns, after_patterns))
    return crude_patterns


def generate_texts_inside_pattern(texts):
    """答案内容的 patterns
    由于不能确定边界，暂时用记忆的方法了
    """
    return [text2pattern(text) for text in texts]


class PartialText(PredictModelBase):
    model_intro = {"doc": "段落中文本内容提取", "name": "段落"}

    @classmethod
    def model_template(cls):
        template = {
            "regs": [],
        }
        default_model_template = cls.default_model_template()
        default_model_template.update(template)
        return default_model_template

    def train(self, dataset, **kwargs):
        model = {}
        for col in self.columns:
            # if col not in '增持主体本次增持前已持有股份的数量':
            #     continue
            crude_patterns, answer_patterns = self.extract_feature(col, dataset)
            exact_patterns = self.filter_pattern(crude_patterns, dataset)
            model[col] = {"around_patterns": exact_patterns, "answer_patterns": answer_patterns}
        self.model = model

    def print_model(self):
        print("\n==== model data of %s ====" % self.config["path"])
        for key, item in self.model.items():
            print("\n# %s:" % key)
            print("\n## around patterns:")
            for pair in item.get("around_patterns", []):
                print(pair)
            print("\n## answer patterns:")
            for pair in item.get("answer_patterns", Counter()).most_common():
                print(pair)

    def get_col_regs(self, col):
        regs = self.config.get("regs", [])
        if isinstance(regs, list):
            # 兼容只配置一个的情况
            return regs
        return regs.get(col, [])

    def get_around_regs(self, col):
        regs = self.config.get("around_regs", [])
        if isinstance(regs, list):
            # 兼容只配置一个的情况
            return regs
        return regs.get(col, [])

    def match_near_elts(self, elts, col):
        regs = self.config.get("near_regs", [])
        if not isinstance(regs, list):
            regs = regs.get(col, [])
        if not regs:
            return True
        for reg in regs:
            for elt in elts:
                near_text = clean_txt(elt.get("text", ""))
                if re.search(reg, near_text):
                    return True
        return False

    def predict(self, elements, **kwargs):
        answers = []
        for element in elements:
            if not is_paragraph_elt(element):
                continue
            around_elts = self.pdfinsight.find_elements_near_by(element["index"], step=-1, amount=3)
            content = clean_txt(element.get("text", ""))
            chars = [i for i in element["chars"] if not re.search(r"^\s+$", i["text"])]
            answer = {}
            for col in self.columns:
                # if col != '增持主体本次增持前已持有股份的数量':  # for debug
                #     continue
                col_model = self.model.get(col, {})
                around_patterns = col_model.get("around_patterns", [])
                answer_patterns = col_model.get("answer_patterns", Counter())
                # print('!!!!!!', col)
                # print(content)
                _answer = None
                for kw_pattern in self.get_col_regs(col) + [p[0] for p in answer_patterns.most_common()]:
                    # print('~~~~~', kw_pattern, re.search(kw_pattern, content))
                    # 定位关键字内容
                    for group in re.finditer(kw_pattern, content):
                        c_start, c_end = group.start(), group.end()
                        prev_text = cut_text(content[:c_start], "left")
                        after_text = cut_text(content[c_end:], "right")
                        # 上下文内容匹配
                        if all(is_none_or_whitespace(t) for t in (prev_text, after_text)):
                            sp_start, sp_end = index_in_space_string(content, (c_start, c_end))
                            # print('********', [x['text'] for x in chars[sp_start:sp_end]])
                            _answer = ResultOfPredictor([CharResult(chars[sp_start:sp_end], elt=element)])
                        else:
                            for pattern in around_patterns:
                                if (not prev_text or re.search(pattern[0], prev_text)) and (
                                    not after_text or re.search(pattern[1], after_text)
                                ):
                                    sp_start, sp_end = index_in_space_string(content, (c_start, c_end))
                                    # print('********', [x['text'] for x in chars[sp_start:sp_end]])
                                    _answer = ResultOfPredictor([CharResult(chars[sp_start:sp_end], elt=element)])
                                    break
                        if _answer:
                            break
                    if _answer:
                        break
                if _answer and self.match_near_elts(around_elts, col):
                    answer[col] = _answer
            if answer:
                answers.append(answer)
        return answers

    def extract_feature(self, attr, dataset):
        # For Debug
        # if attr == "户名":
        #     print(attr)
        texts_around_list = []
        texts_inside_list = []
        for item in dataset or []:
            # 取标注答案
            answer = None
            leaves = item.answer.get(attr, {}).values() if not self.leaf else [item.answer]
            for leaf in leaves:
                if leaf.data:
                    answer = leaf.data.simple_text()
                if answer:
                    answer = "".join(answer) if isinstance(answer, list) else answer
                    texts_inside_list.append(answer)
                    # 取上下文内容
                    for elt in item.data.get("elements", {}).values():
                        if is_paragraph_elt(elt):
                            merged_para = elt.get("page_merged_paragraph")
                            content = merged_para.get("text", "") if merged_para else elt.get("text", "")
                            if content and answer in content:
                                texts_around = generate_texts_around(
                                    SSEAnswerFormatter._clean_txt(answer),
                                    SSEAnswerFormatter._clean_txt(content),
                                )
                                texts_around_list.append(texts_around)

        text_around_patterns = generate_texts_around_pattern(texts_around_list)
        text_inside_patterns = generate_texts_inside_pattern(texts_inside_list)
        return (
            reduce(lambda x, y: x + [y] if y not in x else x, [[]] + text_around_patterns),
            Counter(text_inside_patterns),
        )

    def filter_pattern(self, patterns, dataset):
        """TODO: 滤掉正确率低的pattern"""
        return patterns
