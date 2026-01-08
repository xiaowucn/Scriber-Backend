from copy import deepcopy
from functools import cmp_to_key
from itertools import chain, zip_longest

from remarkable.common.pattern import PatternCollection
from remarkable.predictor.models.partial_text import PartialText
from remarkable.predictor.schema_answer import CharResult, PredictorResult


class FundPerformance(PartialText):
    @property
    def split_regs(self):
        return PatternCollection([r"本报告期.*?[;；。]"])

    @property
    def find_element_regs(self):
        regs = chain(
            self.get_config(field)["regs"]
            for field in ["份额名称", "净值增长率", "净值收益率", "同期业绩比较基准收益率"]
        )
        return PatternCollection(list(regs))

    def predict_schema_answer(self, elements):
        ret = []
        split_elements = self.split_elements(elements)
        if not split_elements:
            return ret
        for element in split_elements:
            parent_answer_results = super().predict_schema_answer([element])
            group_answers = self.regroup(parent_answer_results)
            if not group_answers.get("份额名称"):
                # 只有一组
                share_answer = self.create_result(
                    [CharResult({}, [])],
                    column="份额名称",
                    primary_key="1",  # note: Placeholder
                )
                parent_answer_results[0]["份额名称"] = [share_answer]
                return parent_answer_results
            multi_group_answers = self.process_multi_group(group_answers, parent_answer_results)
            ret.extend(multi_group_answers)
        return ret

    def process_multi_group(self, group_answers, parent_answer_results):
        ret = []
        element = self.find_element(group_answers)
        if not element:
            return parent_answer_results
        for answers in group_answers.values():
            answers.sort(key=cmp_to_key(self.sort_answers))
        return_rate_answer = None
        if group_answers.get("同期业绩比较基准收益率"):
            return_rate_answer = group_answers["同期业绩比较基准收益率"][-1]
        for share, rate, income in zip_longest(
            group_answers["份额名称"], group_answers["净值增长率"], group_answers["净值收益率"], fillvalue=None
        ):
            answer = {}
            if return_rate_answer:
                answer["同期业绩比较基准收益率"] = [deepcopy(return_rate_answer)]
            if share:
                answer["份额名称"] = [share]
            if rate:
                answer["净值增长率"] = [rate]
            if income:
                answer["净值收益率"] = [income]
            ret.append(answer)
        return ret

    @staticmethod
    def find_element(answers):
        for answer in answers.values():
            return answer[0].relative_elements[0]
        return None

    def split_elements(self, elements):
        """
        https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2435
        """
        for element in elements:
            if self.find_element_regs.nexts(element["text"]):
                return self.split_by_regex(element)
        return []

    def split_by_regex(self, element):
        if (matches := list(self.split_regs.finditer(element["text"]))) and len(matches) <= 1:
            return [element]

        split_elements = []
        for match in matches:
            start, end = match.start(), match.end()
            new_element = deepcopy(element)
            new_element["chars"] = element["chars"][start:end]
            new_element["text"] = "".join([c["text"] for c in new_element["chars"]])
            new_element["page_merged_paragraph"] = {}
            split_elements.append(new_element)
        return split_elements

    def sort_answers(self, predictor_result_a: PredictorResult, predictor_result_b: PredictorResult):
        page_a = predictor_result_a.element_results[0].chars[0]["page"]
        page_b = predictor_result_b.element_results[0].chars[0]["page"]
        if page_a > page_b:
            return 1
        elif page_a < page_b:
            return -1

        box_a = predictor_result_a.element_results[0].chars[0]["box"]
        box_b = predictor_result_b.element_results[0].chars[0]["box"]
        box_a_left, box_a_top, _, box_a_bottom = box_a
        box_b_left, box_b_top, _, box_b_bottom = box_b
        if self.is_overlap((box_a_top, box_a_bottom), (box_b_top, box_b_bottom)):
            # 在同一行，如果元素a的左边框线大于b的左边框线，则认为a在b的后面,返回1,表示a比b大
            if box_a_left > box_b_left:
                return 1
            elif box_a_left < box_b_left:
                return -1
            return 0
        else:
            # 不在同一行，判断上下边框线，如果元素a的下边框线小于b的上面框，则认为a在上一行（不考虑分栏情况），则返回-1,表示a比b小
            if box_a_bottom < box_b_top:
                return -1
            else:
                return 1

    @staticmethod
    def is_overlap(interval1, interval2):
        """
        判断元素是否有相交的部分,一般情况下，有相交就算是在同一行
        args: (a_top, a_bottom), (b_top, b_bottom)
        """
        min1, max1 = interval1
        min2, max2 = interval2
        return max1 >= min2 and min1 <= max2
