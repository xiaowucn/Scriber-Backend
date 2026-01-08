import re
from collections import Counter

from remarkable.common.util import clean_txt, group_cells
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.plugins.predict.common import find_syl_by_elt_index, is_table_elt
from remarkable.plugins.predict.models.model_base import PredictModelBase
from remarkable.plugins.predict.models.partial_text_v3 import PartialTextV3
from remarkable.plugins.predict.models.table_row import RowTable
from remarkable.predictor.predict import ResultOfPredictor, TblResult


class RelationshipOfShareholder(PredictModelBase):
    """
    发行人基本情况-股东关系
    模型：统计标注内容对应的章节标题
    model 示例:
    {
        "发行人基本情况-股东关系": Counter({
            "本次发行前各股东间的关联关系": 10,
            "各股东间的关联关系及持股比例": 6,
            ...
        }),
        ...
    }

    """

    model_intro = {
        "doc": """
        股东关系章节下的表格解析，段落形式待定
        """,
        "name": "股东关系",
        "hide": True,
    }

    def __init__(self, *args, **kwargs):
        self.main_partial_text = PartialTextV3(*args, **kwargs)
        self._model = {}
        super(RelationshipOfShareholder, self).__init__(*args, **kwargs)
        self.base_on_crude_element = False

    @property
    def model(self):
        return self._model

    @model.setter
    def model(self, data):
        self._model = data
        self.main_partial_text.model = data.get("main_partial_text")

    @classmethod
    def model_template(cls):
        template = {}
        default_model_template = cls.default_model_template()
        default_model_template.update(template)
        return default_model_template

    @staticmethod
    def extract_feature(anser_item, answer):
        sylls = anser_item.data.get("syllabuses", [])
        features = Counter()
        for answer_data in answer["data"]:
            if not answer_data["elements"]:
                continue
            for elt_idx in answer_data["elements"]:
                aim_syls = find_syl_by_elt_index(elt_idx, sylls)
                if aim_syls:
                    clear_syl = clear_syl_title(aim_syls[-1]["title"])
                    features.update(
                        [
                            clear_syl,
                        ]
                    )
                break
        return features

    def train(self, dataset, **kwargs):
        model = {}
        dataset = dataset or []
        # print('----------', self.columns, self.config, len(dataset), self.leaf)
        for item in dataset:
            # 表头
            for col in self.columns:
                if "原文" in col:
                    continue
                leaves = item.answer.get(col, {}).values() if not self.leaf else [item.answer]
                for leaf in leaves:
                    if leaf.data is None:
                        continue
                    _features = RowTable.extract_feature(item.data["elements"], leaf.data)
                    model.setdefault(col, Counter()).update(_features)
        for item in dataset:
            # 章节标题
            for col in self.columns:
                if "原文" not in col:
                    continue
                leaves = item.answer.get(col, {}).values() if not self.leaf else [item.answer]
                for leaf in leaves:
                    if leaf.data is None:
                        continue
                    _features = self.extract_feature(item, leaf.data)
                    model.setdefault(self.config["path"][0], Counter()).update(_features)
                    break
        self.main_partial_text.train(dataset)
        model.update({"main_partial_text": self.main_partial_text.model})
        self._model = model

    def is_header_row(self, row_cells):
        for _, cell in row_cells.items():
            for attr in ["股东名称", "关联关系"]:
                _model = self.model.get(attr)
                if not _model:
                    continue
                for _key, _cnt in _model.most_common():
                    if clean_txt(cell["text"]) == _key:
                        return True
        return False

    def _predict_just_table(self, elt, **kwargs):
        answers = []
        cells_by_row, cells_by_col = group_cells(elt["cells"])
        headers = dict.fromkeys(["股东名称", "关联关系"])
        for attr in headers:
            _model = self.model.get(attr)
            if not _model:
                continue
            for _key, _cnt in _model.most_common():
                for col, cell in cells_by_row.get("0", {}).items():
                    if clean_txt(cell["text"]) == _key and headers.get(attr) is None:
                        headers[attr] = col
                        break
                if headers.get(attr) is not None:
                    break
        # print('headers', headers)
        if not all(headers.values()):
            return answers
        groups = [
            {},
        ]
        for row, cells in cells_by_row.items():
            if self.is_header_row(cells):
                continue
            if cells[headers["关联关系"]].get("dummy") is None:
                group = {}
                groups.append(group)
            else:
                group = groups[-1]
            for attr, col in headers.items():
                cell = cells.get(col)
                cell_idx = "_".join(map(str, [row, col]))
                if cell and not cell.get("dummy") and cell.get("text"):
                    group.setdefault(attr, []).append(cell_idx)
        for group in groups:
            if not all(group.get(attr) for attr in headers):
                continue
            # print('****', group)
            answer = {}
            for attr in self.columns:
                if "原文" in attr:
                    answer[attr] = ResultOfPredictor([TblResult([], elt)], score=elt.get("score"))
                else:
                    answer[attr] = ResultOfPredictor(
                        [TblResult([cell_idx], elt) for cell_idx in group[attr]], score=elt.get("score")
                    )
            if answer and all(attr in answer for attr in self.config.get("necessary", [])):
                answers.append(answer)
        return answers

    def predict(self, elements, **kwargs):
        answers = []
        # print('--------', self.config, self.columns)
        title_model = self.model.get(self.config["path"][0])
        if not title_model:
            return answers
        aim_syl = None
        for title, _ in title_model.most_common():
            syls = self.pdfinsight.find_sylls_by_pattern(
                [
                    re.compile(title),
                ]
            )
            if syls:
                aim_syl = syls[0]
                break
        if not aim_syl:
            return answers
        # print('aim_syl', aim_syl)
        tbl_cache = {}
        table_candidate = []
        para_candidate = []
        for elt_idx in range(*aim_syl["range"]):
            elt_typ, elt = self.pdfinsight.find_element_by_index(elt_idx)
            if not elt:
                continue
            if elt_typ == "PARAGRAPH":
                para_candidate.append(elt)
            if is_table_elt(elt):
                table_candidate.append(elt)

        for table_elt in table_candidate:
            key = []
            cells_by_row, _ = group_cells(table_elt["cells"])
            for row, cells in cells_by_row.items():
                for col, cell in cells.items():
                    key.append((row, col, cell.get("text")))
            key = tuple(key)
            if key not in tbl_cache:
                answers.extend(self._predict_just_table(table_elt))
            tbl_cache.setdefault(key, []).append(table_elt["index"])
        answers.extend(self.main_partial_text.predict(para_candidate))
        return answers
