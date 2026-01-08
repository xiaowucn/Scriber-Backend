from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.eltype import ElementType
from remarkable.predictor.models.table_tuple import TupleTable
from remarkable.predictor.szse_poc_predictor.common import reorganize_preset_answer

invalid_table_title = [
    # r'(?<!公司及)子公司',
    # r'(?<!发行人及其)子公司',
    r"平均薪酬|印度各类|入职时间|级别分布|工资和奖金|食品员工|科技及其子公司",
]

SUB_SCHEMAS = [
    "研发人员数量（硕士及以上学历）（人）",
]

PRIORITY_RESERVATION_PATTERNS = [
    r"研发",
    r"技术",
]

SECOND_HEADER_PATTERNS = [r"类别|分类标准|细分类别|结构"]


class EmployeesNum(TupleTable):
    target_element = ElementType.TABLE_TUPLE
    filter_elements_by_target = True

    def __init__(self, options, schema, predictor):
        super(EmployeesNum, self).__init__(options, schema, predictor)

    def predict_schema_answer(self, elements):
        rets = []
        for element in elements:
            table = parse_table(element, tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight)
            table_title = table.title.text if table.title else element.get("title")
            if table_title and PatternCollection(invalid_table_title).nexts(clean_txt(table_title)):
                continue
            answer_results = super(EmployeesNum, self).predict_schema_answer([element])
            second_header_cols = self.has_second_header(table)
            answer_results = self.filter_answer_results(answer_results, table, second_header_cols)
            rets.extend(answer_results)
        return rets

    # todo 在通用的逻辑里添加 正则优先级过滤
    @staticmethod
    def filter_answer_results(answer_results, table, second_header_cols):
        rets = []
        answers = reorganize_preset_answer(answer_results, SUB_SCHEMAS)
        for answer in answers.values():
            report_period_answer = answer.get("报告期")
            for sub_schema, item in answer.items():
                find_rd_items = False
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
                for pattern in PRIORITY_RESERVATION_PATTERNS:
                    for data_item in item:
                        element_result = data_item.element_results[0]
                        parsed_cell = element_result.parsed_cells[0]
                        second_headers = []
                        if second_header_cols:
                            for second_header_col in second_header_cols:
                                second_headers.append(table.rows[parsed_cell.rowidx][second_header_col])
                        for cell in parsed_cell.headers + second_headers:
                            if PatternCollection([pattern]).nexts(clean_txt(cell.text)):
                                rets.append(
                                    {
                                        "报告期": report_period_answer,
                                        sub_schema: [data_item],
                                    }
                                )
                                find_rd_items = True
                                break
                        if find_rd_items:
                            break
                    if find_rd_items:
                        break
                if not find_rd_items:
                    rets.append(
                        {
                            "报告期": report_period_answer,
                            sub_schema: item,
                        }
                    )
        return rets

    @staticmethod
    def has_second_header(table):
        second_header_cols = []
        for header_cell in table.header:
            if PatternCollection(SECOND_HEADER_PATTERNS).nexts(clean_txt(header_cell.text)):
                second_header_cols.append(header_cell.colidx)
        return second_header_cols
