import logging
from dataclasses import dataclass

from remarkable.common.constants import TableType
from remarkable.common.pattern import PatternCollection
from remarkable.common.storage import localstorage
from remarkable.common.util import clean_txt
from remarkable.converter import AnswerWorkShop, BaseConverter, SimpleJSONConverter
from remarkable.converter.ebscn.open_day import open_day_convert
from remarkable.converter.ebscn.performance_principle import performance_principle_convert
from remarkable.converter.ebscn.performance_principle_rate import performance_principle_ratio_convert
from remarkable.converter.ebscn.redemption_rate import redemption_rate_convert
from remarkable.pdfinsight.parser import parse_table
from remarkable.pdfinsight.reader import PdfinsightReader
from remarkable.pw_models.model import NewSpecialAnswer

logger = logging.getLogger(__name__)


def simple_convert(ebscn_answer):
    config = ebscn_answer.config
    clean_text = clean_txt(ebscn_answer.answer_text)
    enum_map = config.get("enum_map", {})
    if not enum_map:
        return clean_text
    for enum, regs in enum_map.items():
        if PatternCollection(regs).nexts(clean_text):
            return enum
    return clean_text


CONVERT_MAP = {
    "产品代码": {
        "func": lambda x: x.answer_text,
        "from_keys": ["self"],
    },
    "产品名称": {
        "func": lambda x: x.answer_text,
        "from_keys": ["self"],
    },
    "管理人名称": {
        "func": lambda x: x.answer_text,
        "from_keys": ["self"],
    },
    "管理人代码": {
        "func": lambda x: x.answer_text,
        "from_keys": ["self"],
    },
    "认购费率": {
        "func": simple_convert,
        "from_keys": ["self"],
        "enum_map": {
            "0": [
                r"不收取",
            ]
        },
    },
    "首次投资最低金额": {
        "func": lambda x: str(int(x.answer_text) * 10000),
        "from_keys": ["self"],
    },
    "认购利息处理方式": {
        "func": simple_convert,
        "from_keys": ["self"],
        "enum_map": {
            "利息转份额": [
                r"折算为投资者份额",
            ],
            "归基金资产": [
                r"计入基金财产",
            ],
        },
    },
    "基金申购和赎回的开放日": {
        "func": open_day_convert,
        "from_keys": ["self"],
    },
    "赎回费率": {
        "func": redemption_rate_convert,
        "from_keys": ["self"],
    },
    "归基金资产比例": {
        "func": simple_convert,
        "from_keys": ["self"],
        "enum_map": {
            "0": [
                r"赎回费归募集机构所有",
                r"^$",
            ],
        },
    },
    "赎回后资产低于最低保有金额处理方式": {
        "func": simple_convert,
        "from_keys": ["self"],
        "enum_map": {
            "0": [
                r"赎回费归募集机构所有",
                r"^$",
            ],
            "全部确认": [r"全部赎回处理"],
        },
    },
    "净值精度": {
        "func": lambda x: x.answer_text,
        "from_keys": ["self"],
    },
    "业绩报酬提取原则": {
        "func": performance_principle_convert,
        "from_keys": ["业绩报酬提取"],
    },
    "业绩报酬计提比例及公式": {
        "func": performance_principle_ratio_convert,
        "from_keys": ["业绩报酬计算公式（单公式）", "业绩报酬计算公式（多行公式）"],
    },
}


@dataclass
class EbscnAnswer:
    column: str
    answer_data: list[dict] | None = None
    config: dict | None = None
    answer_text: str = ""

    def __post_init__(self):
        if len(self.answer_data) == 1:
            self.answer_text = "".join(list(self.answer_data[0].values())[0])


class EbscnWorkShop(AnswerWorkShop):
    def __init__(self, metadata, debug=False):
        super().__init__(metadata, debug)
        self.preset_answer = metadata.question.preset_answer
        # self.answer = metadata.answer if metadata.answer else self.preset_answer
        self.answer = self.preset_answer
        self.pdfinsight = PdfinsightReader(localstorage.mount(self.file.pdfinsight_path()))
        self.special_answer = SimpleJSONConverter(self.answer).convert()
        self.answer_node = BaseConverter(self.answer).answer_node

    async def work(self):
        answer_data = {}
        for key, config in CONVERT_MAP.items():
            origin_answer = self.get_origin_text(key, config)
            ebscn_answer = EbscnAnswer(key, origin_answer, config)
            converted_answer = config["func"](ebscn_answer)
            answer_data[key] = converted_answer
            logger.debug(f"convert_key: {key}")
            logger.debug(f"converted_answer: {converted_answer}")
        await NewSpecialAnswer.update_or_create(self.question.id, NewSpecialAnswer.ANSWER_TYPE_JSON, answer_data)

    def get_origin_text(self, column, config):
        res = []
        if column == "业绩报酬计提比例及公式":
            return self.get_multi_formula_answer(column)
        from_keys = config["from_keys"]
        from_keys = [column] if "self" in from_keys else from_keys
        for from_key in from_keys:
            answer_node = self.answer_node.get(from_key, {})
            for item in answer_node.values():
                if item.data:
                    res.append({column: item.data.plain_text})
                else:
                    item_dict = item.to_dict()
                    item_dict = {k: v.plain_text if v else "" for k, v in item_dict.items()}
                    # test = {k: v.relative_element_indexes if v else '' for k, v in item_dict.items()}
                    res.append(item_dict)
        return res

    def get_multi_formula_answer(self, column):
        res = []
        single_formula = "业绩报酬计算公式（单公式）"
        multi_formula = "业绩报酬计算公式（多行公式）"
        answer_node = self.answer_node.get(single_formula, {})
        for item in answer_node.values():
            if item.data:
                res.append({column: item.data.plain_text})
            else:
                item_dict = item.to_dict()
                item_dict = {k: v.plain_text if v else "" for k, v in item_dict.items()}
                res.append(item_dict)
        if res:
            return res
        answer_node = self.answer_node.get(multi_formula, {})
        for item in answer_node.values():
            if item.data:
                continue
            answer = {}
            fund_type = item["基金类型"]
            for fund_item in fund_type.values():
                if not fund_item.data:
                    continue
                answer["基金类型"] = fund_item.data.plain_text
            formula = item["计提比例及公式"]
            formula_texts = []
            for formula_item in formula.values():
                if not formula_item.data:
                    continue
                if not (relative_element_indexes := list(formula_item.relative_element_indexes)):
                    continue
                relative_element_index = relative_element_indexes[0]
                _, element = self.pdfinsight.find_element_by_index(relative_element_index)
                if not element:
                    continue
                table = parse_table(element, tabletype=TableType.TUPLE.value, pdfinsight_reader=self.pdfinsight)
                for row in table.rows:
                    formula_texts.append([cell.text for cell in row])
                answer["计提比例及公式"] = formula_texts
            res.append(answer)
        return res
