"""按行读取的表格
表格解析方法：除 header 外，每行解析成 {"col1": "val1", "col2": "val2"}
模型：统计字段对应的 key
特殊情况：暂无

model 示意:
{
    "attr1": Counter({
        "header_key_1": 100,
        "header_key_2": 60,
        ...
    }),
    ...
}
"""

import logging
import re
from collections import Counter

from remarkable.common.util import DATE_PATTERN, clean_txt
from remarkable.pdfinsight.reader import PdfinsightTable
from remarkable.predictor.predict import ResultOfPredictor, TblResult

from .model_base import PredictModelBase


class RowTable(PredictModelBase):
    model_intro = {
        "doc": """
        信息项具备多个结果，每一行代表一组数据，如：股东情况（股东1、股东2、股东3）
        """,
        "name": "多行信息值列示表",
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
                    _features = RowTable.extract_feature(item.data["elements"], leaf.data)
                    _model = model.setdefault(col, Counter())
                    _model.update([x for x in _features if x not in _model])
        self.model = model

    def predict(self, elements, **kwargs):
        answers = []
        for element in elements:
            if element["class"] != "TABLE":
                continue
            groups = RowTable.parse_table(element)
            mid_date = None
            for group in groups:
                if self.is_date_row(group):
                    mid_date = [cell for _, cell in group][0]
                    continue
                answer = {}
                for col in self.columns:
                    if col in ("币种",) or (col.startswith("<") and "单位" in col):
                        _answer = self.find_special_attr(col, element)
                        if _answer:
                            answer[col] = _answer
                        continue
                    _model = self.model.get(col)
                    if not _model:
                        continue
                    for _key, _ in _model.most_common():
                        _, _cell = RowTable.find_tuple_by_header_text(group, _key)
                        if _cell and _cell.get("text") and clean_txt(_cell["text"]) != _key:
                            answer[col] = ResultOfPredictor([TblResult([_cell["index"]], element)])
                            break
                # mid_row中提取年度
                if "年度" in self.columns and "年度" not in answer:
                    date_answer = (
                        ResultOfPredictor([TblResult([mid_date["index"]], element)])
                        if mid_date
                        else self.find_special_attr("年度", element)
                    )
                    if date_answer:
                        answer.update({"年度": date_answer})

                if answer and all(attr in answer for attr in self.config.get("necessary", [])):
                    answers.append(answer)
        return answers

    def predict_just_table(self, elements):
        answers = []
        for element in elements:
            table_answer = {}
            group = next(iter(RowTable.parse_table(element)), None)
            if not group:
                logging.warning("can't parse any record in table element")
                continue
            columns = [col for col in self.columns if col not in self.config.get("exclude_attr", [])]
            for col in columns:
                neglect_patterns = self.config.get("neglect_patterns", {}).get(col) or []
                if "序号" not in col:
                    neglect_patterns.append("序号")
                if col in ("（表格）", ">表格<"):
                    # 大表格，取整个表格
                    table_answer[col] = ResultOfPredictor([TblResult([], element)])
                elif col == "币种" or (col.startswith("<") and "单位" in col):
                    answer = self.find_special_attr(col, element)
                    if answer:
                        table_answer.update({col: answer})
                else:
                    # 其他字段，取 header 的位置
                    _model = self.model.get(col)
                    if not _model:
                        continue
                    for _key, _cnt in _model.most_common():
                        if any(re.search("^%s$" % pattern, _key) for pattern in neglect_patterns):
                            continue
                        header_cells, _ = RowTable.find_tuple_by_header_text(group, _key)
                        if header_cells:
                            if col == "年度" and any(
                                "占比" in _cell["text"] for _cell in header_cells
                            ):  # hard code, to fix
                                continue
                            table_answer[col] = ResultOfPredictor(
                                [
                                    TblResult(
                                        [_cell["index"] for _cell in header_cells if not _cell.get("dummy")], element
                                    )
                                ]
                            )
                            break
            # 尝试从表格上方提取年度
            if "年度" in columns and not table_answer.get("年度"):
                answer = self.find_special_attr("年度", element)
                if answer:
                    table_answer.update({"年度": answer})
            if table_answer and all(attr in table_answer for attr in self.config.get("necessary", [])):
                answers.append(table_answer)
        return answers

    @staticmethod
    def is_date_row(group):
        cells = [cell for headers, cell in group if not cell.get("dummy")]
        texts = [clean_txt(cell["text"]) for cell in cells if cell["text"]]
        if len(cells) == 1 and len(texts) == 1:
            if re.search(DATE_PATTERN, texts[0]):
                return True
        return None

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
                groups = RowTable.parse_table(element)
                for group in groups:
                    if RowTable.is_date_row(group):
                        continue
                    header, value = RowTable.find_tuple_by_outline(group, box)
                    if not header:
                        continue
                    header_str = RowTable.text_feature_key({c["text"] for c in header})
                    features.update([header_str])
        return features

    @staticmethod
    def parse_table(element):
        """按行解析
        | col1 | col2 | col3 |
        | val1 | val2 | val3 |
        """
        groups = []
        tbl = PdfinsightTable(element)
        offset = 0  # 第一行可能为mid_row
        if len([cell for cell in tbl.cells[0].values() if not cell.get("dummy")]) == 1:
            offset += 1
        topleft = tbl.cells[0 + offset][0]
        header_height = topleft["bottom"] - topleft["top"]
        headers = {}
        for i in range(tbl.size[1]):
            header_cells = [tbl.cells[j][i] for j in range(header_height + offset)]
            if all(cell.get("dummy") for cell in header_cells):
                continue
            headers[i] = header_cells
        for ridx in range(header_height + offset, len(tbl.cells)):
            row = tbl.cells[ridx]
            group = []
            for cidx, header in headers.items():
                val_cell = row.get(cidx, {})
                if val_cell:
                    group.append((header, val_cell))
            groups.append(group)
        return groups

    @staticmethod
    def find_tuple_by_outline(group, answer_box):
        for header, value_cell in group:
            if RowTable.same_box(value_cell, answer_box):
                return header, value_cell
            if any(RowTable.same_box(_cell, answer_box) for _cell in header):
                return header, value_cell
        return None, None

    @staticmethod
    def find_tuple_by_header_text(group, text):
        keys = text.split("|")
        for header_cells, value_cell in group:
            if all(any(RowTable.same_text(_cell, key) for _cell in header_cells) for key in keys):
                return header_cells, value_cell
        return None, None
