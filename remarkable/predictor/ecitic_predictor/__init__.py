import re

from remarkable.common.util import clean_txt
from remarkable.plugins.cgs.common.patterns_util import R_NOT_CONJUNCTION_PUNCTUATION
from remarkable.predictor.base_prophet import BaseProphet
from remarkable.predictor.predictor import JudgeByRegex


class PrivateFundContract(JudgeByRegex):
    col_patterns = {
        "运作方式": {
            "开放式": [
                r"开放式",
            ],
            "封闭式": [
                r"封闭式",
            ],
        }
    }


R_PUNCTUATION = re.compile(r"[、،,，｡。;；：、？?.…⋯᠁]+\s?$")


class Prophet(BaseProphet):
    def parse_enum_value(self, predictor_result, schema):
        if self.enum_predictor:
            return self.enum_predictor.predict(predictor_result, schema)
        return None

    def get_enum_predictor(self):
        enum_classes = {
            "私募基金合同": PrivateFundContract,
        }
        if predictor := (enum_classes.get(self._mold.name) or enum_classes.get(clean_txt(self._mold.name))):
            return predictor()

    def post_process(self, preset_answer, **kwargs):
        schema_investment_restriction_split = ["投资限制(其它-投资监督)", "拆分"]
        need_clean_text_schemas = [
            ["产品名称"],
            schema_investment_restriction_split,
            ["投资比例(其它-投资监督)", "拆分"],
            ["证券交易所释义(其它-投资监督)", "拆分"],
            ["期货交易所释义(其它-投资监督)", "拆分"],
            ["交易所释义(其它-投资监督)", "拆分"],
            ["投资范围(其它-投资监督)", "拆分"],
        ]
        for item in preset_answer["userAnswer"]["items"]:
            if any(all(key in item["key"] for key in keys) for keys in need_clean_text_schemas):
                is_investment_split = all(key in item["key"] for key in schema_investment_restriction_split)
                if item["value"] and isinstance(item["value"], str):
                    item["value"] = clean_txt(item["value"])
                    if is_investment_split:
                        item["value"] = R_PUNCTUATION.sub("", item["value"])
                for data in item["data"]:
                    for i, box in enumerate(data["boxes"], start=1):
                        if box["text"]:
                            box["text"] = clean_txt(box["text"])
                        if is_investment_split and i == len(data["boxes"]) and box["text"]:
                            box["text"] = R_PUNCTUATION.sub("", box["text"])
        return preset_answer
