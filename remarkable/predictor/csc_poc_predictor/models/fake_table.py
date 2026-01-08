from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.dataset import DatasetItem
from remarkable.predictor.models.base_model import TableModel
from remarkable.predictor.schema_answer import CellCharResult


class FakeTable(TableModel):
    def extract_feature(self, elements, answer):
        pass

    def train(self, dataset: list[DatasetItem], **kwargs):
        pass

    @property
    def pattern(self):
        return PatternCollection(self.get_config("pattern", []))

    def predict_schema_answer(self, elements):
        ret = []
        if not elements:
            elements = get_elements_from_first_page(self.pdfinsight)
        for element in elements:
            table = parse_table(element, tabletype=TableType.KV.value, pdfinsight_reader=self.pdfinsight)
            first_row = table.rows[0]
            for cell in first_row:
                matcher = self.pattern.nexts(clean_txt(cell.text))
                if matcher:
                    dst_chars = self.get_dst_chars_from_matcher(matcher, cell.raw_cell)
                    element_results = [CellCharResult(element, dst_chars, [cell])]
                    answer = self.create_result(element_results, column=self.schema.name)
                    ret.append(answer)
                    break
            if ret:
                break
        return ret


def get_elements_from_first_page(pdfinsight):
    for index, items in pdfinsight.element_dict.items():
        if index != 0:
            continue
        for item in items:
            if item.data["class"] == "TABLE":
                _, element = pdfinsight.find_element_by_index(item.index)
                if not element:
                    continue
                return [element]
    return []
