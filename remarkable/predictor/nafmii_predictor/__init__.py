from decimal import Decimal

from remarkable.answer.node import AnswerItem
from remarkable.answer.reader import AnswerReader
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import clean_txt
from remarkable.converter.csc_octopus.data_formater import date_format
from remarkable.plugins.cgs.common.para_similarity import ConvertText
from remarkable.predictor.base_prophet import BaseProphet
from remarkable.predictor.predictor import JudgeByRegex

p_rate = PatternCollection([r"(?P<rate>[0-9.]+)"])
p_rate_format = PatternCollection(r"(?P<rate>[\d.]+\d{2,})")
p_money_unit = PatternCollection(r"(?P<unit>[亿万元]+)")
p_rmb = PatternCollection(r"rmb|RMB")
p_date_blank = PatternCollection(r"\d{4}\s+\d{1,2}\s+\d{1,2}")
p_blank = PatternCollection(r"\s+")
p_enter = PatternCollection(r"[\r\t\f\v\n]+")


class PaymentEnumPredictor(JudgeByRegex):
    col_patterns = {
        "金额单位": {
            "亿元": [
                r"亿元",
                r"亿[)）]$",
            ],
            "万元": [
                r"万元",
                r"万[)）]$",
            ],
            "千元": [
                r"千元",
                r"千[)）]$",
            ],
            "元": [
                r"元",
            ],
        },
        "期限单位": {
            "年": [
                r"年",
            ],
            "月": [
                r"月",
            ],
            "天": [
                r"[日天]",
            ],
        },
    }


class ExerciseEnumPredictor(JudgeByRegex):
    col_patterns = {
        "金额单位": PaymentEnumPredictor.col_patterns["金额单位"],
        "期限单位": PaymentEnumPredictor.col_patterns["期限单位"],
    }


class Prophet(BaseProphet):
    def parse_enum_value(self, predictor_result, schema):
        if self.enum_predictor:
            return self.enum_predictor.predict(predictor_result, schema)
        return None

    def get_enum_predictor(self):
        enum_classes = {
            "付息兑付安排公告": PaymentEnumPredictor,
            "行权公告": ExerciseEnumPredictor,
            "行权结果公告": ExerciseEnumPredictor,
        }
        if predictor := (enum_classes.get(self._mold.name) or enum_classes.get(clean_txt(self._mold.name))):
            return predictor()

    @staticmethod
    def bond_rate(answer_reader, item):
        answer_item = AnswerItem(**item)
        text = answer_item.plain_text
        if rate := p_rate_format.nexts(text):
            text = f"{rate.groupdict()['rate']}%"
        elif rate := p_rate.nexts(text):
            text = "{:.2f}%".format(float(rate.groupdict()["rate"]))

        item["data"][0]["text"] = text
        return item

    @staticmethod
    def date_format(answer_reader, item):
        answer_item = AnswerItem(**item)
        text = answer_item.plain_text
        if p_date_blank.nexts(text):
            text = p_blank.sub("-", text)
        if date := date_format(text, "%Y年%m月%d日"):
            item["data"][0]["text"] = date
        return item

    @staticmethod
    def amount_format(answer_reader, item):
        unit = ""
        answer_item = AnswerItem(**item)
        text = answer_item.plain_text
        if p_rmb.nexts(text) or not p_money_unit.nexts(text):
            return item
        amount = ConvertText.convert_number_text(text + unit)
        item["data"][0]["text"] = "{:,.2f}元".format(Decimal(amount))

        return item

    @classmethod
    def post_process_handler(cls, field):
        handlers = {
            "起息日": cls.date_format,
            "兑付日": cls.date_format,
            "公告披露日期": cls.date_format,
            "投资人回售申请开始日": cls.date_format,
            "投资人回售申请截止日": cls.date_format,
            "行权日": cls.date_format,
            "行权日01": cls.date_format,
            "利率生效日01": cls.date_format,
            "行权日02": cls.date_format,
            "利率生效日02": cls.date_format,
            "发行金额": cls.amount_format,
            "债项余额": cls.amount_format,
            "本期应偿付金额": cls.amount_format,
        }

        return handlers.get(field)

    def post_process(self, preset_answer):
        answer_reader = AnswerReader(preset_answer)
        answer_items = []
        for item in answer_reader.items:
            label = item["schema"]["data"]["label"]
            if post_handler_func := self.post_process_handler(label):
                item = post_handler_func(answer_reader, item)
            item = self.format_answer_item(item)
            answer_items.append(item)
        preset_answer["userAnswer"]["items"] = answer_items
        return preset_answer

    def format_answer_item(self, item):
        answer_item = AnswerItem(**item)
        for idx, text in enumerate(answer_item.get_data_texts()):
            item["data"][idx]["text"] = p_enter.sub("", text)
        return item
