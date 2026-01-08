# CYC: build-with-nuitka
import logging
import re
from typing import Generator

from remarkable.predictor.models.base_model import BaseModel
from remarkable.predictor.schema_answer import CharResult, PredictorResult

logger = logging.getLogger(__name__)


def clear_suffixes(text: str, replace_pairs: tuple[tuple[str, str], ...] | None) -> str:
    for pattern, repl in replace_pairs or []:
        text = re.sub(pattern, repl, text)
    return text


def get_depend_predictors(predictors, depends: list[str]):
    for predictor in predictors:
        if predictor.schema.name in depends:
            yield predictor


class ProductAbbSubmission(BaseModel):
    """
    1. 60011 产品中文简称_监管报送
    2. 200136 产品中文简称（内部使用）
    3. 200043 A级基金简称
    4. 200044 C级基金简称
    5. 205463 投资范围是否包含其他基金
    """

    @property
    def replace_pairs(self) -> tuple[tuple[str, str], ...] | None:
        return self.get_config("replace_pairs")

    def train(self, dataset, **kwargs):
        pass

    def gen_depend_answers(self, predictors) -> Generator[PredictorResult, None, None]:
        for predictor in predictors:
            predictor.load_model_data()
            elements = self.predictor.get_candidate_elements(predictor.schema.path[1:])
            for answers in predictor.predict_answer_from_models(elements) or []:
                for answer in (a for ans in answers.values() for a in ans):
                    yield answer

    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        depends = self.get_config("depends", [])
        depend_predictors = get_depend_predictors(self.predictor.prophet.predictors, self.get_config("depends", []))
        predictors = {p.schema.name: p for p in depend_predictors}
        depend_answer = next(self.gen_depend_answers([predictors[depends[0]]]), None)

        fund_type = None
        if "基金合同类型" in depends:
            fund_type = next(self.gen_depend_answers([predictors["基金合同类型"]]), None)

        if not depend_answer:
            return []
        for column in self.columns:
            text = clear_suffixes(depend_answer.text, self.replace_pairs)
            if text == depend_answer.text:
                for result in depend_answer.element_results:
                    if column == "200043 A级基金简称":
                        display_text = "无" if fund_type.answer_value in ["联接型", "ETF"] else f"{text}A"
                    elif column == "200044 C级基金简称":
                        display_text = "无" if fund_type.answer_value in ["联接型", "ETF"] else f"{text}C"
                    else:
                        display_text = text
                    return [
                        self.create_result(
                            [CharResult(result.element, result.element["chars"], display_text)], column=column
                        )
                    ]
            else:
                for result in depend_answer.element_results:
                    chars = []
                    for part in text.split("ETF"):
                        if m := re.search(part, result.text):
                            chars.extend(result.element["chars"][m.start() : m.end()])
                        else:
                            chars.extend(result.element["chars"])
                    return [self.create_result([CharResult(result.element, chars, text)], column=column)]
        return []


class ETFClassifier:
    def __init__(self, listing_place, full_name):
        self.listing_place = listing_place
        self.full_name = full_name

    def classify(self):
        if any(p in self.listing_place for p in ("上海证券交易所", "上交所")):
            return self.classify_sse()
        if any(p in self.listing_place for p in ("深圳证券交易所", "深交所")):
            return self.classify_szse()
        return "其他"

    def classify_sse(self):
        if "沪港深" in self.full_name:
            return "上交所沪港深"
        if any(keyword in self.full_name for keyword in ["中证", "沪深"]):
            return "上交所跨市场"
        if any(keyword in self.full_name for keyword in ["上证", "创业板", "中小板"]):
            return "上交所单市场"
        return "其他"

    def classify_szse(self):
        if "沪港深" in self.full_name:
            return "深交所沪港深"
        if any(keyword in self.full_name for keyword in ["中证", "沪深"]):
            return "深交所跨市场"
        if any(keyword in self.full_name for keyword in ["深证", "创业板", "中小板"]):
            return "深交所单市场"
        return "其他"


class ETFFundType(ProductAbbSubmission):
    def predict_schema_answer(self, elements) -> list[dict[str, list[PredictorResult]]]:
        depends = self.get_config("depends", [])
        assert depends, "ETFFundType depends is empty"
        depend_predictors = get_depend_predictors(self.predictor.prophet.predictors, depends)
        predictors = {p.schema.name: p for p in depend_predictors}
        type_answer = next(self.gen_depend_answers([predictors[depends[0]]]), None)
        if not type_answer or "ETF" != type_answer.answer_value:
            return []
        full_name_answer = next(self.gen_depend_answers([predictors[depends[1]]]), None)
        listing_place_answer = next(self.gen_depend_answers([predictors[depends[2]]]), None)
        if not full_name_answer or not listing_place_answer:
            logger.warning("ETFFundType full_name_answer or listing_place_answer is empty")
            return []
        full_name = full_name_answer.text
        listing_place = listing_place_answer.text
        for column in self.columns:
            text = ETFClassifier(listing_place, full_name).classify()
            return [self.create_result([CharResult({}, [], text)], column=column)]
        return []
