import re
from collections import Counter, defaultdict

from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.common_pattern import DATE_PATTERN
from remarkable.predictor.models.syllabus_based import SyllabusBased
from remarkable.predictor.mold_schema import SchemaItem
from remarkable.predictor.schema_answer import CharResult

SYLLABUS_PATTERN = [re.compile(r"股本[与和及]股东变化情况|历史沿革情况|有限公司的设立情况")]

SUB_TITLE_PATTERN = PatternCollection([r"^\d[、.]\d{4}\s*年"])

INVALID_FEATURE = PatternCollection([r"年\d+月"])

LAST_INCREASE_DATE = PatternCollection(
    [
        rf"{DATE_PATTERN}.*?(获得|向).*?(颁发|换发)",
        rf"{DATE_PATTERN}.*?完成工商变更登记手续",
    ]
)

INCREASE_AMOUNT = PatternCollection(
    [
        r"公司已收到.*?(新增注册资本|出资)(（股本）)?(?P<dst>.*?)万元",
        r"同意公司新增注册资本(（股本）)?(?P<dst>.*?)万元",
        r"新增注册资本(（股本）)?(?P<dst>.*?)万元",
    ]
)
BEFORE_INCREASE_AMOUNT = PatternCollection(
    [
        r"注册资本由(原来的)?(?P<dst>.*?)万元(人民币)?增至",
    ]
)
AFTER_INCREASE_AMOUNT = PatternCollection(
    [
        r"注册资本由(原来的)?.*?增至(?P<dst>.*?)万元",
        r"注册资本将变更为人民币(?P<dst>.*?)万元",
        r"注册资本增加至(?P<dst>.*?)万元",
    ]
)

INVALID_ELEMENT = PatternCollection([r"股[权份]转让|代扣代缴|进场交易|资本公积转增股本"])

INVALID_ELEMENT_CAPITAL_REPORT = PatternCollection([r"出具了.*?验资报告"])

VALID_ELEMENT = PatternCollection([r"增资"])


SUB_SCHEMAS_PATTERN = {
    "最近一次增资日期": LAST_INCREASE_DATE,
    "最近一次增资金额": INCREASE_AMOUNT,
    "最近一次增资前金额": BEFORE_INCREASE_AMOUNT,
    "最近一次增资后金额": AFTER_INCREASE_AMOUNT,
}


class LastCapitalIncrease(SyllabusBased):
    def __init__(self, options: dict, schema: SchemaItem, predictor):
        super().__init__(options, schema, predictor=predictor)

    def load_model_data(self):
        self.model_data = self.predictor.model_data.get(self.name, {})
        self.para_model.model_data = self.model_data["paragraph"]
        self.table_model.model_data = self.model_data["table"]
        most_counter = self.get_model_data(column="syllabus")[self.schema.name].most_common()[0][1]
        for feature in self.get_config("inject_syllabus_features", default=[]):
            self.get_model_data("syllabus").get(self.schema.name, Counter()).update({feature: most_counter + 1})
        fixed_model = Counter()
        syllabus_model = self.get_model_data(column="syllabus")[self.schema.name]
        for feature, count in syllabus_model.items():
            feature_list = feature.split("|")
            if INVALID_FEATURE.nexts(clean_txt(feature_list[-1])):
                fixed_feature = "|".join(feature_list[:-1])
                fixed_model.update({fixed_feature: count})
            else:
                fixed_model.update({feature: count})
        self.model_data["syllabus"]["最近一次增资日期"] = fixed_model

    def predict_schema_answer(self, elements):
        answer_results = super().predict_schema_answer(elements)
        answer_results = self.reorganize_preset_answer(answer_results)
        exist_answer_schemas = {key for answer_result in answer_results for key in answer_result.keys()}
        need_preset_schema = set(SUB_SCHEMAS_PATTERN.keys()).difference(exist_answer_schemas)
        if not need_preset_schema:
            return answer_results
        sections = []
        syllabus_model_data = self.get_model_data(column="syllabus")[self.schema.name]
        aim_syllabuses = self.get_aim_syllabus(syllabus_model_data)
        for syllabus in aim_syllabuses:
            sections.extend(self.parse_sub_sections(syllabus, self.pdfinsight.syllabus_dict))
        if not sections:
            for element in elements:
                if element["class"] == "PARAGRAPH":
                    answer_results.extend(self.para_model.predict([element]))
                elif element["class"] == "TABLE":
                    answer_results.extend(self.table_model.predict([element]))
            return answer_results
        for col in need_preset_schema:
            for start, end in sections[::-1]:
                section_answers = self.extract_from_sub_section(start, end, col)
                if section_answers:
                    answer_results.extend(section_answers)
                    break
        return answer_results

    def reorganize_preset_answer(self, answer_results):
        answers = defaultdict(list)
        for answer_result in answer_results:
            for key, value in answer_result.items():
                answers[key].append(value)

        for key, values in answers.items():
            values.sort(key=lambda x: x[0].relative_elements[0]["index"], reverse=True)
            for value in values:
                if self.is_invalid(value):
                    continue
                answers[key] = value
                break
            else:
                answers[key] = values[0]

        return [answers]

    def is_invalid(self, answer):
        ret = False
        element = answer[0].relative_elements[0]
        syllabus = self.pdfinsight.syllabus_dict[element["syllabus"]]
        syllabus_chain = self.pdfinsight_syllabus.full_syll_path(syllabus)
        syllabus_chain_text = "|".join([item["title"] for item in syllabus_chain])
        if element["class"] == "TABLE":
            return INVALID_ELEMENT.nexts(clean_txt(syllabus_chain_text))
        element_text = element["text"]
        if element.get("page_merged_paragraph"):
            element_text = element["page_merged_paragraph"]["text"]
        # 段落或者标题中出现 `增资` 相关描述的 为有效元素块
        if VALID_ELEMENT.nexts(clean_txt(element_text)):
            return False
        if VALID_ELEMENT.nexts(clean_txt(syllabus["title"])):
            return INVALID_ELEMENT_CAPITAL_REPORT.nexts(clean_txt(element_text))
        if self.is_invalid_element(element, element_text, syllabus):
            return True
        return ret

    def is_invalid_element(self, element, element_text, syllabus):
        # 段落或者标题中出现 `股权转让` 相关描述的 为无效元素块
        if INVALID_ELEMENT.nexts(clean_txt(element_text)):
            return True
        if INVALID_ELEMENT.nexts(clean_txt(syllabus["title"])):
            return True
        above_elements = self.get_above_elements(element, special_pattern=SUB_TITLE_PATTERN)
        above_element_texts = "|".join([item["text"] for item in above_elements])
        if INVALID_ELEMENT.nexts(clean_txt(above_element_texts)):
            return True
        return False

    def extract_from_sub_section(self, start, end, col):
        answers = []
        pattern = SUB_SCHEMAS_PATTERN[col]
        for i in range(start, end):
            ele_type, element = self.pdfinsight.find_element_by_index(i)
            if ele_type != "PARAGRAPH":
                continue
            matcher = pattern.nexts(clean_txt(element["text"]))
            if matcher:
                name_dst_chars = self.get_dst_chars_from_matcher(matcher, element)
                if not name_dst_chars:
                    continue
                answers.append(self.create_result([CharResult(element, name_dst_chars)], column=col))
                break
        return answers

    def parse_sub_sections(self, syllabus, syllabus_dict):
        sections = []
        syllabus_start, syllabus_end = syllabus["range"]
        if syllabus["children"]:
            # 每节是一个 section
            for sub_syllabus in (syllabus_dict[c] for c in syllabus["children"]):
                sections.append(sub_syllabus["range"])
            return sections
        sub_titles = self.identify_sub_titles(syllabus)
        if sub_titles:
            # 每个小标题 是一个 section
            for start, end in zip([syllabus_start] + sub_titles, sub_titles + [syllabus_end]):
                sections.append([start, end])
            return sections
        # 每段是一个 section
        if syllabus_end - syllabus_start < 50:
            for i in range(syllabus_start, syllabus_end):
                sections.append((i, i + 1))
        return sections

    def identify_sub_titles(self, syllabus):
        ret = []
        start, end = syllabus["range"]
        for index in range(start, end):
            ele_type, element = self.pdfinsight.find_element_by_index(index)
            if ele_type != "PARAGRAPH":
                continue
            if SUB_TITLE_PATTERN.nexts(element["text"]):
                ret.append(index)
        return ret
