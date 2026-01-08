from copy import deepcopy

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.cmbchina_predictor.models import SplitTableRow
from remarkable.predictor.schema_answer import PredictorResult


class SubscriptionRate(SplitTableRow):
    """
    以提取最多的列为准，进行分组
    """

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        answer_results = super().predict_schema_answer(elements)
        if not answer_results:
            return answer_results
        fix_answer_results = []
        for answer_result in answer_results:
            max_answer_size = 0
            for column in self.columns:
                answer_size = len(answer_result.get(column) or [])
                if answer_size > max_answer_size:
                    max_answer_size = answer_size
            if max_answer_size < 2:
                fix_answer_results.append(answer_result)
                continue
            for index in range(max_answer_size):
                fix_answer_result = deepcopy(answer_result)
                for column in self.columns:
                    answer_size = len(answer_result.get(column) or [])
                    if not answer_size:
                        continue
                    if index < answer_size:
                        fix_answer_result[column] = [fix_answer_result[column][index]]
                    elif index >= answer_size:
                        fix_answer_result[column] = [fix_answer_result[column][-1]]
                fix_answer_results.append(fix_answer_result)

        return fix_answer_results

    def get_answer_from_above_row(self, column, table, row, regs):
        answer_result = {}
        pattern = PatternCollection(regs)

        above_rows = [x for x in table.rows if x[0].rowidx < row[0].rowidx]
        for item in above_rows[::-1]:
            for cell in item:
                if cell.dummy:
                    continue
                if matcher := pattern.nexts(clean_txt(cell.text)):
                    if dst_chars := self.get_dst_chars_from_matcher(matcher, cell.raw_cell):
                        answer_result.setdefault(column, []).append(
                            self.create_result(
                                self.create_content_result(table.element, dst_chars, [cell], None), column=column
                            )
                        )
        return answer_result
