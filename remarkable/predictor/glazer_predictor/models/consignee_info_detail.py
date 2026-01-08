"""
主承销商详情
"""

from collections import defaultdict

from remarkable.predictor.glazer_predictor.models import ConsigneeInfo


class ConsigneeInfoDetail(ConsigneeInfo):
    COMPANY_FIELD = "主承销商"

    def create_consignee_result(self, item):
        if "info" in item:
            answer_results = self.para_model.predict(item["info"])
        else:
            answer_results = self.table_model.predict([item["table"]])

        answer_result = defaultdict(list)
        for result in answer_results:
            for key, value in result.items():
                answer_result[key].extend(value)
        answer_result[self.COMPANY_FIELD] = [self.create_result([item["company"]], column=self.COMPANY_FIELD)]
        return answer_result
