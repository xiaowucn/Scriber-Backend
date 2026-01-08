# -*- coding: utf-8 -*-
"""ColHeader-RowHeader-Value 形式的表格
表格解析方法：取所有 body 中的值，取行头、列头作为 header
模型：统计目标字段 header 对应的 key
预测：首先根据特征匹配单元格，再将单元格的 headers 根据配置的维度字段 pattern 进行对应（）,例如
    {
        'name': 'table_tuple',
        'dimensions': [
            {
                "column": "年度",
                "pattern": "(?:18|19|20|21)\\d{2}",
            },
            {
                "column": "项目",
                "pattern": r"资产|负债",
                "required": True,
            }
        ]
    }

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

输入：
|      | 2019 | 2018 |
| ---- | ---- | ---- |
| 资产 |  111  | 222 |
| 负债 |  333  | 444 |

输出：
[
    {
        "年份": 2019,
        "项目": "资产",
        "数值": 111,
    },
    {
        "年份": 2018,
        "项目": "资产",
        "数值": 222,
    },
    ...
]
"""

import logging
import re
from collections import Counter, defaultdict

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt, index_in_space_string
from remarkable.pdfinsight.parser import (
    ParsedTable,
    ParsedTableCell,
    cell_data_patterns,
    parse_table,
)
from remarkable.predictor.eltype import ElementType
from remarkable.predictor.models.base_model import TableModel
from remarkable.predictor.schema_answer import CharResult, PredictorResult, TableResult

logger = logging.getLogger(__name__)

YEAR_PATTERN = re.compile(r"(largest_year_minus_\d|[本当上][年期]数?)[^|]*")
feature_patterns = [r"largest_year_minus_\d", r"[本当上][年期]数?"]
split_pattern = re.compile(r"\|")


class TupleTable(TableModel):
    """
    选项：
    - distinguish_year：是否区分年份（last_year_minux_0/1/2...）
    """

    target_element = ElementType.TABLE_TUPLE
    filter_elements_by_target = True

    def __init__(self, options, schema, predictor=None):
        super().__init__(options, schema, predictor=predictor)
        if self.config.get("strict_element_type", False):
            self.filter_elements_by_target = True
        self.dimensions = self.get_config("dimensions", [])  # 附加维度字段

    @property
    def distinguish_year(self):
        return self.get_config("distinguish_year", True)

    @property
    def multi(self):
        return self.get_config("multi", True)

    @property
    def feature_from(self):
        return self.get_config("feature_from", "headers")

    @property
    def width_from_all_rows(self):
        return self.get_config("width_from_all_rows", False)  # 默认取表格第一行宽度, 为True时取最宽的行

    def get_model_data(self, column=None):
        model_data = super().get_model_data(column=column) or Counter()

        # ignore year
        if not self.distinguish_year:
            fixed_model_data = Counter()
            for key, cnt in model_data.items():
                fixed_model_data.update({self.fix_feature(key, distinguish_year=False): cnt})
            model_data = fixed_model_data

        # blacklist
        blacklist = self.get_config("feature_black_list", default=[], column=column)
        blacklist_features = [k for k in model_data if any(self.is_match(b, k) for b in blacklist)]
        for bfeature in blacklist_features:
            model_data.pop(bfeature)

        # whitelist
        model_data.update(self.get_config("feature_white_list", default=[], column=column))

        return model_data

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        elements = self.revise_elements(elements)

        answer_results = []
        for element in elements:
            if element["class"] != "TABLE":
                # AutoModel中 filter_elements_by_target设置为None 所有这里需要再次过滤下
                continue
            element_results = []
            table = parse_table(
                element,
                tabletype=TableType.TUPLE.value,
                pdfinsight_reader=self.pdfinsight,
                width_from_all_rows=self.width_from_all_rows,
            )
            for col in self.columns:
                column_results = []
                model_data = self.get_model_data(column=col)
                if not model_data:
                    continue
                # 用特征匹配单元格
                neglect_header = PatternCollection(self.get_config("neglect_header", default=[], column=col))
                for cell in self.find_cells_by_header_feature(
                    table, model_data, distinguish_year=self.distinguish_year, neglect_header=neglect_header
                ):
                    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4336
                    if cell.merge_to and column_results:
                        bFind = False
                        for result in column_results:
                            for item in result.get(col):
                                if (
                                    isinstance(item, PredictorResult)
                                    and item.meta["cell"][0] == cell.merge_to[0]
                                    and item.meta["cell"][1] == cell.merge_to[1]
                                ):
                                    bFind = True
                                    break
                        if bFind:
                            continue
                    # row_headers, col_headers, val_cell
                    if not cell.text:
                        continue
                    answer_result = {
                        col: [
                            self.create_result(
                                [TableResult(element, [cell])],
                                column=col,
                                meta={"cell": [int(i) for i in cell.raw_cell["index"].split("_")]},
                            )
                        ]
                    }
                    missing_dimension = False
                    for dimension in self.dimensions:
                        # 用 dimensions 配置 匹配维度字段
                        if not dimension.get("column"):
                            logger.warning(f"TupleTable: dimension column was missing for schema {self.name}")
                            continue
                        dimension_cells = self.find_dimension_from_header(cell.headers, dimension)
                        dimension_answer = self.find_dimension_from_title(dimension["column"], table, dimension)
                        if dimension_cells:
                            answer_result[dimension["column"]] = [
                                self.create_result(
                                    [TableResult(element, dimension_cells)],
                                    column=dimension["column"],
                                    meta={"cell": [int(i) for i in dimension_cells[0].raw_cell["index"].split("_")]},
                                )
                            ]
                        elif dimension_answer:
                            answer_result[dimension["column"]] = [dimension_answer]
                        elif dimension.get("required", True):
                            missing_dimension = True
                            break
                    if missing_dimension:
                        continue
                    column_results.append(answer_result)
                element_results.extend(column_results)
            answer_results.extend(element_results)
            if answer_results and not self.multi_elements:
                break
        return answer_results

    def extract_feature(self, elements, answer):
        features = Counter()
        for answer_data in answer["data"]:
            if not answer_data["boxes"]:
                continue
            answer_tables = {}
            for idx in answer_data["elements"]:
                try:
                    element = elements[idx]
                except KeyError as e:
                    logger.exception(e)
                    continue
                if self.is_target_element(element):
                    answer_tables[idx] = parse_table(
                        elements[idx], tabletype=TableType.TUPLE.value, width_from_all_rows=self.width_from_all_rows
                    )
            for box in answer_data["boxes"]:
                for table in answer_tables.values():
                    for aim_cell in table.find_cells_by_outline(box["page"], box["box"]) or []:
                        feature_key = self.get_feature_for_cell(aim_cell, distinguish_year=self.distinguish_year)
                        # 过滤空 feature
                        if feature_key == "":
                            continue
                        features.update([feature_key])
        return features

    def get_headers(self, cell: ParsedTableCell):
        if self.feature_from == "row_headers":
            return cell.row_header_cells
        return cell.headers

    def get_feature_for_cell(self, cell, distinguish_year):
        valid_headers = self.get_headers(cell)
        cell_feature = self.feature_from_cells(valid_headers, distinguish_year)
        return cell_feature

    def feature_from_cells(self, cell_headers: list[ParsedTableCell], distinguish_year: bool) -> str:
        valid_headers = [c for c in cell_headers if not cell_data_patterns.nexts(c.normalized_text) and c.text]
        if len(valid_headers) < 2:
            # table_tuple 至少需要两个特征， 若只有一个特征则适用于 table_row/table_col
            return ""
        cell_feature = self.feature_key_str([c.normalized_text for c in valid_headers])
        cell_feature = self.fix_feature(cell_feature, distinguish_year=distinguish_year)
        return cell_feature

    def find_cells_by_header_feature(
        self, table: ParsedTable, features: Counter, distinguish_year: bool, neglect_header: PatternCollection
    ) -> list[ParsedTableCell]:
        selected_cells = []
        cells_map = defaultdict(list)
        for cell in table.body:
            if any(neglect_header.nexts(clean_txt(x.text)) for x in self.get_headers(cell)):
                continue
            cell_feature = self.get_feature_for_cell(cell, distinguish_year)
            cells_map[cell_feature].append(cell)

        for feature, _ in features.most_common():
            for cell_feature, cells in cells_map.items():
                if self.is_match(feature, cell_feature):
                    selected_cells.extend(cells)
        selected_cells.sort(key=lambda x: (x.rowidx, x.colidx))
        return selected_cells

    @classmethod
    def fix_feature(cls, feature, distinguish_year=True):
        matcher = list(PatternCollection(feature_patterns).finditer(feature))
        normalized_time = {match.group() for match in matcher}
        if len(matcher) == len(normalized_time):
            # return feature
            pass
        elif len(normalized_time) == 1:
            segmented_text = split_pattern.split(feature)
            non_time_feature = list(normalized_time)[:1]
            for item in segmented_text:
                if not PatternCollection(feature_patterns).nexts(item):
                    non_time_feature.append(item)
            feature = "|".join(non_time_feature)
        if matcher and not distinguish_year:
            # 不区分年份，统一替换为 DATE
            feature = YEAR_PATTERN.sub("DATE", feature)
        return feature

    @classmethod
    def find_dimension_from_header(cls, cells: list[ParsedTableCell], dimension: dict) -> list[ParsedTableCell]:
        selected_cells = []
        for cell in cells:
            if PatternCollection(dimension["pattern"]).nexts(clean_txt(cell.text)):
                selected_cells.append(cell)
        selected_cells.sort(key=lambda x: (x.rowidx, x.colidx))
        return selected_cells

    def find_dimension_from_title(self, column: str, table: ParsedTable, dimension: dict) -> PredictorResult | None:
        # todo move to parent class
        answer_result = None
        if not table.elements_above:
            return None
        for ele in table.elements_above:
            if ele.get("class") not in ["PARAGRAPH"]:
                continue
            ele_text = ele.get("text")
            if not ele_text:
                continue
            match = PatternCollection(dimension["pattern"]).nexts(clean_txt(ele_text))
            if match:
                value = match.groupdict().get("dst", None)
                if not value:
                    continue
                start = clean_txt(ele_text).index(clean_txt(value))
                end = start + len(clean_txt(value))
                sp_start, sp_end = index_in_space_string(ele_text, (start, end))
                dst_chars = ele.get("chars")[sp_start:sp_end]
                answer_result = self.create_result([CharResult(ele, dst_chars)], column=column)
                break
        return answer_result
