# -*- coding: utf-8 -*-
import re

from remarkable.pdfinsight.reader import PdfinsightTable
from remarkable.predictor.models.base_model import TableModel
from remarkable.predictor.schema_answer import CharResult

END_PATTERN = r"(?:RMB|HK\$?|HKD)?\s{,2}(?:\d+,?)+"
START_PATTERN = r"nil|(?:RMB|HK\$?|HKD)?\s{,2}(?:\d,?)+"

CONTENT_PATTERN = re.compile(rf"(?P<start>(?:{START_PATTERN}))\s+(?:to|-|－|–)\s+(?P<end>{END_PATTERN})", re.I)


class TableColumnContent(TableModel):
    filter_elements_by_target = True

    def predict_schema_answer(self, elements):
        answers = []
        elements = self.revise_elements(elements)

        for element in elements:
            table = PdfinsightTable(element)
            valid_rows = [row_data[0] for row_data in table.rows if all(c[0]["text"] for c in row_data[1])]
            cells = [{"key": f"{row}_0", "data": table.cell(row, 0)[0]} for row in valid_rows]
            matched_data = []
            for cell in cells:
                matched = CONTENT_PATTERN.search(cell["data"]["text"])
                if matched:
                    matched_data.append((matched, cell))
            answer_result = self.build_answer_result(matched_data, element)
            answers.append(answer_result)
        return answers

    def build_answer_result(self, matched_data, element):
        element_results = []
        for matched, cell in matched_data:
            start, end = matched.regs[-1]
            element_results.append(CharResult(element, cell["data"]["chars"][start:end]))
        return self.create_result(element_results)

    def train(self, dataset, **kwargs):
        pass

    def print_model(self):
        pass

    def extract_feature(self, elements, answer):
        pass
