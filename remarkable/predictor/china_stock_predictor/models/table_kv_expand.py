from collections import defaultdict
from copy import deepcopy

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.models.middle_paras import MiddleParas
from remarkable.predictor.models.table_kv import KeyValueTable
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import CellCharResult


class KvCellExpand(KeyValueTable):
    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super().__init__(options, schema, predictor=predictor)
        self.top_anchor_pattern = PatternCollection(self.get_config("top_anchor_regs", []))  # 顶部锚点正则
        self.bottom_anchor_pattern = PatternCollection(self.get_config("bottom_anchor_regs", []))  # 底部锚点正则
        self.include_top_anchor = self.get_config("include_top_anchor", True)  # 包含顶部锚点
        self.include_bottom_anchor = self.get_config("include_bottom_anchor", False)  # 包含底部锚点
        self.top_content_regs = self.get_config("top_anchor_content_regs")  # 从顶部锚点提取内容的正则
        self.bottom_content_regs = self.get_config("bottom_anchor_content_regs")  # 从底部锚点提取内容的正则
        self.table_regarded_as_paras = self.get_config("table_regarded_as_paras")
        self.element_offset_range = self.get_config("element_offset_range", 10)

    def predict_schema_answer(self, elements):
        ret = []
        parent_answer_results = super().predict_schema_answer(elements)
        if not parent_answer_results:
            return ret
        parent_answer_results = self.regroup(parent_answer_results)
        for col in self.columns:
            parent_answers = parent_answer_results.get(col)
            if not parent_answers:
                continue
            for parent_answer in parent_answers:
                element = parent_answer.relative_elements[0]
                cell = parent_answer.element_results[0].parsed_cells[0]
                if self.table_regarded_as_paras:
                    paras = self.get_paras(element, cell)
                    option = deepcopy(self.config)
                    option["use_direct_elements"] = True
                    middle_paras = MiddleParas(option, self.schema, predictor=self.predictor)
                    results = middle_paras.predict_schema_answer(paras)
                    ret.extend(results)
                else:
                    cells = self.get_nearby_cells(element, cell)
                    middle_cells = self.get_middle_cells(cells)
                    if middle_cells:
                        dst_chars = []
                        for middle_cell in middle_cells:
                            dst_chars.extend(middle_cell["chars"])
                        answer = self.create_result([CellCharResult(element, dst_chars, cells)], column=col)
                        ret.append(answer)
        return ret

    def get_paras(self, element, cell):
        paras = []
        for index in range(element["index"] - self.element_offset_range, element["index"] + self.element_offset_range):
            ele_type, ele = self.pdfinsight.find_element_by_index(index)
            if ele_type == "PARAGRAPH":
                paras.append(ele)
            elif ele_type == "TABLE":
                paras.extend(self.get_paragraphs_from_table(ele, cols=[cell.colidx]))

        return paras

    def get_middle_cells(self, cells):
        top_index = None
        bottom_index = None
        middle_cells = None
        cells = [x.raw_cell for x in cells]
        for idx, cell in enumerate(cells):
            text = clean_txt(cell["text"])
            if top_index is None and self.top_anchor_pattern.nexts(text):
                top_index = idx
                continue
            if top_index is not None and self.bottom_anchor_pattern.nexts(text):
                bottom_index = idx
                break

        if top_index is None or bottom_index is None:
            return middle_cells

        middle_cells = cells[top_index + 1 : bottom_index]

        if self.include_top_anchor:
            top_anchor_cell = self.get_element_with_content_chars(cells[top_index], self.top_content_regs)
            if top_anchor_cell:
                middle_cells.insert(0, top_anchor_cell)
        if self.include_bottom_anchor:
            bottom_anchor_cell = self.get_element_with_content_chars(cells[bottom_index], self.bottom_content_regs)
            if bottom_anchor_cell:
                middle_cells.append(bottom_anchor_cell)
        return middle_cells

    def get_nearby_cells(self, element, cell):
        table = parse_table(
            element,
            tabletype=TableType.KV.value,
            pdfinsight_reader=self.pdfinsight,
            width_from_all_rows=self.width_from_all_rows,
        )
        return table.cols[cell.colidx]

    @staticmethod
    def regroup(answers):
        ret = defaultdict(list)
        for answer in answers:
            for col, value in answer.items():
                ret[col].extend(value)
        return ret
