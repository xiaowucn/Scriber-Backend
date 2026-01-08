from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.models.table_kv import KeyValueTable
from remarkable.predictor.schema_answer import CellCharResult, PredictorResult

AMOUNT_PATTERN = PatternCollection([r"(不超过)?(?P<dst>[\d,\.]+)\s?万?[元股]"])
VALID_TABLE_TITLE = PatternCollection([r"本次发行概况"])

VALID_TABLE_TITLE2 = PatternCollection([r"本次发行的基本情况"])

SYLLABUS_PATTERN = PatternCollection(["三"])

valid_unit = PatternCollection([r"(?P<dst>万?股)"])


class DistributionProfile(KeyValueTable):
    def __init__(self, options, schema, predictor):
        super(DistributionProfile, self).__init__(options, schema, predictor)

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        rets = []
        for element in elements:
            if not self.is_valid_table(element):
                continue
            answer_results = super(DistributionProfile, self).predict_schema_answer([element])
            for answer_result in answer_results:
                for col, answer in answer_result.items():
                    element_result = answer[0].element_results[0]
                    parsed_cell = element_result.parsed_cells[0]
                    matcher = AMOUNT_PATTERN.nexts(clean_txt(parsed_cell.text))
                    if matcher:
                        dst_chars = self.get_dst_chars_from_matcher(matcher, parsed_cell.raw_cell)
                        answer_result[col] = [
                            self.create_result(
                                [CellCharResult(element, dst_chars, element_result.parsed_cells)], column=col
                            )
                        ]
                rets.append(answer_result)
        return rets

    def is_valid_table(self, element):
        current_syllabus_idx = element["syllabus"]
        if current_syllabus_idx < 1:
            return False
        current_syllabus = self.pdfinsight_syllabus.syllabus_dict[current_syllabus_idx]
        root_syllabus = self.pdfinsight_syllabus.get_root_syllabus(current_syllabus)
        if not SYLLABUS_PATTERN.nexts(clean_txt(root_syllabus["title"])):
            return False
        table = parse_table(element, tabletype=TableType.KV.value, pdfinsight_reader=self.pdfinsight)
        table_title = table.title.text if table.title else element.get("title")
        if not table_title:
            return False
        if VALID_TABLE_TITLE2.search(clean_txt(table_title)):
            for above_element in table.elements_above:
                if above_element["class"] != "PARAGRAPH":
                    continue
                if VALID_TABLE_TITLE.nexts(clean_txt(above_element["text"])):
                    return True
        if VALID_TABLE_TITLE.nexts(clean_txt(table_title)):
            return True
        return False
