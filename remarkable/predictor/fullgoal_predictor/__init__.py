from remarkable.answer.reader import AnswerReader
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.predictor.base_prophet import BaseProphet
from remarkable.predictor.predictor import JudgeByRegex

from .judge_func import judge_product_type

R_MORE_THAN = r"(不得?低于|高于|超过)"


class PensionPlanSelector(JudgeByRegex):
    col_patterns = {
        "资产类型": {
            "现金类资产": [r"(现金类|货币类|流动性)资产"],
            "固定收益类资产": [r"固定收益类?资产"],
        }
    }


class FullgoalFundSelector(JudgeByRegex):
    p_investment_scope = PatternCollection([r"不包[括含].*港股通"])
    col_patterns = {
        "基金合同类型": {
            "FOF": [r"FOF"],
            "联接型": [r"联接"],
            "ETF": [r"ETF", r"交易型开放式"],
            "债券型": [r"债"],
            "混合型": [r"混合"],
            "货币型": [r"货币"],
            "QDII": [r"QDII?"],
            "股票型": [r"股票", r"证券"],
        },
        "204039 产品开放频率": {
            "12_按日开放（最短持有期）": [r"最短持有期", r"[最至]少持有"],
            "13_按日开放（滚动持有期）": [r"滚动运作"],
            "01_周（定期开放式） ": [r"每周"],
            "02_月（定期开放式） ": [r"每月"],
            "03_季度（定期开放式） ": [r"每季度", r"每满?[3三]个月", r"[3三]个月月度对日"],
            "04_半年（定期开放式） ": [r"每半年", r"每满?[6六]个月", r"[6六]个月月度对日"],
            "05_一年（定期开放式）": [
                r"[每下]一?年",
                r"一年为一个封闭期",
            ],
            "06_一年（不含）至三年（含）（定期开放式）": [
                "[23两三]年",
                "(1[3-9]|2[0-9]|3[0-6])个月",
            ],
            "07_三年以上（不含）（定期开放式）": [
                "[4-9四五六七八九]年",
                r"(3[7-9]|[456789]\d)个月",
            ],
            "08_其他（定期开放式）": [r"定期开放的?方?式"],
            "00_按日开放（开放式） ": [r"每[日天]", r"(?<!定期)开放式"],
            "11_封闭式": [r"封闭式"],
            "10_其他（不定期开放式）": [r""],
            "09_每季多次（不定期开放式）": [r""],
        },
        "203395 基金合同的投资范围是否包含港股通投资标的": {
            "是": [r"港股通"],
            "否": [r".*"],
        },
        "205463 投资范围是否包含其他基金": {
            "是": [
                r"经(中国)?证监会.*?公开募集证券投资基金",
            ],
            "否": [r".*"],
        },
        "203429 基金合同的投资范围是否包含股指期货投资标的": {
            "是": [r"股指期货"],
            "否": [r".*"],
        },
        "203301 是否为发起式基金": {
            "是": [r"发起式"],
            "否": [r".*"],
        },
        "100209946 基金合同中是否有对风格股票的约定": {
            "是": [r".+"],
            "否": [r""],
        },
        "203504 基金是否是指数基金": {
            "是": [r"指数"],
            "否": [r".*"],
        },
        "203431 基金合同中是否有上市条款": {
            "是": [r".+"],
            "否": [r""],
        },
        "20001106 ETF基金类型": {},
        "204030 混合投资偏向性": {
            "偏股": [
                r"股票(资产)?及.*的比例不低于基金资产的[6789]\d",
                r"股票(资产)?及.*占基金资产的[比例为]*[6789]\d",
                r"债券(资产)?及.*的比例不高于基金资产的[1234]\d",
                r"债券(资产)?及.*占基金资产的[比例为]*[1234]\d",
            ],
            "偏债": [
                r"股票(资产)?及.*的比例不高于基金资产的[1234]\d",
                r"债券(资产)?及.*的比例不低于基金资产的[6789]\d",
            ],
            "灵活配置": [r".+"],
        },
        "203209 产品类型": judge_product_type,
        "205233 小微基金模式": {
            "模式二（备案并在6个月内开会）": [r"[6六]个?月内[召|开].*(持有人|股东)大?会"],
            "模式三（触发清盘）": [r"(不|无)[需要须].*?召.*(持有人|股东)大?会"],
            "模式一（向证监会备案）": [
                # r"向(中国证监|证监)会报告并提出解决方案",
                # r"(中国证监|证监)会.*?(申|说)明.*?原因(并|且)提出.*?方案",
                r".+",
            ],
        },
        "204029 基金类别": {
            "股票基金": [r"股票"],
            "债券基金": [r"债券"],
            "货币市场基金": [r"货币"],
            "基金中基金": [r"基金中基金|联接|FOF"],
            "混合基金": [r"混合"],
            "商品基金（黄金）": [r"上海金|黄金"],
            "其他": [r".*"],
            "商品基金（其他基金）": [r""],
            "基础设施基金": [r""],
            "其他另类": [r""],
        },
        "201481 产品投资类型": {
            "固定收益类": [
                rf"(债券|固定收益类资产).*?比例{R_MORE_THAN}.*[89]\d%",
                r"(债券|固定收益类资产).*?比例为[89]\d%-",
            ],
            "权益类": [
                rf"股票(及存托凭证)?.*?(比例|资产){R_MORE_THAN}.*[89]\d%",
                r"股票(及存托凭证)?.*?的(比例|资产)为[89]\d%-",
                rf"成份股.*?的(比例|资产){R_MORE_THAN}.*[89]\d%",
                r"成份股.*?的(比例|资产)为[89]\d%-",
                r"股票(及存托凭证)?.*?的(比例|资产)为0%-[89]\d%",
            ],
            "混合类": [r".*"],
        },
    }

    @classmethod
    def clean_investment_scope(cls, text):
        text = cls.p_investment_scope.sub("***", text)
        text = clean_txt(text)
        return text


class Prophet(BaseProphet):
    def parse_enum_value(self, predictor_result, schema):
        if self.enum_predictor:
            clean_func = clean_txt
            if schema.name == "203395 基金合同的投资范围是否包含港股通投资标的":
                clean_func = FullgoalFundSelector.clean_investment_scope
            return self.enum_predictor.predict(predictor_result, schema, clean_func)
        return None

    def get_enum_predictor(self):
        enum_classes = {
            "年金计划": PensionPlanSelector,
            "富国基金": FullgoalFundSelector,
        }
        if predictor := (enum_classes.get(self._mold.name) or enum_classes.get(clean_txt(self._mold.name))):
            return predictor()

    @classmethod
    def post_process_handler(cls, field):
        handlers = {
            "20001503 权益类资产下限(%)": cls.lower_limit_of_equity_assets,
            "201481 产品投资类型": cls.invest_type,
        }

        return handlers.get(field)

    @staticmethod
    def lower_limit_of_equity_assets(answer_reader, answer_item):
        fund_type = None
        if nodes := answer_reader.find_nodes(["基金合同类型"]):
            fund_type = list(nodes)[0].data.value

        if fund_type == "债券型":
            answer_item["data"][0]["text"] = "0"
        return answer_item

    @staticmethod
    def invest_type(answer_reader, answer_item):
        fund_type = None
        if nodes := answer_reader.find_nodes(["基金合同类型"]):
            fund_type = list(nodes)[0].data.value

        if fund_type == "联接型":
            answer_item["data"] = []
            answer_item["value"] = []
        return answer_item

    @staticmethod
    def fields_only():
        """
        例,仅基金类型为ETF的,需要提取: '202671 业绩比较基准'
        :return:
        """
        data = {
            "基金合同类型": {
                "100209946 基金合同中是否有对风格股票的约定": ["混合型", "股票型"],
                "20001106 ETF基金类型": ["ETF"],
                "204030 混合投资偏向性": ["混合型"],
                "100209947 基金合同中对风格股票库界定标准": ["ETF"],
                "205463 投资范围是否包含其他基金": ["ETF", "债券型", "混合型", "货币型", "QDII", "股票型"],
            },
            "205233 小微基金模式": {
                "205234 小微触发清盘工作日连续天数": ["模式三（触发清盘）"],
            },
        }
        return data

    @staticmethod
    def fields_need_pop(configs, field_value):
        ret = []
        for key, values in configs.items():
            if field_value not in values:
                ret.append(key)
        return ret

    @staticmethod
    def post_process(preset_answer):
        answer_reader = AnswerReader(preset_answer)
        all_pop_fields = []
        for field, configs in Prophet.fields_only().items():
            field_value = None
            if nodes := answer_reader.find_nodes([field]):
                field_value = list(nodes)[0].data.value
            field_value = field_value or None
            pop_fields = Prophet.fields_need_pop(configs, field_value)
            all_pop_fields.extend(pop_fields)

        answer_items = []
        for item in answer_reader.items:
            label = item["schema"]["data"]["label"]
            if label in all_pop_fields:
                continue
            if post_handler_func := Prophet.post_process_handler(label):
                item = post_handler_func(answer_reader, item)

            answer_items.append(item)
        preset_answer["userAnswer"]["items"] = answer_items
        return preset_answer
