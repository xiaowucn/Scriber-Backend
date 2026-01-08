import copy

from utensils.util import index_in_space_string

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.models.middle_paras import MiddleParas
from remarkable.predictor.schema_answer import CharResult


# 把多个para 合并作为一个段落再匹配，为解决标题识别为多个段落情况
class FundName(MiddleParas):
    @property
    def combine_regs(self):
        return PatternCollection(self.get_config("combine_regs", []))

    def predict_schema_answer(self, elements):
        answer_results = []
        elements_blocks = self.collect_elements(elements)
        if not elements_blocks:
            return []
        for col in self.columns:
            answer_results.append(self.build_answer(elements_blocks, col))
        return answer_results

    def collect_elements(self, elements):
        ret = []
        elements = self.collect_crude_elements(elements)
        elements = [x for x in elements if x["page"] not in self.elements_not_in_page_range]
        fixed_elements = self.fixed_elements(elements)
        fixed_elements = self.filter_elements_by_range(fixed_elements)
        top_element_index, bottom_element_index = self.get_margin_index(fixed_elements)
        if bottom_element_index is None or top_element_index > bottom_element_index:
            return ret
        if top_element_index == bottom_element_index and not (self.top_default or self.bottom_default):
            return ret
        combine_text = []
        combine_chars = []
        combine_elements = []
        for element in fixed_elements:
            if top_element_index <= element["temp_index"] <= bottom_element_index:
                combine_text.append(element["text"])
                combine_chars.append(element["chars"])
                combine_elements.append(element)
        # 匹配合并后的text 后再按每个char 所在的element 将这些element 组成一个答案
        matched = self.combine_regs.nexts(clean_txt("".join(combine_text)))
        if not matched:
            return ret
        start, end = matched.span("dst")
        sp_start, sp_end = index_in_space_string("".join(combine_text), (start, end))
        cur_idx = 0
        for ele_idx, combine_char in enumerate(combine_chars):
            new_chars = []
            for char in combine_char:
                if sp_start <= cur_idx < sp_end:
                    new_chars.append(char)
                cur_idx += 1
            if new_chars:
                ele = copy.deepcopy(combine_elements[ele_idx])
                ele["chars"] = new_chars
                ret.append(ele)
            if cur_idx >= sp_end:
                break
        return ret

    def build_answer(self, elements, column):
        element_results = [CharResult(ele, ele["chars"]) for ele in elements]
        answer_result = self.create_result(element_results, column=column)
        return answer_result
