# -*- coding: utf-8 -*-
"""ColHeader-RowHeader-Value 形式的表格，取其中
表格解析方法：取所有 body 中的值，取行头、列头作为 header
模型：可以指定统计行头或列头，据此选择目标的单元格
特殊情况：暂无

model 示意:
{
    "attr1": Counter({
        "key_1|key_2": 100,
        "key_3": 60,
        ...
    }),
    ...
}
"""

from collections import Counter, defaultdict
from itertools import groupby

from remarkable.predictor.models.base_model import TableModel
from remarkable.predictor.schema_answer import TableCellsResult
from remarkable.predictor.utils import make_pattern


def group_by(cell, select_by="both"):
    if isinstance(cell, tuple):
        cell = cell[2]
    index_map = {"row": 1, "column": 0}  # 取行头做header，按列分组  # 取列头做header，按行分组
    index = index_map.get(select_by, 1)
    return cell["index"].split("_")[index] if select_by != "both" else cell["index"].replace("_", "")


class TupleTableSelect(TableModel):
    filter_elements_by_target = True

    def __init__(self, options, schema, predictor=None):
        super(TupleTableSelect, self).__init__(options, schema, predictor=predictor)
        self.select_by = self._options.get("select_by", "both")

    def predict_grouped_schema_answer(self, elements):
        answer_results = []
        for element in elements:
            records = self.parse_table(element)
            model_data = self.get_model_data()
            if not model_data:
                continue
            cells = []
            header_pattern = make_pattern(self.config.get("header_pattern"))
            if header_pattern.patterns:
                records = TupleTableSelect.find_by_header_pattern(records, header_pattern)
            for _key, _cnt in model_data.most_common():
                cells.extend(TupleTableSelect.find_record_by_header_key(records, _key, self.select_by))
            if cells:
                grouped = defaultdict(set)
                for _, col_cells in groupby(cells, key=lambda x: group_by(x, self.select_by)):
                    for primary, _, cell in col_cells:
                        if primary:
                            grouped[primary[0]["text"]].add(cell["index"])

                for primary_key in grouped:
                    element_results = [TableCellsResult(element, list(grouped[primary_key]))]
                    # TODO: primary_key=primary_key
                    answer_results.append(self.create_result(element_results))

        return answer_results

    def predict_schema_answer(self, elements):
        answer_results = []
        elements = self.revise_elements(elements)

        for element in elements:
            records = self.parse_table(element)
            element_results = []
            model_data = self.get_model_data()
            if not model_data:
                continue
            cells = []
            header_pattern = make_pattern(self.config.get("header_pattern"))
            if header_pattern.patterns:
                records = TupleTableSelect.find_by_header_pattern(records, header_pattern)
            for _key, _cnt in model_data.most_common():
                selected_records = TupleTableSelect.find_record_by_header_key(records, _key, self.select_by)
                for record in selected_records:
                    cells.append(record[2])
            if cells:
                grouped = defaultdict(set)
                for column, col_cells in groupby(cells, key=lambda x: group_by(x, self.select_by)):
                    for cell in col_cells:
                        grouped[column].add(cell["index"])

                for column in grouped:
                    element_results.append(TableCellsResult(element, list(grouped[column])))
                answer_results.append(self.create_result(element_results, value=self.get_answer_value(cells)))

        return answer_results

    def extract_feature(self, elements, answer):
        features = Counter()
        for answer_data in answer["data"]:
            if not answer_data["boxes"]:
                continue
            for box in answer_data["boxes"]:
                for eid in answer_data["elements"]:
                    element = elements.get(eid)
                    if element["class"] != "TABLE":
                        continue
                    records = TupleTableSelect.parse_table(element)
                    selected_records = TupleTableSelect.find_records_by_annotation(records, box)
                    for record in selected_records:
                        row_headers, col_headers, val_cell = record
                        headers = TupleTableSelect.feature_headers(row_headers, col_headers, self.select_by)
                        feature_key = TupleTableSelect.feature_key_str([c["text"] for c in headers])
                        features.update([feature_key])
        return features

    @staticmethod
    def feature_headers(row_headers, col_headers, select_by):
        if select_by == "row":
            headers = row_headers
        elif select_by == "column":
            headers = col_headers
        else:
            headers = row_headers + col_headers
        return headers

    @classmethod
    def find_records_by_annotation(cls, records, val):
        selected = []
        for record in records:
            if TupleTableSelect.aim_cell(record[2], val):
                selected.append(record)
        return selected

    @classmethod
    def find_record_by_header_key(cls, records, text, select_by):
        selected = []
        keys = text.split("|")
        for record in records:
            headers = TupleTableSelect.feature_headers(record[0], record[1], select_by)
            # TODO: 港交所这里直接 same 可能效果不好
            if all(any(TupleTableSelect.same_text(cell, key) for cell in headers) for key in keys):
                selected.append(record)
        return selected

    @classmethod
    def find_by_header_pattern(cls, records, header_pattern):
        return [i for i in records if header_pattern.nexts(i[0][0]["text"]) or header_pattern.nexts(i[1][0]["text"])]

    def get_answer_value(self, cells):
        neg_pattern = self.config.get("cell_neg_pattern")
        if neg_pattern is None:
            return None

        matched_cells = [i for i in cells if neg_pattern.search(i["text"])]
        if len(matched_cells) / len(cells) > 0.7:
            enum_values = self.predictor.get_enum_values(self.schema.type)
            return enum_values[1]
        return None
