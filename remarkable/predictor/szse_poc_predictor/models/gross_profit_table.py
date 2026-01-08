from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.common_pattern import DATE_PATTERN
from remarkable.predictor.eltype import ElementType
from remarkable.predictor.models.table_tuple import TupleTable
from remarkable.predictor.schema_answer import TableCellsResult
from remarkable.predictor.szse_poc_predictor.common import reorganize_preset_answer

invalid_table_title = [r"分业务|营业毛利率构成情况|售后维保毛利率"]

SUB_SCHEMAS = [
    "综合毛利率（%）",
]

PRIORITY_RESERVATION_PATTERNS = PatternCollection(
    [
        r"综合",
        r"合计",
    ]
)

INVALID_PATTERNS = PatternCollection(
    [
        r"^毛利$",
        # r'营业(收入|成本|毛利)',
    ]
)

PERIOD_PATTERNS = PatternCollection(DATE_PATTERN)

invalid_table_below_title = PatternCollection([r"毛利率剔除了.*?影响"])

PROFIT_PATTERNS = PatternCollection([r"综合毛利率"])


class GrossProfitTable(TupleTable):
    target_element = ElementType.TABLE_TUPLE
    filter_elements_by_target = True

    def __init__(self, options, schema, predictor):
        super(GrossProfitTable, self).__init__(options, schema, predictor)

    def predict_schema_answer(self, elements):
        rets = []
        for element in elements:
            table = parse_table(element, tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight)
            table_title = table.title.text if table.title else element.get("title")
            if table_title and PatternCollection(invalid_table_title).nexts(clean_txt(table_title)):
                continue
            ele_type, table_note = self.pdfinsight.find_element_by_index(element.get("index") + 1)
            # 表格下方有 剔除XXX 等描述 file id 816
            if ele_type == ElementType.PARAGRAPH.name and invalid_table_below_title.nexts(
                clean_txt(table_note["text"])
            ):
                continue
            answer_results = super(GrossProfitTable, self).predict_schema_answer([element])
            answer_results = self.filter_answer_results(answer_results)
            rets.extend(answer_results)
            if rets:
                break
        return rets

    def filter_answer_results(self, answer_results):
        rets = []
        answers = reorganize_preset_answer(answer_results, SUB_SCHEMAS)

        for answer in answers.values():
            report_period_answer = answer.get("报告期")
            answers_for_period = []
            for sub_schema, items in answer.items():
                if sub_schema == "报告期":
                    continue
                if len(items) == 1:
                    rets.append(
                        {
                            "报告期": report_period_answer,
                            sub_schema: items,
                        }
                    )
                    continue
                for index, data_item in enumerate(items):
                    element_result = data_item.element_results[0]
                    parsed_cell = element_result.parsed_cells[0]
                    for cell in parsed_cell.headers:
                        if INVALID_PATTERNS.nexts(clean_txt(cell.text)):
                            del items[index]
                find_rd_items = False
                for data_item in items:
                    element_result = data_item.element_results[0]
                    parsed_cell = element_result.parsed_cells[0]
                    for cell in parsed_cell.headers:
                        if PRIORITY_RESERVATION_PATTERNS.nexts(clean_txt(cell.text)):
                            answers_for_period.append(
                                {
                                    "报告期": report_period_answer,
                                    "综合毛利率（%）": [data_item],
                                }
                            )
                            find_rd_items = True
                            break
                    if find_rd_items:
                        break
                if find_rd_items and len(items) == 2 and len(answers_for_period) == 1:
                    # 处理 一个报告期有两个答案的情况 822 恒昌医药 毛利表
                    middle_table_report_period_answer = self.find_period_in_middle_of_table(items)
                    if not middle_table_report_period_answer:
                        continue
                    answers_for_period.append(
                        {
                            "报告期": middle_table_report_period_answer,
                            "综合毛利率（%）": items[-1:],
                        }
                    )
                if find_rd_items and len(items) > 2:
                    # 处理 行头应该有两列的情况
                    item = self.find_only_item(items)
                    # 删除前一个答案 因为find_only_item会返回这一组里的一个答案 所以前面的答案就不需要了
                    answers_for_period = answers_for_period[:-1]
                    answers_for_period.append(
                        {
                            "报告期": report_period_answer,
                            "综合毛利率（%）": item,
                        }
                    )
                if not find_rd_items:
                    rets.append(
                        {
                            "报告期": report_period_answer,
                            "综合毛利率（%）": items,
                        }
                    )
            rets.extend(answers_for_period)
        return rets

    def find_period_in_middle_of_table(self, answers):
        """
        | 项目| 2021年1-9月| 2020年度|
        |毛利率| XXX      | XXX     |
        | 项目| 2019年度| 2018年度|
        |毛利率| XXX      | XXX     |
        """
        answer = answers[-1]
        element_result = answer.element_results[0]
        parsed_cell = element_result.parsed_cells[0]
        table = parsed_cell.table
        col_idx = parsed_cell.colidx
        row_idx = parsed_cell.rowidx
        for cell in parsed_cell.table.cols[col_idx][:row_idx][::-1]:
            if PERIOD_PATTERNS.nexts(clean_txt(cell.text)):
                return [self.create_result([TableCellsResult(table.element, [cell])], column="报告期")]
        return []

    @staticmethod
    def find_only_item(items):
        """
        表格解析到了倒数四行的数据 只需要最后一行的毛利率  810 软通动力 毛利表
        | 业务类型| 项目 | 2021年1-6月|
        |XXX    | XXX      | XXX     |
        |XXX    | XXX      | XXX     |
        |综合| 营业收入      | XXX     |
        |综合| 营业成本      | XXX     |
        |综合| 营业毛利      | XXX     |
        |综合| 营业毛利率      | XXX     |
        """
        for item in items:
            element_result = item.element_results[0]
            parsed_cell = element_result.parsed_cells[0]
            col_idx = parsed_cell.colidx
            row_idx = parsed_cell.rowidx
            for cell in parsed_cell.table.rows[row_idx][1:col_idx]:
                if PROFIT_PATTERNS.nexts(clean_txt(cell.text)):
                    return [item]
        return items[:1]
