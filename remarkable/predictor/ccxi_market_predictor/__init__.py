"""
中诚信市场部
"""

from remarkable.common.util import clean_txt
from remarkable.predictor.base_prophet import BaseProphet
from remarkable.predictor.predictor import JudgeByRegex


class ContractEnumPredictor(JudgeByRegex):
    col_patterns = {
        "品种": {
            "同业存单": [
                r"同业存单",
            ],
            "金融债": [
                r"金融债券?",
            ],
            "企业债": [
                r"企业债券?",
            ],
            "公司债": [
                r"公司债券?",
            ],
            "中期票据": [
                r"中期票据",
            ],
            "短期融资券": [
                r"短期融资券",
            ],
            "国际机构债": [
                r"国际机构债券?",
            ],
            "政府支持机构债": [
                r"政府支持机构债券?",
            ],
            "定向工具": [
                r"定向工具",
            ],
            "主体": [
                r"主体",
            ],
            "DFI": [
                r"DFI",
            ],
            "资产支持证券": [
                r"资产支持",
            ],
            "美元债": [
                r"美元债券?",
            ],
            "非标产品": [
                r"非标产品",
            ],
            "项目收益票据": [
                r"项目收益票据",
            ],
            "资产证券化": [
                r"资产证券化",
            ],
            "其他": [
                r".*",
            ],
        },
    }


class Prophet(BaseProphet):
    def parse_enum_value(self, predictor_result, schema):
        if self.enum_predictor:
            return self.enum_predictor.predict(predictor_result, schema)
        return None

    def get_enum_predictor(self):
        enum_classes = {
            "合同提取": ContractEnumPredictor,
        }
        if predictor := (enum_classes.get(self._mold.name) or enum_classes.get(clean_txt(self._mold.name))):
            return predictor()
