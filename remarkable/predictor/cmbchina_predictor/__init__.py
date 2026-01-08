import json
import logging
import operator
import re
from contextlib import suppress
from decimal import Decimal

from remarkable.answer.node import AnswerItem
from remarkable.answer.reader import AnswerReader
from remarkable.common.pattern import PatternCollection
from remarkable.common.util import box_to_outline, clean_txt
from remarkable.plugins.cgs.common.para_similarity import ConvertText
from remarkable.plugins.cgs.common.patterns_util import R_CN_NUMBER, R_CONJUNCTION, R_PERCENT_UNIT
from remarkable.plugins.predict.models.sse.other_related_agencies import clean_text
from remarkable.predictor.base_prophet import BaseProphet
from remarkable.predictor.common_pattern import R_HYPHEN
from remarkable.predictor.predictor import JudgeByRegex

logger = logging.getLogger(__name__)

P_PERCENT = re.compile(rf"{R_PERCENT_UNIT}")
P_YUAN = re.compile(r"元$")
P_MONEY_UNIT = PatternCollection(r"(?P<unit>[亿万元]+)")
P_RMB = PatternCollection(r"rmb|RMB")
P_NUMBER = re.compile(rf"[{R_CN_NUMBER}]")
P_THOUSAND_SEP = re.compile(r"[,，]")


R_DATE = r"\d{4}[年/\.—–-]\d{1,2}[月/\.—–-]\d{1,2}[日/\.—–-]?"
R_CONTAIN_DATE = r"([（(]含(该日)?[[)）])"
R_A_Z = re.compile(r"[A-Z]")
R_MSNYT = "MSNYT"
R_DMSNYT = f"天{R_MSNYT}"
R_SECTION = [
    rf"[≤][{R_MSNYT}]",
    rf"[{R_MSNYT}][〈＜<]",
    rf"[{R_MSNYT}][≥]",
    r"持有期大于\d+[天万][（(]含[)）]",
    r"\d+[天万]以上[（(]含",
    r"\d+[天万][（(]含[)）](以上|至\d+)",
    r"\d+[天万]以内",
    r"持有期小于\d+[天万]",
    r"\d+[万千元份]+以下",
    rf"^\d+{R_HYPHEN}\d+$",
]

R_PUBLIC_OFFERING = PatternCollection(r"公募|公开募集")

R_PUBLIC_PRIVATE_OFFERING = PatternCollection(
    [
        r"暂不向.*机构.*账户销售",
        r"(允许投资证券投资基金|(符合|有关)法律法规(及其他有关)?规定|中华人民共和国境内)[^,，。；;]*(个人投资者|机构投资者|合格境外投资者)",
        r"符合规定的私募.*以及其他符合(中国)?证监会",
        r"满足《基础设施基金指引》",
    ]
)


def gen_product_type_enum(answer, _text):
    if R_PUBLIC_OFFERING.nexts(_text) and not R_PUBLIC_PRIVATE_OFFERING.nexts(_text):
        return {"公募": None}
    if R_PUBLIC_PRIVATE_OFFERING.nexts(_text):
        return {"公募": None, "私募": None}
    return {"公募": None} if _text else {}


class UpgradeAnnouncement(JudgeByRegex):
    col_patterns = {
        "是否升降级": {
            "否": [r"(不再?|取消)[^,，]*[升降]+级"],
            "是": [".+"],
        },
    }


class Fund(JudgeByRegex):
    col_patterns = {
        "是否升降级": UpgradeAnnouncement.col_patterns["是否升降级"],
        "产品持有期单位": {
            "年": [r"年"],
            "月": [r"月"],
            "周": [r"周"],
            "天": [r"[天日]"],
        },
    }
    multi_answer_col_patterns = {
        "赎回限制类型": {
            "values": {
                "最短": [
                    r"最短|锁定",
                ],
                "滚动": [
                    r"滚动",
                    r"持有人.*未申请赎回",
                    r"第一个运作期.*第二个运作期",
                ],
            },
            "default": "不限",
        },
    }


class Prospectus(JudgeByRegex):
    col_patterns = {
        "是否升降级": UpgradeAnnouncement.col_patterns["是否升降级"],
        # "是否共用限额": {
        #     "是": [r"(?<!定投和转换转入的申请金额)合并?(进行)?(限制|计算)"],
        #     "否": [r"单独|分别|每个基金"],
        # },
        "限额控制模式": {
            "合并": [r"合并(进行限制|计算)"],
            "分级": [r"单独|分别"],
        },
        "分红方式修改": {
            "是": [r"可(自行)?选择"],
            "否": [r".*"],
        },
        "认购区间": {
            "M1<=M<M2": R_SECTION,
            "M1<M<=M2": [r".+"],
        },
        "申购区间": {
            "M1<=M<M2": R_SECTION,
            "M1<M<=M2": [r".+"],
        },
        "赎回区间": {
            "M1<=M<M2": R_SECTION,
            "M1<M<=M2": [r".+"],
        },
        "购买金额": {
            "份额（S）": [r"S"],
            "金额（M）": [r"M"],
            "持有期限（N）": [rf"[{R_DMSNYT}]"],
        },
        "升降级阈值类型": {
            "按持有份额": [r"份"],
            "按持有净资产": [r"元"],
            "按持有期限": [r"[年月日天周]"],
        },
        "最小值单位": {
            "年": [r"年"],
            "月": [r"月"],
            "周": [r"周"],
            "天": [r"[天日]"],
            "份": [r"份"],
            "元": [r"元"],
        },
        "最大值单位": {
            "年": [r"年"],
            "月": [r"月"],
            "周": [r"周"],
            "天": [r"[天日]"],
            "份": [r"份"],
            "元": [r"元"],
        },
    }
    multi_answer_col_patterns = {
        "产品销售对象": {
            "values": {
                "个人": [
                    r"个人投资者",
                    rf"符合法律法规规定的(?:(?:个人投资者|机构投资者|合格境外投资者)[{R_CONJUNCTION}]?){{3}}.以及法律法规或中国证监会允许购买证券投资基金的其他投资者",
                    r"暂不向.*机构.*账户.*?销售",
                ],
                "机构": [
                    r"公司",
                    r"机构投资者",
                    rf"符合法律法规规定的(?:(?:个人投资者|机构投资者|合格境外投资者)[{R_CONJUNCTION}]?){{3}}.以及法律法规或中国证监会允许购买证券投资基金的其他投资者",
                ],
                "产品": [
                    r"年金基金|基金养老保险|社会保障基金",
                    r"暂不向.*机构.*账户.*?销售",
                    r"资产管理产品",
                    rf"符合法律法规规定的(?:(?:个人投资者|机构投资者|合格境外投资者)[{R_CONJUNCTION}]?){{3}}.以及法律法规或中国证监会允许购买证券投资基金的其他投资者",
                    r"法律法规或中国证监会允许购买证券投资基金的其他投资人",
                ],
            },
        },
        "产品户类型": gen_product_type_enum,
        "赎回限制类型": Fund.multi_answer_col_patterns["赎回限制类型"],
    }


class Subscription(JudgeByRegex):
    col_patterns = {
        "是否升降级": Prospectus.col_patterns["是否升降级"],
        # "是否共用限额": Prospectus.col_patterns["是否共用限额"],
        "限额控制模式": Prospectus.col_patterns["限额控制模式"],
        "产品持有期单位": Fund.col_patterns["产品持有期单位"],
        "是否暂停、恢复大额申购、转换转入、定期定额投资": {
            "是": [r"是"],
            "否": [rf"否|{R_HYPHEN}|不适用"],
        },
    }
    multi_answer_col_patterns = {
        "产品销售对象": Prospectus.multi_answer_col_patterns["产品销售对象"],
        "产品户类型": Prospectus.multi_answer_col_patterns["产品户类型"],
        "公告类型": {
            "values": {
                "暂停大额申购": [r"(暂停|调整|限制).*申购"],
                "恢复大额申购": [r"恢复.*申购"],
                "开放日常申购": [r"(?<!定期)开放(?!证券|债券|式指).*(日常|申购)"],
                "单个基金账户持有限额": [r"单个基金账户"],
            }
        },
        "赎回限制类型": Fund.multi_answer_col_patterns["赎回限制类型"],
    }


class Information(JudgeByRegex):
    col_patterns = {
        "产品持有期单位": Fund.col_patterns["产品持有期单位"],
        "认购区间": Prospectus.col_patterns["认购区间"],
        "申购区间": Prospectus.col_patterns["申购区间"],
        "赎回区间": Prospectus.col_patterns["赎回区间"],
        # "认购": Prospectus.col_patterns["认购"],
    }
    multi_answer_col_patterns = {
        "赎回限制类型": Fund.multi_answer_col_patterns["赎回限制类型"],
    }


class Announcement(JudgeByRegex):
    multi_answer_col_patterns = {
        "产品户类型": Prospectus.multi_answer_col_patterns["产品户类型"],
        "产品销售对象": Prospectus.multi_answer_col_patterns["产品销售对象"],
    }


class RateAdjustment(JudgeByRegex):
    col_patterns = {
        "申购区间": Prospectus.col_patterns["申购区间"],
        "购买金额": Prospectus.col_patterns["购买金额"],
        "赎回区间": Prospectus.col_patterns["赎回区间"],
        "认购区间": Prospectus.col_patterns["认购区间"],
    }


class Prophet(BaseProphet):
    def parse_enum_value(self, predictor_result, schema):
        if self.enum_predictor:
            return self.enum_predictor.predict(predictor_result, schema)
        return None

    def get_enum_predictor(self):
        enum_classes = {
            "升降级公告": UpgradeAnnouncement,
            "基金合同": Fund,
            "招募说明书": Prospectus,
            "申购调整公告": Subscription,
            "产品资料概要": Information,
            "产品发售公告": Announcement,
            "费率调整公告": RateAdjustment,
        }
        if predictor := (enum_classes.get(self._mold.name) or enum_classes.get(clean_txt(self._mold.name))):
            return predictor()

    @staticmethod
    def rate_format(answer_reader: AnswerReader, answer_item: AnswerItem):
        text = answer_item.plain_text
        if not P_NUMBER.search(text):
            text = "0"
        else:
            text = P_PERCENT.sub("", text)
        if answer_item.namepath.endswith(
            ("管理费率", "管理费", "销售服务费率", "销售服务费", "调整后管理费率", "调整后销售服务费率")
        ):
            with suppress(ValueError):
                text = f"{float(text):.4f}"
        answer_item.data[0]["text"] = text
        return answer_item

    @staticmethod
    def amount_format(answer_reader: AnswerReader, answer_item: AnswerItem):
        unit = ""
        text = answer_item.plain_text
        answer_item.data[0]["text"] = P_THOUSAND_SEP.sub("", text)
        if P_RMB.nexts(text) or not P_MONEY_UNIT.nexts(text):
            return answer_item
        amount = ConvertText.convert_number_text(text + unit)
        answer_item.data[0]["text"] = "{:.2f}".format(Decimal(amount))
        return answer_item

    @staticmethod
    def clean_text(answer_reader: AnswerReader, answer_item: AnswerItem):
        answer_item.data[0]["text"] = clean_text(answer_item.plain_text)
        return answer_item

    @staticmethod
    def management_fee_fund_name(answer_reader: AnswerReader, answer_item: AnswerItem):
        if answer_item.plain_text in ("本基金",):
            if nodes := answer_reader.find_nodes(["基金名称"]):
                answer_item.data = nodes.pop().data.data
        return answer_item

    @staticmethod
    def sales_target(answer_reader: AnswerReader, answer_item: AnswerItem):
        neglect_multi_answer_col_patterns = {
            "values": {
                "机构": [
                    r"不向.*?机构.*?账户.*?销售",
                ],
            },
        }
        text = clean_txt("".join(answer_item.get_data_texts()))
        for val, patterns in neglect_multi_answer_col_patterns.get("values", {}).items():
            if PatternCollection(patterns).nexts(text) and val in answer_item.value:
                answer_item.value.remove(val)

        return answer_item

    @classmethod
    def post_process_handler(cls, mold_name: str, answer_item: AnswerItem):
        handlers = {
            "费率调整公告": {
                "调整后管理费率_基金名称": cls.management_fee_fund_name,
            }
        }
        if answer_item.namepath.endswith(("费率", "服务费", "管理费")):
            return cls.rate_format
        if answer_item.namepath.endswith(("金额", "限额")) and answer_item.namepath not in (
            "是否共用限额",
            "单客户每日累计申购、转入限额",
            "认购费率_购买金额",
            "申购费率_购买金额",
            "赎回费率_购买金额",
            "单客户每日累计认购限额",
        ):
            return cls.amount_format

        if answer_item.namepath.endswith(("基金名称", "基金简称", "产品简称")):
            return cls.clean_text

        if answer_item.namepath.endswith("产品销售对象"):
            return cls.sales_target

        return handlers.get(mold_name, {}).get(answer_item.namepath)

    def combine_minimum_amount(self, answer_reader: AnswerReader, answer_items):
        for schema in (
            "首次申购下限",
            "追加申购下限",
            "首次认购下限",
            "追加认购最低金额",
            "单笔申购下限",
            "销售服务费率",
        ):
            nodes = list(answer_reader.find_nodes([schema]))
            nodes.sort(key=operator.attrgetter("fullpath"))
            temp_dict = {}
            delete_nodes = []
            for node in nodes:
                for name, item in node.items():
                    answer_items.remove(AnswerItem(**item.data).to_dict())
                    if (matcher := R_A_Z.search(item.data.origin_text)) and "基金名称" in name:
                        page, outline = (
                            item.data.data[0]["boxes"][0]["page"],
                            box_to_outline(item.data.data[0]["boxes"][0]["box"]),
                        )
                        etype, elt = self.reader.find_element_by_outline(page, outline)
                        if matcher.group() in temp_dict and etype != temp_dict[matcher.group()]:
                            delete_nodes.append(node)
                        elif matcher.group() not in temp_dict:
                            temp_dict[matcher.group()] = etype
            nodes = list(set(nodes) - set(delete_nodes))
            nodes.sort(key=operator.attrgetter("fullpath"))
            for index, node in enumerate(nodes):
                for _, item in node.items():
                    answer_item = AnswerItem(**item.data)
                    if index != node.idx:
                        keys = json.loads(answer_item.key)
                        keys[1] = f"{schema}:{index}"
                        answer_item.key = json.dumps(keys, ensure_ascii=False)
                    answer_items.append(answer_item.to_dict())
        return answer_items

    @staticmethod
    def keep_with_only_enum(mold_name):
        """
        例,mold:申购调整公告, 仅[公告类型]字段的枚举值为[暂停大额申购]时,才提取: '恢复大额申购、转换金额' 、'恢复大额申购、转换起始日'
        :return:
        """
        data = {
            "申购调整公告": {
                "公告类型": {
                    "恢复大额申购、转换金额": ["暂停大额申购"],
                    "恢复大额申购、转换起始日": ["暂停大额申购"],
                    "恢复大额申购、转换转入及定期定额投资业务时间": ["暂停大额申购"],
                    "申购开放周期-开始日期": ["开放日常申购"],
                    "申购开放周期-结束日期": ["开放日常申购"],
                    "赎回开放周期-开始日期": ["开放日常申购"],
                    "赎回开放周期-结束日期": ["开放日常申购"],
                    "滚动期开放天数": ["开放日常申购"],
                    "单笔申购上限": ["开放日常申购"],
                    "申购基数": ["开放日常申购"],
                    "单笔赎回上限": ["开放日常申购"],
                    "赎回基数": ["开放日常申购"],
                    "基金转出最高份额": ["开放日常申购"],
                },
            }
        }
        return data.get(mold_name, {})

    def get_fields_need_pop(self, answer_reader):
        """
        需要丢掉的字段
        :param answer_reader:
        :return:
        """
        all_pop_fields = []
        for field, configs in self.keep_with_only_enum(answer_reader.mold_name).items():
            value = None
            if nodes := answer_reader.find_nodes([field]):
                value = list(nodes)[0].data.value
            value = value or None
            pop_fields = self.fields_need_pop(configs, value)
            all_pop_fields.extend(pop_fields)

        return all_pop_fields

    @staticmethod
    def fields_need_pop(configs, value):
        ret = []
        for key, values in configs.items():
            if isinstance(value, list):
                if not set(value).intersection(values):
                    ret.append(key)
            elif value not in values:
                ret.append(key)

        return ret

    def post_process(self, preset_answer):
        answer_reader = AnswerReader(preset_answer)
        answer_items = []
        all_pop_fields = []

        if not answer_reader.find_nodes(["单笔申购下限"]):
            all_pop_fields.append("单笔申购下限-原文")

        for item in answer_reader.items:
            answer_item = AnswerItem(**item)
            label = answer_item.schema["data"]["label"]
            if label in all_pop_fields:
                logger.info(f"post_process pop: {label}")
                continue

            if not answer_item.is_empty:
                if post_handler_func := self.post_process_handler(answer_reader.mold_name, answer_item):
                    answer_item = post_handler_func(answer_reader, answer_item)
            answer_items.append(answer_item.to_dict())
        answer_items = self.combine_minimum_amount(answer_reader, answer_items)
        preset_answer["userAnswer"]["items"] = answer_items
        return preset_answer
