"""中诚信"""

from remarkable.common.util import clean_txt
from remarkable.plugins.diff.common import gen_cache_for_diff
from remarkable.predictor.base_prophet import BaseProphet
from remarkable.predictor.predictor import JudgeByRegex


class Iduciary(JudgeByRegex):
    col_patterns = {
        "封包期利息是否入池": {
            "否": [
                r"初始起算日.*?已经?实际收到的.*?(利息|罚息|复利|违约金|收入回收款).*?除外",
                r"初始起算日.*?不包含.*?利息",
                r"初始起算日.*?但不包括.*?收入回收款",
            ],
            "是": [
                "初始起算日.*?产生的(全部|所有).*?回收款",
                "初始起算日.*?收到的所有.*?(收入)?回收款",
                "初始起算日.*?标的信托利益",
                "初始起算日.*?全部资金",
            ],
            "不适用": [r""],
        }
    }


class IduciaryForStandard(JudgeByRegex):
    col_patterns = {
        "封包期利息是否入池": {
            "否": [
                r"不归入",
            ],
            "是": [
                "归入专项计划资产",
                "权利|权益|收益",
            ],
            "不适用": [r""],
        }
    }


class Prophet(BaseProphet):
    def parse_enum_value(self, predictor_result, schema):
        if self.enum_predictor:
            return self.enum_predictor.predict(predictor_result, schema)
        return None

    def get_enum_predictor(self):
        enum_classes = {
            "信托合同": Iduciary,
            "标准条款": IduciaryForStandard,
        }
        if predictor := (enum_classes.get(self._mold.name) or enum_classes.get(clean_txt(self._mold.name))):
            return predictor()

    def post_process(self, preset_answer):
        gen_cache_for_diff(preset_answer, self.reader)
        return preset_answer
