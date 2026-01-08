# -*- coding: utf-8 -*-
import copy
import logging
import re
from collections import Counter, defaultdict
from copy import deepcopy
from functools import reduce
from typing import Iterable

from remarkable.common.box_util import get_bound_box
from remarkable.common.constants import Language, TableType
from remarkable.common.exceptions import CmfChinaAPIError
from remarkable.common.pattern import RE_TYPE, PatternCollection
from remarkable.common.rectangle import Rectangle
from remarkable.common.util import clean_txt, index_in_space_string
from remarkable.pdfinsight.parser import parse_table
from remarkable.pdfinsight.reader import PdfinsightParagraph, PdfinsightReader, PdfinsightTable
from remarkable.plugins.predict.models.model_base import (
    DIMENSION_PATTERNS,
    SPECIAL_ATTR_PATTERNS,
)
from remarkable.predictor.common_pattern import PERCENT_PATTERN, UNIT_PATTERN
from remarkable.predictor.dataset import DatasetItem
from remarkable.predictor.eltype import ElementClassifier, ElementType
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import (
    CellCharResult,
    CharResult,
    ElementResult,
    PredictorResult,
    TableCellsResult,
    TableResult,
)
from remarkable.predictor.utils import ElementCollector, filter_table_cross_page

logger = logging.getLogger(__name__)


SPECIAL_WORDS = PatternCollection([r"[:：（）()、\.%．，的]"])
SERIAL_WORDS = PatternCollection([r"^[一二三四五六七八九\d](?!\d)"])
SUPPLEMENTARY_UNIT = PatternCollection(
    [
        r"[（\(【](次[/∕／]年([，、]次[/∕／]半年)?)[】\)）]",
        r"[（\(【](倍数?)[】\)）]",
        r"[（\(【](注\d?)[】\)）]",
        r"[（\(【](次[/∕／]?[期年])[】\)）]",
        r"[（\(【](合并，元)[】\)）]",
        r"[（\(【](元[/∕／]股、元[/∕／]注册资本)[】\)）]",
        r"[（\(【]?(元股)[】\)）]?",
    ]
)
P_HEADER_CELL_UNIT = PatternCollection(
    [
        rf"[（\(](?P<dst>{UNIT_PATTERN})[\)）]",
        rf"[（（\(]?(?P<dst>{PERCENT_PATTERN})[\)）]?",
        r"人民币(?P<dst>元)",
    ]
)


class BaseModel:
    __name__: str = ""
    target_element: ElementType | list | None = None
    base_all_elements = False
    filter_elements_by_target = False

    # predictor: SchemaPredictor = None
    def __init__(self, options: dict, schema: SchemaItem, predictor=None):
        self._options = options
        self.name = self.__name__ or options.get("name")
        self.schema = schema
        self.predictor = predictor
        self.original_columns = predictor.columns
        self.model_data = {}
        self.primary_key = predictor.primary_key

    @property
    def is_english(self):
        return self.get_config("client.content_language", "zh_CN") != Language.ZH_CN.value

    @property
    def leaf(self):
        return self.schema.is_leaf

    @property
    def config(self):
        return self._options

    @property
    def group_answer(self):
        return self.predictor.config.get("group_answer")

    @property
    def value_required(self):
        return self.predictor.schema.is_enum

    @property
    def group_by(self):
        return self.predictor.config.get("group_by")

    @property
    def multi(self):
        return self.get_config("multi", False)

    @property
    def multi_elements(self):
        return self.get_config("multi_elements", False)

    @property
    def order_by_index(self):
        return self.get_config("order_by_index", False)

    @property
    def multi_elements_limit(self):
        return self.get_config("multi_elements_limit", None)

    @property
    def keep_dummy(self):
        return self.get_config("keep_dummy", False)

    def get_model_data(self, column=None, *, name=None) -> Counter:
        # TODO: 梳理旧模型文件，处理可能错配的name key，简化此处逻辑
        if not self.model_data:
            for key in (name, self._options.get("name"), self.name):
                if not key:
                    continue

                if model_data := self.predictor.model_data.get(key):
                    self.model_data = copy.deepcopy(model_data)
                    break

        if self.model_data:
            return self.model_data.get(column or self.schema.name) or Counter()
        return Counter()

    @property
    def pdfinsight(self) -> PdfinsightReader:
        return self.predictor.pdfinsight

    @property
    def pdfinsight_syllabus(self):
        return self.pdfinsight.syllabus_reader

    @property
    def use_all_elements(self):
        """是否使用所有元素，即提取该字段不需要初步定位"""
        return self.get_config("use_all_elements", False)

    @property
    def columns(self):
        if only_columns := self.get_config("only_columns", []):
            # 仅支持的字段
            return [column for column in self.original_columns if column in only_columns]
        return self.original_columns

    def get_config(self, key, default=None, column=None):
        """获取字段模型配置
        TODO: unit test
        兼容统一配置和各自配置：
        0. 先确定config：option[model|{model_name}]，若缺省则self.config：
        1. 再取column下的key配置：option[column][key]，若缺省则：
        2. 再取key下的column配置：option[key][column]，若缺省则：
        3. 再取key下公共配置：option[key]，若缺省则：
        4. 默认配置 default
        """
        return self._get_config(
            self.config, self.name, key, default=default, column=column, columns=self.original_columns
        )

    @staticmethod
    def _get_config(config, model_name: str, key: str, *, default=None, column=None, columns=None):
        config = config.get(f"model|{model_name}", {}) or config

        if column and column in config and key in config[column]:
            return config[column][key]

        if key in config and isinstance(config[key], dict) and column:
            if column in config[key]:
                return config[key][column]
            elif set(columns).intersection(
                config[key]
            ):  # 该key下没有配置当前column,但是配了其他column,说明当前column不用配
                return default

        return config.get(key, default)

    def columns_with_fullpath(self) -> list[str]:
        for column in self.columns:
            yield column, self.schema.sibling_path(column)

    def train(self, dataset, **kwargs):
        raise NotImplementedError

    def find_answer_nodes(self, item, path):
        schema = self.schema.mold_schema.find_schema_by_path(path[1:])
        if schema.is_amount:
            return item.answer.find_nodes(path[1:] + schema.orders[:1])
        return item.answer.find_nodes(path[1:])

    def print_model(self):
        pass

    def match_syllabus(self, element, pattern):
        syllabuses = self.pdfinsight.syllabus_reader.find_by_elt_index(element["index"])
        for syllabus in syllabuses:
            if pattern.nexts(clean_txt(syllabus.get("title", ""))):
                return True
        return False

    def filter_elements_by_text_regs(self, elements: Iterable[dict]) -> Iterable[dict]:
        text_regs = PatternCollection(self.get_config("text_regs"))
        neglect_text_regs = PatternCollection(self.get_config("neglect_text_regs"))
        for element in elements:
            if ElementClassifier.is_table(element):
                pdfinsight_element = PdfinsightTable(element)
            elif ElementClassifier.like_paragraph(element):
                pdfinsight_element = PdfinsightParagraph(element)
            else:
                continue

            element_text = clean_txt(pdfinsight_element.text)

            if text_regs and not text_regs.nexts(element_text):
                logger.debug(f"{''.join(element_text[:10])}... not match text_regs, skip...")
                continue
            if neglect_text_regs and neglect_text_regs.nexts(element_text):
                logger.debug(f"{''.join(element_text[:10])}... match neglect_text_regs, skip...")
                continue
            yield element

    def filter_elements_by_syllabus_regs(self, elements: Iterable[dict]) -> Iterable[dict]:
        syllabus_pattern = PatternCollection(self.get_config("syllabus_regs"))
        neglect_syllabus_pattern = PatternCollection(self.get_config("neglect_syllabus_regs"))
        for element in elements:
            if syllabus_pattern and not self.match_syllabus(element, syllabus_pattern):
                logger.debug(f"{''.join(element.get('text', '')[:5])}... not match syllabus_regs, skip...")
                continue
            if neglect_syllabus_pattern and self.match_syllabus(element, neglect_syllabus_pattern):
                logger.debug(f"{''.join(element.get('text', '')[:5])}...match neglect_syllabus_regs, skip...")
                continue
            yield element

    def filter_elements_by_page(self, elements: Iterable[dict]) -> Iterable[dict]:
        if page_range := self.get_config("page_range", []):
            # 负值：倒数某页 比如 -1是最后一页
            fix_range = []
            pages = sorted(int(x) for x in self.pdfinsight.data["pages"])
            for x in page_range:
                if x < 0 and abs(x) <= len(pages):
                    fix_range.append(pages[x])
            if fix_range:
                fix_range.extend(page_range)
            else:
                fix_range = page_range
            return filter(lambda x: x["page"] in fix_range, elements)
        return elements

    def filter_elements_by_nearby_anchor(self, elements: Iterable[dict]) -> Iterable[dict]:
        def is_valid(pattern: PatternCollection, neglect_pattern: PatternCollection, element: dict) -> bool:
            nearby_elements = self.pdfinsight.find_elements_near_by(element["index"], step=step, amount=amount)
            if not nearby_elements:
                return False
            for nearby_element in nearby_elements:
                if ElementClassifier.is_table(nearby_element):
                    pdfinsight_element = PdfinsightTable(nearby_element)
                elif ElementClassifier.like_paragraph(nearby_element):
                    pdfinsight_element = PdfinsightParagraph(nearby_element)
                else:
                    continue

                text = clean_txt(pdfinsight_element.text)
                if neglect_pattern and neglect_pattern.nexts(text):
                    return False
                if pattern and pattern.nexts(text):
                    return True

            if pattern:
                return False
            return True

        if elements_nearby := self.get_config("elements_nearby"):
            elements_nearby_regs = PatternCollection(elements_nearby.get("regs", []))
            elements_nearby_neglect_regs = PatternCollection(elements_nearby.get("neglect_regs", []))
            amount = elements_nearby["amount"]
            step = elements_nearby["step"]
            valid_elements = []
            for ele in elements:
                if is_valid(elements_nearby_regs, elements_nearby_neglect_regs, ele):
                    valid_elements.append(ele)
            return valid_elements
        return elements

    def filter_elements(self, elements):
        elements = self.target_elements_iter(elements) if self.filter_elements_by_target else iter(elements)
        elements = self.filter_elements_by_text_regs(elements)
        elements = self.filter_elements_by_page(elements)
        elements = self.filter_elements_by_nearby_anchor(elements)
        return list(self.filter_elements_by_syllabus_regs(elements))

    def merge_neighbor_elements(self, elements):
        merge_neighbor = self.get_config("merge_neighbor")
        if not merge_neighbor:
            return elements

        new_elements = []
        for element in elements:
            all_neighbors = []
            for item in merge_neighbor:
                neighbors = self.pdfinsight.find_elements_near_by(
                    index=element["index"],
                    amount=item.get("amount") or 2,
                    step=item.get("step") or 1,
                    steprange=item.get("steprange") or 5,
                    aim_types=item.get("aim_types") or ["PARAGRAPH"],
                )
                break_pattern = PatternCollection(item.get("break_pattern", []))
                for neighbor in neighbors:
                    if break_pattern.nexts(clean_txt(neighbor.get("text", ""))):
                        break
                    if self.pdfinsight.is_element_multi_lines(neighbor):
                        break
                    all_neighbors.append(neighbor)
            new_elements.append(self.pdfinsight.merge_elements(element, all_neighbors))

        return new_elements

    def fix_cross_page_table_empty_header(self, elements):
        """
        |A|B|C|D|
        | |x|y|z|
        | |a|b|c|
        尝试修复跨页后，表头列全为空的情况
        :param elements:
        :return:
        """

        def _fix(table):
            cells_group_by_page = defaultdict(dict)
            max_row_per_page = defaultdict(lambda: 0)
            for key, cell in table["cells"].items():
                cells_group_by_page[cell["page"]][key] = cell
                if cell["row"] > max_row_per_page[cell["page"]]:
                    max_row_per_page[cell["page"]] = cell["row"]

            pages = list(cells_group_by_page.keys())
            if len(pages) != 2:
                return table

            all_row_header_empty = True
            col_cell_idx = []
            for key, cell in cells_group_by_page[pages[1]].items():
                if cell["col"] == 0:
                    col_cell_idx.append(key)
                    if cell["text"] != "":
                        all_row_header_empty = False
                        break
            if not all_row_header_empty:
                return table

            table = deepcopy(table)
            start_row_index = max_row_index = max_row_per_page[pages[0]]
            while True:
                current_cell = table["cells"][f"{start_row_index}_0"]
                current_cell["bottom"] += len(col_cell_idx)
                if not current_cell.get("dummy"):
                    break
                if start_row_index == 0:
                    break
                start_row_index -= 1

            row_header_cell = cells_group_by_page[pages[0]][f"{max_row_index}_0"]
            for idx in col_cell_idx:
                table["cells"][idx]["text"] = row_header_cell["text"]
                table["cells"][idx]["dummy"] = True
                if row_header_cell.get("dummy"):
                    table["cells"][idx]["top"] = table["cells"][f"{max_row_index}_0"]["top"]
                    table["cells"][idx]["bottom"] = table["cells"][f"{max_row_index}_0"]["bottom"]
                else:
                    table["cells"][idx]["top"] = table["cells"][f"{max_row_index}_0"]["row"]
                    table["cells"][idx]["bottom"] = table["cells"][f"{max_row_index}_0"]["row"] + len(col_cell_idx)

            return table

        fixed_elements = []
        for element in elements:
            if element["class"] == "TABLE":
                try:
                    element = _fix(element)
                except Exception as exp:
                    logger.error(f"fix_cross_page_table_empty_header error: {exp}")
            fixed_elements.append(element)
        return fixed_elements

    def fix_elements(self, elements):
        elements = self.merge_neighbor_elements(elements)
        elements = self.fix_cross_page_table_empty_header(elements)
        return elements

    def predict(self, elements):
        logger.debug(f"length of candidate elements, {len(elements)}")
        elements = self.fix_elements(elements)
        elements = self.filter_elements(elements)
        logger.debug(f"after filter_element, length of candidate elements, {len(elements)}")
        if not elements and self.use_all_elements:
            elements = self.filter_elements(self.pdfinsight.elements_iter())
        if self.order_by_index and self.multi_elements:
            elements = sorted(elements, key=lambda x: x["index"])
        answer_results = []
        logger.debug(f"predict for: {self.columns}")
        try:
            answer_results = self.predict_schema_answer(elements)
        except CmfChinaAPIError as e:
            raise e
        except Exception as e:
            logger.exception(e)
        logger.debug(f"Answers from model {self.name}:")
        if isinstance(answer_results, PredictorResult):
            logger.debug(answer_results)
        if isinstance(answer_results, list):
            if self.multi_elements_limit:
                answer_results = answer_results[: self.multi_elements_limit]

            for answer_result in answer_results:
                if isinstance(answer_result, PredictorResult):
                    logger.debug(answer_result)
                else:
                    for key, ans in answer_result.items():
                        if not ans or not hasattr(ans[0], "text"):
                            continue
                        ans_text = "".join(x.text for x in ans)
                        logger.debug(f"{key}: {ans_text}")

        return answer_results

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        raise NotImplementedError

    def create_result(
        self, element_results, value=None, schema=None, column=None, text=None, score=None, meta=None, primary_key=None
    ):
        if column is None:
            logger.warning("create_result must specific the column")
            logger.warning(f"Schema: {self.schema.name}, model: {self.name}")
        if schema is None:
            if column and column != self.schema.name:
                schema = self.predictor.parent.find_child_schema(column)
            else:
                schema = self.schema
        if not schema:
            raise ValueError(f"can't find column {column} according {self.schema.path}")
        result = PredictorResult(
            element_results, value, schema=schema, text=text, score=score, meta=meta, primary_key=primary_key
        )
        if schema.is_enum and value is None:
            # TODO: 在这里调用无法引用其他字段
            value = self.predictor.predict_value(result)
            result.update_answer_value(value)
        return result

    @staticmethod
    def get_element_with_content_chars(element, content_regs):
        content_element = copy.deepcopy(element)
        chars = content_element.get("chars", [])
        if content_regs:
            content_pattern = PatternCollection(content_regs)
            matched = content_pattern.nexts(clean_txt(content_element["text"]))
            if not matched:
                return None
            start, end = matched.span("content")
            sp_start, sp_end = index_in_space_string(content_element["text"], (start, end))
            chars = chars[sp_start:sp_end]
            if not chars:
                return None
            content_element["chars"] = chars
            content_element["text"] = "".join([char["text"] for char in chars])
            content_element["outline"] = get_bound_box(
                [char["box"] for char in chars if char["page"] == content_element["page"]]
            )

        return content_element

    def is_target_element(self, element: dict) -> bool:
        if (config_target_element := self.get_config("target_element")) and isinstance(config_target_element, list):
            return element["class"] in config_target_element
        if not self.target_element and config_target_element:
            self.target_element = ElementType(config_target_element)
        if not self.target_element or not self.filter_elements_by_target:
            return True
        return ElementClassifier.get_type(element) == self.target_element

    def target_elements_iter(self, elements) -> Iterable[dict]:
        return filter(self.is_target_element, elements)

    def get_title_element(self, element):
        if not element.get("syllabus"):
            return None
        syllabus = self.pdfinsight_syllabus.syllabus_dict[element["syllabus"]]
        if syllabus["element"] == element["index"]:  # syllabus指向自己,说明该element本来就是标题,返回其父标题
            parent_syllabus = self.pdfinsight_syllabus.syllabus_dict.get(syllabus["parent"])
            if not parent_syllabus:
                return None
            title_element_index = parent_syllabus["element"]
        else:
            title_element_index = syllabus["element"]
        _, para = self.pdfinsight.find_element_by_index(title_element_index)
        if not para:
            return None
        return para

    @staticmethod
    def feature_key_str(texts):
        """取内容特征字符串
        在此做一些泛化替换
        去掉 表头中的序号相关的描述：  五现金及现金等价物净增加额 ==> 现金及现金等价物净增加额
        去掉 虚词  ：  r':：（）()、.%．， 的' ===> ''
        去掉 表头中包含括号的单位：  r'(倍) （次）（次/年）'===> ''
        TODO: unit test needed.
        """
        texts = [P_HEADER_CELL_UNIT.sub("", text) for text in texts]
        texts = [SUPPLEMENTARY_UNIT.sub("", text) for text in texts]
        texts = [SPECIAL_WORDS.sub("", text) for text in texts]
        texts = [SERIAL_WORDS.sub("", text) for text in texts]
        texts = sorted(texts)
        return clean_txt("|".join(texts))

    def find_special_attr(self, col, elt, **kwargs):
        """
        从当前或上一个element中获取特定属性信息
        :param col: 币种, <金额单位>, <每股收益单位>, <百分比单位>, <**单位>其中之一
        :param elt:
        :return: ResultOfPredictor object or None
        """

        def _filter_chars(item):
            patterns = []
            # 正则优先级: 特殊属性 > 配置文件 > 词频统计
            if col in SPECIAL_ATTR_PATTERNS:
                patterns.extend(SPECIAL_ATTR_PATTERNS[col])
            patterns.extend(self.config.get("regs", []))

            for reg_p in kwargs.get("patterns", []):
                if reg_p is None:
                    print("error!")
                if reg_p.startswith("D_"):
                    patterns.extend(SPECIAL_ATTR_PATTERNS.get(reg_p.split("_")[-1]))
                else:
                    patterns.append(reg_p)

            for pattern in patterns:
                if isinstance(pattern, str):
                    pattern = re.compile(r"{}".format(pattern))

                if isinstance(pattern, RE_TYPE):
                    match = pattern.search(clean_txt(item["text"]))
                    if match:
                        try:
                            m_s, m_e = match.span("dst")
                        except IndexError:
                            # 正则未指定dst参数, 直接返回当前element所有chars
                            return item["chars"]
                        sp_start, sp_end = index_in_space_string(clean_txt(item["text"]), (m_s, m_e))
                        # 去掉空的文本框, 可能是space/\n\r\t其中一种
                        chars = [i for i in item["chars"] if not re.search(r"^\s+$", i["text"])]
                        return chars[sp_start:sp_end]
            return None

        def _find_special_attr(idx):
            chars = None
            ele_typ, _elt = self.pdfinsight.find_element_by_index(idx)
            if ele_typ == "PARAGRAPH":
                chars = _filter_chars(_elt)
            elif ele_typ == "TABLE":
                for _idx, cell in _elt["cells"].items():
                    chars = _filter_chars(cell)
                    if chars:
                        return CharResult(_elt, chars)
            else:
                logger.debug(f"不支持的元素类型: {ele_typ}")
            return CharResult(_elt, chars) if chars else None

        element_results = []
        if col in SPECIAL_ATTR_PATTERNS:
            start, end = 0, -3
        else:
            start, end = self.config.get("pos", (0, 1))
        for idx in range(start, end, 1 if start < end else -1):
            _idx = elt["index"] + idx
            unit = _find_special_attr(_idx if _idx > 0 else 0)
            if unit:
                element_results.append(unit)
                break
        else:
            logger.debug(f"未找到: {col}")
        return self.create_result(element_results) if element_results else None

    @staticmethod
    def same_text(cell, text):
        cell_text = cell if isinstance(cell, str) else cell["text"]
        if text.startswith("D_") and text[2:] in DIMENSION_PATTERNS:
            return DIMENSION_PATTERNS[text[2:]].match(cell_text)
        pattern = re.compile(r"\s{2,}")
        cell_text = re.sub(pattern, " ", cell_text)
        text = re.sub(pattern, " ", text)
        return clean_txt(cell_text) == clean_txt(text)

    @staticmethod
    def select_elements(elements, box):
        selected = []
        for ele in elements:
            if not ele["page"] == box["page"]:
                continue
            if PdfinsightReader.overlap_percent(ele["outline"], box["box"], base="box") > 0.2:
                selected.append(ele)
            elif PdfinsightReader.overlap_percent(ele["outline"], box["box"], base="element") > 0.2:
                selected.append(ele)
        return selected

    def get_dst_chars_from_text(self, text, element, span=None):
        cell_text = element["text"]
        return self.get_chars(cell_text, text, element.get("chars"), span)

    @classmethod
    def get_dst_chars_from_matcher(cls, matcher, element, is_clean_matcher=True, group_key="dst"):
        element_text = element["text"]
        value = matcher.groupdict().get(group_key, None)
        if not value:
            return None
        if is_clean_matcher:
            return cls.get_chars(element_text, value, element["chars"], matcher.span(group_key))

        start, end = matcher.span(group_key)
        return element["chars"][start:end]

    @staticmethod
    def get_chars(origin_text, aim_text, chars, span=None):
        if span is None:
            c_text = clean_txt(aim_text)
            start = clean_txt(origin_text).index(c_text)
            span = [start, start + len(c_text)]
        sp_start, sp_end = index_in_space_string(origin_text, span)
        dst_chars = chars[sp_start:sp_end]
        return dst_chars

    def get_above_elements(self, element, ele_type="PARAGRAPH", special_pattern=None):
        element_index = element["index"]
        above_element_indexes = list(range(element_index - 10, element_index))[::-1]
        element_syllabus_index_start = self.pdfinsight_syllabus.syllabus_dict[element["syllabus"]]["range"][0]
        ret = []
        for idx in above_element_indexes:
            if idx < 0:
                break
            if ele_type == "PARAGRAPH" and idx in self.pdfinsight.table_dict:
                break
            elt_type, element = self.pdfinsight.find_element_by_index(idx)
            if elt_type != ele_type or not element:
                continue
            if idx == element_syllabus_index_start:  # 匹配到章节标题 则停止
                ret.append(element)
                break
            if special_pattern and elt_type == "PARAGRAPH" and special_pattern.search(element["text"]):
                ret.append(element)
                break
            ret.append(element)
        return ret

    @staticmethod
    def is_match(pattern, text, origin_texts=None):
        # 允许feature传入正则表达式, 以"__regex__"为前缀作为区分
        prefix = "__regex__"
        if pattern.startswith(prefix):
            return BaseModel.match_regex(pattern, text, prefix)
        # 从原始文本匹配，保留停用词，分隔符信息。正则以origin开头
        if pattern.startswith("origin__regex__") and origin_texts:
            pattern = pattern[6:]
            return BaseModel.match_regex(pattern, "|".join(origin_texts), prefix)
        return BaseModel.match_text(pattern, text)

    @staticmethod
    def match_regex(pattern, text, prefix):
        texts = text.split("|")
        patterns = [re.compile(p) for p in pattern.split(prefix) if p]
        texts_match = [[p for p in patterns if p.search(t)] for t in texts]
        if any(m == [] for m in texts_match):
            # some texts mismatch
            return False
        if set(reduce(lambda x, y: x + y, texts_match)) != set(patterns):
            # some patterns mismatch
            return False
        return True

    @staticmethod
    def match_text(pattern, text):
        return pattern == text

    @staticmethod
    def regroup(answers):
        ret = defaultdict(list)
        for answer in answers:
            for col, value in answer.items():
                ret[col].extend(value)
        return ret

    def get_paragraphs_from_table(self, element, cell_separator="", cols=None):
        """
        公司代码/公司简称/公告编号/户名/开户行 等误识别为table的情况,把element组装成paragraphs
        """
        return PdfinsightReader.get_paragraphs_from_table(
            element, cell_separator=cell_separator, cols=cols, keep_dummy=self.keep_dummy
        )

    def restore_table_from_paragraphs(self, paragraphs):
        """get_paragraphs_from_table 的逆向操作"""
        return PdfinsightReader.restore_table_from_paragraphs(paragraphs)

    @staticmethod
    def create_split_results(split_pattern, result, garbage_frag_pattern=None, keep_separator=False):
        results = []
        start = 0
        separators = list(re.finditer(split_pattern, result.text))
        if not separators:
            return [result]

        for separator in separators:
            new_result = copy.deepcopy(result)
            if start != separator.start():
                end = separator.start()
                if keep_separator:
                    end += separator.end() - separator.start()
                new_result.chars = result.chars[start:end]
                results.append(new_result)
            start = separator.end()

        if start < len(result.text):
            new_result = copy.deepcopy(result)
            new_result.chars = result.chars[start:]
            results.append(new_result)

        garbage_frag_pattern = PatternCollection(garbage_frag_pattern)
        if garbage_frag_pattern:
            results = [res for res in results if not garbage_frag_pattern.nexts(res.text)]
        return results

    @staticmethod
    def same_box(cell: dict, box: dict) -> bool:
        if cell.get("fake"):
            return False
        current_page_chars = [char for char in cell["chars"] if char["page"] == box["page"]]
        current_page_chars_box = get_bound_box([char["box"] for char in current_page_chars])
        if not current_page_chars_box or len(current_page_chars_box) != 4:
            return False
        box_outline = (box["box"]["box_left"], box["box"]["box_top"], box["box"]["box_right"], box["box"]["box_bottom"])
        if PdfinsightReader.overlap_percent(current_page_chars_box, box_outline, base="box") < 0.5:
            return False
        return True

    def get_special_elements(self, element_types: list | None = None, page_range: list | None = None):
        ret = []
        for page, elements in self.pdfinsight.element_dict.items():
            if page_range and page not in page_range:
                continue
            for element in elements:
                if element_types and element.data["class"] not in element_types:
                    continue
                _, element = self.pdfinsight.find_element_by_index(element.data["index"])
                if element:
                    ret.append(element)
        return ret

    @classmethod
    def get_elements_from_answer_results(cls, answer_results):
        elements = []
        for answer_result in answer_results:
            elements.extend(cls.get_elements_from_answer_result(answer_result))
        return elements

    @staticmethod
    def get_elements_from_answer_result(answer_result):
        elements = []
        if isinstance(answer_result, dict):
            for answers in answer_result.values():
                for answer in answers:
                    elements.extend(answer.relative_elements)
        elif isinstance(answer_result, PredictorResult):
            for element_result in answer_result.element_results:
                if hasattr(element_result, "origin_elements") and element_result.origin_elements:
                    elements.extend(element_result.origin_elements)
                else:
                    elements.append(element_result.element)
        return elements

    @staticmethod
    def get_common_predictor_results(answer_results) -> list[PredictorResult]:
        predictor_results = []
        for answer_result in answer_results:
            if isinstance(answer_result, dict):
                for answers in answer_result.values():
                    predictor_results.extend(answers)
            elif isinstance(answer_result, PredictorResult):
                predictor_results.append(answer_result)
        return predictor_results

    @staticmethod
    def get_text_from_answer_result(answer_results):
        texts = []
        for answer_result in answer_results:
            if isinstance(answer_result, dict):
                for answers in answer_result.values():
                    for answer in answers:
                        texts.extend(answer.text)
            elif isinstance(answer_result, PredictorResult):
                for element_result in answer_result.element_results:
                    texts.append(element_result.text)
        return "\n".join(texts)

    def is_meet_condition(self, elements) -> bool:
        return False


class TableModel(BaseModel):
    target_element = None
    filter_elements_by_target = False

    def train(self, dataset: list[DatasetItem], **kwargs):
        model_data = {}
        for col, col_path in self.columns_with_fullpath():
            for item in dataset:
                logger.info(f"{col=}, {item.fid=}")
                for node in self.find_answer_nodes(item, col_path):
                    if node.data is None:
                        continue
                    features = self.extract_feature(item.data["elements"], node.data)
                    model_data.setdefault(col, Counter()).update(features)
        self.model_data = model_data

    def is_target_element(self, element: dict) -> bool:
        if self.filter_elements_by_target and self.target_element:
            return ElementClassifier.get_type(element) == self.target_element
        # base filter
        return element["class"] == "TABLE"

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        raise NotImplementedError

    def extract_feature(self, elements, answer):
        raise NotImplementedError

    def revise_elements(self, elements):
        if self.get_config("use_complete_table", False):  # 使用跨页合并后的完整表格
            elements = self.get_complete_tables(self.pdfinsight, elements)
        if self.get_config("middle_rows"):
            elements = self.get_middle_rows(elements)
        return elements

    def get_middle_rows(self, elements):
        from remarkable.predictor.models.middle_paras import MiddleParas

        """
        截取中间行
        """
        if not self.get_config("middle_rows"):
            return elements
        self.config.update(self.get_config("middle_rows", {}))

        for element in elements:
            fake_paras = []
            temp_index = 0
            element["paras"] = self.get_paragraphs_from_table(element)
            for para in element["paras"]:
                para["temp_index"] = temp_index
                temp_index += 1
                fake_paras.append(para)

            if not fake_paras:
                continue
            elements_blocks = MiddleParas(self._options, self.schema, self.predictor).get_elements_blocks(fake_paras)
            if elements_blocks:
                if table := self.restore_table_from_paragraphs(elements_blocks[0]):
                    element["cells"] = table["cells"]

        return elements

    @staticmethod
    def get_complete_tables(pdfinsight, tables):
        complete_tables = {}

        for table in tables:
            if table["index"] in complete_tables:
                continue

            page_merged_table = table.get("page_merged_table")
            cells_idx = page_merged_table.get("cells_idx", {}).keys() if isinstance(page_merged_table, dict) else None
            table_index = int(list(cells_idx)[0]) if cells_idx else None  # 经过fix_tables(),第一个表里有全部的cells

            #  page_merged_table是dict, 说明该table没有与其他表生成MergedTable, 参见 fix_tables(), class MergedTable
            complete_tables[table["index"]] = table
            if table_index and table_index not in complete_tables:
                _, ele = pdfinsight.find_element_by_index(table_index)
                complete_tables[table_index] = ele

        return list(complete_tables.values())

    @staticmethod
    def _filter_invalid_elements(elements):
        return filter_table_cross_page(elements)

    def filter_elements(self, elements):
        elements = [element for element in elements if element["class"] == "TABLE"]
        elements = super().filter_elements(elements)
        # 根据表头过滤 需要配置 neglect_title_patterns 或者 title_patterns
        neglect_title_patterns = PatternCollection(self.config.get("neglect_title_patterns"))
        title_patterns = PatternCollection(self.config.get("title_patterns"))
        element_collector = ElementCollector(elements, self.pdfinsight)
        elements = element_collector.collect(
            title_patterns,
            special_class="TABLE",
            multi_elements=self.multi_elements,
            neglect_pattern=neglect_title_patterns,
            filter_later_elements=self.config.get("filter_later_elements", False),
        )
        return self._filter_invalid_elements(elements)

    @classmethod
    def group_by_pattern(cls, records, pattern, pattern_col_name=None):
        groups = {}
        for record in records:
            headers = record[0] + record[1]
            group_cell = None
            for header_cell in headers:
                header_cell_text = clean_txt(header_cell["text"])
                if pattern.match(header_cell_text):
                    group_cell = header_cell
                    break
            if group_cell:
                groups.setdefault(clean_txt(group_cell["text"]), [([pattern_col_name], [], group_cell)]).append(record)
        return groups

    @staticmethod
    def aim_cell(cell, box):
        if cell.get("fake"):
            return False
        if cell["page"] != box["page"]:
            return False
        box_outline = (box["box"]["box_left"], box["box"]["box_top"], box["box"]["box_right"], box["box"]["box_bottom"])
        if PdfinsightReader.overlap_percent(cell["box"], box_outline, base="box") > 0.5:
            return True
        if PdfinsightReader.overlap_percent(cell["box"], box_outline, base="element") > 0.5:
            return True
        return False

    def filter_element_by_title(self, elements, neglect_title_regs, title_regs):
        ret = []
        neglect_title_pattern = PatternCollection(neglect_title_regs)
        title_pattern = PatternCollection(title_regs)
        for element in elements:
            table = parse_table(element, tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight)
            table_title = table.title.text if table.title else element.get("title")
            if table_title and neglect_title_pattern and neglect_title_pattern.nexts(clean_txt(table_title)):
                continue
            if table_title and title_pattern and title_pattern.nexts(clean_txt(table_title)):
                ret.append(element)
            if not title_pattern.patterns:
                ret.append(element)
        return ret

    def create_content_result(
        self, element, chars, cells, split_pattern, garbage_frag_pattern=None, keep_separator=False
    ):
        result = CellCharResult(element, chars, cells)
        if not split_pattern:
            return [result]
        return self.create_split_results(split_pattern, result, garbage_frag_pattern, keep_separator)


def find_currency_element_result(pdfinsight, result: ElementResult):
    if result.element is None:
        return None
    # 处理"币种"在表格上方段落中的情况
    for elt in pdfinsight.find_elements_near_by(result.element["index"], step=-1, aim_types=("PARAGRAPH",)):
        match = re.search(r"币\s*种\s*[:：]\s*(?P<dst>\w{2,4})\s*$", elt["text"])
        if match:
            return CharResult(elt, elt["chars"][slice(*match.span("dst"))])
    # 处理"币种"在当前段落的情况
    currency_pattern = re.compile(r"(?P<dst>人民币|美元)")
    match = currency_pattern.search(result.element.get("text", ""))
    if match:
        return CharResult(result.element, result.element["chars"][slice(*match.span("dst"))])
    return None


def find_unit_by_element_result(result: ElementResult):
    if result.element is None:
        return None
    if result.element["class"] == "TABLE":
        if not isinstance(result, (TableResult, TableCellsResult, CellCharResult)) or not result.parsed_cells:
            return None
        if isinstance(result, CellCharResult):
            return find_unit_from_text(result, cell=result.parsed_cells[0])
        unit_from_parsed_table = result.parsed_cells[0].unit
        if unit_from_parsed_table:
            return unit_from_parsed_table
        # 处理"单位"在表格表头(首行)中的情况
        for header in result.parsed_cells[0].table.header:
            if header.rowidx != 0:
                continue
            unit_from_header = find_unit_from_text(result, cell=header)
            if unit_from_header:
                return unit_from_header
        return None

    if result.element["class"] in ["PARAGRAPH", "PAGE_HEADER", "PAGE_FOOTER"]:
        if not isinstance(result, CharResult):
            return None
        paragraph = result.element
        return find_unit_from_text(result, paragraph=paragraph)
    return None


def get_char_position(char, chars):
    for index, origin_char in enumerate(chars):
        if Rectangle(*char["box"]).overlap_rate(Rectangle(*origin_char["box"])) > 0.9:
            return index
    return None


def select_unit(result, chars, matched):
    matched = list(matched)
    if not matched:
        return None

    if len(matched) == 1:
        return matched[0]

    position = 0
    for char in result.chars:
        _position = get_char_position(char, chars)
        if _position is not None:
            position = _position
            break

    for match in sorted(matched, key=lambda x: x.start()):
        if match.end() >= position:
            return match
    return matched[0]


def find_unit_from_text(result, paragraph=None, cell=None):
    unit_patterns = PatternCollection(
        [
            rf"{result.text}\s*(?P<dst>{UNIT_PATTERN})",
            rf"{result.text}\s*[（（\(]?(?P<dst>{PERCENT_PATTERN})[\)）]?",
            rf"单位[:：]\s*?(?P<dst>{UNIT_PATTERN})",
        ]
    )
    match = None
    if paragraph:
        match = select_unit(result, paragraph["chars"], unit_patterns.finditer(paragraph["text"]))
    if cell:
        match = select_unit(result, cell.raw_cell["chars"], unit_patterns.finditer(cell.text))
    if match:
        unit_slice = slice(*match.span("dst"))
        if paragraph:
            return CharResult(paragraph, paragraph["chars"][unit_slice])
        if cell:
            return CellCharResult(result.element, cell.raw_cell["chars"][unit_slice], [cell])
    if cell and cell.unit:
        # 如果当前cell取不到有效单位，再尝试从行、列头取
        return cell.unit
    return None
