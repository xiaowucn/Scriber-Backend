from collections import defaultdict

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.predictor.models.table_tuple import TupleTable

SUB_SCHEMAS = [
    "管理费用/营业收入（%）",
    "销售费用/营业收入（%）",
    "财务费用/营业收入（%）",
]

VALID_ABOVE_CELL_PATTERNS = {
    "管理费用/营业收入（%）": [r"管理费用"],
    "销售费用/营业收入（%）": [r"销售费用"],
    "财务费用/营业收入（%）": [r"财务费用"],
}

PRIORITY_RESERVATION_PATTERNS = [
    r"占营?业?收入比重",
    r"占比|比重|比例",
    r"[%％/率]",
]

WRONG_PATTERNS = [
    r"[合小]计",
]

separate_pattern = [
    r"占收入比重",
    r"占营业收入的比例",
]

INVALID_TABLE_TITLE = PatternCollection(
    [
        r"报告期(各期|内)，公司期间费用构成情况如下",
    ]
)


class PeriodFeeSchedule(TupleTable):
    target_element = None
    filter_elements_by_target = True

    def __init__(self, options, schema, predictor):
        super(PeriodFeeSchedule, self).__init__(options, schema, predictor)

    def predict_schema_answer(self, elements):
        rets = []
        for element in elements:
            table = parse_table(element, tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight)
            table_title = table.title.text if table.title else element.get("title")
            if not self.is_valid_element(table_title):
                continue
            answer_results = super(PeriodFeeSchedule, self).predict_schema_answer([element])
            is_separate_line = self.judge_is_separate(table)
            answer_results = self.filter_answer_results(answer_results, is_separate_line, table)
            rets.extend(answer_results)
            if rets:
                break
        return rets

    @staticmethod
    def is_valid_element(table_title):
        if INVALID_TABLE_TITLE.nexts(clear_syl_title(table_title)):
            return False
        return True

    @staticmethod
    def judge_is_separate(table):
        special_cells = [
            cell for cell in table.cols[0] if PatternCollection(separate_pattern).nexts(clean_txt(cell.text))
        ]
        return len(special_cells) > 2

    @staticmethod
    def find_answer_from_above(item, table, sub_schema):
        for data_item in item:
            element_result = data_item.element_results[0]
            parsed_cell = element_result.parsed_cells[0]
            above_cell = table.rows[parsed_cell.rowidx - 1][parsed_cell.colidx]
            for cell in above_cell.headers:
                if PatternCollection(VALID_ABOVE_CELL_PATTERNS[sub_schema]).nexts(clean_txt(cell.text)):
                    return [data_item]
        return item

    def filter_answer_results(self, answer_results, is_separate_line, table):
        rets = []
        answers = defaultdict(dict)
        for answer_result in answer_results:
            report_period_answer = answer_result.get("报告期")
            if not report_period_answer:
                continue
            report_period = clean_txt(report_period_answer[0].text)
            answers[report_period] = defaultdict(list)
            answers[report_period]["报告期"] = report_period_answer
        for sub_schema in SUB_SCHEMAS:
            for answer_result in answer_results:
                report_period_answer = answer_result.get("报告期")
                if not report_period_answer:
                    continue
                report_period = clean_txt(report_period_answer[0].text)
                for key, item in answer_result.items():
                    if key == sub_schema:
                        answers[report_period][sub_schema].extend(item)

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
                if is_separate_line:
                    separate_answer = self.find_answer_from_above(item, table, sub_schema)
                    rets.append(
                        {
                            "报告期": report_period_answer,
                            sub_schema: separate_answer,
                        }
                    )
                    continue
                finally_items = []
                for data_item in item:
                    element_result = data_item.element_results[0]
                    parsed_cell = element_result.parsed_cells[0]
                    is_wrong_answer = False
                    for cell in parsed_cell.headers:
                        if PatternCollection(WRONG_PATTERNS).nexts(clean_txt(cell.text)):
                            is_wrong_answer = True
                            break
                        if PatternCollection(PRIORITY_RESERVATION_PATTERNS).nexts(clean_txt(cell.text)):
                            rets.append(
                                {
                                    "报告期": report_period_answer,
                                    sub_schema: [data_item],
                                }
                            )
                            find_total_items = True
                            break
                    if not is_wrong_answer:
                        finally_items.append(data_item)
                    if find_total_items:
                        break
                if not find_total_items:
                    rets.append(
                        {
                            "报告期": report_period_answer,
                            sub_schema: finally_items,
                        }
                    )
        return rets
