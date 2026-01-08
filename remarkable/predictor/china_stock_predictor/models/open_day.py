from collections import defaultdict

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt, index_in_space_string
from remarkable.predictor.models.table_kv import KeyValueTable
from remarkable.predictor.schema_answer import CellCharResult

split_pattern = PatternCollection(
    [
        r"(?P<dst>(\d[,、\.])本基金存续期间.*?当发生以下.*临时开放[日期])",
        r"(?P<dst>(\d[,、\.）])?当发生以下情况时管理人可在?(封闭期满后)?设置临时开放[日期])",
        r"(?P<dst>(\d[,、\.）])?本基金存续期间，当发生以下情况时管理人可在?(封闭期满后)?设置临时开放[日期])",
        r"(?P<dst>基金存续期间内.*临时开放[日期])",
    ]
)

tmp_patterns = PatternCollection(["临时开放[日期]"])

special_pattern = PatternCollection(["无"])


class OpenDay(KeyValueTable):
    """
    开放日和临时开发日经常会放在一个单元格里
    kv模型没有办法直接区分
    加了一个后处理 对于kv预测的结果使用split_pattern切分
    上半段是开放日 下半段是临时开放日
    """

    def predict_schema_answer(self, elements):
        ret = []
        parent_answer_results = super(OpenDay, self).predict_schema_answer(elements)
        if not parent_answer_results:
            return ret
        parent_answer_results = self.regroup(parent_answer_results)
        is_tmp = self.schema.name == "临时开放日"
        parent_answers = parent_answer_results.get(self.schema.name)
        if not parent_answers:
            return ret

        for parent_answer in parent_answers:
            element = parent_answer.relative_elements[0]
            cell = parent_answer.element_results[0].parsed_cells[0]
            split_matcher = split_pattern.nexts(clean_txt(cell.text))
            if not split_matcher:
                if is_tmp and special_pattern.nexts(clean_txt(cell.text)):
                    ret.append(parent_answer)
                    break
                if is_tmp and not tmp_patterns.nexts(clean_txt(cell.text)):
                    continue
                ret.append(parent_answer)
                break
            split_index = self.get_dst_chars_index(split_matcher, cell)
            if is_tmp:
                dst_chars = cell.raw_cell["chars"][split_index:]
                answer = self.create_result([CellCharResult(element, dst_chars, [cell])], column=self.schema.name)
                ret.append(answer)
            else:
                dst_chars = cell.raw_cell["chars"][:split_index]
                answer = self.create_result([CellCharResult(element, dst_chars, [cell])], column=self.schema.name)
                ret.append(answer)

        return ret

    @staticmethod
    def get_dst_chars_index(split_matcher, cell):
        aim_text = split_matcher.groupdict().get("dst", None)
        origin_text = cell.text
        start = clean_txt(origin_text).index(clean_txt(aim_text))
        end = start + len(clean_txt(aim_text))
        sp_start, _ = index_in_space_string(origin_text, (start, end))
        return sp_start

    @staticmethod
    def regroup(answers):
        ret = defaultdict(list)
        for answer in answers:
            for col, value in answer.items():
                ret[col].extend(value)
        return ret
