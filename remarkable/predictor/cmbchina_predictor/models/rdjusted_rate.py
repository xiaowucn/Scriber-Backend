from remarkable.predictor.models.table_row import TableRow
from remarkable.predictor.schema_answer import PredictorResult


class AdjustedRate(TableRow):
    """
    处理 费率调整公告 基金名称 和 调整后费率 在不同表格中的情况
    """

    FUND_NAME = "基金名称"

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        ret_result = []
        # new_result = []
        results = super().predict_schema_answer(elements)
        used_elements = set()
        for result in results:
            if result.get("销售服务费率") and result.get(self.FUND_NAME):
                ret_result.append(result)
            elif fee_results := result.get("销售服务费率"):
                fee_result_indices = {fee_result.relative_elements[0]["index"] for fee_result in fee_results}
                unused_elements = [
                    elt
                    for elt in elements
                    if elt["index"] not in used_elements and elt["index"] not in fee_result_indices
                ]
                new_results = super().predict_schema_answer(unused_elements)
                fund_name_results = []
                for new_result in new_results:
                    if new_result.get(self.FUND_NAME):
                        used_elements.update(r.relative_elements[0]["index"] for r in new_result[self.FUND_NAME])
                        fund_name_results.extend(new_result[self.FUND_NAME])
                if fund_name_results:
                    result[self.FUND_NAME] = fund_name_results
                ret_result.append(result)
        return ret_result
