import re
from collections import Counter

from remarkable.common.util import clean_txt, group_cells
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.plugins.predict.common import find_syl_by_elt_index
from remarkable.plugins.predict.models.model_base import PredictModelBase
from remarkable.plugins.predict.models.table_row import RowTable
from remarkable.predictor.predict import CharResult, ResultOfPredictor, TblResult


class Correlation(PredictModelBase):
    """
    公司治理与独立性-关联方及关联关系
    模型：统计标注内容对应的章节标题 + 表头
    model 示例:
    {
        "发行人基本情况-关联方及关联关系": Counter({
            "八、关联方、关联关系和关联交易": 10,
            "九、关联方和关联交易": 6,
            ...
        }),
        "关联方名称": Counter({
            "关联方": 10,
            "姓名": 6,
            ...
        }),
        ...
    }

    """

    model_intro = {
        "doc": """
        解析关联方章节，标题=>关联类型，表格=>关联方名称+关联关系（段落提取待定）
        """,
        "name": "关联方及关联关系",
        "hide": True,
    }

    def __init__(self, *args, **kwargs):
        super(Correlation, self).__init__(*args, **kwargs)
        self.base_on_crude_element = False

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
                elt_syls = find_syl_by_elt_index(elt_idx, sylls)
                if elt_syls:  # 统计完整的章节路径？
                    clear_syl = clear_syl_title(elt_syls[-1]["title"])
                    features.update(
                        [
                            clear_syl,
                        ]
                    )
        return features

    def train(self, dataset, **kwargs):
        model = {}
        dataset = dataset or []
        for item in dataset:
            # 统计表格所在的章节标题
            for col in self.columns:
                if "表格" not in col:
                    continue
                leaves = item.answer.get(col, {}).values() if not self.leaf else [item.answer]
                for leaf in leaves:
                    if leaf.data is None:
                        continue
                    _features = self.extract_feature(item, leaf.data)
                    model.setdefault(self.config["path"][0], Counter()).update(_features)
                    # break

        for item in dataset:
            # 表头
            for col in ["关联方名称", "关联关系"]:  # todo:训练关联类型
                leaves = item.answer.get(col, {}).values() if not self.leaf else [item.answer]
                for leaf in leaves:
                    if leaf.data is None:
                        continue
                    _features = RowTable.extract_feature(item.data["elements"], leaf.data)
                    model.setdefault(col, Counter()).update(_features)

        self.model = model

    @staticmethod
    def syl_exist(syl, syls):
        for scope in syls:
            if any(elt_idx in range(*scope) for elt_idx in range(*syl["range"])):
                return True
        return False

    def predict(self, elements, **kwargs):
        """
        提取章节标题&表头
        """
        answers = []
        title_model = self.model.get("公司治理与独立性-关联方及关联关系", Counter())
        # 确定目标章节
        aim_syls = []
        for title, _ in title_model.most_common():
            syls = self.pdfinsight.find_sylls_by_clear_title(title, order_by="level", reverse=True)
            if syls and syls[0] not in aim_syls:
                aim_syls.append(syls[0])
        if not aim_syls:
            return answers
        syls = {}
        # 自底向上筛选合适的章节
        for syl in sorted(aim_syls, key=lambda x: x["level"], reverse=True):
            if not self.syl_exist(syl, syls):
                syls[tuple(syl["range"])] = syl
        tables = {}
        for syl in syls.values():
            for elt_idx in range(*syl["range"]):
                elt_typ, elt = self.pdfinsight.find_element_by_index(elt_idx)
                if elt_typ != "TABLE":
                    continue
                group = next(iter(RowTable.parse_table(elt)), None)
                if not group:
                    continue
                sylls = self.pdfinsight.find_syllabuses_by_index(elt_idx)
                if not sylls:
                    continue
                _, nearest_title = self.pdfinsight.find_element_by_index(sylls[-1]["element"])
                if not nearest_title:
                    continue
                # 跳过重复的跨页表格
                key = []
                cells_by_row, _ = group_cells(elt["cells"])
                for row, cells in cells_by_row.items():
                    for col, cell in cells.items():
                        key.append((row, col, cell.get("text")))
                key = tuple(key)
                tables.setdefault(key, [elt, group, nearest_title])
        if not tables:
            return answers
        necessary_attr = ["关联方名称", "关联关系"]
        for idx in sorted(tables, key=lambda x: tables[x][0]["index"]):
            elt, group, nearest_title = tables[idx]
            answer = {}
            necessary_headers = {}
            for col in necessary_attr:
                _model = self.model.get(col)
                if not _model:
                    continue
                for header_txt, _ in _model.most_common():
                    if header_txt in ["D_date", "序号"]:  # todo：为什么会有这种标注
                        continue
                    header_cells, _ = RowTable.find_tuple_by_header_text(group, header_txt)
                    headers = (
                        tuple((cell["index"] for cell in header_cells if not cell.get("dummy"))) if header_cells else []
                    )
                    if headers and headers not in necessary_headers:  # 名称和关系不应该在同一列
                        necessary_headers.setdefault(headers, col)
                        break
            if not all(attr in necessary_headers.values() for attr in necessary_attr):
                continue
            answer["（表格）"] = ResultOfPredictor([TblResult([], elt)])
            for headers, col in necessary_headers.items():
                answer[col] = ResultOfPredictor([TblResult(headers, elt)])
            aim_cells = None
            for header_cells, _ in group:
                if any(re.search(r"^(关联)?类型$", clean_txt(_cell["text"])) for _cell in header_cells):
                    aim_cells = header_cells
                    break
            if aim_cells:  # 关联类型位于表头
                answer["关联类型"] = ResultOfPredictor(
                    [TblResult([_cell["index"] for _cell in aim_cells if not _cell.get("dummy")], elt)]
                )
            else:  # 关联类型位于标题
                answer["关联类型"] = ResultOfPredictor(
                    [
                        CharResult(
                            chars=nearest_title.get("chars", []),
                            text=clear_syl_title(nearest_title.get("text")),
                            elt=nearest_title,
                        )
                    ]
                )
            answers.append(answer)
        return answers
