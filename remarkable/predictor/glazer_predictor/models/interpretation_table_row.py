import re

from remarkable.predictor.models.table_row import TableRow

p_interpretation = re.compile(r"^本[次期](公司)?(债券|发行)")


class InterpretationTableRow(TableRow):
    def predict_schema_answer(self, elements):
        tables = self.pdfinsight.find_tables_by_pattern([p_interpretation], start=50, multi=False)
        answer_results = super(InterpretationTableRow, self).predict_schema_answer(tables)
        if self.schema.name == "公司名" or self.schema.parent.name == "公司名":
            answer_results = self.fix_company_name(answer_results)

        return answer_results

    @staticmethod
    def fix_company_name(answer_results):
        for answer_result in answer_results:
            if answer_result.get("全称"):
                answer_result["全称"] = answer_result["全称"][-1:]
        return answer_results
