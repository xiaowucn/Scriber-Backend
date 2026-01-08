# CYC: skip-file
"""海通基金合同"""

from remarkable.common.util import clean_txt
from remarkable.predictor.base_prophet import BaseProphet
from remarkable.predictor.predictor import JudgeByRegex


class Fund(JudgeByRegex):
    col_patterns = {
        "有无预警线": {
            "是": [
                r"(?<!(无|不))设置.*?预警线|基金份额净值",
            ],
            "否": [
                r"不设置",
            ],
        },
        "有无止损线": {
            "是": [
                r"(?<!(无|不))设置.*?止损线",
                r"基金份额净值",
            ],
            "否": [
                r"不设置",
            ],
        },
        "是否收取赎回费": {
            "是": [
                r"赎回费费?[率用](?!为0)",
            ],
            "否": [
                r"不收取赎回费|赎回费率为0",
            ],
        },
        "是否收取申购费": {
            "是": [
                r"申购费费?[率用](?!为0)",
            ],
            "否": [
                r"(无|不).*?申购费",
                r"申购费费?率?为0",
            ],
        },
        "是否收取认购费": {
            "是": [
                r"认购费费?[率用]?(?!为0)",
            ],
            "否": [
                r"(无|不).*?认购费",
                r"认购费费?率?为0",
            ],
        },
        "是否巨额赎回": {
            "是": [
                r"(?<!(无|不))巨额赎回|基金净赎回申请份额",
            ],
            "否": [
                r"",
            ],
        },
        "是否允许收益分配": {
            "是": [
                r"收益分配|现金分红|收益转换为份额",
            ],
            "否": [
                r"",
            ],
        },
        "是否有收益分配次数": {
            "是": [
                r"分配次数不超过|超过.*?分红|分配不超过",
            ],
            "否": [
                r"",
            ],
        },
        "是否收取业绩报酬": {
            "是": [
                r"分红时提取|赎回时提取|合同终止时提取|业绩报酬成功计提",
            ],
            "否": [
                r"",
            ],
        },
        "是否有锁定期": {
            "是": [
                r"(?<!(无|不))锁定期|禁止赎回",
            ],
            "否": [
                r"^$",
            ],
        },
        "是否有封闭期": {
            "是": [
                r"(?<!(无|不))封闭期|禁止赎回",
            ],
            "否": [
                r"^$",
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
            "私募类基金合同": Fund,
        }
        if predictor := (enum_classes.get(self._mold.name) or enum_classes.get(clean_txt(self._mold.name))):
            return predictor()

    def post_process(self, preset_answer):
        need_add_schemas = [
            "有无预警线",
            "有无止损线",
            "是否收取赎回费",
            "是否收取申购费",
            "是否收取认购费",
            "是否巨额赎回",
            "是否允许收益分配",
            "是否有收益分配次数",
            "是否收取业绩报酬",
            "是否有锁定期",
            "是否有封闭期",
        ]
        for schema in need_add_schemas:
            for item in preset_answer["userAnswer"]["items"]:
                if schema in item["key"]:
                    break
            else:
                mock_answer = {
                    "key": f'["私募类基金合同:0","{schema}:0"]',
                    "data": [],
                    "value": "否",
                    "schema": {
                        "data": {
                            "label": schema,
                            "required": False,
                            "multi": True,
                            "type": "是否",
                            "words": "",
                            "description": None,
                        },
                    },
                    "meta": None,
                }
                preset_answer["userAnswer"]["items"].append(mock_answer)

        return preset_answer
