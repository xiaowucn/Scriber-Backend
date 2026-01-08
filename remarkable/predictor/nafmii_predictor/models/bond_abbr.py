from remarkable.pdfinsight.reader import PdfinsightParagraph, PdfinsightTable
from remarkable.predictor.eltype import ElementClassifier
from remarkable.predictor.models.fixed_position import FixedPosition
from remarkable.predictor.schema_answer import CharResult, PredictorResult


class BondAbbr(FixedPosition):
    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        answer_results = super().predict_schema_answer(elements)
        for answer_result in answer_results:
            for items in answer_result.values():
                for predictor_result in items:
                    next_elements = self.pdfinsight.find_elements_near_by(
                        index=predictor_result.relative_elements[-1]["index"], step=1, steprange=5
                    )
                    if not next_elements:
                        continue
                    next_ele = next_elements[0]
                    if next_ele["outline"][0] < 300:
                        continue
                    if self.neglect_patterns.nexts(next_ele.get("text", "")):
                        continue
                    if ElementClassifier.is_table(next_ele):
                        pdfinsight_element = PdfinsightTable(next_ele)
                    elif ElementClassifier.like_paragraph(next_ele):
                        pdfinsight_element = PdfinsightParagraph(next_ele)
                    else:
                        continue
                    predictor_result.element_results.append(CharResult(next_ele, pdfinsight_element.chars))
        return answer_results
