class ParaSplitterMixin:
    def get_predict_elements(self, elements):
        parent_answers = super().predict_schema_answer(elements)
        origin_answer = None
        for parent_answer in parent_answers:
            if isinstance(parent_answer, dict):
                origin_answer = parent_answer.get("原文")
                if isinstance(origin_answer, list):
                    origin_answer = origin_answer[0]

            elif parent_answer.schema.name == "原文":
                origin_answer = parent_answer

            if origin_answer:
                break
        return parent_answers, origin_answer, self.get_elements_from_answer_result(origin_answer)

    def predict_schema_answer(self, elements):
        parent_answers, origin_answer, predict_elements = self.get_predict_elements(elements)
        if not predict_elements:
            return parent_answers
        if not (split_results := super().split(predict_elements)):
            return parent_answers
        return [super().create_result(split_results, column="拆分"), origin_answer]
