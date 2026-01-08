"""中泰证券"""

from remarkable.answer.reader import AnswerReader
from remarkable.common.util import clean_txt
from remarkable.converter.utils import convert_unit
from remarkable.predictor.base_prophet import BaseProphet
from remarkable.predictor.predictor import JudgeByRegex


class ZtsSSECorporateBond(JudgeByRegex):
    col_patterns = {
        "单项资产受限金额超过报告期末合并口径净资产 10%": {
            "适用": [r"(?<!不)适用"],
            "不适用": [r"不适用"],
        }
    }


class Prophet(BaseProphet):
    def parse_enum_value(self, predictor_result, schema):
        if self.enum_predictor:
            return self.enum_predictor.predict(predictor_result, schema)
        return None

    def get_enum_predictor(self):
        enum_classes = {"上交所企业债": ZtsSSECorporateBond}
        if predictor := (enum_classes.get(self._mold.name) or enum_classes.get(clean_txt(self._mold.name))):
            return predictor()

    @staticmethod
    def unify_unit(answer, to_unit, amount_fields):
        answer_reader = AnswerReader(answer)
        for field in amount_fields:
            for node in answer_reader.find_nodes([field]):
                if node.isleaf():
                    answer_item = node.data
                    answer_item.data[0]["text"] = convert_unit(answer_item.plain_text, to_unit=to_unit) + to_unit
                else:
                    amount_node = None
                    unit_node = None
                    for _, item in node.items():
                        if item.name.endswith("金额"):
                            amount_node = item
                        elif item.name == "单位":
                            unit_node = item

                    if amount_node is None or unit_node is None:
                        continue

                    if unit_node.data.plain_text != to_unit:
                        if converted_value := convert_unit(
                            amount_node.data.plain_text, to_unit=to_unit, from_unit=unit_node.data.plain_text
                        ):
                            amount_node.data.data[0]["text"] = converted_value
                            unit_node.data.data[0]["text"] = to_unit

        answer["userAnswer"]["items"] = answer_reader.dump_answer_items()
        return answer

    @staticmethod
    def post_process(preset_answer):
        amount_fields = [
            "所有者权益金额",
            "资产受限金额合计",
            "报告期初有息债务余额",
            "报告期末有息债务余额",
            "报告期初对外担保余额",
            "报告期末对外担保余额",
            "单项资产受限",
        ]
        preset_answer = Prophet.unify_unit(preset_answer, to_unit="万元", amount_fields=amount_fields)
        return preset_answer
