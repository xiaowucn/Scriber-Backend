from remarkable.predictor.models.table_kv import KeyValueTable
from remarkable.predictor.schema_answer import PredictorResult


class CustomKeyValueTable(KeyValueTable):
    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        results = []
        predictor_results = super().predict_schema_answer(elements)
        predictor_results = self.get_common_predictor_results(predictor_results)
        for predictor in predictor_results:
            for element_result in predictor.element_results:
                predictor_result = self.create_result(
                    [element_result], schema=predictor.schema, column=predictor.schema.name
                )
                results.append(predictor_result)
        return results
