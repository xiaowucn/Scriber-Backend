import logging

from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import PredictorResult

logger = logging.getLogger(__name__)


def post_process_ocr(answers: list[dict[str, list[PredictorResult]]], **kwargs) -> list[dict]:
    """
    过滤扫描页
    """
    pdfinsight_reader = kwargs.get("pdfinsight_reader")
    for answer in answers:
        for field_name, field_answers in answer.items():
            elements = BaseModel.get_elements_from_answer_results(field_answers)
            for element in elements:
                if pdfinsight_reader.is_ocr_page(element["page"]):
                    answer[field_name] = []
                    break
    return answers
