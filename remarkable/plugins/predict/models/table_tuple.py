"""ColHeader-RowHeader-Value 形式的表格
表格解析方法：取所有 body 中的值，取行头、列头作为 header
模型：统计字段 header 对应的 key
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

import logging
from collections import Counter

from remarkable.common.util import clean_txt
from remarkable.pdfinsight.reader import PdfinsightTable
from remarkable.plugins.predict.models.model_base import DIMENSION_PATTERNS, PredictModelBase
from remarkable.predictor.predict import ResultOfPredictor, TblResult


class TupleTable(PredictModelBase):
    model_intro = {
        "doc": """
        行头列头定义特征，如“行-总资产（列-金额、比例）、行-流动资产（列-金额、比例）
        """,
        "name": "二维信息表",
        "hide": True,
    }

    def __init__(self, *args, **kwargs):
        super(TupleTable, self).__init__(*args, **kwargs)
        self.dimension_config = self.config.get("3rd_dimension")

    @classmethod
    def model_template(cls):
        template = {"3rd_dimension": {"type": "", "column": ""}, "just_table": True}
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
                    _features = TupleTable.extract_feature(item.data["elements"], leaf.data)
                    model.setdefault(col, Counter()).update(_features)
        self.model = model

    def predict(self, elements, **kwargs):
        answers = []
        if not self.dimension_config:
            return answers
        dimension_column = self.dimension_config["column"]
        for element in elements:
            if element["class"] != "TABLE":
                continue
            records = TupleTable.parse_table(element)
            groups = self.group_by_pattern(records, DIMENSION_PATTERNS[self.dimension_config["type"]], dimension_column)
            for group in groups.values():
                answer = {}
                for col in self.columns:
                    if col == "币种" or (col.startswith("<") and "单位" in col):
                        _answer = self.find_special_attr(col, element)
                        if _answer:
                            answer[col] = _answer
                        continue
                    _model = self.model.get(col)
                    if not _model:
                        continue
                    for _key, _cnt in _model.most_common():
                        record = TupleTable.find_record_by_header_key(group, _key)
                        if record:
                            _cell = record[2]
                            answer[col] = ResultOfPredictor([TblResult([_cell["index"]], element)])
                            break
                if answer:
                    dimension_cell = TupleTable.find_record_by_header_key(group, dimension_column)[2]
                    answer[dimension_column] = ResultOfPredictor([TblResult([dimension_cell["index"]], element)])
                    answers.append(answer)
        return answers

    def predict_just_table(self, elements):
        answers = []
        for element in elements:
            table_answer = {}
            if element["class"] != "TABLE":
                continue
            for col in self.columns:
                if col in ("（表格）", ">表格<"):
                    # 大表格，取整个表格
                    table_answer[col] = ResultOfPredictor([TblResult([], element)])
                elif col == "币种" or (col.startswith("<") and "单位" in col):
                    _answer = self.find_special_attr(col, element)
                    if _answer:
                        table_answer[col] = _answer
                else:
                    # 其他字段，pass
                    pass
            if table_answer:
                answers.append(table_answer)
        return answers

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
                records = TupleTable.parse_table(element)
                record = TupleTable.find_record_by_value_box(records, box)
                if not record:
                    continue
                feature_key = TupleTable.text_feature_key([c["text"] for c in record[0] + record[1]])
                features.update([feature_key])
        return features

    @staticmethod
    def parse_table(ele_table):
        """将每个 val 和 对应的 row / col 组成一对儿
        |      | col1 | col2 | col3 |
        | row1 | val1 | val2 | val3 |
        | row2 | val4 | val5 | val6 |
        """
        records = []
        tbl = PdfinsightTable(ele_table)

        # 解析表格 header
        topleft = tbl.cells[0][0]
        header_height = topleft["bottom"] - topleft["top"]
        header_width = topleft["right"] - topleft["left"]
        row_header_dict = {}
        col_header_dict = {}
        tbl_width = len(tbl.cells[0])

        for row_idx in range(topleft["bottom"], len(tbl.cells)):
            row_header_dict[row_idx] = [tbl.cells[row_idx][i] for i in range(0, header_width)]
        for col_idx in range(topleft["right"], tbl_width):
            col_header_dict[col_idx] = [tbl.cells[i][col_idx] for i in range(0, header_height)]

        # 解析表格 body
        for row_idx, row_headers in row_header_dict.items():
            for col_idx, col_headers in col_header_dict.items():
                try:
                    val_cell = tbl.cells[row_idx][col_idx]
                except KeyError as e:
                    logging.debug(e)
                    continue
                if val_cell.get("dummy"):
                    continue
                records.append((row_headers, col_headers, val_cell))

        return records

    @classmethod
    def find_record_by_value_box(cls, records, val):
        for record in records:
            if TupleTable.same_box(record[2], val):
                return record
        return None

    @classmethod
    def find_record_by_header_key(cls, records, text):
        keys = text.split("|")
        for record in records:
            headers = record[0] + record[1]
            if all(any(TupleTable.same_text(cell, key) for cell in headers) for key in keys):
                return record
        return None

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
