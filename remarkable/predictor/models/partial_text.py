import logging
from collections import Counter

from remarkable import config
from remarkable.common.constants import Language
from remarkable.common.multiprocess import run_in_multiprocess
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt, index_in_space_string
from remarkable.predictor.dataset import DatasetItem
from remarkable.predictor.eltype import ElementType
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import CharResult, ParagraphResult
from remarkable.service.predictor import (
    PatternString,
    _batch_split_text_by_boundary,
    extract_feature_by_group,
    generate_answer_boundary,
    get_all_answer_text_parts,
    is_paragraph_elt,
    match_length,
)

logger = logging.getLogger(__name__)


def iter_split_text_by_boundary(text, boundary):
    lword, rword = boundary
    for _left_text, _other_text in _batch_split_text_by_boundary(text, lword, "left") or []:
        for _answer_text, _right_text in _batch_split_text_by_boundary(_other_text, rword, "right") or []:
            yield VMSPAnswer(_left_text, _answer_text, _right_text)


class VMSPInput:
    def __init__(self, content, chars, element):
        self.content = content
        self.clean_content = clean_txt(content)
        self.chars = chars
        self.element = element

        self.start = None
        self.end = None

    @classmethod
    def from_element(cls, element, pdfinsight):
        merged_para = element.get("page_merged_paragraph")
        if merged_para:
            content = merged_para.get("text", "")
            chars = []
            for merged_idx in merged_para.get("paragraph_indices", []):
                _, elt = pdfinsight.find_element_by_index(merged_idx)
                if not is_paragraph_elt(element):
                    continue
                chars.extend(elt.get("chars", []))
        else:
            content = element.get("text", "")
            chars = element.get("chars", [])

        return VMSPInput(content, chars, element)

    @classmethod
    def from_cell(cls, cell, element):
        content = cell.get("text", "")
        chars = cell.get("chars", [])
        return VMSPInput(content, chars, element)

    def get_text(self, start, end):
        return "".join([char["text"] for char in self.chars[start:end]])


class VMSPOutput:
    def __init__(self, vmsp_input, start, end):
        self.vmsp_input = vmsp_input
        self.start = start
        self.end = end

    @property
    def text(self):
        return self.vmsp_input.get_text(self.start, self.end)


class VMSPAnswer:
    def __init__(self, left_text, answer_text, right_text):
        self.left_text = left_text
        self.answer_text = answer_text
        self.right_text = right_text

    @property
    def left_pattern(self):
        return PatternString(self.left_text)

    @property
    def answer_pattern(self):
        return PatternString(self.answer_text)

    @property
    def right_pattern(self):
        return PatternString(self.right_text)

    def is_valid(self, feature, use_answer_pattern=True, need_match_length=True):
        if need_match_length and not match_length(self.answer_pattern, feature.length_counter):
            logger.debug(f"{self.answer_pattern.text=}, {feature.length_counter=}")
            logger.debug("need_match_length, not match answer length, skip...")
            return False
        if use_answer_pattern and not any((self.answer_pattern.match_vmsp_pattern(p) for p in feature.answer_patterns)):
            logger.debug(f"{self.answer_pattern.text=}, {feature.answer_patterns=}")
            logger.debug("use_answer_pattern, not match answer_pattern, skip...")
            return False
        if feature.left_patterns and not any(
            (self.left_pattern.match_vmsp_pattern(p, direction="left") for p in feature.left_patterns)
        ):
            logger.debug(f"{self.left_pattern.text=}, {feature.left_patterns=}")
            logger.debug("not match left_patterns, skip...")
            return False
        if feature.right_patterns and not any(
            (self.right_pattern.match_vmsp_pattern(p, direction="right") for p in feature.right_patterns)
        ):
            logger.debug(f"{self.right_pattern.text=}, {feature.right_patterns=}")
            logger.debug("not match right_patterns, skip...")
            return False

        return True

    def get_text_range(self, content, ignore_offset):
        start = len(self.left_pattern)
        end = len(self.left_pattern) + len(self.answer_pattern)
        if ignore_offset:
            return start, end
        return index_in_space_string(content, (start, end))


class VMSPFeature:
    P_INVALID_LEFT = PatternCollection([r"^.$", r"^[^\u4e00-\u9fa5\w]*$"])

    def __init__(self, data):
        self.data = data

    @property
    def answer_boundary(self):
        return self.data.get("boundary", [])

    @property
    def answer_patterns(self):
        return self.data.get("answer_patterns", [])

    @property
    def left_patterns(self):
        patterns = self.data.get("left_patterns", [])
        ret = [x for x in patterns if not self.P_INVALID_LEFT.nexts("".join(x))]
        return ret

    @property
    def right_patterns(self):
        return self.data.get("right_patterns", [])

    @property
    def length_counter(self):
        return self.data.get("answer_length", Counter())

    def extract_answers(self, vmsp_input, use_answer_pattern, need_match_length):
        results = []
        for vmsp_answer in iter_split_text_by_boundary(vmsp_input.clean_content, self.answer_boundary):
            if vmsp_answer.is_valid(self, use_answer_pattern, need_match_length):
                sp_start, sp_end = vmsp_answer.get_text_range(vmsp_input.content, False)
                vmsp_output = VMSPOutput(vmsp_input, sp_start, sp_end)
                results.append(vmsp_output)

        return results


class VMSP:
    @classmethod
    def extract_answer_texts(cls, elements, box):
        res = []
        for elt in elements:
            if not is_paragraph_elt(elt):
                continue
            para = elt.get("page_merged_paragraph") or elt
            all_text_parts = get_all_answer_text_parts(para, [box])
            for text_parts in all_text_parts:
                if not text_parts[1]:
                    continue
                answer_texts = [[PatternString(t) for t in text_parts]]
                res.extend(answer_texts)

        return res

    @classmethod
    def extract_answer_texts_for_cell(cls, elements, box):
        return cls.extract_answer_texts(elements, box)

    @classmethod
    def extract_answers(cls, vmsp_input, feature_data, use_answer_pattern, need_match_length):
        answers = []
        vmsp_features = [VMSPFeature(item) for item in feature_data]
        for feature in vmsp_features:
            if not cls.is_valid_feature(feature, use_answer_pattern):
                logger.debug("valid feature, please check...")
                continue
            answer_items = feature.extract_answers(vmsp_input, use_answer_pattern, need_match_length)
            for item in answer_items:
                answers.append(item)

        return answers

    @staticmethod
    def is_valid_feature(feature, use_answer_pattern):
        if not use_answer_pattern:
            if not [x for x in feature.left_patterns if x] and not [x for x in feature.right_patterns if x]:
                return False
        return True


class PartialText(BaseModel):
    """使用 vmsp pattern 自动学习内容字符序列模式，进行提取
    注：配置在父级节点提取多个字段时，如果内容来自多个段落，需要配置 `multi_elements: True`

    config template:
    {
        'name': 'partial_text',
        'multi_elements': True,
        'merge_char_result': True,  # 将来自不同元素块的答案合并到一起
        # 以下可按二级字段配置
        'regs': [],  # 注入正则,要来替代模型
        'model_alternative': False,  # 为True时,注入正则未能提取时用模型提
        'neglect_patterns': [],  # 负面正则  用来过滤错误的初步定位元素块
        'neglect_answer_patterns': [],  # 负面答案正则  用来过滤错误的答案
        'use_answer_pattern': True,  # 答案本身需符合特征,为False时,只需匹配边界特征
        'need_match_length': True,  # 答案长度需样本近似
    }
    """

    target_element = ElementType.PARAGRAPH
    filter_elements_by_target = True

    def __init__(self, options, schema, predictor=None):
        super().__init__(options, schema, predictor=predictor)
        self.use_vmsp = True
        self.use_boundary_words = True
        self.merge_char_result = self.get_config("merge_char_result", True)
        self.extract_other_element_type = self.get_config("extract_other_element_type", [])
        self.other_element_type_page_range = self.get_config("other_element_type_page_range", [])

    @property
    def is_english(self):
        return config.get_config("client.content_language", "zh_CN") != Language.ZH_CN.value

    def train(self, dataset: list[DatasetItem], **kwargs):
        model_data = {}
        for col in self.columns:
            features = self.extract_feature(col, dataset, workers=kwargs.get("workers"))
            model_data[col] = features
        self.model_data = model_data

    def get_model_data(self, column=None):
        model_data = super().get_model_data(column=column) or Counter()
        use_answer_pattern = self.get_config("use_answer_pattern", default=True, column=column)

        # blacklist
        blacklist_pattern = PatternCollection(self.get_config("feature_black_list", default=[], column=column))
        keys = ["left_patterns", "right_patterns"]
        if use_answer_pattern:
            keys.append("answer_patterns")
        for item in model_data:
            for key in keys:
                item[key] = [x for x in item[key] if not blacklist_pattern.nexts("".join(x))]

        return model_data

    def print_model(self):
        print("\n==== model data of %s ====" % self.schema.path)
        for key, features in self.model_data.items():
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

    def get_para_chars(self, element):
        merged_para = element.get("page_merged_paragraph")
        if merged_para:
            chars = []
            for merged_idx in merged_para.get("paragraph_indices", []):
                _, elt = self.pdfinsight.find_element_by_index(merged_idx)
                if not is_paragraph_elt(element):
                    continue
                chars.extend(elt.get("chars", []))
        else:
            chars = element.get("chars", [])

        return chars

    def create_content_result(self, element, chars, split_pattern, keep_separator=None):
        # TODO cell_partial_text中单元格所有的chars都被匹配上的时候 需要返回整个单元格
        if not split_pattern and element.get("chars"):
            chars_text = "".join(c["text"] for c in chars)
            ele_text = "".join(c["text"] for c in element["chars"])
            if (
                chars_text == ele_text
                and chars[0]["box"] == element["chars"][0]["box"]
                and chars[0]["page"] == element["chars"][0]["page"]
            ):
                return [ParagraphResult(element, element["chars"])]
        char_result = CharResult(element, chars)
        if split_pattern:
            return self.create_split_results(split_pattern, char_result, keep_separator=keep_separator)
        return [char_result]

    def predict_schema_answer(self, elements):
        answer_results = []
        elements = elements or []
        if self.extract_other_element_type:
            elements.extend(
                self.get_special_elements(
                    element_types=self.extract_other_element_type, page_range=self.other_element_type_page_range
                )
            )
        predicted_columns = []
        logger.debug(f"start predict answer by partial_text, for schema: {self.predictor.schema_name}")
        for element in elements:
            answer_result = self.extract_by_element(element, predicted_columns)
            if answer_result:
                answer_results.append(answer_result)
                if not self.multi_elements:
                    break
        logger.debug(f"length of result by partial_text: {len(answer_results)}")
        return answer_results

    def extract_by_element(self, element, predicted_columns):
        answer_result = {}
        vmsp_input = VMSPInput.from_element(element, self.pdfinsight)
        logger.debug(f"<partial_text>: {element['index']=}")
        for column in self.columns:
            logger.debug(f"<partial_text>: {column=}")
            column_answer_result = self.extract_for_column(element, column, predicted_columns, vmsp_input)
            if column_answer_result:
                answer_result.update(column_answer_result)

        return answer_result

    def extract_for_column(self, element, column, predicted_columns, vmsp_input):
        answer_result = {}
        element_results = []
        # 是否允许一个字段从多个element里提(前提是multi_elements为True)
        column_from_multi_elements = self.get_config("column_from_multi_elements", column=column, default=True)
        if column in predicted_columns and not column_from_multi_elements:
            logger.debug("not column_from_multi_elements, skip...")
            return None
        neglect_patterns = PatternCollection(self.get_config("neglect_patterns", column=column))
        if neglect_patterns.nexts(vmsp_input.clean_content):
            logger.debug("match neglect_patterns, skip...")
            return None

        model_alternative = self.get_config("model_alternative", column=column)
        config_regex_pattern = self.get_config("regs", column=column)
        if not config_regex_pattern:
            # auto 模型里的配置 为了不跟partial_text冲突 重新起了名字
            config_regex_pattern = self.get_config("custom_regs", column=column)
        split_pattern = self.get_config("split_pattern", column=column)  # 分隔符
        keep_separator = self.get_config("keep_separator", column=column)
        clean_text = self.get_config("clean_text", column=column, default=True)

        neglect_answer_patterns = PatternCollection(self.get_config("neglect_answer_patterns", column=column))

        if config_regex_pattern:
            logger.debug("use config_regex_pattern by regs or custom_regs")
            # 首先根据配置的 regs 取答案
            answer_results_by_regs = self.extract_by_custom_regs(
                config_regex_pattern,
                element,
                vmsp_input,
                split_pattern,
                keep_separator,
                neglect_answer_patterns,
                clean_text,
            )
            element_results.extend(answer_results_by_regs)
        if not config_regex_pattern or (model_alternative and not element_results):
            logger.debug("start extract_by_model")
            # model_alternative为True时,配置的regs未能提取时用模型提
            element_results.extend(
                self.extract_by_model(
                    column, element, vmsp_input, split_pattern, keep_separator, neglect_answer_patterns
                )
            )

        if element_results:
            predicted_columns.append(column)
            if self.merge_char_result:
                answer_result[column] = [self.create_result(element_results, column=column)]
            else:
                answer_result[column] = []
                for element_result in element_results:
                    answer_result[column].append(self.create_result([element_result], column=column))
        return answer_result

    def extract_by_model(self, column, element, vmsp_input, split_pattern, keep_separator, neglect_answer_patterns):
        element_results = []
        model_data = self.get_model_data(column=column)
        if not model_data:
            logger.debug("no model exists, return!!!")
            return element_results
        use_answer_pattern = self.get_config("use_answer_pattern", default=True, column=column)
        need_match_length = self.get_config("need_match_length", default=True, column=column)
        answer_items = VMSP.extract_answers(vmsp_input, model_data, use_answer_pattern, need_match_length)
        logger.debug(f"extract_answers by VMSP, length of answer items: {len(answer_items)}")
        for item in answer_items:
            chars = vmsp_input.chars[item.start : item.end]
            if not chars:
                continue
            answer_text = "".join([i["text"] for i in chars])
            if neglect_answer_patterns and neglect_answer_patterns.nexts(clean_txt(answer_text)):
                logger.debug(f"{answer_text=}")
                logger.debug("match neglect_answer_patterns, skip...")
                continue
            element_results.extend(self.create_content_result(element, chars, split_pattern, keep_separator))
            if not self.multi:
                break
        # todo 每一行的字的大小字体都有可能不同 按照上 左排序  不是很稳定 ，可以将char index 添加到element中
        # if self.multi:
        #     element_results.sort(key=lambda x: (int(x.chars[0]['box'][1]), int(x.chars[0]['box'][0])))
        return element_results

    def extract_by_custom_regs(
        self,
        config_regex_pattern,
        element,
        vmsp_input,
        split_pattern,
        keep_separator,
        neglect_answer_patterns,
        clean_text,
    ):
        # 根据配置的 regs 取内容
        element_results = []
        matched_position = []
        pattern = PatternCollection(config_regex_pattern)
        matchers = pattern.finditer(vmsp_input.clean_content if clean_text else vmsp_input.content)
        for match in matchers:
            if "dst" in match.groupdict():
                c_start, c_end = match.span("dst")
            else:
                c_start, c_end = match.span()
            if clean_text:
                sp_start, sp_end = index_in_space_string(vmsp_input.content, (c_start, c_end))
            else:
                sp_start, sp_end = c_start, c_end

            if (sp_start, sp_end) in matched_position:
                logger.debug(f"match deduplicate, skip {match}")
                continue
            matched_position.append((sp_start, sp_end))

            chars = vmsp_input.chars[sp_start:sp_end]
            if not chars:
                continue
            answer_text = "".join([i["text"] for i in chars])
            if neglect_answer_patterns and neglect_answer_patterns.nexts(clean_txt(answer_text)):
                logger.debug(f"{answer_text=}")
                logger.debug("match neglect_answer_patterns, skip...")
                continue
            element_results.extend(self.create_content_result(element, chars, split_pattern, keep_separator))
            if not self.multi:
                break
        # if self.multi:
        #     element_results.sort(key=lambda x: (int(x.chars[0]['box'][1]), int(x.chars[0]['box'][0])))
        return element_results

    def extract_feature(self, attr, dataset: list[DatasetItem], workers=None):
        answer_texts_list = []

        for item in dataset:
            elements = item.data["elements"]
            col_path = self.schema.sibling_path(attr)
            logger.debug(f"{col_path=}, {item.fid=}")
            nodes = self.find_answer_nodes(item, col_path)
            for node in nodes:
                if not node.data or not node.data["data"]:
                    continue
                answer_texts_list.extend(self.process_answer_node(node, elements))

        answers_groupby_boundary = generate_answer_boundary(answer_texts_list)
        features = run_in_multiprocess(
            extract_feature_by_group, list(answers_groupby_boundary), workers=workers, maxtasksperchild=10
        )
        return sorted(features, key=lambda f: f["score"], reverse=True)

    def process_answer_node(self, node, elements):
        answer_texts_list = []
        for data in node.data["data"]:
            box_elts = set()
            for box in data["boxes"]:
                box_relative_elements = self.select_elements(elements.values(), box)
                index_ex = [x["index"] for x in box_relative_elements if self.is_target_element(x)]
                if not index_ex:
                    continue
                box_elts.add(tuple(index_ex))
            aim_para = {}
            if len(box_elts) == 1 and len(list(box_elts)[0]) == 1:
                aim_para = elements[list(box_elts)[0][0]]
            content = clean_txt("".join([box.get("text", "") for box in data["boxes"]]))
            if aim_para and content in clean_txt(aim_para.get("text", "")):  # 完整句子被切分的情况
                answer_texts = self.get_answer_list_from_para(data, aim_para)
                answer_texts_list.extend(answer_texts)
            else:
                if self.is_cross_page_para(box_elts, elements):
                    box_relative_elements = self.select_elements(elements.values(), data["boxes"][0])
                    aim_para = box_relative_elements[0]["page_merged_paragraph"]
                    answer_texts = self.get_answer_list_from_para(data, aim_para)
                    answer_texts_list.extend(answer_texts)
                else:
                    for box in data["boxes"]:
                        box_relative_elements = self.select_elements(elements.values(), box)
                        answer_texts = VMSP.extract_answer_texts(box_relative_elements, box)
                        answer_texts_list.extend(answer_texts)
        return answer_texts_list

    @staticmethod
    def is_cross_page_para(box_elts, elements):
        # 处理跨页段落中答案的框跨页的情况 仅处理跨两页的情况
        elt_index = [x[0] for x in box_elts if x]
        if len(elt_index) != 2:
            return False
        elt_index.sort()
        above_element = elements[elt_index[0]]
        if page_merged_paragraph := above_element.get("page_merged_paragraph"):
            if elt_index[1] in page_merged_paragraph["paragraph_indices"]:
                return True
        return False

    @staticmethod
    def get_answer_list_from_para(data, aim_para):
        answer_texts_list = []
        all_text_parts = get_all_answer_text_parts(aim_para, data["boxes"])
        for text_parts in all_text_parts:
            if not text_parts[1]:
                continue
            answer_texts = [[PatternString(t) for t in text_parts]]
            answer_texts_list.extend(answer_texts)
        return answer_texts_list
