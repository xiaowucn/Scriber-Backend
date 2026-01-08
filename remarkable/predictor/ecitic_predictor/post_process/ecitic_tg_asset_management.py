from remarkable.pdfinsight.reader import PdfinsightSyllabus
from remarkable.pdfinsight.text_util import clear_syl_title
from remarkable.predictor.models.syllabus_elt_v2 import SyllabusEltV2
from remarkable.predictor.schema_answer import OutlineResult, PredictorResult


def post_process_investment_ratio(answers: list[dict[str, list[PredictorResult]]], **kwargs) -> list[dict]:
    pdfinsight = kwargs["pdfinsight_reader"]
    patterns = [r"投资比例和投资限制超限的处理方式及流程"]
    syllabuses = pdfinsight.find_sylls_by_pattern(
        patterns,
        clean_func=clear_syl_title,
    )
    if syllabuses:
        page_box = PdfinsightSyllabus.syl_outline(
            syllabuses[0],
            pdfinsight,
            include_title=True,
        )
        text = "\n".join(i["text"] for i in page_box)
        elements = SyllabusEltV2.get_elements_from_page_box(page_box)
        if elements:
            element_results = [
                OutlineResult(page_box=page_box, text=text, element=elements[0], origin_elements=elements)
            ]
            for answer in answers:
                if "原文" in answer:
                    answer["原文"][0].element_results.extend(element_results)

    return answers
