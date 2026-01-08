import re

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import date_patterns, parse_table
from remarkable.predictor.models.table_tuple import TupleTable
from remarkable.predictor.schema_answer import TableCellsResult

RETURNONNETASSETS = "加权平均净资产收益率"

BEFORE_DEDUCTION = "加权平均净资产收益率（扣除非经常性损益前）（%）"
AFTER_DEDUCTION = "加权平均净资产收益率（扣除非经常性损益后）（%）"
special_cell_data_patterns = PatternCollection(
    [
        re.compile(r"^\d+(\.\d+)?[%％]?$"),
        re.compile(r"-?\d*?(,?\d+)+(\.\d+)?[%％]?"),
    ]
)

feature_patterns = {
    "报告期": PatternCollection([date_patterns]),
    BEFORE_DEDUCTION: special_cell_data_patterns,
    AFTER_DEDUCTION: special_cell_data_patterns,
}

# return_rate_patterns = {
# before_deduction: PatternCollection([r'^((?!扣除).)+$']),
# after_deduction_patterns = PatternCollection([r'扣除'])
# }
after_deduction_patterns = PatternCollection([r"扣除"])
report_period_patterns = PatternCollection([date_patterns, r"20\d\d"])
last_report_period = PatternCollection([r"\d{4}年\d{1,2}[-~]\d{1,2}月"])
valid_subtitile = PatternCollection([r"加权平均净资产收益率", date_patterns])

merge_cell_report_period_patterns = PatternCollection(
    [
        r"^报告期间$",
        r"^时间$",
    ]
)


class ReturnOnNetAssets(TupleTable):
    target_element = None
    filter_elements_by_target = True

    def __init__(self, options, schema, predictor):
        super(ReturnOnNetAssets, self).__init__(options, schema, predictor)

    def predict_schema_answer(self, elements):
        rets = []
        for element in elements:
            table = parse_table(element, tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight)
            if self.is_table_tuple(table):
                answer_results = super(ReturnOnNetAssets, self).predict_schema_answer([element])
                if self.multi_report_row(table):
                    answer_results = self.add_report_period_from_above(answer_results, element, table)
                else:
                    answer_results = self.add_report_period(answer_results, element, table)
                if not answer_results or self.only_has_report_period(answer_results):
                    # 818 笛东规划
                    answer_results = self.extract_from_special_table(table)
            else:
                answer_results = self.parser_from_row(table, element)
            rets.extend(answer_results)
        return rets

    @staticmethod
    def only_has_report_period(answer_results):
        # check if answer_results only has report period answer
        answer_map = {}
        for answer_result in answer_results:
            for key, value in answer_result.items():
                answer_map[key] = value
        return len(answer_map) == 1 and list(answer_map.keys())[0] == "报告期"

    def extract_from_special_table(self, table):
        """
        |   报告期利润              | 2021年1-6月 | 2020年度 | 2019年度 | 2018年度 |
        | -----------             |         加权平均净资产收益率                |
        | 归属于母公司普通股东的净利润 | XXX       |     X XX |    XXX  |    XXX  |
        | 扣除非经常性损益XXXX净利润 | XXX       |     X XX |    XXX  |    XXX  |
        """
        return_on_assets_rowidx = None
        for idx, row in enumerate(table.rows):
            row_text = clean_txt("".join(cell.text for cell in row if not cell.dummy))
            if RETURNONNETASSETS in row_text:
                return_on_assets_rowidx = idx
                break
        if return_on_assets_rowidx is None:
            return []
        if return_on_assets_rowidx + 2 > table.height:
            return []
        ret = []
        # return_on_assets_rowidx 下一行是 BEFORE_DEDUCTION
        for cell in table.rows[return_on_assets_rowidx + 1]:
            assets_answer = [self.create_result([TableCellsResult(table.element, [cell])], column=BEFORE_DEDUCTION)]
            report_answer = None
            for header in cell.col_header_cells:
                if report_period_patterns.nexts(clean_txt(header.text)):
                    report_answer = [self.create_result([TableCellsResult(table.element, [header])], column="报告期")]
                    break
            if report_answer:
                ret.append(
                    {
                        "报告期": report_answer,
                        BEFORE_DEDUCTION: assets_answer,
                    }
                )
        # return_on_assets_rowidx 下面第二行是 AFTER_DEDUCTION
        for cell in table.rows[return_on_assets_rowidx + 2]:
            assets_answer = [self.create_result([TableCellsResult(table.element, [cell])], column=AFTER_DEDUCTION)]
            report_answer = None
            for header in cell.col_header_cells:
                if report_period_patterns.nexts(clean_txt(header.text)):
                    report_answer = [self.create_result([TableCellsResult(table.element, [header])], column="报告期")]
                    break
            if report_answer:
                ret.append(
                    {
                        "报告期": report_answer,
                        AFTER_DEDUCTION: assets_answer,
                    }
                )
        return ret

    @staticmethod
    def is_table_tuple(table):
        # todo 基本每股收益 和收益率合并的表格  29
        upper_left_cell = table.rows[0][0]
        # 表格左上角单元格为时间
        if report_period_patterns.nexts(clean_txt(upper_left_cell.text)):
            return True
        report_cells = [
            cell for cell in table.header if report_period_patterns.nexts(clean_txt(cell.text)) and cell.is_col_header
        ]
        return len(report_cells) >= 3

    @staticmethod
    def multi_report_row(table):
        has_report_row_num = 0
        for row in table.rows:
            report_cell = [cell for cell in row if report_period_patterns.nexts(clean_txt(cell.text))]
            if report_cell:
                has_report_row_num += 1
        return has_report_row_num >= 3

    def add_report_period_from_above(self, answer_results, element, table):
        rets = []
        for answer_result in answer_results:
            if "报告期" in answer_result:
                if len(answer_result) > 1:
                    rets.append(answer_result)
                continue
            ret = {}
            for answer in answer_result.values():
                element_result = answer[0].element_results[0]
                parsed_cell = element_result.parsed_cells[0]
                if not special_cell_data_patterns.nexts(clean_txt(parsed_cell.text)):
                    break
                for row in table.rows[0 : parsed_cell.rowidx][::-1]:
                    for cell in row:
                        if report_period_patterns.nexts(clean_txt(cell.text)):
                            ret["报告期"] = [self.create_result([TableCellsResult(element, [cell])], column="报告期")]
                            ret.update(answer_result)
                            break
                    if "报告期" in ret:
                        break
            rets.append(ret)
        return rets

    def add_report_period(self, answer_results, element, table):
        rets = []
        for answer_result in answer_results:
            if "报告期" in answer_result:
                if len(answer_result) > 1:
                    rets.append(answer_result)
                continue
            ret = {}
            for answer in answer_result.values():
                element_result = answer[0].element_results[0]
                parsed_cell = element_result.parsed_cells[0]
                # 过滤表格中非 加权平均净资产收益率的数据 file id 212
                if parsed_cell.subtitle and not valid_subtitile.nexts(clean_txt(parsed_cell.subtitle)):
                    continue
                for header_cell in parsed_cell.headers + [table.rows[0][0]]:
                    if report_period_patterns.nexts(clean_txt(header_cell.text)):
                        ret["报告期"] = [
                            self.create_result([TableCellsResult(element, [header_cell])], column="报告期")
                        ]
                        ret.update(answer_result)
                        break
            rets.append(ret)
        return rets

    def parser_from_row(self, table, element):
        rets = []
        row_tags = []
        row_tag_num = 3  # 默认有三个报告期
        for row in table.rows:
            ret = {}
            row_tag = self.get_row_tag(row, row_tag_num, row_tags)
            for cell in row:
                if report_period_patterns.nexts(clean_txt(cell.text)):
                    # 如果匹配到三年一期中的一期 则 row_tag_num变为4
                    if last_report_period.nexts(clean_txt(cell.text)):
                        row_tag_num = 4
                    ret["报告期"] = [self.create_result([TableCellsResult(element, [cell])], column="报告期")]
                    continue
                if cell.rowidx > 1 and merge_cell_report_period_patterns.nexts(clean_txt(cell.text)):
                    above_cell = table.rows[cell.rowidx - 1][cell.colidx]
                    if report_period_patterns.nexts(clean_txt(above_cell.text)):
                        ret["报告期"] = [self.create_result([TableCellsResult(element, [above_cell])], column="报告期")]
                    continue
                if special_cell_data_patterns.nexts(clean_txt(cell.text)):
                    ret[row_tag] = [self.create_result([TableCellsResult(element, [cell])], column=row_tag)]
                    if "报告期" not in ret and cell.subtitle:
                        # 尝试从subtitle中提取报告期
                        report_cell = self.get_report_from_subtitle(cell, table)
                        if report_cell:
                            ret["报告期"] = [
                                self.create_result([TableCellsResult(element, [report_cell])], column="报告期")
                            ]
                    break
            if ret and len(ret) == 2:
                rets.append(ret)
                # 预测到答案 记录一下预测到的答案属于扣除前还是扣除后
                row_tags.append(row_tag)
        return rets

    @staticmethod
    def get_report_from_subtitle(cell, table):
        if report_period_patterns.nexts(clean_txt(cell.subtitle)):
            for idx, tag in enumerate(table.row_tags):
                if tag == "subtitle":
                    subtitle_cell = table.rows[idx][0]
                    if clean_txt(subtitle_cell.text) == clean_txt(cell.subtitle):
                        return subtitle_cell
        return None

    @staticmethod
    def get_row_tag(row, row_tag_num, row_tags):
        row_tag = BEFORE_DEDUCTION
        for cell in row:
            if after_deduction_patterns.nexts(clean_txt(cell.text)):
                row_tag = AFTER_DEDUCTION
                break
        if row_tags.count(BEFORE_DEDUCTION) == row_tag_num and row_tag == BEFORE_DEDUCTION:
            row_tag = AFTER_DEDUCTION
        return row_tag
