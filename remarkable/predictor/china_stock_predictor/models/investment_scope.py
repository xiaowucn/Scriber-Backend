from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.models.table_kv import KeyValueTable


class InvestmentScope(KeyValueTable):
    def predict_schema_answer(self, elements):
        ret = []
        parent_answer_results = super(InvestmentScope, self).predict_schema_answer(elements)
        # return parent_answer_results
        if not parent_answer_results:
            return ret

        self.config.update(self.get_config("table_config", {}))
        row_tag_pattern = PatternCollection(self.config.get("row_tag_pattern", []))

        for parent_answer in parent_answer_results:
            for col, answer_item in parent_answer.items():
                split_pattern = self.get_config("split_pattern", column=col)
                garbage_frag_pattern = self.get_config("garbage_frag_pattern", column=col)
                keep_separator = self.get_config("keep_separator", column=col)
                element = answer_item[0].relative_elements[0]
                current_table = parse_table(element, tabletype=TableType.KV.value, pdfinsight_reader=self.pdfinsight)
                special_row_index = 0
                for idx, row in enumerate(current_table.rows):
                    valid_row = self.is_valid_row(row_tag_pattern, row, special_row_index, idx)
                    if not valid_row:
                        continue
                    if special_row_index == 0:
                        special_row_index = idx
                    if len(row) == 4:
                        second_cell = row[1]
                        last_cell = row[-1]
                        if len(second_cell.text) > len(last_cell.text):
                            aim_cell = second_cell
                        else:
                            aim_cell = last_cell
                    else:
                        aim_cell = row[-1]
                    element_results = self.create_content_result(
                        element,
                        aim_cell.raw_cell["chars"],
                        [aim_cell],
                        split_pattern,
                        garbage_frag_pattern,
                        keep_separator,
                    )
                    answer = self.create_result(element_results, column=col)
                    ret.append(answer)
                if special_row_index == len(current_table.rows) - 1:
                    answer_from_next_table = self.get_answer_from_next_table(
                        element, col, split_pattern, garbage_frag_pattern, keep_separator
                    )
                    ret.extend(answer_from_next_table)
        return ret

    def get_answer_from_next_table(self, element, col, split_pattern, garbage_frag_pattern, keep_separator):
        ret = []
        next_table, next_element = self.get_next_table(element)
        if not next_table:
            return ret
        if col == "投资比例、限制-基金基本情况表":
            cells = []
            chars = []
            for row in next_table.rows:
                if clean_txt(row[0].text) == "":
                    for aim_cell in row:
                        if not clean_txt(aim_cell.text):
                            continue
                        if aim_cell.dummy:
                            continue
                        cells.append(aim_cell)
                        chars.extend(aim_cell.raw_cell["chars"])
                else:
                    break
            element_results = self.create_content_result(
                element, chars, cells, split_pattern, garbage_frag_pattern, keep_separator
            )
            answer = self.create_result(element_results, column=col)
            ret.append(answer)
        else:
            first_row = next_table.rows[0]
            if clean_txt(first_row[0].text) == "":
                aim_cell = first_row[-1]
                element_results = self.create_content_result(
                    element, aim_cell.raw_cell["chars"], [aim_cell], split_pattern, garbage_frag_pattern, keep_separator
                )
                answer = self.create_result(element_results, column=col)
                ret.append(answer)
        return ret

    def get_next_table(self, element):
        post_elts = self.pdfinsight.find_elements_near_by(element["index"], amount=1, aim_types=["TABLE"])
        if post_elts:
            table = parse_table(post_elts[0], tabletype=TableType.KV.value, pdfinsight_reader=self.pdfinsight)
            return table, post_elts[0]
        return None

    @staticmethod
    def is_valid_row(pattern, row, special_row_index, idx):
        cells = [c for c in row if c.text]
        if not cells:
            return False
        first_cell = cells[0]
        if pattern.nexts(clean_txt(first_cell.text)):
            return True
        if special_row_index and idx == special_row_index + 1 and clean_txt(first_cell.text) == "":
            return True
        return False
