import re

from remarkable.common.util import clean_txt
from remarkable.pdfinsight.reader import PdfinsightTable
from remarkable.plugins.predict.models.table_row import RowTable
from remarkable.predictor.predict import ResultOfPredictor, TblResult


class RowTableFilter(RowTable):
    model_intro = {"doc": "发行人基本情况-员工情况", "name": "", "hide": True}

    def is_certain_row(self, element, group):
        group_by = self.config.get("group_by", {})
        if not group_by:
            return True
        table = PdfinsightTable(element)
        if not any(table.is_merged_cell(value_cell) for _, value_cell in group):
            return True
        for _, value_cell in group:
            if not table.is_merged_cell(value_cell):
                continue
            for regs in group_by.values():
                if any(re.search(reg, clean_txt(value_cell.get("text", ""))) for reg in regs):
                    return True
        return False

    def predict(self, elements, **kwargs):
        answers = []
        for element in elements:
            if element["class"] != "TABLE":
                continue
            groups = self.parse_table(element)
            for group in groups:
                if not self.is_certain_row(element, group):
                    continue
                answer = {}
                for col in self.columns:
                    certain_regs = self.config.get("group_by", {}).get(col, [])
                    if col in ("币种",) or (col.startswith("<") and "单位" in col):
                        _answer = self.find_special_attr(col, element)
                        if _answer:
                            answer[col] = _answer
                        continue
                    _model = self.model.get(col)
                    if not _model:
                        continue
                    for _key, _ in _model.most_common():
                        _, _cell = self.find_tuple_by_header_text(group, _key)
                        if (
                            _cell
                            and _cell.get("text")
                            and clean_txt(_cell["text"]) != _key
                            and not PdfinsightTable(element).is_merged_cell(_cell)
                            and not any(re.search(reg, clean_txt(_cell["text"])) for reg in certain_regs)
                        ):
                            answer[col] = ResultOfPredictor([TblResult([_cell["index"]], element)])
                            break
                if answer and all(attr in answer for attr in self.config.get("necessary", [])):
                    answers.append(answer)
        return answers
