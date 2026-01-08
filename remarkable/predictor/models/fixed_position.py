# -*- coding: utf-8 -*-
import re

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.plugins.predict.common import is_paragraph_elt, is_shape_with_text, is_stamp_with_text, is_table_elt
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import CharResult, OutlineResult, PredictorResult


class FixedPosition(BaseModel):
    """
    固定位置提取
    在文档固定位置出现的属性，如证券代码、证券简称、公告编号等
    """

    base_all_elements = True
    filter_elements_by_target = True

    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super().__init__(options, schema, predictor=predictor)
        self.neglect_patterns = PatternCollection(self.get_config("neglect_patterns"))
        self.ignore_element_class = self.get_config("ignore_element_class", [])

    def train(self, dataset, **kwargs):
        pass

    @staticmethod
    def get_text_from_para(element):
        texts = element["text"]
        chars = [i for i in element["chars"] if not re.search(r"^\s+$", i["text"])]
        text = {"text": texts, "chars": chars, "class": "PARAGRAPH"}
        return [text]

    def get_dst_from_content(self, element, column):
        clean_text = clean_txt(element["text"])
        for pattern in self.get_config("regs", [], column=column):
            pattern = PatternCollection(pattern)
            matcher = pattern.nexts(clean_text)
            if not matcher:
                continue
            if is_stamp_with_text(element):
                page_box = self.pdfinsight.elements_outline([element])
                text = matcher.groupdict().get("dst", None)
                return self.create_result([OutlineResult(page_box, text, element)], score=1, column=column)
            else:
                dst_chars = self.get_dst_chars_from_matcher(matcher, element)
                if not dst_chars:
                    continue
                return self.create_result([CharResult(element, dst_chars)], score=1, column=column)
        return None

    def convert_sequences(self, index, key: str):
        if index == 0:
            return index
        if index > 0:
            return index - 1  # 大于0的序列
        else:
            # 小于0的序列
            return len(self.pdfinsight.data[key]) + index

    def flatten_item(self, items, key="_index"):
        if all(isinstance(x, int) and x >= 0 for x in items):
            return items

        # 用户在页面上配的position需要转换
        res = []
        for item in items:
            if not item:
                continue
            if isinstance(item, int) and item >= 0:
                res.append(item)
            else:
                if "," in str(item):
                    res.extend([int(i) for i in item.split(",")])
                else:
                    res.append(int(item))
        res = [self.convert_sequences(i, key) for i in res]
        return res

    def pages(self, column):
        pages = self.get_config("pages", [], column=column)
        return self.flatten_item(pages, key="pages")

    def positions(self, column):
        positions = self.get_config("positions", [], column=column)
        return self.flatten_item(positions, key="_index")

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        answer_results = []
        answer_result = {}
        for column in self.columns:
            column_results = []
            elements_block = self.collect_elements(elements, column)
            eles = self.target_elements_iter(elements_block[0])
            for ele in eles:
                if self.get_config("filter_headers", False):
                    if ele["class"] == "PAGE_HEADER":
                        continue
                if self.neglect_patterns.patterns and self.neglect_patterns.nexts(clean_txt(ele.get("text", ""))):
                    continue
                paragraphs = self.pretreatment(column, ele)
                answer = self.predict_from_text(column, ele, paragraphs)
                if answer:
                    column_results.append(answer)
                if column_results and not self.multi_elements:
                    break
            if column_results:
                answer_result[column] = column_results
        if answer_result:
            answer_results.append(answer_result)
        return answer_results

    def collect_elements(self, elements, column=None):
        pages = self.pages(column)
        positions = self.positions(column)
        eles = []
        if self.get_config("use_crude_answer", False, column=column) and elements:
            eles.extend(elements)
        elif positions:
            for position in positions:
                _, ele = self.pdfinsight.find_element_by_index(position)
                if not ele or (pages and ele["page"] not in pages):
                    continue
                if ele.get("class") not in self.ignore_element_class:
                    eles.append(ele)
            eles = self.merge_neighbor_elements(eles)
        elif pages:
            for page in pages:
                eles.extend(self.pdfinsight.find_elements_by_page(page))
            eles = self.merge_neighbor_elements(eles)
        return [eles]

    def pretreatment(self, column, element):
        paragraphs = []
        if is_paragraph_elt(element) or is_shape_with_text(element) or is_stamp_with_text(element):
            paragraphs = [element]
        elif is_table_elt(element):
            paragraphs = self.get_paragraphs_from_table(element)
        return paragraphs

    def predict_from_text(self, column, element, paragraphs):
        anchor_regs = self.get_config("anchor_regs", [], column=column)
        is_aim_elt = not anchor_regs
        if anchor_regs:
            prev_elts = self.pdfinsight.find_elements_near_by(element["index"], step=1, amount=3)
            if self.get_config("use_crude_answer", False, column=column):
                prev_elts.insert(0, element)
            for prev_elt in prev_elts:
                if is_paragraph_elt(prev_elt):
                    if any(re.search(reg, clean_txt(prev_elt["text"])) for reg in anchor_regs):
                        is_aim_elt = True
                        break
        if is_aim_elt:
            for paragraph in paragraphs:
                ret = self.get_dst_from_content(paragraph, column)
                if ret:
                    return ret
        return None
