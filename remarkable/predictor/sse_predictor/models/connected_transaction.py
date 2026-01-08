import re

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.models.table_row import TableRow
from remarkable.predictor.schema_answer import CharResult


class ConnectedTransaction(TableRow):
    def __init__(self, options, schema, predictor=None):
        super(ConnectedTransaction, self).__init__(options, schema, predictor=predictor)
        self.text_split_patterns = self._options.get("text_split_patterns", {})

    def predict_schema_answer(self, elements):
        elements = self.filter_elements_by_title(elements)
        return super(ConnectedTransaction, self).predict_schema_answer(elements)

    def create_answer_result(self, column, element, cell):
        if column not in self.text_split_patterns:
            return super(ConnectedTransaction, self).create_answer_result(column, element, cell)

        char_ranges = self.split_text(column, cell)
        element_results = []
        for char_range in char_ranges:
            chars = cell.raw_cell["chars"][char_range[0] : char_range[1]]
            element_results.append(CharResult(element, chars))

        return self.create_result(element_results, column=column)

    def split_text(self, column, cell):
        def _find_split_range(text, words):
            ret = []
            tail = 0
            for word in words:
                truncate_texts = text[tail:]
                start = truncate_texts.find(word)
                end = start + len(word)
                start += tail
                end += tail
                ret.append((start, end))
                tail = end + 1
            return ret

        text = cell.text
        words = [text]
        for pattern in self.text_split_patterns[column]:
            words = re.split(pattern, text)
            if len(words) > 1:
                break
        return _find_split_range(text, words)

    def filter_elements_by_title(self, elements):
        title_neglect_patterns = self.config.get("title_neglect_patterns", [])
        ret = []
        elements.sort(key=lambda x: x["index"])
        for ele in elements:
            table = parse_table(ele, tabletype=TableType.ROW.value, pdfinsight_reader=self.pdfinsight)
            element_title = ele.get("title", "") or ""
            if not element_title and table.title:
                element_title = table.title.text
            if not element_title:
                ret.append(ele)
                continue
            if not PatternCollection(title_neglect_patterns).nexts(element_title):
                ret.append(ele)
        return ret
