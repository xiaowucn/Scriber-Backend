"""按阈值取值"""

from collections import Counter

from remarkable.common.util import clean_txt
from remarkable.pdfinsight.reader import PdfinsightTable
from remarkable.predictor.predict import ParaResult, ResultOfPredictor, TblResult, get_tbl_text

from .model_base import DIMENSION_PATTERNS, PredictModelBase, TableRecords


class ScoreFilter(PredictModelBase):
    model_intro = {"doc": "按位置定位结果，提取单个段落/表格", "name": "段落/表格定位"}

    def __init__(self, *args, **kwargs):
        super(ScoreFilter, self).__init__(*args, **kwargs)
        self.need_training = False

    @classmethod
    def model_template(cls):
        template = {}
        default_model_template = cls.default_model_template()
        default_model_template.update(template)
        return default_model_template

    def train(self, dataset, **kwargs):
        model = {}
        # for item in dataset:
        #     for col in self.columns:
        #         leaves = item.answer.get(col, {}).values() if col != "_main" else [item.answer]
        #         for leaf in leaves:
        #             if leaf.data is None:
        #                 continue
        #             _features = ScoreFilter.extract_feature(item.data["elements"], leaf.data, self.config)
        #             model.setdefault(col, Counter()).update(_features)
        self.model = model

    def predict(self, elements, **kwargs):
        threshold = self.config.get("threshold", 0.5)
        answers = []
        elements = elements or []
        for element in elements:
            if element.get("score", 0) < threshold:
                continue
            answer = {}
            for col in self.columns:
                if col == "币种" or (col.startswith("<") and "单位" in col):
                    _answer = self.find_special_attr(col, element)
                    if _answer:
                        answer[col] = _answer
                    continue
                data = []
                if element["class"] == "PARAGRAPH":
                    data.append(ParaResult(element["chars"], element, text=clean_txt(element["text"])))
                elif element["class"] == "TABLE":
                    data.append(TblResult([], element, text=get_tbl_text(element)))
                if data:
                    answer[col] = ResultOfPredictor(data)
            if answer:
                answers.append(answer)
        return answers

    def predict_just_table(self, elements):
        answers = []
        for element in elements:
            if element["class"] != "TABLE":
                continue
            dimension_data, common_data = next(iter(ScoreFilter.parse_table(element, self.config)), (None, None))
            for dimension_group in dimension_data.values():
                table_answer = {}
                group = dimension_group + common_data
                for col in self.columns:
                    if col in ("（表格）", ">表格<"):
                        # 大表格，取整个表格
                        table_answer[col] = ResultOfPredictor([TblResult([], element)])
                    elif col == "币种" or (col.startswith("<") and "单位" in col):
                        _answer = self.find_special_attr(col, element)
                        if _answer:
                            table_answer[col] = _answer
                    else:
                        # 其他字段，取 header 的位置
                        _model = self.model.get(col)
                        if not _model:
                            continue
                        for _key, _cnt in _model.most_common():
                            header_cells, _ = ScoreFilter.find_tuple_by_header_text(group, _key)
                            if header_cells:
                                table_answer[col] = ResultOfPredictor(
                                    [
                                        TblResult(
                                            [_cell["index"] for _cell in header_cells if not _cell.get("fake")], element
                                        )
                                    ]
                                )
                                break
                if table_answer:
                    answers.append(table_answer)
        return answers

    @staticmethod
    def extract_feature(elements, answer, config):
        features = Counter()
        for answer_data in answer["data"]:
            if not answer_data["boxes"]:
                continue
            box = answer_data["boxes"][0]  # TODO:
            for eid in answer_data["elements"]:
                element = elements.get(eid)
                if element["class"] != "TABLE":
                    continue
                records = []
                for dimension_data, common_data in ScoreFilter.parse_table(element, config):
                    records.extend(common_data)
                    for _dimension_data in dimension_data.values():
                        records.extend(_dimension_data)
                header, _ = ScoreFilter.find_tuple_by_outline(records, box)
                if not header:
                    continue
                header_str = ScoreFilter.text_feature_key([c["text"] for c in header if not c.get("dummy")])
                features.update([header_str])
        return features

    @staticmethod
    def parse_table(element, config):
        """按行解析
        |      | split_by_col |
        | col1 | col2 | col3  |
        | val1 | val2 | val3  |
        """
        records = TableRecords()
        tbl = PdfinsightTable(element)
        topleft = tbl.cells[0][0]
        header_height = topleft["bottom"] - topleft["top"]

        # 解析表格 header
        headers = {}
        for i in range(len(tbl.cells[0])):
            header_cells = [tbl.cells[j][i] for j in range(header_height)]
            if all((cell.get("dummy") for cell in header_cells)):
                continue
            headers[i] = header_cells

        # 按行解析表格 body，输出 groups = [{ header1: body_item1, ...}, {header1: body_item2, ...}, ...]
        groups = []
        for ridx in range(header_height, len(tbl.cells)):
            row = tbl.cells[ridx]
            group = []
            for cidx, header in headers.items():
                val_cell = row[cidx]
                if val_cell.get("dummy"):
                    continue
                group.append((header, val_cell))
            groups.append(group)

        # 根据 dimension 配置，从 header 值里匹配新增一个维度
        records = []
        dimension_config = config["3rd_dimension"]
        dimension_pattern = DIMENSION_PATTERNS[dimension_config["type"]]

        for group in groups:
            dimension_data = {}  # {"2018年": [([Cell("占比")], Cell(val1)), ([Cell("总值")], Cell(val2))]}
            common_data = []
            for header, val_cell in group:
                dimension_cell = next(
                    (_cell for _cell in header if dimension_pattern.match(clean_txt(_cell["text"]))), None
                )
                # header_cells = [_cell for _cell in header if _cell != dimension_cell]
                if dimension_cell:
                    dimension_data.setdefault(
                        clean_txt(dimension_cell["text"]),
                        [([fake_cell(dimension_config["column"])], dimension_cell)],  # dimension_cell
                    ).append(
                        (header + [fake_cell("D_%s" % dimension_config["type"])], val_cell)
                    )  # 给 header 里加一条 D_type
                else:
                    common_data.append((header, val_cell))
            records.append((dimension_data, common_data))

        return records

    @staticmethod
    def find_tuple_by_outline(group, answer_box):
        for header, value_cell in group:
            if ScoreFilter.same_box(value_cell, answer_box):
                return header, value_cell
            if any(ScoreFilter.same_box(_cell, answer_box) for _cell in header):
                return header, value_cell
        return None, None

    @staticmethod
    def find_tuple_by_header_text(group, text):
        keys = text.split("|")
        for header_cells, value_cell in group:
            if all(any(ScoreFilter.same_text(_cell, key) for _cell in header_cells) for key in keys):
                return header_cells, value_cell
        return None, None


def fake_cell(text):
    return {"text": text, "fake": True}
