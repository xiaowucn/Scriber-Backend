"""Key-Value 形式的表格
表格解析方法：每两个格子组成 pair， 左 key 右 value
模型：统计字段对应的 key
特殊情况：暂无

model 示意:
{
    "attr1": Counter({
        "key_1": 100,
        "key_2": 60,
        ...
    }),
    ...
}

注：带大表格的先不用实现，只取定位大表格即可
"""

import re
from collections import Counter
from copy import deepcopy

from remarkable.common.util import clean_txt
from remarkable.pdfinsight.reader import PdfinsightReader, PdfinsightTable
from remarkable.predictor.predict import ResultOfPredictor, TblResult

from .model_base import PredictModelBase


class KeyValueTable(PredictModelBase):
    model_intro = {
        "doc": """
        多个信息项以表格列示，如发行人-值，注册地址-值
        """,
        "name": "多个信息项列示表",
    }

    @classmethod
    def model_template(cls):
        template = {"just_table": True}
        default_model_template = cls.default_model_template()
        default_model_template.update(template)
        return default_model_template

    def train(self, dataset, **kwargs):
        model = {}
        dataset = dataset or []
        for item in dataset:
            for col in self.columns:
                leaves = item.answer.get(col, {}).values() if not self.leaf else [item.answer]
                for leaf in leaves:
                    if leaf.data is None:
                        continue
                    _features = KeyValueTable.extract_feature(item.data["elements"], leaf.data)
                    model.setdefault(col, Counter()).update(_features)
        self.model = model

    def predict(self, elements, **kwargs):
        answer = {}
        for element in elements:
            for col in self.columns:
                if col == "币种" or (col.startswith("<") and "单位" in col):
                    _answer = self.find_special_attr(col, element)
                    if _answer:
                        answer[col] = _answer
            if element["class"] != "TABLE":
                continue
            element = regroup_table_element(element)
            kv_pairs = KeyValueTable.parse_table(element)
            for col in self.columns:
                _model = self.model.get(col)
                if not _model:
                    continue
                for _key, _cnt in _model.most_common():
                    pair = KeyValueTable.find_kv_pair(kv_pairs, _key)
                    if pair:
                        _cell = pair[1]
                        answer[col] = ResultOfPredictor([TblResult([_cell["index"]], element)])
                        break
        return [answer]

    def predict_just_table(self, elements):
        answer = {}
        for element in elements:
            if element["class"] != "TABLE":
                continue
            for col in self.columns:
                if col in ("（表格）", ">表格<"):
                    answer[col] = ResultOfPredictor([TblResult([], element)])
                if col == "币种" or (col.startswith("<") and "单位" in col):
                    _answer = self.find_special_attr(col, element)
                    if _answer:
                        answer[col] = _answer
        return [answer]

    @staticmethod
    def extract_feature(elements, answer):
        features = Counter()
        for answer_data in answer["data"]:
            if not answer_data["boxes"]:
                continue
            box = answer_data["boxes"][0]  # TODO:
            for eid in answer_data["elements"]:
                element = elements.get(eid)
                if element["class"] != "TABLE":
                    continue
                element = regroup_table_element(element)
                kv_pairs = KeyValueTable.parse_table(element)
                pair = KeyValueTable.find_kv_pair(kv_pairs, box, idx=1, mode="box")
                if not pair:
                    continue
                features.update([clean_txt(pair[0]["text"])])
        return features

    @staticmethod
    def parse_table(ele_table):
        """将表格相邻两个单元格解析成键值对
        | key1 | value1 | key2 | value2 |
        """
        kv_pairs = []
        tbl = PdfinsightTable(ele_table)
        for _, row in sorted(tbl.cells.items()):
            availcells = [c for cidx, c in sorted(row.items()) if not c.get("dummy")]
            kv_pairs.extend(zip(availcells[0::2], availcells[1::2]))
        return kv_pairs

    @staticmethod
    def find_kv_pair(kv_pairs, val, idx=0, mode="text"):
        """根据单元格的 text 或者 box 查找对应的 kv_pair"""

        def same_text(cell, text):
            return clean_txt(cell["text"]) == clean_txt(text)

        def same_box(cell, box):
            if cell["page"] != box["page"]:
                return False
            box_outline = (
                box["box"]["box_left"],
                box["box"]["box_top"],
                box["box"]["box_right"],
                box["box"]["box_bottom"],
            )
            if not cell.get("box"):
                return False
            if PdfinsightReader.overlap_percent(cell["box"], box_outline, base="box") < 0.5:
                return False
            return True

        for pair in kv_pairs:
            cell = pair[idx]
            if mode == "text" and same_text(cell, val):
                return pair
            if mode == "box" and same_box(cell, val):
                return pair
        return None


def regroup_table_element(element):
    """尝试将可能合并的单元格分割开，重组成新的元素块"""
    ret_elt = deepcopy(element)
    tbl = PdfinsightTable(element)
    for _, row in tbl.cells.items():
        cells = [c for cidx, c in sorted(row.items()) if not c.get("dummy")]
        for cell in split_cell(cells):
            ret_elt["cells"][cell["index"]] = cell
    return ret_elt


def split_cell(cells):
    """将可能的合并单元格拆成两个单元格，暂用冒号做拆分依据"""
    pattern = re.compile(r":|：")
    if len(cells) != 1:
        return cells
    cell = cells[0]
    if cell["right"] - cell["left"] < 2 or len(pattern.split(cell["text"])) != 2:
        # 只考虑列向合并的情况
        return cells
    ret_cells = []
    virtual_cell = {
        "styles": cell["styles"],
        "box": [],
        "text": "",
        "chars": [],
        "page": cell["page"],
        "styles_diff": cell["styles_diff"],
        "left": 0,
        "right": 1,
        "top": cell["top"],
        "bottom": cell["bottom"],
        "index": f"{cell['index'].split('_')[0]}_0",
    }
    for char in cell["chars"]:
        if pattern.search(char["text"]):
            ret_cells.append(deepcopy(virtual_cell))
            virtual_cell.update(
                {"box": [], "text": "", "chars": [], "left": 1, "right": 2, "index": f"{cell['index'].split('_')[0]}_1"}
            )
        else:
            virtual_cell["box"] = expand_box(virtual_cell["box"], char["box"][::])
            virtual_cell["text"] += char["text"]
            virtual_cell["chars"].append(char)
    ret_cells.append(virtual_cell)
    return ret_cells


def expand_box(origin_box, new_box):
    if not origin_box:
        return new_box
    left_top_x = min(origin_box[0], new_box[0])
    left_top_y = min(origin_box[1], new_box[1])
    right_bottom_x = max(origin_box[2], new_box[2])
    right_bottom_y = max(origin_box[3], new_box[3])
    return [left_top_x, left_top_y, right_bottom_x, right_bottom_y]
