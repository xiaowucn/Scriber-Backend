from remarkable.common.pattern import PatternCollection
from remarkable.predictor.models.partial_text import PartialText


class FundName(PartialText):
    """
    基金名称换行，但是没被识别为一个段落
    根据基类获得基金名称，向下找一个段落，根据R_FUND_NAME取下半段内容
    """

    R_FUND_NAME = PatternCollection(
        [
            r".*?基金.*联接基金([(（]?[a-zA-Z]+[）)])?",
            r".*?基金(中基金)?([(（]?[a-zA-Z]+[）)])?",
        ]
    )

    @property
    def follow_paras_patterns(self):
        return PatternCollection(self.get_config("follow_paras_patterns", []))

    def predict_schema_answer(self, elements):
        parent_answers = super().predict_schema_answer(elements)
        if not parent_answers:
            return parent_answers
        answer = parent_answers[-1][self.columns[0]][-1]
        neglect_patterns = PatternCollection(self.get_config("neglect_patterns", []))
        # 根据答案文本判断
        _type, next_para = self.pdfinsight.find_element_by_index(answer.element_results[-1].element["index"] + 1)
        if _type == "PARAGRAPH" and next_para:
            para_text = next_para["text"]
            if match := self.R_FUND_NAME.nexts(para_text) and not neglect_patterns.match(para_text):
                if self.follow_paras_patterns and not self.follow_paras_patterns.nexts(para_text):
                    return []
                c_start, c_end = match.span()
                for parent_answer in parent_answers:
                    parent_answer[self.columns[0]].append(
                        self.create_result(
                            self.create_content_result(next_para, next_para["chars"][c_start:c_end], None),
                            column=self.columns[0],
                        )
                    )
                    break
        return parent_answers
