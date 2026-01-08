from collections import defaultdict

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.predictor.models.syllabus_elt import SyllabusElt
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import OutlineResult

income_sub_account_pattern_for_standard = PatternCollection(
    [
        r"(违约事件发生前|违约事件及加速清偿事件发生前).*?(本金科目|本金项)",
    ]
)

capital_sub_account_pattern_for_standard = PatternCollection(
    [
        r"(违约事件发生前|违约事件及加速清偿事件发生前).*?((收益|收入)(科目|项))",
    ]
)

income_sub_account_pattern = PatternCollection(
    [
        r'(["“]?违约事件["”]?发生前|["“]?违约事件["”]?及加速清偿事件发生前).*?(收入回收款|收入分账户|收入科目)',
        r"收益回收款的分配顺序如下",
    ]
)

capital_sub_account_pattern = PatternCollection(
    [
        r'(["“]?违约事件["”]?发生前|["“]?违约事件["”]?及加速清偿事件发生前).*?(本金回收款|本金分账户|本金科目)',
        r"本金回收款的分配顺序如下",
    ]
)

income_capital_split_pattern_prefix = PatternCollection(
    [
        r"^收入分账户",
    ]
)

income_capital_split_pattern = PatternCollection(
    [
        r'违约事件["”]?发生前.*?本金分?账户?项?下资金的分配',
        r'违约事件["”]?发生前.*?本金科目项下资金的分配',
        r'违约事件["”]?发生前.*?本金账项下资金的分配(在"“]?违约事件["”]?发生前)?',
        r"本金回收款的分配顺序如下",
        r"^本金分账户",
    ]
)


after_default_pattern = PatternCollection(
    [
        r"在“违约事件”发生时或之后",
        r'["“]?违约事件["”]?发生后',
        r'["“]?违约事件["”]?或提前终止事件发生后',
        r"在发生加速清偿事件或违约事件情况下",
        r"违约事件或加速清偿事件发生后",
        r"在发生违约事件或加速清偿事件发生后",
        r'发生["“]?违约事件["”]?后',
        r'(?<!未)发生["“]?违约事件["”]?的情况下',
        r"(?<!未)发生提前结束循环购买期事件、提前终止事件和违约事件情况下的分配顺序",
        r"在“委托机构”进行“清仓回购”且向“收付账户”",
        r"非正常情况下的信托财产的分配顺序",
        r"违约事件/信托清算事件发生后的回收款分配",
        r"若发生“信托贷款担保责任启动事件”，“单一资金信托受托人”决定行使抵押权与质权的",
        r"违约事件或提前还款事件发生后的回收款分配",
        r"发生合伙企业临时分配事件或违约事件后的分配顺序",
    ]
)

INCOME_SUB_ACCOUNT_COLUMNS = "违约事件发生前，收入分账户项下资金的分配（分账）"
CAPITAL_SUB_ACCOUNT_COLUMNS = "违约事件发生前，本金分账户项下资金的分配（分账）"
NON_SUB_ACCOUNT_COLUMNS = "违约事件发生前的回收款分配（不分账）"
AFTER_DEFAULT_COLUMNS = "违约事件发生后的回收款分配"


class CashFlow(SyllabusElt):
    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super(CashFlow, self).__init__(options, schema, predictor=predictor)

    def predict_schema_answer(self, elements):
        ret = []
        is_standard_term = self.schema.path[0] == "标准条款"
        income_pattern = income_sub_account_pattern_for_standard if is_standard_term else income_sub_account_pattern
        capital_pattern = capital_sub_account_pattern_for_standard if is_standard_term else capital_sub_account_pattern
        answer_results = super(CashFlow, self).predict_schema_answer(elements)
        answer_results = self.reassemble_answer(answer_results)
        if not answer_results:
            return ret
        has_sub_account = False
        for answer_result in answer_results:
            column = answer_result.key_path[-1]
            text = clean_txt(answer_result.text)
            if column == INCOME_SUB_ACCOUNT_COLUMNS:
                if income_pattern.nexts(text):
                    has_sub_account = True
                    answer_result = self.get_split_front_answer(
                        answer_result,
                        column,
                        income_capital_split_pattern,
                        prefix_pattern=income_capital_split_pattern_prefix,
                    )
                    ret.append(answer_result)
            if column == CAPITAL_SUB_ACCOUNT_COLUMNS:
                if capital_pattern.nexts(text):
                    has_sub_account = True
                    answer_result = self.get_split_back_answer(answer_result, column, income_capital_split_pattern)
                    ret.append(answer_result)
            if column == NON_SUB_ACCOUNT_COLUMNS:
                if has_sub_account:
                    continue
                answer_result = self.get_split_front_answer(answer_result, column, after_default_pattern)
                ret.append(answer_result)
            if column == AFTER_DEFAULT_COLUMNS:
                if after_default_pattern.nexts(text):
                    answer_result = self.get_split_back_answer(answer_result, column, after_default_pattern)
                    ret.append(answer_result)
        return ret

    def reassemble_answer(self, answer_results):
        ret = []
        answers_map = defaultdict(list)
        for answer_result in answer_results:
            column = answer_result.key_path[-1]
            answers_map[column].append(answer_result)

        for answers in answers_map.values():
            syllabuses = []
            answer_results_map = {}
            for answer_result in answers:
                for element in answer_result.relative_elements:
                    syll = self.pdfinsight_syllabus.syllabus_dict[element["syllabus"]]
                    syllabuses.append(syll)
                    answer_results_map[syll["index"]] = answer_result
            syllabuses.sort(key=lambda x: x["level"], reverse=True)
            syll_children_map = {syll["index"]: syll["children"] for syll in syllabuses}
            # 因为配置中加了multi  所以有可能某个章节会被父级目录和子目录都预测出来 但同一章节只需出现一次
            for syll in syllabuses:
                for syll_index, syll_children in syll_children_map.items():
                    if syll["index"] == syll_index:
                        continue
                    if syll["index"] in syll_children:
                        if syll_index in answer_results_map:
                            answer_results_map.pop(syll_index)
            for values in answer_results_map.values():
                ret.append(values)
        return ret

    def get_split_front_answer(self, answer_result, column, after_pattern, prefix_pattern=None):
        element_result = answer_result.element_results[0]
        all_elements = element_result.origin_elements or []
        # 获取上边界
        start_element_index = all_elements[0]["index"]
        if prefix_pattern:
            start_element_index = self.get_split_index(all_elements, start_element_index, prefix_pattern)
        all_elements = [element for element in all_elements if element["index"] >= start_element_index]
        after_element_index = all_elements[-1]["index"]
        after_element_index = self.get_split_index(all_elements, after_element_index, after_pattern)
        if after_element_index == all_elements[-1]["index"]:
            after_element_index += 1
        new_answer_elements = [element for element in all_elements if element["index"] < after_element_index]
        if not new_answer_elements:
            return answer_result
        para_range = {"range": (new_answer_elements[0]["index"], new_answer_elements[-1]["index"] + 1)}
        answer_result = self.gen_answer(new_answer_elements, para_range, column)
        return answer_result

    def get_split_back_answer(self, answer_result, column, pattern):
        element_result = answer_result.element_results[0]
        all_elements = element_result.origin_elements or []
        after_element_index = all_elements[0]["index"]
        after_element_index = self.get_split_index(all_elements, after_element_index, pattern)
        new_answer_elements = [element for element in all_elements if element["index"] >= after_element_index]
        if not new_answer_elements:
            return answer_result
        para_range = {"range": (new_answer_elements[0]["index"], new_answer_elements[-1]["index"] + 1)}
        answer_result = self.gen_answer(new_answer_elements, para_range, column)
        return answer_result

    @staticmethod
    def get_split_index(all_elements, split_index, pattern):
        for element in all_elements:
            if element["class"] != "PARAGRAPH":
                continue
            if pattern.nexts(clean_txt(element["text"])):
                split_index = element["index"]
                break
        return split_index

    def gen_answer(self, new_answer_elements, para_range, column):
        page_box = PdfinsightSyllabus.syl_outline(
            para_range, self.pdfinsight, include_title=self.config.get("include_title", True)
        )
        element_results = [
            OutlineResult(page_box=page_box, element=new_answer_elements[0], origin_elements=new_answer_elements)
        ]
        answer_result = self.create_result(element_results, column=column)
        return answer_result
