"""前五客户"""

from copy import deepcopy
from itertools import zip_longest

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt, index_in_space_string
from remarkable.pdfinsight.parser import cell_data_patterns, parse_table
from remarkable.predictor.models.table_row import TableRow
from remarkable.predictor.schema_answer import CharResult, TableCellsResult

REPORT_PERIOD_PATTERN = [r"(?P<dst>\d{2,4}\s?年?\s?(\d{1,2}\s?月\s?\d{1,2}\s?日|\d[--]\d\s?月|度)?)"]


class ClassificationHandler:
    def __init__(self, report_results):
        self.report_results = report_results

    def extract_report_result(self, answer_results):
        raise NotImplementedError


class TitleClassification(ClassificationHandler):
    def extract_report_result(self, answer_results):
        ret = []
        for answer_result in answer_results:
            top_five_name_answer = answer_result.get("名称", [])
            if not top_five_name_answer:
                continue
            element_result = top_five_name_answer[0].element_results[0]
            element_index = element_result.element["index"]
            report_answer = deepcopy(self.report_results.get(element_index))
            if report_answer:
                answer_result["报告期"] = [report_answer]
                ret.append(answer_result)
        return ret


class TableClassification(ClassificationHandler):
    def __init__(self, report_results, table=None):
        super(TableClassification, self).__init__(report_results)
        self.table = table

    def extract_report_result(self, answer_results):
        ret = []
        for answer_result in answer_results:
            top_five_name_answers = answer_result.get("名称", [])
            if not top_five_name_answers:
                continue
            top_five_name_answers = self.filter_name_answer(top_five_name_answers)
            if not top_five_name_answers:
                continue
            element_result = top_five_name_answers[0].element_results[0]
            parsed_cell = element_result.parsed_cells[0]
            if len(self.table.regions) == 1 and self.table.row_tags.count("subtitle") == 3:
                answer_row_idx = parsed_cell.rowidx
                report_result_key = self.get_report_key(answer_row_idx)
                if report_result_key is None:
                    continue
            else:
                report_result_key = parsed_cell.region.num
            report_answer = deepcopy(self.report_results.get(report_result_key))
            if report_answer:
                answer_result["报告期"] = [report_answer]
                answer_result["名称"] = top_five_name_answers
                ret.append(answer_result)
        return ret

    @staticmethod
    def filter_name_answer(top_five_name_answers):
        ret = []
        for top_five_name_answer in top_five_name_answers:
            table_cell_result = top_five_name_answer.element_results[0]
            if next(cell_data_patterns.search(table_cell_result.text), None):
                continue
            ret.append(top_five_name_answer)
        return ret

    def get_report_key(self, answer_row_idx):
        keys = list(self.report_results.keys())
        for left, right in zip_longest(keys, keys[1:], fillvalue=len(self.table.rows)):
            if left < answer_row_idx < right:
                return left
        return None


class TopFiveCustomers(TableRow):
    base_all_elements = True

    def predict_schema_answer(self, elements):
        elements = self.filter_elements_by_title(elements)
        ret = []
        for element in elements:
            classification_handler = self.gen_classification_handler(element)
            answer_results = super(TopFiveCustomers, self).predict_schema_answer([element])
            if classification_handler.report_results:
                ret.extend(classification_handler.extract_report_result(answer_results))
            else:
                ret.extend(self.filter_answer_results(answer_results))
        if not ret:
            ret = super(TopFiveCustomers, self).predict_schema_answer(elements)
        return ret

    def gen_classification_handler(self, element):
        # 处理时间在表格上方的段落或者表头或者章节标题里
        classification_hander = self.gen_classification_from_above(element)
        if not classification_hander:
            # 处理多region 时间在region最上面一行
            classification_hander = self.gen_classification_from_region(element)
        return classification_hander

    def gen_classification_from_above(self, element):
        report_results = {}
        above_elements = self.get_above_elements(element)
        title_element = self.get_title_element(element)
        for above_element in above_elements + [title_element]:
            above_element_text = above_element["text"]
            match = PatternCollection(REPORT_PERIOD_PATTERN).nexts(clean_txt(above_element_text))
            if match:
                c_start, c_end = match.span("dst")
                sp_start, sp_end = index_in_space_string(above_element_text, (c_start, c_end))
                dst_chars = above_element.get("chars")[sp_start:sp_end]
                report_result = self.create_result([CharResult(above_element, dst_chars)], column=self.schema.name)
                report_results.update({element["index"]: report_result})
                return TitleClassification(report_results)
        return None

    def gen_classification_from_region(self, element):
        report_results = {}
        table = parse_table(element, tabletype=TableType.ROW.value, pdfinsight_reader=self.pdfinsight)
        if len(table.regions) == 1 and table.row_tags.count("subtitle") == 3:
            for idx, tag in enumerate(table.row_tags):
                if tag == "subtitle":
                    subtitle_row = table.rows[idx]
                    if all(PatternCollection(REPORT_PERIOD_PATTERN).search(cell.text) for cell in subtitle_row):
                        report_result = self.create_result(
                            [TableCellsResult(element, subtitle_row[:1])], column="报告期"
                        )
                        report_results.update(
                            {
                                idx: report_result,
                            }
                        )
            return TableClassification(report_results, table)
        for region in table.regions:
            if region.row_tags[0] == "subtitle":
                first_row = region.rows[0]
                if all(PatternCollection(REPORT_PERIOD_PATTERN).search(cell.text) for cell in first_row):
                    report_result = self.create_result([TableCellsResult(element, first_row[:1])], column="报告期")
                    report_results.update(
                        {
                            region.num: report_result,
                        }
                    )
        return TableClassification(report_results, table)

    def filter_elements_by_title(self, elements):
        title_neglect_patterns = self.config.get("title_neglect_patterns", [])
        title_patterns = self.config.get("title_patterns", [])
        ret = []
        elements.sort(key=lambda x: x["index"])
        for ele in elements:
            table = parse_table(ele, tabletype=TableType.ROW.value, pdfinsight_reader=self.pdfinsight)
            element_title = ele.get("title", "") or ""
            if not element_title and table.title:
                element_title = table.title.text
            if not element_title:
                ret.append(ele)
                continue
            if not PatternCollection(title_neglect_patterns).nexts(element_title) and PatternCollection(
                title_patterns
            ).nexts(element_title):
                ret.append(ele)
        return ret

    @staticmethod
    def filter_answer_results(answer_results):
        ret = []
        for answer_result in answer_results:
            top_five_name_answer = answer_result.get("名称", [])
            if not top_five_name_answer:
                continue
            report_period_answer = answer_result.get("报告期", [])
            for item in report_period_answer:
                match = PatternCollection(REPORT_PERIOD_PATTERN).nexts(item.text)
                if match:
                    answer_result.update({"报告期": [item]})
                    ret.append(answer_result)
                    break
        return ret
