# -*- coding: utf-8 -*-
"""根据表格标题提取整个表格"""

import logging
import re
import sre_constants
from collections import Counter

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.models.base_model import TableModel
from remarkable.predictor.schema_answer import TableResult

logger = logging.getLogger(__name__)


syllabus_start_pattern = PatternCollection(
    [
        r"^\(i+\)",
        r"^\((\d\.)+\)",
    ],
    re.I,
)


class TableTitle(TableModel):
    def extract_feature(self, elements, answer):
        features = Counter()
        for answer_data in answer["data"]:
            if not answer_data["boxes"]:
                continue
            answer_tables = {
                idx: parse_table(elements[idx], tabletype=TableType.TUPLE.value)
                for idx in answer_data["elements"]
                if self.is_target_element(elements[idx])
            }
            for table in answer_tables.values():
                table_title = table.title.text if table.title else table.element["title"]
                if table_title == "":
                    continue
                try:
                    re.compile(table_title)
                except sre_constants.error:
                    logger.error(f"invalid feature:{table_title}")
                    return None
                if not self.is_valid_feature(table_title):
                    return None
                features.update([table_title])
        return features

    @staticmethod
    def is_valid_feature(feature, count=2):
        # count 的默认值为训练时使用
        if count == 1:
            return False
        if len(feature.split()) == 1:
            return False
        return True

    def get_model_data(self, column=None):
        if self.get_config("only_inject_features"):
            model_data = Counter()
        else:
            model_data = super().get_model_data(column=column) or Counter()

            # blacklist
            blacklist = self.get_config("feature_black_list", default=[], column=column)
            blacklist_features = [k for k in model_data if any(self.is_match(b, k) for b in blacklist)]
            for bfeature in blacklist_features:
                model_data.pop(bfeature)

        # whitelist
        model_data = {key: value for key, value in model_data.items() if self.is_valid_feature(key, value)}
        model_data = Counter(model_data)
        most_counter = model_data.most_common()[0][1] if model_data else 0
        for feature in self.get_config("feature_white_list", default=[], column=column):
            model_data.update({feature: most_counter + 1})

        return model_data

    def predict_schema_answer(self, elements):
        answer_results = []
        model_data = self.get_model_data()

        for element in elements:
            table = parse_table(element, tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight)
            table_titles = self.filter_title(table.possible_titles)
            if self.get_config("first_row_as_title"):
                table_titles.append(" ".join([cell.text for cell in table.rows[0]]))

            if not self.is_match_feature(table_titles, model_data):
                continue
            answer_result = self.create_result([TableResult(element, [])], column=self.schema.name)
            if answer_result:
                answer_results.append(answer_result)
            if not self.multi_elements and answer_results:
                break
        answer_results.sort(key=lambda x: x.relative_elements[0]["index"])
        return answer_results

    @staticmethod
    def is_match_feature(table_titles, model_data):
        for feature, _ in model_data.most_common():
            try:
                if any(re.compile(feature, re.I).search(table_title) for table_title in table_titles):
                    return True
            except re.error:
                continue
        return False

    def filter_title(self, table_titles):
        ret = []
        for title in table_titles:
            if len(title.split()) > 20:
                # 单词数量过多的一般是误识别的title
                continue
            if syllabus_start_pattern.nexts(title):
                # (ii) 等开头的认为是一个章节标题 不是表格标题
                continue
            ret.append(title)
        return ret
