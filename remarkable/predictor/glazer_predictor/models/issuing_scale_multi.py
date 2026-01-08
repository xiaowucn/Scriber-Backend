"""
多品种情况
"""

import re

from remarkable.predictor.glazer_predictor.models import GroupByPosition
from remarkable.predictor.models.partial_text import PartialText
from remarkable.predictor.mold_schema import SchemaItem


class IssuingScaleMulti(PartialText):
    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super(IssuingScaleMulti, self).__init__(options, schema, predictor=predictor)
        self.group_by_position_on = self.get_config("group_by_position_on")

    def predict_schema_answer(self, elements):
        answer_results = []
        is_multi = False
        for element in elements:
            if re.compile(r"品种二").search(element.get("text", "")):
                is_multi = True
                break
        if not is_multi:
            return answer_results

        answer_results = super(IssuingScaleMulti, self).predict_schema_answer(elements)
        schema_name = self.schema.parent if self.schema.parent else self.schema
        return GroupByPosition.group_by_position(answer_results, self.columns, self.group_by_position_on, schema_name)
