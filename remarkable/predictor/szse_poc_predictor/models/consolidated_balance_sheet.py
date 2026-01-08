from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.eltype import ElementClass, ElementType
from remarkable.predictor.models.table_tuple import TupleTable
from remarkable.predictor.szse_poc_predictor.common import reorganize_preset_answer
from remarkable.predictor.utils import ElementCollector

special_feature = [r"[小合]计"]
invalid_table_title = [
    r"母公司",
]

SUB_SCHEMAS = [
    "流动资产",
    "非流动资产",
    "流动负债",
    "非流动负债",
    "归属于母公司所有者权益",
]


class ConsolidatedBalanceSheet(TupleTable):
    target_element = ElementType.TABLE_TUPLE
    filter_elements_by_target = True

    table_title_pattern = PatternCollection([r"资产负债表"])
    neglect_title_pattern = PatternCollection(invalid_table_title)
    neglect_title_above_pattern = PatternCollection(invalid_table_title)
    continued_table = PatternCollection(
        [
            r"续上表|资产负债表（续）",
            r"合并资产负债表（负债和所有者权益）",
        ]
    )

    def __init__(self, options, schema, predictor):
        super(ConsolidatedBalanceSheet, self).__init__(options, schema, predictor)

    def predict_schema_answer(self, elements):
        rets = []
        for element in self.adjust_elements(elements):
            answer_results = super(ConsolidatedBalanceSheet, self).predict_schema_answer([element])
            answer_results = self.filter_answer_results(answer_results)
            rets.extend(answer_results)
        return rets

    def adjust_elements(self, elements):
        element_collector = ElementCollector(elements, self.pdfinsight)
        elements = element_collector.collect(
            self.table_title_pattern,
            special_class="TABLE",
            multi_elements=self.multi_elements,
            neglect_pattern=self.neglect_title_pattern,
            neglect_title_above_pattern=self.neglect_title_above_pattern,
        )
        if len(elements) == 1:
            next_paras = self.pdfinsight.find_elements_near_by(
                elements[0]["index"], aim_types=[ElementClass.PARAGRAPH.value], steprange=5
            )
            if next_paras and self.continued_table.nexts(clean_txt(next_paras[0]["text"])):
                next_table = self.pdfinsight.find_elements_near_by(
                    next_paras[0]["index"], aim_types=[ElementClass.TABLE.value], steprange=2
                )
                if next_table:
                    elements.append(next_table[0])

        return elements

    @staticmethod
    def filter_answer_results(answer_results):
        rets = []
        answers = reorganize_preset_answer(answer_results, SUB_SCHEMAS)

        for answer in answers.values():
            report_period_answer = answer.get("报告期")
            for sub_schema, item in answer.items():
                find_total_items = False
                if sub_schema == "报告期":
                    continue
                if len(item) == 1:
                    rets.append(
                        {
                            "报告期": report_period_answer,
                            sub_schema: item,
                        }
                    )
                    continue
                for data_item in item:
                    element_result = data_item.element_results[0]
                    parsed_cell = element_result.parsed_cells[0]
                    for cell in parsed_cell.headers:
                        if PatternCollection(special_feature).nexts(clean_txt(cell.text)):
                            rets.append(
                                {
                                    "报告期": report_period_answer,
                                    sub_schema: [data_item],
                                }
                            )
                            find_total_items = True
                            break
                    if find_total_items:
                        break
                if not find_total_items:
                    rets.append(
                        {
                            "报告期": report_period_answer,
                            sub_schema: item,
                        }
                    )
        return rets
