"""
将各column按在文中出现的顺序分组
"""

import logging
from collections import defaultdict

from remarkable.predictor.models.syllabus_based import SyllabusBased
from remarkable.predictor.mold_schema import SchemaItem


class GroupByPosition(SyllabusBased):
    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super(GroupByPosition, self).__init__(options, schema, predictor=predictor)
        self.group_by_position_on = self.get_config("group_by_position_on")

    def predict_schema_answer(self, elements):
        schema_name = self.schema.parent if self.schema.parent else self.schema
        answer_results = super(GroupByPosition, self).predict_schema_answer(elements)
        return self.group_by_position(answer_results, self.columns, self.group_by_position_on, schema_name)

    @classmethod
    def group_by_position(cls, temp_answer_results, columns, group_by_position_on, schema_name):
        answer_results = []
        if not temp_answer_results:
            return answer_results

        answer_result_collections = defaultdict(list)
        for temp_answer_result in temp_answer_results:
            if group_by_position_on not in temp_answer_result:
                logging.warning(f"Bad result without {group_by_position_on} for {schema_name}")
                continue
            for column, predictor_results in temp_answer_result.items():
                answer_result_collections[column].extend(predictor_results)

        for column in answer_result_collections:
            answer_result_collections[column] = cls.sorted_by_position(answer_result_collections[column])
        answer_num = len(answer_result_collections.get(group_by_position_on, []))
        for index in range(answer_num):
            answer_result = {}
            for column in columns:
                column_temp_answer_result = answer_result_collections[column]
                if index < len(column_temp_answer_result):
                    answer_result[column] = [column_temp_answer_result[index]]
            answer_results.append(answer_result)

        return answer_results

    @staticmethod
    def sorted_by_position(predictor_results):
        def position(predictor_result):
            """
            左上角的排前面
            :param predictor_result:
            :return:
            """
            chars = predictor_result.element_results[0].chars
            if not chars:
                return 1
            first_char = chars[0]
            box = first_char["origin_box"]
            return box[0] + 1000 * box[1]

        return sorted(predictor_results, key=position)
