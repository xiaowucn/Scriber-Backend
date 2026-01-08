from collections import defaultdict

import attr

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import CellCharResult


class FundAccount(BaseModel):
    """
    先根据row_tag_pattern定位到row
    再获取cell_text_patterns获取具体答案
    """

    def train(self, dataset, **kwargs):
        pass

    def predict_schema_answer(self, elements):
        answer_results = []
        cell_text_patterns = self.config.get("cell_text_patterns", {})
        row_tag_pattern = PatternCollection(self.config.get("row_tag_pattern", []))
        for element in elements:
            if element["class"] != "TABLE":
                continue
            table = parse_table(element, tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight)
            last_table_element = self.pdfinsight.find_elements_near_by(
                element["index"], step=-1, steprange=5, aim_types="TABLE"
            )
            last_table = (
                parse_table(last_table_element[0], tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight)
                if last_table_element
                else None
            )
            for row_idx, row in enumerate(table.rows):
                answers = defaultdict(list)
                valid_row = self.is_valid_row(row_tag_pattern, table.rows, row_idx, last_table)
                if not valid_row:
                    continue
                cell = row[-1]
                for column in self.columns:
                    pattern = cell_text_patterns.get(column)
                    matcher_results = self.get_dst_chars_from_pattern(pattern, cell=cell)
                    for dst_chars in matcher_results:
                        answer = self.create_result([CellCharResult(element, dst_chars, [cell])], column=column)
                        answers[column].append(answer)
                        if answers and not self.multi:
                            break
                if answers:
                    answer_results.append(answers)
            if answer_results and not self.multi_elements:
                break

        if self.get_config("reassemble_with_supervision"):  # 对从同一个element里提出来的多组答案进行分组
            return self.reassemble_answer_for_supervisory_agencies(answer_results)
        if answer_results and len(answer_results) == 1 and self.predictor.primary_key:
            return self.reassemble_answer(answer_results)
        return answer_results

    def reassemble_answer(self, answer_results):
        primary_key = self.predictor.primary_key[0]
        primary_key_answer = answer_results[0].get(primary_key)
        if not primary_key_answer:
            return answer_results
        ret = [{primary_key: [item]} for item in primary_key_answer]

        for answer_result in answer_results:
            for key, values in answer_result.items():
                if key != primary_key:
                    for answer, item in zip(ret, values):
                        answer[key] = [item]
        return ret

    def reassemble_answer_for_supervisory_agencies(self, answer_results):
        ret = []
        for answer_result in answer_results:
            for primary_key in self.predictor.primary_key:
                if primary_key_answer := answer_result.get(primary_key):
                    break
            else:
                continue

            if len(primary_key_answer) == 1:
                ret.append(answer_result)
                continue
            primary_answers = []
            for answer in primary_key_answer:
                primary_first_cell = answer.element_results[0].chars[0]
                primary_answer_position = (
                    primary_first_cell["page"],
                    primary_first_cell["box"][1],
                )  # 答案第一个字符的page和该字符框的上边界
                primary_answers.append(PrimaryAnswer(answer, position=primary_answer_position))
            primary_answers.sort(key=lambda x: x.position)
            for key, values in answer_result.items():
                if key == primary_key:
                    continue
                for value in values:
                    first_cell = value.element_results[0].chars[0]
                    answer_position = (first_cell["page"], first_cell["box"][1])
                    distances = []
                    for idx, primary_answer in enumerate(primary_answers):
                        page, top = primary_answer.position
                        if page == answer_position[0]:
                            distance = (0, answer_position[1] - top)  # 0 表示在同一页 仅用于排序
                        else:
                            distance = (1, answer_position[1])  # 1 表示在不同页 仅用于排序
                        distances.append((idx, distance))

                    distances.sort(key=lambda x: x[1])
                    for idx, distance in distances:
                        if distance[1] > 0:
                            special_primary_answer = primary_answers[idx]
                            special_primary_answer.answer[key] = [value]
                            break

            for primary_answer in primary_answers:
                primary_answer.answer[primary_key] = [primary_answer.main_answer]
                ret.append(primary_answer.answer)
        return ret

    @staticmethod
    def is_valid_row(pattern, rows, row_idx, last_table):
        first_cell = rows[row_idx][0]
        if first_cell.text == "" and row_idx == 0 and last_table:
            last_row_first_cell = last_table.rows[-1][0]
            if last_row_first_cell and pattern.nexts(clean_txt(last_row_first_cell.text)):
                return True
        return pattern.nexts(clean_txt(first_cell.text))

    def get_dst_chars_from_pattern(self, pattern, cell):
        ret = []
        matchers = PatternCollection(pattern).finditer(clean_txt(cell.text))
        for matcher in matchers:
            if not matcher:
                continue
            dst_chars = self.get_dst_chars_from_matcher(matcher, cell.raw_cell)
            if dst_chars:
                ret.append(dst_chars)
        return ret


@attr.s
class PrimaryAnswer:
    main_answer = attr.ib()
    position: tuple = attr.ib()
    answer: dict = attr.ib(default=attr.Factory(dict))
