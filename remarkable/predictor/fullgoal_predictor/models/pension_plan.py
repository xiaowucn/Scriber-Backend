from collections import Counter
from copy import copy

from remarkable.common.pattern import PatternCollection
from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.predictor.models.middle_paras import MiddleParas
from remarkable.predictor.models.para_match import ParaMatch
from remarkable.predictor.models.syllabus_elt_v2 import SyllabusEltV2
from remarkable.predictor.schema_answer import PredictorResult


class PensionPlan(SyllabusEltV2):
    type_patterns = {
        "现金类资产": [
            r"__regex__(现金类|货币类|流动性)资产",
        ],
        "固定收益类资产": [
            r"__regex__固定收益类?资产",
        ],
    }
    sub_model_config = {
        "资产类型": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"(?P<content>(现金类|货币类|流动性)资产)",
                    r"(?P<content>(稳定类|波动类)?固定收益类?资产)",
                ],
            },
        ],
        "资产比例": [
            {
                "name": "middle_paras",
                "use_direct_elements": True,
                "include_top_anchor": False,
                "top_anchor_regs": [
                    r"配置比例要求",
                ],
                "bottom_anchor_regs": [
                    r"投资申请要求",
                ],
            },
            {
                "name": "para_match",
                "multi_elements": True,
                "paragraph_pattern": [r"投资比例.*[\d.]+[%％]", r"配置.*净值的?[\d.]+[%％]"],
            },
        ],
        "集中度": [
            {
                "name": "para_match",
                "paragraph_pattern": [r"集中度|单一股票|单一证券|同一发行人"],
            }
        ],
        "期限": [
            {
                "name": "para_match",
                "paragraph_pattern": [r"组合久期|久期策略"],
            }
        ],
    }

    def get_col_models(self, col):
        col_models = []
        predictor = copy(self.predictor)
        predictor.columns = [col]
        for model_config in self.sub_model_config[col]:
            if model_config["name"] == "para_match":
                col_models.append(ParaMatch(model_config, self.schema, predictor=predictor))
            elif model_config["name"] == "middle_paras":
                col_models.append(MiddleParas(model_config, self.schema, predictor=predictor))
        return col_models

    mold_data = {}
    for key, items in type_patterns.items():
        mold_data[key] = Counter(items)

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        answer_results = []
        for _, type_pattern in self.mold_data.items():
            aim_syllabuses = self.get_aim_syllabus(
                type_pattern,
                min_level=self.min_level,
                max_level=self.syllabus_level,
                syllabus_black_list=PatternCollection(self.get_config("syllabus_black_list")),
            )
            if not aim_syllabuses:
                continue

            for aim_syl in aim_syllabuses:
                page_box = PdfinsightSyllabus.syl_outline(
                    aim_syl,
                    self.pdfinsight,
                    include_title=self.include_title,
                    ignore_pattern=self.ignore_pattern,
                    only_before_first_chapter=self.only_before_first_chapter,
                    include_sub_title=self.include_sub_title,
                    break_para_pattern=self.break_para_pattern,
                    skip_table=self.skip_table,
                    page_header_patterns=self.page_header_patterns,
                )
                elements = self.get_elements_from_page_box(page_box)
                elements_result = {}
                for col in self.sub_model_config:
                    for col_model in self.get_col_models(col):
                        ret = col_model.predict_schema_answer(elements)
                        if not ret:
                            continue
                        if first_ret := ret[0]:
                            if isinstance(first_ret, dict):
                                elements_result.update(first_ret)
                            elif isinstance(first_ret, PredictorResult):
                                elements_result.update({col: [first_ret]})
                            break

                if elements_result:
                    answer_results.append(elements_result)

        return answer_results
