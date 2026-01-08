# -*- coding: utf-8 -*-
import re

from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.models.table_tuple_select import TupleTableSelect
from remarkable.predictor.schema_answer import ParagraphResult, TableCellsResult

class_patterns = [
    re.compile(r'(long positions?|interests?) in(?P<class>.*?shares?.*?)(of[\w\s]+)?', re.I),
    re.compile(r'(?P<class>domestic shares)', re.I),
]

title_pattern = re.compile(r'share', re.I)


class B12Class(BaseModel):
    target_element = 'table'

    def train(self, dataset, **kwargs):
        pass

    def print_model(self):
        pass

    def predict_schema_answer(self, elements):
        answer_results = []
        depending_answer_results = self.predictor.get_depending_answers()
        for answer_result in depending_answer_results:
            element_results = answer_result.element_results
            for element_result in element_results:
                element = element_result.element
                if element['class'] != 'TABLE':
                    continue

                answer_result = self.predict_answer_with_table_title(element)
                if answer_result:
                    answer_results.append(answer_result)
                    continue

                if element_result.cells:
                    records = TupleTableSelect.parse_table(element)
                    cell_records = [r for r in records if r[2]['index'] in element_result.cells]
                    col_headers = [col_header for record in cell_records for col_header in record[1]]
                    header_index = set()
                    for i in col_headers:
                        if i['index'] not in header_index:
                            header_index.add(i['index'])

                    element_results = [TableCellsResult(element, list(header_index))]
                    answer_results.append(self.create_result(element_results, value=self.get_answer_value()))

        return answer_results

    def predict_answer_with_table_title(self, element):
        near_by_elements = self.pdfinsight.find_elements_near_by(element['index'], step=-1, amount=2)
        class_pattern_matched = None
        table_title_element = None
        for near_by_element in near_by_elements:
            if near_by_element['class'] != 'PARAGRAPH' or title_pattern.search(near_by_element['text']) is None:
                continue
            for pattern in class_patterns:
                class_pattern_matched = pattern.search(near_by_element['text'])
                if class_pattern_matched:
                    table_title_element = near_by_element
                    break
            if class_pattern_matched:
                break
        if near_by_elements and class_pattern_matched:
            start, end = class_pattern_matched.span('class')
            element_results = [ParagraphResult(element, table_title_element['chars'][start:end])]
            return self.create_result(element_results, self.get_answer_value())
        else:
            return None

    def get_answer_value(self):
        enum_values = self.predictor.get_enum_values(self.schema.type)
        return enum_values[0]
