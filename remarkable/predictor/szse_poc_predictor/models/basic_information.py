from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.pdfinsight.parser import parse_table
from remarkable.predictor.common_pattern import DATE_PATTERN
from remarkable.predictor.models.syllabus_based import SyllabusBased
from remarkable.predictor.models.table_kv import KeyValueTable
from remarkable.predictor.schema_answer import CharResult

PROVINCE = PatternCollection([r"(?P<dst>(.*?省|(上海|北京|天津|重庆)市))"])
CITY_COUNTY = PatternCollection([r"(.*?省|(上海|北京|天津|重庆)市)?(?P<dst>.*)"])
INVALID_TIME_PATTERN = PatternCollection([r"股份(有限)?公司[成设建]立(时间|日期)"])
TABLE_TIME_PATTERN = PatternCollection([r"(?P<dst>(.*?))，?股份(有限)?公司[成设建]立"])
TABLE_TIME_PATTERN2 = PatternCollection([rf"{DATE_PATTERN}（?(有限公司)?）?"])


class BasicInformation(KeyValueTable):
    def __init__(self, options, schema, predictor):
        super(BasicInformation, self).__init__(options, schema, predictor)

    def predict_schema_answer(self, elements):
        answer_results = super(BasicInformation, self).predict_schema_answer(elements)
        self.filter_address(answer_results)
        self.extract_time(answer_results)
        return answer_results

    def extract_time(self, answer_results):
        for answer_result in answer_results:
            col = "公司设立时间"
            answers = answer_result.get(col, [])
            if answers:
                answers = self.get_time_answer(answers, col)
                answer_result[col] = answers

    def get_time_answer(self, time_answers, col):
        ret = []
        for answer in time_answers:
            element_result = answer.element_results[0]
            element = element_result.element
            if element["class"] == "TABLE":
                parsed_cell = element_result.parsed_cells[0]
                element_text = parsed_cell.text
                matcher_obj = parsed_cell.raw_cell
            else:
                matcher_obj = element_result.element
                element_text = element["text"]
            element = answer.relative_elements[0]
            matcher = TABLE_TIME_PATTERN.nexts(clean_txt(element_text))
            if matcher:
                time_dst_chars = self.get_dst_chars_from_matcher(matcher, matcher_obj)
                if not time_dst_chars:
                    continue
                ret.append(self.create_result([CharResult(element, time_dst_chars)], column=col))
            else:
                ret.append(answer)
        return ret

    def filter_address(self, answer_results):
        for answer_result in answer_results:
            col = "注册地（省市或境外）"
            province = answer_result.get(col, [])
            if province:
                province = self.get_industry_answer(col, province, PROVINCE)
                answer_result[col] = province

            col = "注册地（市区县）"
            city_county = answer_result.get(col, [])
            if city_county:
                city_county = self.get_industry_answer(col, city_county, CITY_COUNTY)
                answer_result[col] = city_county

    def get_industry_answer(self, col, industry_segmentation, pattern):
        ret = []
        for answer in industry_segmentation:
            element_result = answer.element_results[0]
            element = element_result.element
            if element["class"] == "TABLE":
                parsed_cell = element_result.parsed_cells[0]
                element_text = parsed_cell.text
                matcher_obj = parsed_cell.raw_cell
            else:
                matcher_obj = element_result.element
                element_text = element["text"]
            element = answer.relative_elements[0]
            matcher = pattern.nexts(clean_txt(element_text))
            if matcher:
                name_dst_chars = self.get_dst_chars_from_matcher(matcher, matcher_obj)
                if not name_dst_chars:
                    continue
                ret.append(self.create_result([CharResult(element, name_dst_chars)], column=col))
        return ret


class ChapterFiveBasicInformation(SyllabusBased, BasicInformation):
    def predict_schema_answer(self, elements):
        answer_results = super(ChapterFiveBasicInformation, self).predict_schema_answer(elements)
        self.filter_address(answer_results)
        self.filter_similar_time(answer_results)
        return answer_results

    def filter_similar_time(self, answer_results):
        for answer_result in answer_results:
            col = "公司设立时间"
            time_answers = answer_result.get(col, [])
            if time_answers:
                time_answers = self.get_time_answer(time_answers, col)
                answer_result[col] = time_answers

    def get_time_answer(self, time_answers, col):
        ret = []
        for answer in time_answers:
            element = answer.relative_elements[0]
            if element["class"] == "PARAGRAPH":
                matcher = INVALID_TIME_PATTERN.nexts(clean_txt(element["text"]))
                if not matcher:
                    ret.append(answer)
            elif element["class"] == "TABLE":
                element_result = answer.element_results[0]
                parsed_cell = element_result.parsed_cells[0]
                table = parse_table(element, tabletype=TableType.KV.value, pdfinsight_reader=self.pdfinsight)
                ret.extend(self.filter_invalid_time_answer(table, parsed_cell, element, answer, col))
        return ret

    def filter_invalid_time_answer(self, table, parsed_cell, element, answer, col):
        ret = []
        row_header_cell = table.rows[parsed_cell.rowidx][0]
        matcher = INVALID_TIME_PATTERN.nexts(clean_txt(row_header_cell.text))
        if not matcher:
            times = list(PatternCollection(DATE_PATTERN).finditer(clean_txt(parsed_cell.text)))
            if len(times) > 1:
                matcher = TABLE_TIME_PATTERN2.nexts(clean_txt(parsed_cell.text))
                if matcher:
                    dst_chars = self.get_dst_chars_from_matcher(matcher, parsed_cell.raw_cell)
                    if dst_chars:
                        ret.append(self.create_result([CharResult(element, dst_chars)], column=col))
            else:
                ret.append(answer)
        return ret
