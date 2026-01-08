from remarkable.predictor.models.table_row import TableRow
from remarkable.predictor.models.table_tuple import TupleTable


class CompensatoryRate(TupleTable):
    def __init__(self, options, schema, predictor):
        super(CompensatoryRate, self).__init__(options, schema, predictor)

    def predict_schema_answer(self, elements):
        ret = []
        answer_results = super(CompensatoryRate, self).predict_schema_answer(elements)
        for answer_result in answer_results:
            if "年份" in answer_result and len(answer_result) == 1:
                continue
            ret.append(answer_result)

        return ret


class GuaranteeObject(TableRow):
    def predict_schema_answer(self, elements):
        answer_results = super(GuaranteeObject, self).predict_schema_answer(elements)
        return [answer_result for answer_result in answer_results if len(answer_result) > 1]
