"""段落中文本内容提取

港交所处理：
1. 答案取到框外第一个空格为止
2. 取特征值时：按空格分词、全小写、提取词干
3. 去除 score 小于 0.01 的元素块
"""

import re
from collections import Counter

from remarkable.common.multiprocess import run_in_multiprocess
from remarkable.common.util import clean_txt, index_in_space_string
from remarkable.plugins.predict.models.model_base import PredictModelBase
from remarkable.predictor.predict import CharResult, ParaResult, ResultOfPredictor
from remarkable.service.predictor import (
    PatternString,
    extract_feature_by_group,
    generate_answer_boundary,
    get_answer_text_parts,
    is_paragraph_elt,
    iter_split_text_by_boundary,
    match_length,
)


class PartialTextV3(PredictModelBase):
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
        template = {}
        default_model_template = cls.default_model_template()
        default_model_template.update(template)
        return default_model_template

    def train(self, dataset, **kwargs):
        model = {}
        for col in self.columns:
            features = self.extract_feature(col, dataset, workers=kwargs.get("workers"))
            model[col] = features
        self.model = model

    def print_model(self):
        print("\n==== model data of %s ====" % self.config["path"])
        for key, features in self.model.items():
            print("\n# %s:" % key)
            for item in features:
                print("\n===== (%s ... ... %s) =====" % item["boundary"])
                print("\n## answer patterns:")
                for _pattern in item.get("answer_patterns", []):
                    print(_pattern)
                print("\n## left patterns:")
                for _pattern in item.get("left_patterns", []):
                    print(_pattern)
                print("\n## right patterns:")
                for _pattern in item.get("right_patterns", []):
                    print(_pattern)

    def get_col_regs(self, col):
        regs = self.config.get("regs", [])
        if isinstance(regs, list):
            # 兼容只配置一个的情况
            return regs

        return regs.get(col, [])

    @staticmethod
    def answer_by_pattern(patterns, content, chars):
        result = []
        for kw_pattern in patterns:
            for match in re.finditer(kw_pattern, content):
                if "dst" in match.groupdict():
                    c_start, c_end = match.span("dst")
                else:
                    c_start, c_end = match.span()
                sp_start, sp_end = index_in_space_string(content, (c_start, c_end))
                _text = "".join([char["text"] for char in chars[sp_start:sp_end]])
                result.append(CharResult(chars[sp_start:sp_end], text=_text))
        return result

    def predict(self, elements, **kwargs):
        answers = []
        elements = elements or []
        negative_answers = []
        for element in elements:
            if not is_paragraph_elt(element):
                continue
            content = element.get("text", "")
            chars = element.get("chars", [])
            answer = {}
            clean_content = clean_txt(content)
            for col in self.columns:
                _answer = []
                # step1: 根据配置的regs提取答案
                patterns = self.get_col_regs(col)
                if patterns:
                    _answer.extend(self.answer_by_pattern(patterns, clean_content, chars))
                if _answer:
                    answer[col] = ResultOfPredictor(_answer, score=element.get("score"))
                # step2: 根据模型提取答案
                if _answer or not self.model:
                    continue
                for item in self.model.get(col, []):
                    answer_boundary = item.get("boundary", [])
                    answer_patterns = item.get("answer_patterns", [])
                    left_patterns = item.get("left_patterns", [])
                    right_patterns = item.get("right_patterns", [])
                    length_counter = item.get("answer_length", Counter())
                    for _left, _answer_text, _right in iter_split_text_by_boundary(content, answer_boundary):
                        # TODO: 改为输出一个 PatternString + slices
                        _left, _answer_text, _right = [PatternString(t) for t in (_left, _answer_text, _right)]
                        if not match_length(_answer_text, length_counter):
                            continue
                        if not any(_answer_text.match_vmsp_pattern(p) for p in answer_patterns):
                            continue
                        if not any(_left.match_vmsp_pattern(p, direction="left") for p in left_patterns):
                            continue
                        if not any(_right.match_vmsp_pattern(p, direction="right") for p in right_patterns):
                            continue
                        c_start, c_end = len(_left), len(_left) + len(_answer_text)
                        sp_start, sp_end = c_start, c_end
                        _text = "".join([char["text"] for char in chars[sp_start:sp_end]])
                        neg_pattern = self.config.get("neg_pattern")
                        if neg_pattern and neg_pattern.search(_text):
                            _answer.append(ParaResult(element["chars"], element))
                            negative_answers.append(
                                {
                                    col: ResultOfPredictor(
                                        [ParaResult(element["chars"], element)], value="Negative Statement"
                                    )
                                }
                            )
                        else:
                            _answer.append(CharResult(chars[sp_start:sp_end], text=_text))

                        break

                    if _answer:
                        break
                # step3: 根据配置的supplement提取答案
                if not _answer:
                    patterns = self.config.get("supplement", {}).get(col, [])
                    if patterns:
                        _answer.extend(self.answer_by_pattern(patterns, clean_content, chars))

                if _answer:
                    answer[col] = ResultOfPredictor(_answer, score=element.get("score"))
                # else:
                #     # 匹配不到需要保留空答案, 后续要补上ND的枚举值
                #     answer[col] = ResultOfPredictor([])

            if answer:
                answers.append(answer)

        if negative_answers:
            return negative_answers

        return answers

    def extract_feature(self, attr, dataset, workers=None):
        answer_texts_list = []
        for item in dataset or []:
            # 取标注答案
            leaves = item.answer.get(attr, {}).values() if not self.leaf else [item.answer]
            for leaf in leaves:
                # TODO: 暂不支持三级字段
                if not leaf.data:
                    continue
                for data in leaf.data["data"]:
                    if not data["boxes"]:
                        continue
                    elements = PartialTextV3.select_elements(item.data.get("elements", {}).values(), data["boxes"][0])
                    for elt in elements:
                        if not is_paragraph_elt(elt):
                            continue
                        para = elt.get("page_merged_paragraph") or elt
                        text_parts = get_answer_text_parts(para, data["boxes"])
                        if not text_parts[1]:
                            continue
                        answer_texts_list.append([PatternString(t) for t in text_parts])

        answers_groupby_boundary = generate_answer_boundary(answer_texts_list)
        tasks = list(answers_groupby_boundary)
        features = run_in_multiprocess(extract_feature_by_group, tasks, workers=workers, maxtasksperchild=10)
        return sorted(features, key=lambda f: f["score"], reverse=True)
