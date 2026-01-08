from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.common_pattern import DATE_PATTERN
from remarkable.predictor.eltype import ElementType
from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import CharResult

RISK_PATTERNS = [r"(?P<dst>\d{1,2}\.\d{1,2}[%％])"]
GROSS_PROFIT_MARGIN_PATTERN = PatternCollection([r"毛利率"])
SPECIAL_REPORT_PATTERNS = PatternCollection(
    [
        r"(?P<dst>报告期内?各?期?)",
        r"(?P<dst>\d{4}-\d{4}年)",
    ]
)

invalid_patterns = PatternCollection(
    [
        r"主营业务毛利率",
    ]
)


class ComplexGrossMargin(BaseModel):
    target_element = ElementType.PARAGRAPH
    filter_elements_by_target = True

    def __init__(self, options, schema, predictor):
        super(ComplexGrossMargin, self).__init__(options, schema, predictor)

    def train(self, dataset, **kwargs):
        pass

    def print_model(self):
        pass

    def predict_schema_answer(self, elements):
        answer_results = []
        for element in elements:
            report_period_answers = []
            gross_margin_answers = []
            if not self.is_target_element(element):
                continue
            element_text = clean_txt(element["text"])
            # 没有匹配到`毛利率`类似的段落跳过
            margin_matcher = GROSS_PROFIT_MARGIN_PATTERN.nexts(element_text)
            if not margin_matcher:
                continue
            # 匹配到`主营业务毛利率`类似的段落跳过
            invalid_matcher = invalid_patterns.nexts(element_text)
            if invalid_matcher:
                continue
            special_date_matcher = SPECIAL_REPORT_PATTERNS.finditer(element_text)
            for match in special_date_matcher:
                report_period_answers.append(match)
            if not report_period_answers:
                date_matcher = PatternCollection(DATE_PATTERN).finditer(element_text)
                for match in date_matcher:
                    report_period_answers.append(match)
            matcher = PatternCollection(RISK_PATTERNS).finditer(element_text)
            for match in matcher:
                gross_margin_answers.append(match)

            gross_margin_answers = gross_margin_answers[:3]  # 仅仅保留三个毛利率 一般段落里的描述只包含三年的数据

            if len(report_period_answers) == 1 and SPECIAL_REPORT_PATTERNS.nexts(report_period_answers[0].group()):
                ret = []
                report_dst_chars = self.get_dst_chars_from_matcher(report_period_answers[0], element)
                for index, gross_margin in enumerate(gross_margin_answers):
                    answer_result = {}
                    display_text = f"{''.join(i['text'] for i in report_dst_chars)}_{index}"
                    answer_result["报告期"] = [
                        self.create_result(
                            [CharResult(element, report_dst_chars, display_text=display_text)],
                            column="报告期",
                            text=display_text,
                        )
                    ]
                    gross_margin_chars = self.get_dst_chars_from_matcher(gross_margin, element)
                    answer_result["综合毛利率（%）"] = [
                        self.create_result([CharResult(element, gross_margin_chars)], column="综合毛利率（%）")
                    ]
                    ret.append(answer_result)
                return ret
            for report, gross_margin in zip(report_period_answers, gross_margin_answers):
                answer_result = {}
                report_dst_chars = self.get_dst_chars_from_matcher(report, element)
                gross_margin_chars = self.get_dst_chars_from_matcher(gross_margin, element)
                if report_dst_chars:
                    answer_result["报告期"] = [
                        self.create_result([CharResult(element, report_dst_chars)], column="报告期")
                    ]
                if gross_margin_chars:
                    answer_result["综合毛利率（%）"] = [
                        self.create_result([CharResult(element, gross_margin_chars)], column="综合毛利率（%）")
                    ]
                if len(answer_results) >= 4:
                    break
                answer_results.append(answer_result)

        return answer_results
