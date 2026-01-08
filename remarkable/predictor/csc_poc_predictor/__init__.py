from remarkable.common.util import clean_txt
from remarkable.predictor.base_prophet import BaseProphet
from remarkable.predictor.predictor import JudgeByRegex


class AccountInvestment(JudgeByRegex):
    col_patterns = {
        "到账情况": {
            "全部到账": [
                r"☑全部到账",
            ],
            "部分到账": [
                r"☑部分到账",
            ],
        },
    }


class DollarDebt(JudgeByRegex):
    col_patterns = {
        "是否累计": {
            "是": [
                r"can\s?be\s?deferred",
                r"[Cc]umulative|[Aa]rrears",
            ],
            "否": [r".*"],
        },
        "是否次级债-发行事项页": {
            "是": [r"(?<!un)[Ss]ubordinated(?!\s?(to|ob))", "junior"],
            "否": [r".*"],
        },
        "是否永续债-封面": {
            "是": [r"[Pp]erpetual"],
            "否": [r".*"],
        },
        "是否永续债-发行事项页": {
            "是": [r"[Pp]erpetual"],
            "否": [r".*"],
        },
        "利息是否可取消": {
            "是": [r"no\s*obligation\s?to\s?pay"],
            "否": [r".*"],
        },
    }

    multi_answer_col_patterns = {
        "发行人国际评级-发行事项页": {
            "values": {
                "穆迪": [r"Moody"],
                "标普": [r"S&P", r"Standard\s?(and|&)\s?Poor"],
                "惠誉": [r"Fitch"],
            },
            "default": "X",
        },
        "债券国际评级-发行事项页": {
            "values": {
                "穆迪": [r"Moody"],
                "标普": [r"S&P", r"Standard\s?(and|&)\s?Poor"],
                "惠誉": [r"Fitch"],
            },
            "default": "X",
        },
    }


class Prophet(BaseProphet):
    def parse_enum_value(self, predictor_result, schema):
        if self.enum_predictor:
            return self.enum_predictor.predict(predictor_result, schema)
        return None

    def get_enum_predictor(self):
        enum_classes = {
            "发行款到账确认书": AccountInvestment,
            "美元债债项评级字段抽取": DollarDebt,
            "美元债债项评级": DollarDebt,
        }
        if predictor := (enum_classes.get(self._mold.name) or enum_classes.get(clean_txt(self._mold.name))):
            return predictor()
