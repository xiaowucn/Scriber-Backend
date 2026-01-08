from copy import deepcopy
from dataclasses import dataclass

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import ParsedTableCell, parse_table
from remarkable.predictor.eltype import ElementClassifier
from remarkable.predictor.models.table_row import TableRow
from remarkable.predictor.schema_answer import (
    AnswerResult,
    CellCharResult,
    CharResult,
    PredictorResultGroup,
    TableCellsResult,
)

GRANT_TYPE_COLUMN = "授予类型"
TOOL_TYPE_COLUMN = "工具类型"
PERIOD_COLUMN = "期间"
INCENTIVE_OBJECT_COLUMN = "激励对象类型"
ASSESSMENT_YEAR_COLUMN = "考核年度"
PERFORMANCE_GOAL_COLUMN = "业绩考核目标"

TOOL = r"(股票期权|股票增值权|限制性股票|第[一二]类限制性股票|权益工具)"

GRANT_TYPE_PATTERN = PatternCollection(
    [
        r"(?P<dst>首次授予)",
        rf"(?P<dst>预留授予)的?{TOOL}",
        rf"(?P<dst>预留(部分)?)的?{TOOL}",
        r"本计划(?P<dst>首[期次]授予)部分",
        r"(?P<dst>预留)(授予部分|期权|部分)",
        rf"(?P<dst>首次授予|预留)的?{TOOL}的?\s?第[一二三四五六七八九十]",
    ]
)


TOOL_TYPE_PATTERN = PatternCollection(
    [
        rf"(首次授予|预留)的?(?P<dst>{TOOL})\s?第[一二三四五六七八九十]",
        rf"首次授予及预留授予部分\s?的?(?P<dst>{TOOL})",
    ]
)


ABOVE_TOOL_TYPE_PATTERN = PatternCollection(
    [
        rf"本(计划授予|激励计划)的?(?P<dst>{TOOL})",
        rf"首次授予的?(?P<dst>{TOOL})",
        rf"预留部分的?(?P<dst>{TOOL})",
        rf"激励对象持有的?(?P<dst>{TOOL})",
        rf"(?P<dst>{TOOL})的授予",
        rf"获授的?(?P<dst>{TOOL})",
    ]
)

NEED_SPLIT_PATTERN = PatternCollection(
    [
        r"[\/及；]",
        r"(?:行权期\n?)（(?:预留部分)",
    ]
)

PERIOD_COMMON_PATTERN = PatternCollection(
    [
        r"(?P<dst>第[一二三四五六七八九十][个次](行权期|解锁期?|解除限售期))",
    ]
)

FIRST_HALF_PATTERN = PatternCollection(
    [
        # rf'(?P<dst>{period_common_reg}).*?\/'
        r"(?P<dst>.*)[\/及；（]"
    ]
)

SECOND_HALF_PATTERN = PatternCollection(
    [
        # rf'\/.*?(?P<dst>{period_common_reg})'
        r"[\/及；（](?P<dst>.*)"
    ]
)

NEED_SPLIT_GRANT_PATTERN = PatternCollection(
    [
        r"包括预留",
        r"首次授予及预留授予部分",
    ]
)

INCENTIVE_PATTERN = PatternCollection([r"公司业绩条件"])

TIME_PATTERN = r"(((股票期权|首次)?授予日)|授予(完成登记之?)?日|授予登记完成之?日|相应部分限制性股票授予之?日|预留权益授予日|预留授予登记完成之?日|授权日)"

TIME_STRUCT_PATTERN = PatternCollection(
    [
        # rf'自(?P<type>{TIME_PATTERN})起\s?(?P<start>\d+)\s?个月后的首个交易日起至{TIME_PATTERN}起\s?(?P<end>\d+)\s?个月内的最后一个交易日当日止',
        r"自(?P<type>.*?)起[的满]?\s?(?P<start>\d+)\s?个月后的首个交易日起?，?至(?P=type)起的?\s?(?P<end>\d+)\s?个月内的最后一个交易日(当日)?止",
        r"自(?P<type>.*?)起[的满]?\s?(?P<start>\d+)\s?个月后的首个交易日起?至(相应的授予日)起的?\s?(?P<end>\d+)\s?个月内的最后一个交易日(当日)?止",
        r"自(?P<type>.*?)起[的满]?\s?(?P<end>\d+)\s?个月后.*?满足(第\w次)?解锁条件",
        r"自(?P<type>.*?)起[的满]?\s?(?P<start>\d+)\s?个月起?至(?P=type)起的?\s?(?P<end>\d+)\s?个月内止",
        r"(?P<type>\d+\s?年公司年度报告经股东大会审议通过后的首个交易日)起?至.*?(?P<end>\d+)\s?个月内的最后一个交易日(当日)?止",
        rf"自(?P<type>.*?)起[的满]?\s?(?P<start>\d+)\s?个月后的首个交易日起?，?至{TIME_PATTERN}起的?\s?(?P<end>\d+)\s?个月内的最后一个交易日(当日)?止",
    ]
)
primary_indicator = r"(ΔEVA|研发费用|归属于母公司的净利润|净利润复合增长率|累计营业收入值|归属于上市公司股东的净利润|加权平均净资产|净资产|净利润|成本费用占收入|主营业务收入|营业收入|平均净资产|知识产权|毛利)"

P_NEED_ADD_BASE_CONDITION = PatternCollection(
    [rf"^{primary_indicator}$"],
)
P_ADD_BASE_CONDITION = PatternCollection(
    [rf"(?P<addtional_base>\d+\s?年较\s?\d+\s?年){primary_indicator}.*?{primary_indicator}"],
)

GOAL_STRUCT_PATTERN = PatternCollection(
    [
        r"(?P<condition>(?P<evaluation_relationship>(不[高低]于|[大小]于|增长))\s?(?P<target_value>(人民币)?[\d,.]+[万亿]元))",
        r"(?P<condition>(?P<evaluation_relationship>(不[高低]于|[大小]于|增长))\s?(?P<target_value>\d+(\.\d+)?%?件?))",
        r"(?P<condition>(?P<evaluation_relationship>(不[高低]于|[大小]于))\s?(?P<target_value>同行业.*?水平))",
        r"(?P<condition>(?P<evaluation_relationship>(不[高低]于|[大小]于))\s?(?P<target_value>前\w个会计年度平均水准))",
        rf"(?P<condition>(?P<evaluation_relationship>(不[高低]于|[大小]于))\s?(?P<target_value>对标企业{primary_indicator}均值的\d+倍))",
        r"(?P<condition>(?P<evaluation_relationship>(不[高低]于|[大小]于))\s?(?P<target_value>对标企业\d+分位值水平))",
    ]
)

indicator_method = r"(收益率|复合增长率|比重|(平均)?增长率|累计获得数|增长)"

HALF_GOAL_STRUCT_PATTERN = PatternCollection(
    [
        rf"以(?P<base_year>\d+)\s?年.*?(?P<base_condition>(?P<year>\d+(年?[\-、]\d+年)?)\s?年?(?P<indicator>(?P<primary_indicator>{primary_indicator})(?P<indicator_method>{indicator_method})))",
        rf"(?P<base_condition>(?P<year>\d+年[\-、]\d+年)的?(?P<indicator>(?P<primary_indicator>{primary_indicator})(?P<indicator_method>{indicator_method})))",
        rf"(?P<base_condition>(?P<year>\d+[\-、]\d+年)(\w年)?的?(?P<indicator>(?P<primary_indicator>{primary_indicator})))",
        rf"(?P<base_condition>(?P<year>\d+)\s?年较\s?(?P<base_year>\d+)\s?年(?P<indicator>(?P<primary_indicator>{primary_indicator})(?P<indicator_method>{indicator_method})))",
        rf"(?P<base_condition>(?P<year>\d+)\s?年的?(?P<indicator>(?P<primary_indicator>{primary_indicator})(?P<indicator_method>{indicator_method})))",
        rf"(?P<base_condition>(?P<year>\d+)\s?年的?(?P<indicator>(?P<primary_indicator>{primary_indicator})))",
        rf"(?P<base_condition>(?P<year>\d+)\s?年底，(?P<indicator>(?P<primary_indicator>{primary_indicator})(?P<indicator_method>{indicator_method})))",
        rf"(?P<base_condition>(?P<year>\d+)\s?年实现的(?P<indicator>(?P<primary_indicator>{primary_indicator})))",
        rf"(?P<base_condition>(?P<indicator>(?P<primary_indicator>{primary_indicator})(?P<indicator_method>{indicator_method})))",
        rf"(?P<base_condition>(?P<indicator>(?P<primary_indicator>{primary_indicator})))(不[高低]于|[大小]于)",
        rf"(?P<base_condition>(?P<indicator>(?P<primary_indicator>{primary_indicator})))较(?P<base_year>\d+)\s?年",
        # rf'且(?P<base_condition>(?P<indicator>(?P<primary_indicator>Δ\s?EVA)))\s?大于\s?0',
    ]
)

GOAL_SPLIT_PATTERN_WITHOUT_COMMA = PatternCollection(r"[;；]")
GOAL_SPLIT_PATTERN = PatternCollection(r"[;；，]")

GOAL_SPLIT_AGAIN_PATTERN = PatternCollection(r"[且或]")

BASE_YEAR_PATTERN = PatternCollection(
    [
        r"^相比(?P<base_year>\d+)\s?年",
        r"以\s?(?P<base_year>\d+)\s?年.*?为?基[数准]",
        rf"\d+年{primary_indicator}相比(?P<base_year>\d+)年",
    ]
)

YEAR_PATTERN = PatternCollection(
    [
        r"以\s?(?P<base_year>\d+)\s?年.*?为?基[数准]，(?P<year>\d+)\s?年.*?当年",
    ]
)

P_SKIP_FAKE_CELL = PatternCollection(
    [
        r"以(?P<base_year>\d+)\s?年.*?为基数$",
    ]
)

P_LEFT_CELL_YEAR = PatternCollection([r"^\d+$"])


@dataclass
class FakeCell:
    text: str
    chars: list


class Performance(TableRow):
    def predict_schema_answer(self, elements):
        ret = []
        parent_answer_results = super().predict_schema_answer(elements)
        if not parent_answer_results:
            return ret
        answers = self.filter_answers(parent_answer_results)
        answers = self.supplement_answers(answers)
        for answer in answers:
            # 补充授予类型
            if not answer.get(GRANT_TYPE_COLUMN):
                grant_type_answer = self.find_grant_answer(answer)
                answer[GRANT_TYPE_COLUMN] = grant_type_answer
            # 补充工具类型
            if not answer.get(TOOL_TYPE_COLUMN):
                tool_type_answer = self.find_tool_answer(answer)
                answer[TOOL_TYPE_COLUMN] = tool_type_answer
            else:
                self.fix_tool_answer(answer)
            # 补充激励对象类型
            if not answer.get(INCENTIVE_OBJECT_COLUMN):
                # todo
                pass
                # incentive_object_answer = self.find_incentive_object_answer(answer)
                # answer[INCENTIVE_OBJECT_COLUMN] = incentive_object_answer
            else:
                self.fix_incentive_answer(answer)

            self.fix_period_answer(answer)
        if self.schema.parent.name == "安排表":
            self.supplement_time_struct(answers)
        if self.schema.parent.name == "业绩考核":
            self.supplement_goal_struct(answers)

        return answers

    def supplement_goal_struct(self, answers):
        # key_map = {
        #     "业绩条件_细分条件": "condition",
        #     "业绩条件_细分条件的关系": "relation",
        #     "业绩条件_考核基准年": "base_year",
        #     "业绩条件_考核年": "year",
        #     "业绩条件_考核指标": "indicator",
        #     "业绩条件_考核一级指标": "primary_indicator",
        #     "业绩条件_考核一级指标计算方法": "indicator_method",
        #     "业绩条件_考核二级指标": "secondary_indicator",
        #     "业绩条件_考核关系": "evaluation_relationship",
        #     "业绩条件_考核目标值": "target_value"
        # }
        key_map = {
            "base_condition": "业绩条件_细分条件指标",
            "condition": "业绩条件_细分条件关系数值",
            "relation": "业绩条件_细分条件的关系",
            "base_year": "业绩条件_考核基准年",
            "year": "业绩条件_考核年",
            "indicator": "业绩条件_考核指标",
            "primary_indicator": "业绩条件_考核一级指标",
            "indicator_method": "业绩条件_考核一级指标计算方法",
            "secondary_indicator": "业绩条件_考核二级指标",
            "evaluation_relationship": "业绩条件_考核关系",
            "target_value": "业绩条件_考核目标值",
        }
        for answer in answers:
            goal_answer = answer.get("业绩考核目标")
            if not goal_answer:
                continue
            goal_answer = deepcopy(goal_answer[0])
            goal_answer_result = goal_answer.element_results[0]
            parsed_cell = goal_answer_result.parsed_cells[0]
            element = goal_answer_result.element
            split_pattern = (
                GOAL_SPLIT_PATTERN_WITHOUT_COMMA
                if GOAL_SPLIT_AGAIN_PATTERN.nexts(parsed_cell.text)
                else GOAL_SPLIT_PATTERN
            )
            fake_cells = self.split_cell(parsed_cell, split_pattern)
            groups = []
            for fake_cell in fake_cells:
                clean_text = clean_txt(fake_cell.text)
                if P_SKIP_FAKE_CELL.nexts(clean_text):
                    continue
                split_matcher = GOAL_SPLIT_AGAIN_PATTERN.nexts(clean_text)
                relation_answers = None
                if split_matcher:
                    dst_chars = self.get_chars(
                        fake_cell.text, split_matcher.group(), fake_cell.chars, split_matcher.span()
                    )
                    element_result = CellCharResult(element, dst_chars, [parsed_cell])
                    relation_answers = self.create_result(
                        [element_result],
                        column="业绩条件_细分条件的关系",
                        schema=self.predictor.find_child_schema("业绩条件_细分条件的关系"),
                    )
                    sub_fake_cells = self.split_cell(fake_cell, GOAL_SPLIT_AGAIN_PATTERN)
                else:
                    sub_fake_cells = [fake_cell]
                base_group = {}
                if relation_answers:
                    base_group["relation"] = deepcopy(relation_answers)
                self.fill_in_group(base_group, fake_cell, key_map, element, parsed_cell)
                for sub_fake_cell in sub_fake_cells:
                    if not sub_fake_cell.text:
                        continue
                    group = deepcopy(base_group)
                    self.fill_in_group(group, sub_fake_cell, key_map, element, parsed_cell)
                    clean_text = clean_txt(sub_fake_cell.text)
                    if matcher := GOAL_STRUCT_PATTERN.nexts(clean_text):
                        for dst_key, column in key_map.items():
                            if not (value := matcher.groupdict().get(dst_key, None)):
                                continue
                            dst_chars = self.get_chars(
                                sub_fake_cell.text, value, sub_fake_cell.chars, matcher.span(dst_key)
                            )
                            element_result = CellCharResult(goal_answer_result.element, dst_chars, [parsed_cell])
                            item = self.create_result(
                                [element_result],
                                column=column,
                                schema=self.predictor.find_child_schema(column),
                            )
                            group[dst_key] = item

                    if not group or len(group) == 1:
                        continue
                    if "base_year" not in group:
                        if base_year_answer := self.find_base_year_answer(parsed_cell, sub_fake_cell):
                            group["base_year"] = base_year_answer
                    if "year" not in group:
                        if year_answer := self.find_year_answer(parsed_cell):
                            group["year"] = year_answer
                    group_answer = PredictorResultGroup(
                        [list(group.values())], schema=self.predictor.parent.find_child_schema("考核目标结构化拆分")
                    )
                    groups.append(group_answer)

            answer["考核目标结构化拆分"] = groups

    def supplement_base_condition(self, origin_element_result, sub_fake_cell, parsed_cell):
        if not P_NEED_ADD_BASE_CONDITION.nexts(origin_element_result.text):
            return None
        clean_text = clean_txt(parsed_cell.text)
        if not (matcher := P_ADD_BASE_CONDITION.nexts(clean_text)):
            return None
        if not (value := matcher.groupdict().get("addtional_base", None)):
            return None
        dst_chars = self.get_chars(
            parsed_cell.text, value, parsed_cell.raw_cell["chars"], matcher.span("addtional_base")
        )
        element_result = CellCharResult(parsed_cell.table.element, dst_chars, [parsed_cell])
        return element_result

    def fill_in_group(self, group, fake_cell, key_map, element, parsed_cell):
        clean_text = clean_txt(fake_cell.text)
        indicator_element_result = None
        indicator_method_element_result = None
        if matcher := HALF_GOAL_STRUCT_PATTERN.nexts(clean_text):
            for dst_key, column in key_map.items():
                value = matcher.groupdict().get(dst_key, None)
                if not value:
                    continue
                dst_chars = self.get_chars(fake_cell.text, value, fake_cell.chars, matcher.span(dst_key))
                element_result = CellCharResult(element, dst_chars, [parsed_cell])
                element_results = [element_result]
                if dst_key == "base_condition":
                    if addtional_element_result := self.supplement_base_condition(
                        element_result, fake_cell, parsed_cell
                    ):
                        element_results.insert(0, addtional_element_result)
                item = self.create_result(
                    element_results,
                    column=column,
                    schema=self.predictor.find_child_schema(column),
                )
                group[dst_key] = item
                if dst_key == "indicator":
                    indicator_element_result = element_result
                elif dst_key == "indicator_method":
                    indicator_method_element_result = element_result
        if "EVA" not in fake_cell.text and indicator_element_result:
            secondary_indicator_answer = self.create_result(
                [indicator_element_result],
                column="业绩条件_考核二级指标",
                schema=self.predictor.find_child_schema("业绩条件_考核二级指标"),
            )
            group["secondary_indicator"] = secondary_indicator_answer
        if not indicator_method_element_result and indicator_element_result:
            indicator_method_answer = self.create_result(
                [indicator_element_result],
                column="业绩条件_考核一级指标计算方法",
                schema=self.predictor.find_child_schema("业绩条件_考核一级指标计算方法"),
            )
            group["indicator_method"] = indicator_method_answer

    def find_year_answer(self, parsed_cell):
        if answer := self.find_year_from_left_cell(parsed_cell):
            return answer
        if answer := self.find_year_from_pattern(parsed_cell):
            return answer
        return None

    def find_year_from_pattern(self, parsed_cell):
        clean_text = clean_txt(parsed_cell.text)
        if matcher := YEAR_PATTERN.nexts(clean_text):
            if not (value := matcher.groupdict().get("year", None)):
                return None
            dst_chars = self.get_chars(parsed_cell.text, value, parsed_cell.raw_cell["chars"], matcher.span("year"))
            element_result = CellCharResult(parsed_cell.table.element, dst_chars, [parsed_cell])
            item = self.create_result(
                [element_result],
                column="业绩条件_考核年",
                schema=self.predictor.find_child_schema("业绩条件_考核年"),
            )
            return item
        return None

    def find_year_from_left_cell(self, parsed_cell):
        # 从答案单元格左侧单元格提取年份
        row_idx = parsed_cell.rowidx
        col_idx = parsed_cell.colidx - 1
        rows = parsed_cell.table.rows
        if not (row_idx < len(rows) and col_idx < len(rows[col_idx])):
            return None
        left_cell = rows[row_idx][col_idx]
        if not P_LEFT_CELL_YEAR.nexts(left_cell.text):
            return None
        element_result = TableCellsResult(parsed_cell.table.element, [left_cell])
        item = self.create_result(
            [element_result],
            column="业绩条件_考核年",
            schema=self.predictor.find_child_schema("业绩条件_考核年"),
        )
        return item

    def find_base_year_answer(self, parsed_cell, fake_cell):
        fake_cell_index = parsed_cell.text.index(fake_cell.text)
        clean_text = clean_txt(parsed_cell.text)
        if not (matcher := BASE_YEAR_PATTERN.nexts(clean_text)):
            return
        if not (value := matcher.groupdict().get("base_year", None)):
            return
        if matcher.span()[0] > fake_cell_index:
            # 防止前半句提取到后半句的baseyear
            return
        dst_chars = self.get_chars(parsed_cell.text, value, parsed_cell.raw_cell["chars"], matcher.span("base_year"))
        element_result = CellCharResult(parsed_cell.table.element, dst_chars, [parsed_cell])
        item = self.create_result(
            [element_result],
            column="业绩条件_考核基准年",
            schema=self.predictor.find_child_schema("业绩条件_考核基准年"),
        )
        return item

    @staticmethod
    def split_cell(cell: FakeCell | ParsedTableCell, pattern: PatternCollection):
        segments = []
        cell_text = cell.text
        start_index = 0
        chars = cell.chars if isinstance(cell, FakeCell) else cell.raw_cell["chars"]

        for match in pattern.finditer(cell_text):
            end_index = match.start()
            segment = cell_text[start_index:end_index]
            fake_cell = FakeCell(segment, chars[start_index:end_index])
            segments.append(fake_cell)
            start_index = end_index + 1

        # Add the last segment
        fake_cell = FakeCell(cell_text[start_index:], chars[start_index:])
        segments.append(fake_cell)
        return segments

    def supplement_time_struct(self, answers):
        key_map = {
            "type": "时间_计算起始类型",
            "start": "时间_起始月份",
            "end": "时间_结束月份",
        }
        for answer in answers:
            time_answer = answer.get("时间")
            if not time_answer:
                continue
            time_answer = deepcopy(time_answer[0])
            period_answer_result = time_answer.element_results[0]
            parsed_cell = period_answer_result.parsed_cells[0]
            clean_text = clean_txt(parsed_cell.text)
            matcher = TIME_STRUCT_PATTERN.nexts(clean_text)
            if not matcher:
                continue
            group = []
            for dst_key, column in key_map.items():
                value = matcher.groupdict().get(dst_key, None)
                if not value:
                    continue
                dst_chars = self.get_chars(
                    parsed_cell.text, value, parsed_cell.raw_cell["chars"], matcher.span(dst_key)
                )
                element_result = CellCharResult(period_answer_result.element, dst_chars, [parsed_cell])
                item = self.create_result(
                    [element_result],
                    column=column,
                    schema=self.predictor.find_child_schema(column),
                )
                group.append(item)
            if not group:
                continue
            group_answer = PredictorResultGroup(
                [group], schema=self.predictor.parent.find_child_schema("时间结构化拆分")
            )
            answer["时间结构化拆分"] = [group_answer]

    def find_incentive_object_answer(self, answer):
        return answer

    def fix_incentive_answer(self, answer):
        incentive_answers = answer.get(INCENTIVE_OBJECT_COLUMN, [])
        if not incentive_answers:
            return
        incentive_answer = incentive_answers[0]
        incentive_answer_result = incentive_answer.element_results[0]
        if isinstance(incentive_answer_result, CharResult):
            return
        parsed_cell = incentive_answer_result.parsed_cells[0]
        element = incentive_answer_result.element
        table = parse_table(element, tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight)

        if len(incentive_answers) == 1:
            # 查看答案单元格的表头
            for col_header in parsed_cell.col_header_cells:
                if INCENTIVE_PATTERN.nexts(clean_txt(col_header.text)):
                    answer[INCENTIVE_OBJECT_COLUMN] = [
                        self.create_result([TableCellsResult(element, [col_header])], column=INCENTIVE_OBJECT_COLUMN)
                    ]
                    return
        elif len(incentive_answers) > 1:
            # 提取了整行的数据当做 激励对象类型的答案， 从表格的第一行获取
            # 从答案所在的单元格开始从下往上遍历
            for row in table.rows[: parsed_cell.rowidx][::-1]:
                if len({cell.text for cell in row}) == 1 and row[0].text == parsed_cell.subtitle:
                    answer[INCENTIVE_OBJECT_COLUMN] = [
                        self.create_result([TableCellsResult(element, row[:1])], column=INCENTIVE_OBJECT_COLUMN)
                    ]
                    return

    def find_grant_answer(self, answer):
        ret = []
        period_answer = answer.get(PERIOD_COLUMN, [])
        if not period_answer:
            return ret
        period_answer_result = period_answer[0].element_results[0]
        # 从单元格中解析授予类型
        for parsed_cell in period_answer_result.parsed_cells:
            clean_text = clean_txt(period_answer_result.text)
            matcher = GRANT_TYPE_PATTERN.nexts(clean_text)
            if not matcher:
                continue
            predict_answer = self.gen_answer_result(period_answer_result, parsed_cell, matcher, GRANT_TYPE_COLUMN)
            if predict_answer:
                ret.append(predict_answer)
        if ret:
            return ret
        # 从表格上方的段落中解析授予类型
        predict_answer = self.find_tool_from_table_above(period_answer_result, GRANT_TYPE_PATTERN, GRANT_TYPE_COLUMN)
        if predict_answer:
            return [predict_answer]
        # 从表格所在的章节中解析授予类型
        predict_answer = self.find_tool_from_syllabus(period_answer_result, GRANT_TYPE_PATTERN, GRANT_TYPE_COLUMN)
        if predict_answer:
            return [predict_answer]
        # 从表格的章节标题中解析授予类型
        predict_answer = self.find_tool_from_syllabus_title(period_answer_result, GRANT_TYPE_PATTERN, GRANT_TYPE_COLUMN)
        if predict_answer:
            return [predict_answer]
        return ret

    def find_tool_answer(self, answer):
        ret = []
        period_answer = answer.get(PERIOD_COLUMN, [])
        if not period_answer:
            return ret
        period_answer = period_answer[0]
        period_answer_result = period_answer.element_results[0]
        # 从单元格中解析工具类型
        for parsed_cell in period_answer_result.parsed_cells:
            clean_text = clean_txt(period_answer_result.text)
            matcher = TOOL_TYPE_PATTERN.nexts(clean_text)
            if not matcher:
                continue
            predict_answer = self.gen_answer_result(period_answer_result, parsed_cell, matcher, TOOL_TYPE_COLUMN)
            ret.append(predict_answer)
        if ret:
            return ret
        # 从表格上方的段落中解析工具类型
        predict_answer = self.find_tool_from_table_above(
            period_answer_result, ABOVE_TOOL_TYPE_PATTERN, TOOL_TYPE_COLUMN
        )
        if predict_answer:
            return [predict_answer]
        # 从表格所在的章节中解析工具类型
        predict_answer = self.find_tool_from_syllabus(period_answer_result, ABOVE_TOOL_TYPE_PATTERN, TOOL_TYPE_COLUMN)
        if predict_answer:
            return [predict_answer]
        # 从表格的章节标题中解析工具类型
        predict_answer = self.find_tool_from_syllabus_title(
            period_answer_result, ABOVE_TOOL_TYPE_PATTERN, TOOL_TYPE_COLUMN
        )
        if predict_answer:
            return [predict_answer]
        return ret

    def fix_tool_answer(self, answer):
        tool_answer = answer.get(TOOL_TYPE_COLUMN, [])
        if not tool_answer:
            return
        tool_answer = tool_answer[0]
        tool_answer_result = tool_answer.element_results[0]
        if not isinstance(tool_answer_result, TableCellsResult):
            # 不是从表格中提取的说明是table_row from_title 提取到的 不需要修正
            return
        parsed_cell = tool_answer_result.parsed_cells[0]
        clean_text = clean_txt(parsed_cell.text)
        matcher = TOOL_TYPE_PATTERN.nexts(clean_text)
        if matcher:
            # 从单元格中解析工具类型
            predict_answer = self.gen_answer_result(tool_answer_result, parsed_cell, matcher, TOOL_TYPE_COLUMN)
            if predict_answer:
                answer[TOOL_TYPE_COLUMN] = [predict_answer]
                return
        else:
            # 从表格上方的文档中解析工具类型
            predict_answer = self.find_tool_from_table_above(
                tool_answer_result, ABOVE_TOOL_TYPE_PATTERN, TOOL_TYPE_COLUMN
            )
            if predict_answer:
                answer[TOOL_TYPE_COLUMN] = [predict_answer]
                return
            # 从表格所在的章节中解析工具类型
            predict_answer = self.find_tool_from_syllabus(tool_answer_result, ABOVE_TOOL_TYPE_PATTERN, TOOL_TYPE_COLUMN)
            if predict_answer:
                answer[TOOL_TYPE_COLUMN] = [predict_answer]
                return
            # 从表格的章节标题中解析工具类型
            predict_answer = self.find_tool_from_syllabus_title(
                tool_answer_result, ABOVE_TOOL_TYPE_PATTERN, TOOL_TYPE_COLUMN
            )
            if predict_answer:
                answer[TOOL_TYPE_COLUMN] = [predict_answer]
                return
        answer[TOOL_TYPE_COLUMN] = []

    def find_tool_from_syllabus(self, tool_answer, pattern, column):
        element = tool_answer.element
        syllabuses = self.pdfinsight.syllabus_reader.find_by_elt_index(element["index"])
        if not syllabuses:
            return None
        root_syllabus = syllabuses[0]
        start, end = root_syllabus["range"]
        for index in range(element["index"] - 1, start - 1, -1):
            ele_type, candidate_element = self.pdfinsight.find_element_by_index(index)
            if not candidate_element:
                continue
            if ele_type == "TABLE":
                break
            clean_text = clean_txt(candidate_element.get("text", ""))
            matcher = pattern.nexts(clean_text)
            if not matcher:
                continue
            dst_chars = self.get_dst_chars_from_matcher(matcher, candidate_element)
            if not dst_chars:
                continue
            predict_answer = self.create_result([CharResult(candidate_element, dst_chars)], column=column)
            return predict_answer
        return None

    def find_tool_from_syllabus_title(self, tool_answer, pattern, column):
        element = tool_answer.element
        syllabuses = self.pdfinsight.syllabus_reader.find_by_elt_index(element["index"])
        candidate_elements = []
        for syllabus in syllabuses[::-1]:
            _, candidate_element = self.pdfinsight.find_element_by_index(syllabus["element"])
            if not candidate_element:
                continue
            candidate_elements.append(candidate_element)
        for candidate_element in candidate_elements:
            clean_text = clean_txt(candidate_element.get("text", ""))
            matcher = pattern.nexts(clean_text)
            if not matcher:
                continue
            dst_chars = self.get_dst_chars_from_matcher(matcher, candidate_element)
            if not dst_chars:
                return None
            predict_answer = self.create_result([CharResult(candidate_element, dst_chars)], column=column)
            return predict_answer
        return None

    def find_tool_from_table_above(self, tool_answer, pattern, column):
        element = tool_answer.element
        table = parse_table(element, tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight)
        for candidate_element in table.elements_above:
            if ElementClassifier.is_table(candidate_element):
                break
            clean_text = clean_txt(candidate_element.get("text", ""))
            matcher = pattern.nexts(clean_text)
            if not matcher:
                continue
            dst_chars = self.get_dst_chars_from_matcher(matcher, candidate_element)
            if not dst_chars:
                return None
            predict_answer = self.create_result([CharResult(candidate_element, dst_chars)], column=column)
            return predict_answer
        return None

    def fix_period_answer(self, answer):
        period_answer = answer.get(PERIOD_COLUMN, [])
        if not period_answer:
            return
        period_answer = period_answer[0]
        period_answer_result = period_answer.element_results[0]
        if not isinstance(period_answer_result, (TableCellsResult, CellCharResult)):
            return
        parsed_cell = period_answer_result.parsed_cells[0]
        clean_text = clean_txt(period_answer.text)
        if matcher := PERIOD_COMMON_PATTERN.nexts(clean_text):
            if predict_answer := self.gen_answer_result(period_answer_result, parsed_cell, matcher, PERIOD_COLUMN):
                answer[PERIOD_COLUMN] = [predict_answer]
                return

        clean_text = clean_txt(parsed_cell.text)
        if matcher := PERIOD_COMMON_PATTERN.nexts(clean_text):
            fake_element = {"text": parsed_cell.text, "chars": parsed_cell.raw_cell["chars"]}
            dst_chars = self.get_dst_chars_from_matcher(matcher, fake_element)
            if not dst_chars:
                return
            predict_answer = self.create_result(
                [CellCharResult(period_answer_result.element, dst_chars, [parsed_cell])], column=PERIOD_COLUMN
            )
            answer[PERIOD_COLUMN] = [predict_answer]
            return

    def supplement_answers(self, answers):
        answers = self.supplement_answers_by_period(answers)
        answers = self.supplement_answers_by_grant(answers)
        return answers

    def supplement_answers_by_grant(self, answers):
        # http://100.64.0.3:22100/#/project/remark/9992?treeId=68&fileId=1098&schemaId=61&projectId=50&fileName=300482%20%E4%B8%87%E5%AD%9A%E7%94%9F%E7%89%A9%202020-12-21%20%202020%E5%B9%B4%E9%99%90%E5%88%B6%E6%80%A7%E8%82%A1%E7%A5%A8%E6%BF%80%E5%8A%B1%E8%AE%A1%E5%88%92%EF%BC%88%E8%8D%89%E6%A1%88%EF%BC%89.pdf
        supplementary_answers = []
        for answer in answers:
            grant_answer = answer.get(GRANT_TYPE_COLUMN, [])
            if not grant_answer:
                continue
            grant_answer = grant_answer[0].element_results[0]
            if not isinstance(grant_answer, CharResult):
                continue
            element = grant_answer.element
            clean_text = clean_txt(element["text"])
            if NEED_SPLIT_GRANT_PATTERN.nexts(clean_text):
                splited_answer = deepcopy(answer)
                splited_answer[GRANT_TYPE_COLUMN] = []
                supplementary_answers.append(splited_answer)
        answers.extend(supplementary_answers)
        return answers

    def supplement_answers_by_period(self, answers):
        ret = []
        for answer in answers:
            period_answer = answer.get(PERIOD_COLUMN, [])
            if not period_answer:
                continue
            if not NEED_SPLIT_PATTERN.nexts(period_answer[0].text):
                ret.append(answer)
                continue
            period_answer = period_answer[0]
            period_answer_result = period_answer.element_results[0]
            # todo AttributeError: 'CharResult' object has no attribute 'cells'
            parsed_cell = period_answer_result.parsed_cells[0]
            clean_text = clean_txt(parsed_cell.text)
            if first_matcher := FIRST_HALF_PATTERN.nexts(clean_text):
                if dst_chars := self.get_dst_chars_from_matcher(first_matcher, parsed_cell.raw_cell):
                    first_answer = self.create_result(
                        [CellCharResult(period_answer_result.element, dst_chars, [parsed_cell])], column=PERIOD_COLUMN
                    )
                    splited_answer = deepcopy(answer)
                    splited_answer[PERIOD_COLUMN] = [first_answer]
                    splited_answer[GRANT_TYPE_COLUMN] = []
                    splited_answer[TOOL_TYPE_COLUMN] = []
                    ret.append(splited_answer)

            if second_matcher := SECOND_HALF_PATTERN.nexts(clean_text):
                if dst_chars := self.get_dst_chars_from_matcher(second_matcher, parsed_cell.raw_cell):
                    second_answer = self.create_result(
                        [CellCharResult(period_answer_result.element, dst_chars, [parsed_cell])], column=PERIOD_COLUMN
                    )
                    splited_answer = deepcopy(answer)
                    splited_answer[PERIOD_COLUMN] = [second_answer]
                    splited_answer[GRANT_TYPE_COLUMN] = []
                    splited_answer[TOOL_TYPE_COLUMN] = []
                    ret.append(splited_answer)
        return ret

    def filter_answers(self, answers):
        ret = []
        for answer in answers:
            if "期间" not in answer:
                continue
            # if self.schema.parent.name == '安排表' and '比例' not in answer:
            #     continue
            ret.append(answer)

        # 如果授予类型和期间答案完全一样 都是同一个单元格内的相同的文本 那么丢弃授予类型的答案
        for answer in ret:
            grant_type_answer = answer.get(GRANT_TYPE_COLUMN, [])
            period_answer = answer[PERIOD_COLUMN]
            if not grant_type_answer:
                continue
            grant_type_text = grant_type_answer[0].text
            period_text = period_answer[0].text
            if grant_type_text == period_text:
                answer[GRANT_TYPE_COLUMN] = []
        return ret

    def gen_answer_result(self, parent_answer_result: AnswerResult, parsed_cell: ParsedTableCell, matcher, column: str):
        fake_element = {
            "text": parent_answer_result.text,
            "chars": parent_answer_result.chars
            if hasattr(parent_answer_result, "chars")
            else parsed_cell.raw_cell["chars"],
        }
        dst_chars = self.get_dst_chars_from_matcher(matcher, fake_element)
        if not dst_chars:
            return
        predict_answer = self.create_result(
            [CellCharResult(parent_answer_result.element, dst_chars, [parsed_cell])], column=column
        )
        return predict_answer
