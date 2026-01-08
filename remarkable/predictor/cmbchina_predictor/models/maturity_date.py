from datetime import datetime, timedelta

from remarkable.common.pattern import PatternCollection
from remarkable.plugins.predict.models.sse.other_related_agencies import clean_text
from remarkable.predictor.dataset import DatasetItem
from remarkable.predictor.models.partial_text import PartialText


class MaturityDate(PartialText):
    """
    到期日
    """

    def train(self, dataset: list[DatasetItem], **kwargs):
        pass

    def predict_schema_answer(self, elements):
        answer_results = super(MaturityDate, self).predict_schema_answer(elements)
        if not answer_results:
            return answer_results
        for answer_result in answer_results:
            predictor_result = list(answer_result.values())[0][0]
            predictor_result.text = self.fix_date(clean_text(predictor_result.text))

        return answer_results

    @staticmethod
    def fix_date(date_string: str) -> str | None:
        if not date_string:
            return date_string

        date_patterns = PatternCollection(
            [
                r"(\d{4})[^\d](\d{1,2})[^\d](\d{1,2})",
                r"(\d{4})年(\d{1,2})月(\d{1,2})[日号]",
            ]
        )
        match = date_patterns.nexts(date_string)

        if match:
            try:
                year, month, day = match.groups()
                date_obj = datetime(int(year), int(month), int(day))
                adjusted_date = date_obj - timedelta(days=1)
                return adjusted_date.strftime("%Y年%m月%d日")
            except ValueError:
                return date_string

        return date_string
