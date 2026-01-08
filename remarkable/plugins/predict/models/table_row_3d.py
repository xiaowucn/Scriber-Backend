"""按元组读取的表格：在按行读取基础上，增加一个维度
表格解析方法：
1. 基于 RowTable3D 的方法首先按行解析成 groups
2. 根据传入的 split_by 参数，从 header 中提取指定特征的数据作为第三维度，将数据分为 tuples

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

from collections import Counter

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.reader import PdfinsightTable
from remarkable.predictor.predict import ResultOfPredictor, TblResult

from .model_base import DIMENSION_PATTERNS, PredictModelBase, TableRecords


class RowTable3D(PredictModelBase):
    model_intro = {
        "doc": """
        两级表头定义特征，如“行-总资产（一级列-2018、2019，二级列-金额、比例）”
        """,
        "name": "三维信息表",
        "hide": True,
    }

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
                    _features = RowTable3D.extract_feature(item.data["elements"], leaf.data, self.config)
                    model.setdefault(col, Counter()).update(_features)
        self.model = model

    def predict(self, elements, **kwargs):
        answers = []
        if not self.config.get("3rd_dimension", {}):
            return answers
        dimension_col = self.config.get("3rd_dimension", {}).get("column")
        for element in elements:
            if element["class"] != "TABLE":
                continue
            for dimension_data, common_data in RowTable3D.parse_table(element, self.config):
                for dimension_group in dimension_data.values():
                    answer = {}
                    group = dimension_group + common_data
                    for col in self.columns:
                        if "表格" in col:
                            continue
                        if col in ("币种",) or (col.startswith("<") and "单位" in col) or col.endswith("原文单位"):
                            _answer = self.find_special_attr(col, element)
                            if _answer:
                                answer[col] = _answer
                            continue
                        if col == dimension_col:  # pass dimension_col，由 pattern 提取
                            continue
                        _model = self.model.get(col)
                        if not _model:
                            continue
                        for _key, _cnt in _model.most_common():
                            _, _cell = RowTable3D.find_tuple_by_header_text(group, _key)
                            if not _cell:
                                continue
                            if not self.match_special_header(_cell, col, element):
                                continue
                            answer[col] = ResultOfPredictor([TblResult([_cell["index"]], element)])
                            break
                    if answer:
                        _, _cell = RowTable3D.find_tuple_by_header_text(group, dimension_col)
                        if _cell:
                            answer[dimension_col] = ResultOfPredictor([TblResult([_cell["index"]], element)])
                        answers.append(answer)
        return answers

    def match_special_header(self, cell, col_name, element):
        header_config = self.config.get("header_regs", {})
        header_regs = header_config.get(col_name)
        if not header_config or not header_regs:  # 没有配置根据行头过滤
            return True
        header_reg_pattern = PatternCollection(header_regs)
        cell_row_id, cell_col_id = cell.get("index", "_").split("_")
        row_headers = [element["cells"].get(f"{cell_row_id}_{i}", {}).get("text", "") for i in range(3)]
        col_headers = [element["cells"].get(f"{i}_{cell_col_id}", {}).get("text", "") for i in range(3)]
        if any(any(header_reg_pattern.search(i)) for i in row_headers + col_headers):
            return True
        return False

    def predict_just_table(self, elements):
        answers = []
        # print('~~~~~', self.columns, self.config)
        for element in elements:
            if element["class"] != "TABLE":
                continue
            dimension_data, common_data = next(iter(RowTable3D.parse_table(element, self.config)), (None, None))
            if not dimension_data:
                continue
            for dimension_group in dimension_data.values():
                table_answer = {}
                group = dimension_group + common_data
                for col in self.columns:
                    if col in ("（表格）", ">表格<"):
                        # 大表格，取整个表格
                        table_answer[col] = ResultOfPredictor([TblResult([], element)])
                    elif col == "币种" or (col.startswith("<") and "单位" in col):
                        _answer = self.find_special_attr(
                            col, element, unit_priority=self.config.get("unit_priority", {})
                        )
                        if _answer:
                            table_answer[col] = _answer
                    elif col == "年度":
                        header_cells, value_cell = RowTable3D.find_tuple_by_header_text(group, col)
                        if value_cell and value_cell.get("index"):
                            table_answer[col] = ResultOfPredictor([TblResult([value_cell.get("index")], element)])
                    else:
                        # 其他字段，取 header 的位置
                        _model = self.model.get(col)
                        if not _model:
                            continue
                        for _key, _cnt in _model.most_common():
                            header_cells, value_cell = RowTable3D.find_tuple_by_header_text(group, _key)
                            _header = []
                            for _cell in header_cells or []:
                                if _cell.get("fake") or _cell.get("dummy"):
                                    continue
                                if DIMENSION_PATTERNS["date"].search(_cell.get("text", "")):
                                    continue
                                _header.append(_cell)
                            if _header:
                                table_answer[col] = ResultOfPredictor(
                                    [TblResult([_cell["index"] for _cell in _header], element)]
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
                for dimension_data, common_data in RowTable3D.parse_table(element, config):
                    records.extend(common_data)
                    for _dimension_data in dimension_data.values():
                        records.extend(_dimension_data)
                header, _ = RowTable3D.find_tuple_by_outline(records, box)
                if not header:
                    continue
                header_str = RowTable3D.text_feature_key([c["text"] for c in header if not c.get("dummy")])
                features.update([header_str])
        return features

    # @staticmethod
    # def extract_table_feature(elements, answer, config):
    #     features = Counter()
    #     for answer_data in answer["data"]:
    #         box = answer_data["boxes"][0]  # TODO:
    #         for eid in answer_data["elements"]:
    #             element = elements.get(eid)
    #             if element["class"] != "TABLE":
    #                 continue
    #             records = []
    #             for dimension_data, common_data in RowTable3D.parse_table(element, config):
    #                 records.extend(common_data)
    #                 for _dimension_data in dimension_data.values():
    #                     records.extend(_dimension_data)
    #             header, _ = RowTable3D.find_tuple_by_outline(records, box)
    #             if not header:
    #                 continue
    #             header_str = "|".join([clean_txt(cell["text"]) for cell in header])  # if not cell.get("fake")
    #             features.update([header_str])
    #     return features

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
        # headers = {0: [['0_0', ]], 1: [['0_1']], 2:[['0_2']], ... }
        headers = {}
        for i in range(len(tbl.cells[0])):
            header_cells = [tbl.cells[j][i] for j in range(header_height)]
            if all(cell.get("dummy") for cell in header_cells):
                continue
            headers[i] = header_cells

        # 按行解析表格 body，输出 groups = [{ header1: body_item1, ...}, {header1: body_item2, ...}, ...]
        groups = []
        for ridx in range(header_height, len(tbl.cells)):
            row = tbl.cells.get(ridx, {})
            if not row:
                continue
            group = []
            for cidx, header in headers.items():
                val_cell = row.get(cidx, {})
                if not val_cell:
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
            # print('------ dimension_data')
            # for dimension_key, data in dimension_data.items():
            #     print('dimension_key', dimension_key)
            #     print([[[x['text'] for x in headers], _cell['text']] for headers, _cell in data])
            #
            # print('------ common_data')
            # print([[[x['text'] for x in headers], _cell['text']] for headers, _cell in common_data])
            records.append((dimension_data, common_data))

        return records

    @staticmethod
    def find_tuple_by_outline(group, answer_box):
        for header, value_cell in group:
            if RowTable3D.same_box(value_cell, answer_box):
                return header, value_cell
            if any(RowTable3D.same_box(_cell, answer_box) for _cell in header):
                return header, value_cell
        return None, None

    @staticmethod
    def find_tuple_by_header_text(group, text):
        keys = text.split("|")
        for header_cells, value_cell in group:
            if all(any(RowTable3D.same_text(_cell, key) for _cell in header_cells) for key in keys):
                return header_cells, value_cell
        return None, None


def fake_cell(text):
    return {"text": text, "fake": True}
