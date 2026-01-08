import json
import logging
import time
from dataclasses import dataclass
from operator import itemgetter
from typing import Any, ClassVar, Literal

import httpx
from pydantic import Field, field_validator
from redis import Redis

from remarkable.answer.node import AnswerItem
from remarkable.answer.reader import AnswerReader
from remarkable.common.diff.para_similarity import SimilarPara
from remarkable.config import get_config
from remarkable.db import init_rdb, pw_db
from remarkable.hooks.base import PredictFinishHook
from remarkable.models.new_user import NewAdminUser
from remarkable.pw_models.model import MoldWithFK
from remarkable.pw_models.question import QuestionWithFK
from remarkable.service.chatgpt import LLMSchema, OpenAIClient
from remarkable.service.new_question import NewQuestionService

logger = logging.getLogger(__name__)


@dataclass
class RateLimiter:
    KEY: ClassVar[str] = "rate_limit:cmbchina:openai"
    client: Redis

    limit: int = get_config("ai.openai.rate_limit.limit") or 5
    interval: int = get_config("ai.openai.rate_limit.interval") or 10

    @property
    def count(self):
        if count := self.client.get(self.KEY):
            return int(count)
        self.client.set(self.KEY, 1, ex=self.interval)
        return 1

    def __enter__(self):
        while True:
            if self.count <= self.limit:
                break
            time.sleep(1)  # 一直等到key过期才能继续执行
        self.client.incr(self.KEY)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class _EnumMixin:
    _MAP: dict
    answer: list[Any] | Any

    @property
    def enum(self):
        if isinstance(self.answer, list):
            return [self._MAP[v] for v in self.answer]
        return self._MAP[self.answer]


class LLMWithReasonSchema(LLMSchema):
    _MAP: ClassVar[dict]
    assistant: ClassVar[list] = []
    reason: str = Field(default="")


class ProductSaleTargetSchema(LLMWithReasonSchema, _EnumMixin):
    _MAP = {0: "机构", 1: "个人", 2: "产品"}

    answer: list[Literal[0, 1, 2]] = Field(
        description="""
0表示机构, 1表示个人, 2表示产品, 可以多选

1. 如果文本描述是符合法律规定的各类投资者, 并且没有后缀或特殊说明某类机构或投资者或XX机构自营账户不能购买时，选择0,1,2;

2. 只要文本描述提到参与投资的各类公司/机构以及产品名称（例如：年金基金/基金养老保险/全国社会保障基金）还有符合规定的专业个人/机构投资者, 并且没有说明某类机构或投资者或XX机构自营账户不能购买时, 选择0,1,2;

3. 如果文本描述是符合法律规定的各类投资者，但还补充说明 某类机构不能进行购买/暂不向XX机构[自营账户]销售, 则代表只能选择个人或产品，机构类型的投资者不能进行选择；

4. 如果文本描述是 `暂不向XX机构销售` 或者 `不向XX机构自营账户销售` 的，选择2, 不能选择0;
    """
    )


class ProductAccountTypeSchema(LLMWithReasonSchema, _EnumMixin):
    _MAP = {"GM": "公募", "SM": "私募"}

    answer: list[Literal["GM", "SM"]] = Field(
        description="""
GM表示公募, SM表示私募, 可以多选
描述是 `本基金仅向个人投资者（含公募资产管理产品）公开销售`, 选择GM;
描述是 `暂不向XX机构销售`, 选择GM,SM;
其他情况选择GM,SM;
        """
    )


class IsUpDownSchema(LLMWithReasonSchema, _EnumMixin):
    _MAP = {"Y": "是", "N": "否"}
    answer: Literal["Y", "N"] = Field(
        description="""
Y表示是, N表示否
判断为Y-是；描述通常是针对两类基金在（份额数或者持有年限）到达某个值时自动升级为上一级的基金份额类型，或者（份额数或者持有年限）少于某份额数或年限时自动降级为下一级的基金份额类型，
一般是对升降级规则业务的描述文本；【特殊公告】还有部分公告中并未做取消升降级规则处理，只是针对某类销售机构仅单独出售某一类基金时做暂不参与基金升降级规则的处理，这类描述并不是取消，依然判断为Y-是；
判断为N-否；仅针对该类文档或公告明确告知在某个时间点取消了某两类基金份额的升降级业务，这类的文本描述则判断为N-否
"""
    )


class IsShareLimitSchema(LLMWithReasonSchema, _EnumMixin):
    _MAP = {"Y": "是", "N": "否"}
    answer: Literal["Y", "N"] = Field(
        description="""
Y表示是, N表示否
通常是描述2类基金份额及以上的基金限制金额是属于合并计算时，判断为Y-是；通常是有关键词‘合并’或者‘合并计算’的文本描述；判断为Y-是;
通常是描述2类基金份额及以上的基金限制金额是属于单独计算时，判断为N-否；通常是有关键词‘单独’或者‘单独进行判断’的文本描述；判断为N-否;
"""
    )


class QuotaCtlModeSchema(LLMWithReasonSchema, _EnumMixin):
    _MAP = {"merged": "合并", "graded": "分级"}
    answer: Literal["merged", "graded"] = Field(
        description="""
描述2类基金份额及以上的基金限制金额是属于合并计算时，判断为merged；
有关键词‘合并’或者‘合并计算’的文本描述，判断为merged；
描述2类基金份额及以上的基金限制金额是属于单独计算时，判断为graded;
有关键词‘单独’或者‘单独进行判断’的文本描述时,判断为graded;
    """
    )


class RedemptionControlSchema(LLMWithReasonSchema, _EnumMixin):
    _MAP = {"SHORT": "最短", "CUSTOMER": "滚动", "NULL": "不限"}
    answer: Literal["SHORT", "CUSTOMER", "NULL"] = Field(
        description="""
有关键词"最短持有期""锁定持有期”多少天或者年限时, 判断为SHORT；
有关键词“滚动持有期”多少天或者年限, 判断为CUSTOMER;
其他情况判断为NULL;
        """
    )


class HoldingPeriodSchema(LLMWithReasonSchema):
    answer: int = Field(
        description="""
提取数字, 比如一年返回1, 3个月返回3
    """
    )

    @field_validator("answer")
    @classmethod
    def format_period(cls, value):
        return f"{value:.2f}"


class HoldingPeriodUnitSchema(LLMWithReasonSchema, _EnumMixin):
    _MAP = {"YEAR": "年", "MONTH": "月", "WEEK": "周", "DAY": "天"}
    answer: Literal["YEAR", "MONTH", "WEEK", "DAY"] = Field(
        description="""
提取单位, YEAR表示年, MONTH表示月, WEEK表示周, DAY表示天
    """
    )


class MoneyOrLiteralSchema(LLMWithReasonSchema):
    answer: Literal["无限额", "原始值"] | int | float = Field(
        description="""
如果文本中有恢复到原来值类似描述，返回“原始值”；

如果文本中是正常金额数值，转换为“元”后，返回正常金额数值，不带单位（假如1万元，返回10000，不带单位）,转换后如果是整数, 返回int, 如果有小数返回float

如果文本中有无限额相关描述, 可能还会有50%类似的描述或者没有提到恢复到原来值的类似描述, 返回“无限额”；
        """
    )

    assistant = [
        {
            "role": "user",
            "content": "基金管理人可以对募集期间的单个投资人的累计认购金额进行限制具体限制和处理方法请参见基金份额发售公告或相关公告。",
        },
        {
            "role": "assistant",
            "content": '{"answer":"无限额"}',
        },
    ]


class FormatMoneySchema(MoneyOrLiteralSchema):
    @field_validator("answer")
    @classmethod
    def format_money(cls, value):
        if isinstance(value, (int, float)):
            return f"{value:.2f}"
        return value


class HoldMaxUnitSchema(LLMWithReasonSchema, _EnumMixin):
    _MAP = {"0": "份额", "1": "金额"}
    answer: Literal["0", "1"] = Field(
        description="""
0表示份额；1表示金额;
        """
    )


class StandardDateSchema(LLMWithReasonSchema):
    answer: str = Field(
        pattern=r"\d{4}-\d{2}-\d{2}",
        description="""
将字符串中的日期转为YYYY-MM-DD的形式
    """,
    )


class MoneyWithRangeSchema(LLMWithReasonSchema):
    answer: float = Field(
        ge=0.01, le=99_999_999_999_999.99, description="""从字符串中提取数字, 范围为0.01-99,999,999,999,999.99"""
    )

    @field_validator("answer", mode="after")
    def format_money(cls, value):
        return f"{value:,.2f}"


class NumberWithUnitSchema(LLMWithReasonSchema):
    answer: str | None = Field(
        description="""提取数字, 如果是金额或者百分比, 保留2位小数, 带单位, 例:100.00万/1.50%/30天, 使用字符串中出现的单位, 如果提到不收取返回null""",
        pattern=r"\d+\.\d{2}亿?千?百?万?%?|\d+天?",
    )


class MoneyDescCodeSchema(LLMWithReasonSchema, _EnumMixin):
    _MAP = {"S": "份额（S）", "M": "金额（M）", "N": "持有期限（N）"}
    answer: Literal["S", "M", "N"] = Field(
        description="""
        提取对应的枚举值, 份额S；金额M； 除了前面两种，其他都是 持有期限N, 比如：Y，T，N
        """
    )


class FeeTypeSchema(LLMWithReasonSchema, _EnumMixin):
    _MAP = {"0": "认购费", "1": "申购费"}
    answer: Literal["0", "1"] = Field(description="""提取枚举值, 0-认购费；1-申购费""")


class FeeTimeSchema(LLMWithReasonSchema, _EnumMixin):
    _MAP = {"0": "前收费", "1": "后收费"}
    answer: Literal["0", "1"] = Field(
        description="""
提取枚举值, 0-前收费；1-后收费
前收费：前端收费、前收费
后收费：后端收费、后收费
    """
    )


class DividendTypeSchema(LLMWithReasonSchema, _EnumMixin):
    _MAP = {"0": "红利再投资", "1": "现金分红"}
    answer: Literal["0", "1"] = Field(description="""提取枚举值, 0-红利再投资；1-现金分红""")


class DividendTypeChangeableSchema(LLMWithReasonSchema, _EnumMixin):
    _MAP = {"0": "否", "1": "是"}
    answer: Literal["0", "1"] = Field(description="""提取枚举值, 0-否；1-是""")


class RegistrationSystemSchema(LLMWithReasonSchema, _EnumMixin):
    _MAP = {"0": "自建", "1": "中登"}
    answer: Literal["0", "1"] = Field(
        description="""
提取枚举值
0-自建, 1-中登;
如果公告出现“证券登记系统”“上海证券账户”、“深证证券账户”，则为中登，否则，返回自建
不能返回上述未提及的类型
    """
    )


class PurchaseConfirmDateSchema(LLMWithReasonSchema):
    answer: Literal["0", "1", "2", "3", "4", "5", "6", "7", "8"] | None = Field(
        description="""将提取的交易确认日期转为数字, 比如T+0转为0, T转为null"""
    )


class ThresholdUnitSchema(LLMWithReasonSchema, _EnumMixin):
    """份:P，元:A，天:D，周:W，月:m，年:Y"""

    _MAP = {"P": "份", "A": "元", "D": "天", "W": "周", "m": "月", "Y": "年"}
    answer: Literal["P", "A", "D", "W", "m", "Y"] = Field(
        description="""
提取单位, P表示份, A表示元, D表示天, W表示周, m表示月, Y表示年

份：只要文本中含有份
元：只要文本中含有元
天：只要文本中含有天
周：只要文本中含有周
月：只要文本中含有月
年：只要文本中含有年

不能返回上述未提及的类型
    """
    )


class FixedDigitNumberSchema(LLMWithReasonSchema):
    answer: float | None = Field(
        description="""
从文本中只提取数字, 无需带单位
如果不是中文数字和阿拉伯数字, 也不是金额, 返回null, 比如50个工作日, 三年, 9个月都需要返回null
对于金额，需转化为用元作为单位的数值
对于中文的数字, 统一转换为阿拉伯数字, 比如`一` -> 1, `三万` -> 30000
        """,
    )

    @field_validator("answer")
    def format_money(cls, value):
        if value is None:
            return value
        return f"{value:.2f}"


class ThresholdTypeSchema(LLMWithReasonSchema, _EnumMixin):
    """P-按持有份额，N-按持有净资产，T-按持有期限"""

    _MAP = {"P": "按持有份额", "N": "按持有净资产", "T": "按持有期限"}

    answer: Literal["P", "N", "T"] = Field(
        description="""
提取升降级阈值类型, P-按持有份额，N-按持有净资产，T-按持有期限

按持有份额：只要文本中含有份
按持有净资产：只要文本中含有元
按持有期限：只要文本中含有天、周、月和年
        """
    )


INSTITUTIONS = {
    "东莞市商业银行": "001",
    "中国工商银行": "002",
    "中国农业银行": "003",
    "中国银行": "004",
    "中国建设银行": "005",
    "交通银行": "006",
    "招商银行": "007",
    "中信银行": "008",
    "浦东发展银行": "009",
    "江西银行股份有限公司": "010",
    "上海银行": "011",
    "兴业银行": "012",
    "中国光大银行": "013",
    "民生银行": "014",
    "北京市商业银行": "015",
    "平安银行股份有限公司": "017",
    "农村信用合作社": "018",
    "北京农村商业银行": "019",
    "大连市商业银行": "020",
    "平安银行": "021",
    "徽商银行": "022",
    "广州农村商业银行": "023",
    "山西河津农村商业银行": "024",
    "浙江杭州农村商业银行": "025",
    "锦州银行": "026",
    "宁波慈溪农商行": "027",
    "廊坊银行": "028",
    "广东顺德农商行": "029",
    "晋城银行": "030",
    "昆仑银行": "031",
    "天津银行": "032",
    "盛京银行": "033",
    "潮安农信社": "034",
    "江西银行": "035",
    "重庆三峡银行": "036",
    "北京银行": "037",
    "江苏吴江农商行": "038",
    "宁波银行": "039",
    "靖江农商行": "040",
    "广东华兴银行": "041",
    "华润银行": "042",
    "安溪县农村信用合作社": "043",
    "邯郸银行": "044",
    "安徽歙县农村商业银行": "045",
    "南洋商业银行": "046",
    "成都银行": "047",
    "珠海农商行": "048",
    "宁波鄞州农商行": "049",
    "张家口银行": "050",
    "承德银行": "051",
    "东莞银行": "052",
    "唐山银行": "053",
    "华夏银行": "054",
    "南海农商银行": "055",
    "大连银行": "056",
    "广发银行": "060",
    "景德镇农村商业银行": "064",
    "上海农村商业银行": "072",
    "温州银行": "075",
    "江苏银行": "076",
    "渤海银行": "077",
    "杭州银行": "078",
    "桐庐农村合作银行": "079",
    "深圳农村商业银行": "080",
    "浙江民泰商业银行": "081",
    "浙江稠州商业银行": "082",
    "浙江泰隆商业银行": "083",
    "龙湾农商银行": "085",
    "浙商银行": "086",
    "绍兴银行": "087",
    "微商银行": "088",
    "保定银行": "090",
    "新疆昌吉农村商业银行": "092",
    "长安银行": "100",
    "上饶市商业银行": "112",
    "珠海华润银行": "119",
    "泸州银行": "130",
    "杭州联合银行": "131",
    "石嘴山银行": "132",
    "安徽蒙城农商行": "133",
    "国泰君安": "201",
    "海通证券": "202",
    "包商银行": "261",
    "齐鲁银行": "262",
    "龙江银行": "270",
    "广州银行": "413",
    "汉口银行": "603",
    "九江银行": "607",
    "西安银行": "611",
    "包商小马BANK": "612",
    "恒丰银行": "614",
    "常熟农商银行": "615",
    "东莞农村商业银行": "616",
    "鄂尔多斯农商银行": "617",
    "福建海峡银行": "618",
    "抚顺银行": "619",
    "甘肃银行": "620",
    "赣州银行": "621",
    "广东南粤银行": "622",
    "贵阳银行": "623",
    "桂林银行": "624",
    "河北银行": "625",
    "湖北银行": "626",
    "湖州银行": "627",
    "华融湘江银行": "628",
    "黄河农村商业银行": "629",
    "吉林银行": "630",
    "嘉兴银行": "631",
    "江阴农村商业银行": "633",
    "金华银行": "634",
    "晋商银行": "635",
    "兰州银行": "636",
    "临商银行": "637",
    "柳州银行": "638",
    "洛阳银行": "639",
    "内蒙古银行": "640",
    "宁波通商银行": "641",
    "宁夏银行": "642",
    "攀枝花市商业银行": "643",
    "齐商银行": "644",
    "青岛银行": "645",
    "泉州银行": "646",
    "厦门银行": "647",
    "台州银行": "648",
    "天津滨海农商银行": "649",
    "天津农商银行": "650",
    "威海市商业银行": "651",
    "乌鲁木齐商业银行": "652",
    "无锡农村商业银行": "653",
    "武汉农村商业银行": "654",
    "烟台银行": "655",
    "长沙银行": "656",
    "郑州银行": "657",
    "重庆农村商业银行": "658",
    "紫金农商银行": "659",
    "中原银行": "660",
    "贵州银行": "661",
    "中信百信银行": "662",
    "江苏江南农商行": "663",
    "浙江网商银行": "664",
    "河北沧州农商行": "665",
    "广东四会农商行": "666",
    "吉林九台农商行": "667",
    "招商证券": "801",
    "广西北部湾银行": "802",
    "中泰证券": "803",
    "广发证券": "804",
    "中信证券": "805",
    "华泰证券": "806",
    "国信证券": "807",
    "安信证券": "808",
    "申万宏源证券": "809",
    "兴业证券": "810",
    "中国银河证券": "811",
    "南京银行": "826",
    "中央结算公司": "900",
    "中国工商银行广州分行": "901",
    "中国银联": "902",
    "苏州银行": "905",
    "哈尔滨银行": "993",
    "浙江杭州余杭农村商业银行股份有限公司": "994",
    "德意志银行": "995",
    "汇丰银行": "997",
    "花旗银行上海分行": "998",
    "渣打银行": "999",
    "中国邮储银行": "A15",
    "中国证券登记结算有限责任公司": "A21",
    "中国证券金融股份有限公司": "A25",
    "中信建投证券": "A26",
    "中国国际金融股份有限公司": "A27",
    "恒泰证券": "A28",
    "东方证券": "A30",
    "华鑫证券": "A33",
    "光大证券": "A34",
    "华福证券": "A35",
    "万联证券": "A36",
    "华安证券": "A37",
    "国元证券": "A38",
    "财通证券": "A39",
    "国金证券": "A40",
    "长城证券": "A41",
    "长江证券": "A42",
    "浙商证券": "A43",
    "南京证券": "A44",
}


def init_llm_fields():
    fields = {}
    for field, schema in (
        ("产品销售对象", ProductSaleTargetSchema),
        ("产品户类型", ProductAccountTypeSchema),
        ("是否升降级", IsUpDownSchema),
        ("是否共用限额", IsShareLimitSchema),
        ("限额控制模式", QuotaCtlModeSchema),
        ("赎回限制类型", RedemptionControlSchema),
        ("产品持有期", HoldingPeriodSchema),
        ("产品持有期单位", HoldingPeriodUnitSchema),
        ("单客户持仓上限单位", HoldMaxUnitSchema),
        ("单客户持有上限单位", HoldMaxUnitSchema),
        # 保留两位小数的金额
        ("首次认购下限_最低限额", FormatMoneySchema),
        ("首次申购下限_最低限额", FormatMoneySchema),
        ("单笔申购下限_最低限额", FormatMoneySchema),
        ("单笔赎回下限_最低限额", FormatMoneySchema),
        ("单笔持仓下限_最低限额", FormatMoneySchema),
        ("单笔认购下限_最低限额", FormatMoneySchema),
        ("追加申购下限_最低限额", FormatMoneySchema),
        ("追加认购最低金额_最低限额", FormatMoneySchema),
        ("追加认购最低金额_最低限额", FormatMoneySchema),
        ("基金转出最低份额-最低限额", FormatMoneySchema),
        ("单客户每日累计申购、转入限额", FormatMoneySchema),
        ("单客户每日累计认购限额", FormatMoneySchema),
        ("单笔赎回下限", FormatMoneySchema),
        ("单笔认购上限", FormatMoneySchema),
        ("首次认购上限", FormatMoneySchema),
        ("单客户持仓上限", FormatMoneySchema),
        ("恢复大额申购、转换金额", FormatMoneySchema),
        ("基金转出最高份额", FormatMoneySchema),
        # 金额
        ("分类基金_限制申购金额", MoneyOrLiteralSchema),
        ("分类基金_限制转换转入金额", MoneyOrLiteralSchema),
        ("分类基金_主基金限制申购金额", MoneyOrLiteralSchema),
        ("分类基金_主基金限制转换转入金额", MoneyOrLiteralSchema),
        # 日期
        ("管理费率优惠开始日期", StandardDateSchema),
        ("管理费率优惠结束日期", StandardDateSchema),
        ("销售服务费率优惠开始日期", StandardDateSchema),
        ("销售服务费率优惠结束日期", StandardDateSchema),
        ("募集开始日期", StandardDateSchema),
        ("募集结束日期", StandardDateSchema),
        ("调整或延长后时间", StandardDateSchema),
        ("募集开始时间", StandardDateSchema),
        ("费率生效日期", StandardDateSchema),
        ("暂停、取消、生效时间", StandardDateSchema),
        ("暂停、恢复申购起始日", StandardDateSchema),
        ("暂停、恢复赎回起始日", StandardDateSchema),
        ("暂停、恢复转换转入起始日", StandardDateSchema),
        ("暂停、恢复转换转出起始日", StandardDateSchema),
        ("暂停、恢复定期定额投资起始日", StandardDateSchema),
        ("持有份额限制起始日", StandardDateSchema),
        ("恢复大额申购、转换转入及定期定额投资业务时间", StandardDateSchema),
        ("恢复大额申购、转换起始日", StandardDateSchema),
        ("产品成立日", StandardDateSchema),
        ("申购开放周期-开始日期", StandardDateSchema),
        ("申购开放周期-结束日期", StandardDateSchema),
        ("赎回开放周期-开始日期", StandardDateSchema),
        ("赎回开放周期-结束日期", StandardDateSchema),
        # 基数
        ("申购基数", MoneyWithRangeSchema),
        ("赎回基数", MoneyWithRangeSchema),
        # 保留两位小数且带单位
        ("认购费率_区间起始值", NumberWithUnitSchema),
        ("认购费率_区间结束值", NumberWithUnitSchema),
        ("申购费率_区间起始值", NumberWithUnitSchema),
        ("申购费率_区间结束值", NumberWithUnitSchema),
        ("赎回费率_区间起始值", NumberWithUnitSchema),
        ("赎回费率_区间结束值", NumberWithUnitSchema),
        # 费率
        ("认购费率_认购费", NumberWithUnitSchema),
        ("申购费率_申购费", NumberWithUnitSchema),
        ("赎回费率_赎回费", NumberWithUnitSchema),
        # 认购费率/申购费率/赎回费率下的购买金额
        ("认购费率_购买金额", MoneyDescCodeSchema),
        ("申购费率_购买金额", MoneyDescCodeSchema),
        ("赎回费率_购买金额", MoneyDescCodeSchema),
        # 默认分红方式下的默认分红
        ("默认分红方式_默认分红", DividendTypeSchema),
        # 收费方式
        ("收费方式_收费", FeeTimeSchema),
        ("收费方式_费用类型", FeeTypeSchema),
        # `是否支持分红方式修改` 下的 `分红方式修改`, `份额登记系统`
        ("是否支持分红方式修改_分红方式修改", DividendTypeChangeableSchema),
        ("是否支持分红方式修改_份额登记系统", RegistrationSystemSchema),
        # 交易确认日期
        ("认购交易确认日期", PurchaseConfirmDateSchema),
        ("申购交易确认日期", PurchaseConfirmDateSchema),
        ("赎回交易确认日期", PurchaseConfirmDateSchema),
        # 升降级阈值
        ("升降级阈值_最大值单位", ThresholdUnitSchema),
        ("升降级阈值_最小值单位", ThresholdUnitSchema),
        ("升降级阈值_最大值", FixedDigitNumberSchema),
        ("升降级阈值_最小值", FixedDigitNumberSchema),
        ("升降级阈值_升降级阈值类型", ThresholdTypeSchema),
    ):
        fields[field] = {
            "prompt": f"""
你是一个专门处理财报文档的AI助手, 请帮我从给定的文本中总结出{field}, 严格按照给定的规则执行

Return the answer as a Pydantic object. The Pydantic schema is given below:

{schema.model_json_schema()}

Output a valid JSON object but do not repeat the schema.
    """,
            "schema": schema,
        }
    return fields


FIELDS = init_llm_fields()


@dataclass
class _LLMConverter:
    answer_reader: AnswerReader
    client: OpenAIClient

    def __call__(self):
        rdb = init_rdb()
        for item in self.answer_reader.items:
            answer_item = AnswerItem(**item)
            origin_text = answer_item.simple_text(enum=False)
            if isinstance(origin_text, list):
                origin_text = "\n".join(origin_text)
            # 托管机构单独处理, 使用相似度匹配
            if answer_item.namepath == "托管机构":
                item["zyt_value"] = None
                if origin_text is None:
                    pass
                elif origin_text in INSTITUTIONS:
                    item["zyt_value"] = INSTITUTIONS[origin_text]
                else:
                    code_with_score = []
                    for name, code in INSTITUTIONS.items():
                        score = SimilarPara.get_para_similarity(origin_text, name)
                        # 如果开头的字符串完全匹配, 认为是完全匹配
                        if origin_text.startswith(name) or name.startswith(origin_text):
                            code_with_score.append((1, code))
                        # 如果其中一个在另外一个中, 相似度为0.8
                        elif origin_text in name or name in origin_text:
                            code_with_score.append((0.8, code))
                        elif score >= 0.8:
                            code_with_score.append((score, code))
                    for _, code in sorted(code_with_score, key=itemgetter(0), reverse=True):
                        item["zyt_value"] = code
                        break
                continue
            if not (field := FIELDS.get(answer_item.namepath)):
                continue
            # if "购买金额" not in answer_item.namepath:
            #     continue
            item["zyt_value"] = None
            if origin_text is None:
                continue
            logger.info(f"{answer_item.key}: {origin_text=} schema={field['schema']}")
            try:
                with RateLimiter(rdb):
                    ans = self.client.send_message(
                        [
                            {"role": "system", "content": field["prompt"]},
                            *field["schema"].assistant,
                            {"role": "user", "content": origin_text},
                        ]
                    )
                logger.info(f"{ans=}")
                value = field["schema"].from_llm(ans)
                logger.info(f"{value=}")
                if value.answer is None:
                    zyt_value = None
                elif isinstance(value.answer, list):
                    zyt_value = ";".join(str(s) for s in value.answer)
                else:
                    zyt_value = str(value.answer)
                item["zyt_value"] = zyt_value
                item["value"] = getattr(value, "enum", None)
            except Exception as e:
                logger.exception(e)


class CMBChinaPredictFinishHook(PredictFinishHook):
    name = "cmbchina"

    async def __call__(self):
        from remarkable.converter.cmbchina import CMBChinaConverter

        file = self.question.file
        user = await NewAdminUser.get_by_id(file.uid)
        questions = await pw_db.prefetch(
            QuestionWithFK.select().where(QuestionWithFK.file == file), MoldWithFK.select()
        )
        answers = []
        llm_client = OpenAIClient()
        for question in questions:
            try:
                NewQuestionService.fill_group_with_fixed_length(question.preset_answer, self.question.mold, amount=10)
                NewQuestionService.fill_group_with_fixed_length(question.answer, self.question.mold, amount=10)
                answer_reader = AnswerReader(question.answer)
                logger.info(f"LLM Converter begin: {file.id=} {question.id=}")
                _LLMConverter(answer_reader, llm_client).__call__()
                logger.info(f"LLM Converter end: {file.id=} {question.id=}")
                await question.update_(
                    answer=question.answer
                )  # 大模型只处理了question.answer, 没有处理question.preset_answer
                converter = CMBChinaConverter(question)
                answer = converter.convert()
                answers.append(answer)
            except Exception as e:
                logger.exception(e)
                return

        if not (push_api := get_config("cmbchina.answer_push_api")):
            logging.warning("cmbchina.answer_push_api not configured")
            return

        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/5429#note_596570
        try:
            json.dumps(answers)
        except Exception as e:
            logger.info(e, f"{answers=}")

        async with httpx.AsyncClient(transport=httpx.AsyncHTTPTransport(retries=3)) as client:
            rsp = await client.post(
                push_api,
                headers={"Authorization": f"Basic {get_config('cmbchina.basic_auth')}"},
                json={
                    "answers": answers,
                    "user": {"id": user.id, "name": user.name},
                    "file_id": str(file.id),
                    "tree_id": str(file.tree_id),
                    "schema_ids": [q.mold.id for q in questions],
                },
            )
            body = rsp.json()
        if body["returnCode"] == "SUC0000":
            logging.info("answer push succeed")
        else:
            logging.error(f"answer push failed: {body}")
