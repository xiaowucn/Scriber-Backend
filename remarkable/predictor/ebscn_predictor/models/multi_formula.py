from copy import deepcopy

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.eltype import ElementClassifier
from remarkable.predictor.models.partial_text import PartialText
from remarkable.predictor.schema_answer import CharResult, TableResult

P_TITLE = PatternCollection([r"业绩报酬计提如下", r"当R−.*?时，不提取业绩报酬"])


class MultiFormula(PartialText):
    def predict_schema_answer(self, elements):
        ret = []
        answer_results = super().predict_schema_answer(elements)
        for answer_result in answer_results:
            fund_type_answers = answer_result.get("基金类型", [])
            if not fund_type_answers:
                continue
            fund_type_answer = fund_type_answers[0]
            if formula_tables := self.get_formula_table(fund_type_answer):
                answer_result = self.create_result([TableResult(formula_tables[0], [])], column="计提比例及公式")
                fixed_answer_result = {
                    "基金类型": deepcopy(fund_type_answers),
                    "计提比例及公式": [answer_result],
                }
                ret.append(fixed_answer_result)
        if not ret:
            formula_candi_elements = self.predictor.get_candidate_elements(
                key_path=["业绩报酬计算公式（多行公式）", "计提比例及公式"]
            )
            for element in formula_candi_elements:
                if ElementClassifier.is_table(element):
                    table = parse_table(element, tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight)
                    table_titles = [clean_txt(table.element["title"])]
                    if table.title:
                        table_titles.append(table.title.text)
                    if not any(P_TITLE.nexts(i) for i in table_titles):
                        continue
                    formula_answer_result = self.create_result([TableResult(element, [])], column="计提比例及公式")
                    if table.title:
                        fake_char_result = deepcopy(table.title)
                        fake_char_result.display_text = "母基金"
                        fund_type_answers = [self.create_result([fake_char_result], column="基金类型")]
                    else:
                        above_element = table.elements_above[0]
                        fake_char_result = CharResult(above_element, above_element["chars"])
                        fake_char_result.display_text = "母基金"
                        fund_type_answers = [self.create_result([fake_char_result], column="基金类型")]
                    fixed_answer_result = {
                        "基金类型": fund_type_answers,
                        "计提比例及公式": [formula_answer_result],
                    }
                    ret.append(fixed_answer_result)
                    break

        return ret

    def get_formula_table(self, fund_type_answer):
        relative_element = fund_type_answer.relative_elements[0]
        if blew_table := self.pdfinsight.find_elements_near_by(
            relative_element["index"],
            amount=1,
            step=1,
            steprange=5,
            aim_types=["TABLE"],
        ):
            return blew_table
        return None
