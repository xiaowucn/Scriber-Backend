from typing import Pattern

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import ParsedTable, parse_table
from remarkable.predictor.models.base_model import TableModel
from remarkable.predictor.schema_answer import PredictorResult, TableCellsResult

MIDDLE_COL_PATTERN = [r"指"]
FIRST_COL_PATTERN = [r"序号"]

ABBREVIATION = "简称"
FULL_NAME = "全称/释义"

VALID_TABLE_TITLE = [r"术语|释义|(一般|行业|专业|常用|普通|其他)(简称|语言|词语|词汇)|各方主体|缩略语"]
INVALID_TABLE_TITLE = [r"相关销售模式名称表述"]

INVALID_ABBREVIATION_PATTERN = [r"^(简称|名称)$"]
INVALID_FULL_NAME_PATTERN = [r"^(全称|释义)$"]


class Interpretation(TableModel):
    filter_elements_by_target = True

    def __init__(self, options, schema, predictor):
        super(Interpretation, self).__init__(options, schema, predictor)

    def train(self, dataset, **kwargs):
        pass

    def extract_feature(self, elements, answer):
        pass

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        rets = []
        elements.sort(key=lambda x: x["index"])
        for element in elements:
            table = parse_table(element, tabletype=TableType.KV.value, pdfinsight_reader=self.pdfinsight)
            valid_table = self.is_valid_table(element, table)
            if not valid_table:
                continue
            abbreviation_index = 0
            full_name_index = -1
            if len(table.cols) == 4 and self.is_special_middle_col(FIRST_COL_PATTERN, table, 1):
                # table has four cols and first_col like '序号'，then extract second_col for abbreviation,
                abbreviation_index = 1

            for row in table.rows:
                answer_result = {}
                is_valid = self.is_valid_row(row, abbreviation_index, full_name_index)
                if not is_valid:
                    continue
                answer_result[ABBREVIATION] = [
                    self.create_result([TableCellsResult(element, [row[abbreviation_index]])], column=ABBREVIATION)
                ]
                answer_result[FULL_NAME] = [
                    self.create_result([TableCellsResult(element, [row[full_name_index]])], column=FULL_NAME)
                ]
                rets.append(answer_result)
        return rets

    def is_valid_table(self, element, table):
        syllabus_index = element.get("syllabus")
        possible_table_title = {element.get("title")}
        if not (syllabus_index == -1 or syllabus_index is None):
            syllabus = self.pdfinsight_syllabus.syllabus_dict[syllabus_index]
            possible_table_title.add(clean_txt(syllabus["title"]))
        if table.title:
            possible_table_title.add(table.title.text)
        if PatternCollection(INVALID_TABLE_TITLE).nexts(clean_txt(element.get("title", ""))):
            return False
        if not PatternCollection(VALID_TABLE_TITLE).nexts(clean_txt("|".join(possible_table_title))):
            return False
        return True

    @staticmethod
    def is_valid_row(row, abbreviation_index, full_name_index):
        row_texts = {clean_txt(cell.text) for cell in row}
        if len(row_texts) == 1:
            return False
        if any(cell.dummy for cell in row):
            return False
        if PatternCollection(INVALID_ABBREVIATION_PATTERN).nexts(clean_txt(row[abbreviation_index].text)):
            return False
        if PatternCollection(INVALID_FULL_NAME_PATTERN).nexts(clean_txt(row[full_name_index].text)):
            return False
        return True

    @staticmethod
    def is_special_middle_col(special_pattern: list[str | Pattern], table: ParsedTable, col_index: int) -> bool:
        for cell in table.cols[col_index]:
            if PatternCollection(special_pattern).nexts(clean_txt(cell.text)):
                return True
        return False
