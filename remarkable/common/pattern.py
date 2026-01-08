from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Match, Pattern

from attrs import define, field

from remarkable.common.protocol import SearchPatternLike

RE_TYPE = re.Pattern


@define(slots=True, eq=False)
class PatternCollection:
    patterns: None | str | list[str | Pattern] = field(default=None)
    flags: int = field(default=0)
    _pattern_objects: list[Pattern] = field(default=None)

    def __bool__(self):
        return bool(self.patterns)

    @property
    def pattern_objects(self):
        if not self._pattern_objects:
            self._pattern_objects = self._compile(self.patterns, self.flags)
        return self._pattern_objects

    @classmethod
    def _compile(cls, patterns, flags=0) -> list[Pattern]:
        pattern_list = []
        if patterns is None:
            return pattern_list
        if isinstance(patterns, str):
            pattern_list.append(re.compile(rf"{patterns}", flags))
        elif isinstance(patterns, RE_TYPE):
            pattern_list.append(patterns)
        elif isinstance(patterns, (tuple, list)):
            for pattern in patterns:
                pattern_list.extend(cls._compile(pattern, flags))
        return pattern_list

    def search(self, text):
        for pattern in self.pattern_objects:
            match = pattern.search(text)
            if match:
                yield match

    def nexts(self, text):
        return next(self.search(text), None)

    def match(self, text):
        for pattern in self.pattern_objects:
            match = pattern.match(text)
            if match:
                yield match

    def finditer(self, text):
        for pattern in self.pattern_objects:
            match = pattern.finditer(text)
            for item in match:
                if item:
                    yield item

    def sub(self, repl, text):
        for pattern in self.pattern_objects:
            text = pattern.sub(repl, text)
        return text

    def split(self, text, maxsplit=0):
        def _split(pattern: Pattern, texts: list[str]):
            vals = []
            for val in texts:
                vals.extend(pattern.split(val))
            return vals

        split_vals = [text]
        if isinstance(text, list):
            split_vals = text
        for pattern in self.pattern_objects:
            split_vals = _split(pattern, split_vals)
        if maxsplit > 0:
            return split_vals[:maxsplit]
        return split_vals

    def all(self, text):
        return all(pattern.search(text) for pattern in self.pattern_objects)


def _compile(pattern: Any, flag: int = 0) -> SearchPatternLike:
    if isinstance(pattern, str):
        return re.compile(pattern, flag)
    if isinstance(pattern, SearchPatternLike):
        return pattern
    raise TypeError(f"{pattern} is not a valid pattern")


def get_all_patterns(patterns: tuple[SearchPatternLike]) -> list[str]:
    all_patterns = []
    for pattern in patterns:
        if isinstance(pattern, re.Pattern):
            all_patterns.append(pattern.pattern)
        else:
            all_patterns.extend(get_all_patterns(pattern.patterns))

    return all_patterns


@dataclass
class SplitBeforeMatch:
    pattern: SearchPatternLike
    separator: Pattern
    operator: Callable[[Iterable], bool] = any

    def __hash__(self):
        return hash((self.pattern, self.separator))

    @classmethod
    def compile(
        cls,
        pattern: str | SearchPatternLike,
        separator: str,
        operator: Callable[[Iterable], bool] = any,
    ) -> "SplitBeforeMatch":
        return cls(_compile(pattern), re.compile(separator), operator)

    def split(self, string: str, pos: int = 0, endpos: int = sys.maxsize) -> Iterable[str]:
        start = 0
        for matched in self.separator.finditer(string, pos, endpos):
            yield string[start : matched.start()]
            start = matched.end()
        yield string[start:]

    def search(self, string: str, pos: int = 0, endpos: int = sys.maxsize) -> bool:
        return self.operator(self.pattern.search(text, pos, endpos) for text in self.split(string, pos, endpos))


@dataclass
class MatchMulti:
    patterns: tuple[SearchPatternLike, ...]
    operator: Callable[[Iterable], bool]

    def __hash__(self):
        return hash(self.patterns)

    def search(self, string: str, pos: int = 0, endpos: int = sys.maxsize) -> bool:
        return self.operator(pattern.search(string, pos, endpos) for pattern in self.patterns)

    @classmethod
    def compile(
        cls,
        *patterns: SearchPatternLike | str,
        operator: Callable[[Iterable], bool],
        flag: int = re.I,
    ) -> "MatchMulti":
        return cls(tuple(_compile(pattern, flag) for pattern in patterns), operator)

    def union(self, pattern: SearchPatternLike | str, flag: int = re.I) -> "MatchMulti":
        return type(self)((*self.patterns, _compile(pattern, flag)), self.operator)  # type: ignore

    @classmethod
    def never(cls):
        return cls.compile(operator=any)

    def __str__(self):
        return "\n".join(get_all_patterns(self.patterns))


@dataclass
class MatchFirst:
    patterns: tuple[Pattern, ...]

    def __hash__(self):
        return hash(self.patterns)

    @classmethod
    def compile(
        cls,
        *patterns: Pattern | str,
        flag: int = re.I,
    ) -> "MatchFirst":
        return cls(tuple(re.compile(pattern, flag) for pattern in patterns))

    def search(self, string: str, pos: int = 0, endpos: int = sys.maxsize) -> Match | None:
        for pattern in self.patterns:
            if matched := pattern.search(string, pos, endpos):
                return matched
        return None


@dataclass
class NeglectPattern:
    match: SearchPatternLike
    unmatch: SearchPatternLike

    def __hash__(self):
        return hash((self.match, self.unmatch))

    @classmethod
    def compile(
        cls, *, match: str | SearchPatternLike, unmatch: str | SearchPatternLike, flag: int = re.I
    ) -> "NeglectPattern":
        return cls(_compile(match, flag), _compile(unmatch, flag))

    def search(self, string: str, pos: int = 0, endpos: int = sys.maxsize) -> bool:
        return self.match.search(string, pos, endpos) and not self.unmatch.search(string, pos, endpos)


@dataclass
class PositionPattern:
    """按照顺序依次匹配多个正则, 全部匹配则返回True, 否则返回False"""

    patterns: tuple[Pattern, ...]
    ignore: Pattern

    def __hash__(self):
        return hash((self.patterns, self.ignore))

    def search(self, string: str, pos: int = 0, endpos: int = sys.maxsize) -> bool:
        patterns = iter(self.patterns)
        string = self.ignore.sub("", string)
        while pattern := next(patterns, None):
            start = 0
            try:
                for matched in pattern.finditer(string, pos, endpos):
                    if matched.start() == matched.end():
                        raise StopIteration
                    start = matched.end()
                    break
            except StopIteration:
                continue
            if start == 0:
                return False
            string = string[start:]
        return True

    @classmethod
    def compile(
        cls, *patterns: str | Pattern, flag: int = re.I, ignore: str | Pattern = re.compile("^$")
    ) -> "PositionPattern":
        return cls(tuple(re.compile(pattern, flag) for pattern in patterns), re.compile(ignore))


MATCH_NEVER = MatchMulti.compile(operator=any)
MATCH_ALWAYS = re.compile(".?", re.DOTALL)


lst_colon = ("：", ":")
pat_cell_filt = re.compile(r"[^\s\d,.%+\-\/元万亿]+")
pat_col_title_esc = re.compile(r"当年|承诺|预测|未来|20\d{2}E|后.{1}年", flags=re.I)
pat_mean = re.compile(r"均值|平均|中位|中值")
pat_compare = [
    re.compile(r"可比交易"),
    re.compile(r"可比案例"),
    re.compile(r"可比并购(重组|交易)|同行业并购案例"),
    re.compile(r"可比上市公司"),
    re.compile(r"可比国内上市公司"),
    re.compile(r"可比国外同行业公司"),
    re.compile(
        r"可比((交易)?(案例|估值|价格)?|并购(重组|交易)|(国内|同行业)?(上市)?公司|国外同行业公司)|同行业并购案例|对比分析|与.*(对|相)比"
    ),
]
pat_target = pat_compare
pat_conform_to_sylla = pat_compare[-1]
PATTERNS = {
    "方案简介": {
        "syl": [],
        # 'para': re.compile(r'(?P<target>.*拟?以?.*发行.*股份.*方式.*购买.*持有.*股(权|份).*)'),
        "para": [
            re.compile(r"(?P<target>.*拟?以?.*(发行.*股份|现金|向).*(方式)?.*(购买|取得|收购).*(持有)?.*股(权|份).*)"),
        ],
    },
    "配套融资金额": {
        # 'syl': [re.compile(r'募集配套资金|本次交易.*?方案'), ],
        "tbl": [
            [
                re.compile(r"募集配套资金"),
                re.compile(r"交易作价"),
                re.compile(r"交易作价"),
            ],
            [
                re.compile(r"合计"),
                re.compile(r"拟募集配套资金"),
                re.compile(r"金额"),
            ],
            [
                re.compile(r"合计"),
                re.compile(r"募集(配套)?资金|认购金额"),
            ],
            [
                re.compile(r"合计"),
                re.compile(r"使用金额|募投.*金额|募集金额|投资总额|拟投资金额|配套资金金额|融资规模|预计投资额"),
            ],
            [
                re.compile(r"合计"),
                re.compile(r"金额"),
            ],
        ],
        "para": [
            re.compile(
                r"("
                r"募集配套资金[^，：；。]*?由[^，：；。]*?(调|改)"
                r")[^，：；。]*?(?P<target>\d{1,3}(,\d{3})*(\.\d{1,4})?\s*(万|亿)?元(人民币)?)"
            ),
            re.compile(
                r"("
                r"(募集配套资金|配套融资|配套资金总金?额|(公开)?发行股(份|票)募集|募集资金总额)[^，：；。]*?(上限为|不超过)?"
                r"|(募集资金|募集金额)[^，：；。]*?(上限为|不超过)?"
                r")[^，：；。]*?(?P<target>\d{1,3}(,\d{3})*(\.\d{1,4})?\s*(万|亿)?元(人民币)?)"
            ),
            re.compile(
                r"("
                r"募集[^，：；。]*?(上限为|不超过|合计)"
                r")[^，：；。]*?(?P<target>\d{1,3}(,\d{3})*(\.\d{1,4})?\s*(万|亿)?元(人民币)?)[^，：；。]*?("
                r"配套资金)"
            ),
            re.compile(
                r"("
                r"(募集配套资金|配套融资|配套资金总金?额|(公开)?发行股(份|票)募集|募集资金总额)[^，：；。]*?(，)"
                r"|(募集资金)[^，：；。]*?(，)"
                r")[^，：；。]*?(，(即|上限为|不超过))?[^，：；。]*?(?P<target>\d{1,3}(,\d{3})*(\.\d{1,4})?\s*(万|亿)?元(人民币)?)"
            ),
        ],
    },
    "股票定价方式": {
        # 'syl': [re.compile(r'发行价格|发行股份|本次重组方案概述|本次交易已履行的决策过程|募集配套资金|本次合并的换股价格和换股比例'), ],
        "para": [
            re.compile(r"((?:定价基准日|公告日)?(?:（.*）)?前.*?个交易日的?.*?均价)"),
        ],
    },
    "交易金额": {
        "syl": [
            re.compile(r"发行股份|本次.*?(方案|重组)"),
        ],
        "para": [
            re.compile(
                r"("
                r"合计[^，：；。]*?(交易价格|对价)"
                r"|((交易价格|交易金额|对价)[^，：；。]*?合计)"
                r")[^，：；。]*?(?P<target>\d{1,3}(,\d{3})*(\.\d+)?[^，：；。]{0,3}(元|镑))"
            ),
            re.compile(
                r"("
                r"置入资产作价"
                r"|协商[^，：；。]*?(，)?[^，：；。]*?\d{2,3}(,\d{2})?%股权[^，：；。]*?(作价|交易价格|交易对价|交易作价)"
                r"|协商[^，：；。]*?(，)?[^，：；。]*?(作价|交易价格|交易对价|交易作价|转让价格)"
                r")[^，：；。]*?(?P<target>\d{1,3}(,\d{3})*(\.\d+)?[^，：；。]{0,3}(元|镑))"
            ),
            re.compile(
                r"("
                r"(置入资产作价)"
                r"|(交易对价|认购金额|对价|交易定价|交易总价)"
                r"|(总体作价|交易总对价|交易价格|交易总价格|交易总金额|交易金额|总交易价款|交易作价|成交金额|标的作价)"
                r")[^，：；。]*?(?P<target>\d{1,3}(,\d{3})*(\.\d+)?[^，：；。]{0,3}(元|镑))"
            ),
            re.compile(
                r"("
                r"(总体作价|交易总对价|交易价格|交易总价格|交易总金额|交易金额|总交易价款|交易作价|成交金额|预估值|标的作价|评估值)"
                r")[^，：；。]*?(?P<target>\d{1,3}(,\d{3})*(\.\d+)?[^，：；。]{0,3}(元|镑))"
            ),
        ],
        "tbl": [
            [
                re.compile(r"合计"),
                re.compile(r"交易价格|交易作价|交易对价|获取对价"),
                re.compile(r"交易价格|交易作价|交易对价|总对价金额|获取对价"),
            ],
            [
                re.compile(r"合计"),
                re.compile(
                    r"交易.*对价|交易价格|交易作价|初步作价|取得对价|合计对价|合计金额|对价合计|对价总额|总对价|支付.*对价"
                    r"|支付.*金额|支付方式|支付金额|收购对价|获取对价|评估值|资产置换对价|转让对价"
                ),
                re.compile(
                    r"交易.*对价|交易价格|交易作价|交易对价|出售价值|初步作价|合计对价|合计金额|对价合计|对价总额|对价金额"
                    r"|总对价|总金额|支付.*对价|置入资产交易价格|股份对价|评估值|资产置换对价|转让对价|金额"
                ),
            ],
            [
                re.compile(r"合计"),
                re.compile(
                    r"交易.*作价|交易.*对价|交易价格|交易价款|交易总金?额|交易金额|总对价|总对价金额|总支付对价|支付对价|支付对价合计|标的资产交易价格|标的资产作价"
                ),
            ],
            [
                re.compile(r"合计"),
                re.compile(
                    r"交易.*价格|交易.*对价|标的公司.*出资|标的资产.*作价|转让.*对价|出售价值|初步作价|协商定价|对价合计"
                    r"|对价总金?额|对价总额|对价金额|对应作价|标的公司股权|标的对价|股权价值|获取对价|认购金额|评估价值|评估值"
                    r"|评估结果|转让总价|预估值|金额|对价"
                ),
            ],
            [
                re.compile(r"总计|交易金额"),
                re.compile(r"交易(对价|价格)|资产净额|资产总额"),
            ],
        ],
    },
    "交易货币兑人民币汇率": {
        "para": [
            re.compile(
                r""".*?
            (?P<target>((人民币|美元|英镑|欧元|港币|新西兰元)[对兑](人民币|美元|英镑|欧元|港币|新西兰元)[^。，]*?([1-9]\d*|0)(\.\d+)\s*元?)
            |(10*\s*(人民币|美元|英镑|欧元|港币|新西兰元)\s*=\s*(\d+\.\d+)\s*元?(人民币|美元|英镑|欧元|港币|新西兰元)元?)).*""",
                flags=re.VERBOSE,
            ),
            re.compile(r"汇率(?P<target>.+?)[，。；（(]"),
        ],
    },
    "标的承诺期第一年净利润": {
        # 'syl': [re.compile(r'承诺|补偿|预测|预计'), ],
        "para": [
            re.compile(
                r"("
                r"|利润补偿期间各年度的承诺净利润"
                r"|净利润(合计|总额)[^，：；。]*?(，)[^，；。]*?不低于"
                r"|分别实现[^，：；。]*?净利润不低于"
                r"|(归属于)?.*?(净利润|承诺利润数).*?(不低于|不少于|分别为|分别达到|不得低于|分别)"
                r")[^，：；。]*?(?P<target>(-)?\d+(\,\d+)*(\.\d+)?\s*[^，：；。]{1,4}(元|万))"
            ),
        ],
        "tbl": [
            [
                re.compile(r"业绩承诺|净利润|利润承诺数|承诺业绩|承诺值|承诺扣非.*净利润|盈利承诺数|预测净利润"),
                re.compile(r"20\d{2}年"),
            ],
            [re.compile(r"承诺.*净利润"), re.compile(r"20\d{2}年")],
            [
                re.compile(r"业绩承诺|净利润|利润承诺数|承诺业绩"),
                re.compile(r"承诺净利润数|预测净利润数|净利润承诺数"),
                re.compile(r"20\d{2}年"),
            ],
        ],
    },
    "可比公司 静态市盈率 算术平均数": {
        "syl": pat_compare,
        "tbl": [
            [
                re.compile(r"均值|平均"),
                re.compile(r"^[^动]*?市盈率.*?"),
                re.compile(r"20\d{2}年|市盈率|(平)?均值|.*?PE|前一年度"),
            ],
            [
                re.compile(r"均值|平均"),
                re.compile(r"^[^动]*?(市盈率|LYR).*?$|^P(/)?E$", flags=re.I),
            ],
        ],
        # 'syl': '可比交易|同行业上市公司|可比公司|可比上市公司|同行业收购案例|并购交易|对比分析|与 对比|比较分析|公允性合理性|与 比较',
    },
    "可比公司 静态市盈率 中位数": {
        "syl": pat_compare,
        "tbl": [  # 21% locally
            [re.compile(r"中值"), re.compile(r"市盈率（倍）"), re.compile(r"前一年度|20\d{2}年")],
            [re.compile(r"中位(值|数)|中值"), re.compile(r"^[^动]*?(市盈率|LYR)|^P(/)?E$", flags=re.I)],
        ],
        # 'syl': '可比交易|同行业上市公司|可比公司|可比上市公司|同行业收购案例|并购交易|对比分析|与 对比|比较分析|公允性合理性|与 比较',
    },
    "可比公司 动态市盈率 算术平均数": {
        "syl": pat_compare,
        "tbl": [
            [
                re.compile(r"平均|均值"),
                re.compile(r"TTM|动态市盈率", flags=re.I),
            ],
        ],
        # 'syl': '可比交易|同行业上市公司|可比公司|可比上市公司|同行业收购案例|并购交易|对比分析|与 对比|比较分析',
    },
    "可比公司 动态市盈率 中位数": {
        "syl": pat_compare,
        "tbl": [
            [
                re.compile(r"中位(数|值)|中值"),
                re.compile(r"TTM|动态市盈率", flags=re.I),
            ],
            [
                re.compile(r".*?\d{2,3}%股权"),
                re.compile(r"TTM|动态市盈率", flags=re.I),
            ],
        ],
        # 'syl': '可比交易|同行业上市公司|可比公司|可比上市公司|同行业收购案例|并购交易|对比分析|与 对比|比较分析',
    },
    "可比公司 市净率 算术平均数": {
        "syl": pat_compare,
        "tbl": [
            [
                re.compile(r"均值"),
                re.compile(r"市净率|20\d{2}年(\d+月\d+日)?"),
                re.compile(r"前一年度|20\d{2}年|市净率"),
            ],
            [
                re.compile(r"均值|平均"),
                re.compile(r"市净率|PB", flags=re.I),
            ],
        ],
        # 'syl': '可比交易|同行业上市公司|可比公司|可比上市公司|并购交易|对比分析|公允性|合理性|与 对比|比较分析',
    },
    "可比公司 市净率 中位数": {
        "syl": pat_compare,
        "tbl": [
            [re.compile(r"中位(数|值)|中值"), re.compile(r"市净率"), re.compile(r"前一年度|20\d{2}年")],
            [
                re.compile(r"中位(数|值)|中值"),
                re.compile(r"市净率|PB", flags=re.I),
            ],
            [re.compile(r".*?\d{2,3}%股权"), re.compile(r"市净率"), re.compile(r"前一年度|20\d{2}年")],
            [
                re.compile(r".*?\d{2,3}%股权"),
                re.compile(r"市净率|PB", flags=re.I),
            ],
        ],
        # 'syl': '可比交易|同行业上市公司|可比公司|可比上市公司|并购交易|对比分析|公允性|合理性|与 对比|比较分析',
    },
    "市盈率（静态）": {
        "syl": pat_target,
        # 'syl': '本次交易|交易标的',
        "default": re.compile(r"静态市盈率"),
        "tbl": [
            [
                re.compile(r"交易标的|本次交易|标的(公司|资产)|静态"),
                re.compile(r"^[^动]*?市盈率|^P(/)?E(\d{1})?(（倍）)?$|LYR", flags=re.I),
            ],
            [
                re.compile(r"^[^动]*?(交易)?市盈率"),
                re.compile(r"金额|20\d{2}年.*?|前一年度|当期|本次交易", flags=re.I),
            ],
            [
                re.compile(r"^.*?\d{2,3}%股权$"),
                re.compile(r"^[^动]*?市盈率|^P(/)?E$", flags=re.I),
            ],
            [
                re.compile(r"^本次交易$"),
                re.compile(r"^[^动]*?市盈率"),
                re.compile(r"20\d{2}(年)?|市盈率|第\d+年|前一年度|^P(/)?E$|LYR", flags=re.I),
            ],
            [
                re.compile(r"交易标的|本次交易|标的(公司|资产)"),
                re.compile(r"^[^动]*?市盈率|^P(/)?E\d{1}?(（倍）?)$|报告期", flags=re.I),
                re.compile(r"最后1年"),
            ],
            [
                re.compile(r"交易标的|本次交易|标的(公司|资产)"),
                re.compile(r"^[^动]*?市盈率"),
                re.compile(r"报告期"),
                re.compile(r"最后1年"),
            ],
        ],
    },
    "市盈率（动态）": {
        "syl": pat_target,
        "default": re.compile(r"动态市盈率"),
        "tbl": [  # 48% locally
            [re.compile(r"交易标的|本次交易|标的(公司|资产)|动态"), re.compile(r"动态(市盈率|P(/)?E)|TTM", flags=re.I)],
            [re.compile(r".*?\d{2,3}%股权"), re.compile(r"动态(市盈率|P(/)?E)|TTM", flags=re.I)],
            [re.compile(r"动态(市盈率|P(/)?E)|TTM", flags=re.I), re.compile(r"金额")],
        ],
    },
    "市净率": {
        "syl": pat_target,
        "default": re.compile(r"市净率"),
        "tbl": [
            [
                re.compile(r"标的(公司|资产)|交易标的|本次交易"),
                re.compile(r"市净率"),
                re.compile(r"20\d{2}年.*?|前一年度|市净率"),
            ],
            [
                re.compile(r"标的(公司|资产)|交易标的|本次交易"),
                re.compile(r"市净率|P(/)?B", flags=re.I),
            ],
            [re.compile(r"市净率"), re.compile(r"20\d{2}年.*?")],
            [re.compile(r".*?\d{2,3}(\.\d+)%股权"), re.compile(r"市净率"), re.compile(r"20\d{2}年.*?|前一年度|市净率")],
        ],
    },
    "股份对价支付数量": {
        "tbl": [
            # [re.compile(r'合计'), re.compile(r'股(份|票)对价|股份支付|支付方式'), re.compile(r'数量|股份数|万股|（万?股）|股数')],
            # [re.compile(r'合计'), re.compile(r'发行股份|出让.*股权|获得.*股份'), re.compile(r'数量|股份数|万股|（万?股）|股数')],
            # [re.compile(r'合计'), re.compile(r'(数量|股份数|股数).*（万?股）')],
            # [re.compile(r'合计'), re.compile(r'数量|股份数|股数|股份（万?股）')],
            [
                re.compile(r"合计"),
                re.compile(r"股份对价|发行股份|支付方式|股份支付|股份数量|股票对价"),
                re.compile(r"股份.*万股|股份.*股|股票.*股|股份.*数量|股份数|数量|股数"),
            ],
            [
                re.compile(r"合计"),
                re.compile(r"交易对价|发行股票数量|支付对价|支付情况|股份数|股份认购方式|获取对价"),
                re.compile(r"股份数|数量.*股|数量.*万股|股数|股数.*股|股份.*股"),
            ],
            [
                re.compile(r"总计|小计"),
                re.compile(r"支付方式|股份对价|股份支付"),
                re.compile(r"股份.*股|数量.*股|股数.*股|数量"),
            ],
            [
                re.compile(r"合计"),
                re.compile(r"数量.*万股|数量.*股|股份.*万股|股份.*数量|股份.*股|股份数|股数|股数.*股|股票.*股|数量"),
            ],
            [
                re.compile(r"总计"),
                re.compile(r"股份.*股|数量.*股"),
            ],
        ],
        "para": [
            re.compile(
                r"("
                r"发行[^，：；。]*?(数量|股数)[^，：；。]*?(分别|不超过)[^，：；。]*?(，)(合计|即)"
                r"|同时拟向.*发行股份数量不超过"
                r"|折合股数"
                r"|发行[^，：；。]*?(股数|股票|数量|股份)"
                r"|向[^，：；。]*?发行"
                r"|(认购|收购)[^，：；。]*?(发行|持有)"
                r"|(共计发行|发行|取得|认购|购买)"
                r")[^，：；。]*?(?P<target>\d+(\,\d+)*(\.\d+)?\s*(万|亿)?股)"
            ),
        ],
    },
    "股份对价支付金额": {
        # 'default': re.compile(r'股份.*元'), table
        "tbl": [
            # untested
            [re.compile(r"合计"), re.compile(r"股(份|票)对价|股份支付|支付方式"), re.compile(r"股份对价|股份支付")],
            [re.compile(r"合计"), re.compile(r"股(份|票)对价|股份支付|支付方式"), re.compile(r"金额")],
            [re.compile(r"合计"), re.compile(r"支付总金额"), re.compile(r"股份")],
            [
                re.compile(r"合计"),
                re.compile(r"取得对价|发行股份|交易总对价|交易对价|股权转让"),
                re.compile(r"股份|金额|交易对价|转让价款"),
            ],
            [
                re.compile(r"合计"),
                re.compile(
                    r"交易价格|交易作价|交易对价|交易金额|出资金额|对应金额|支付对价|现金对价|股份对价|股份支付"
                ),
            ],
            [re.compile(r"合计"), re.compile(r"金额")],
        ],
        "para": [
            re.compile(
                r"(发行股份[^，：。]*?支付"
                r"|(股份对价|股份支付金额|股份转让对价|股权作价|股票对价)"
                r"|发行股份[^，：。]*?购买资产[^，：。]*?交易对价"
                r"|派发股利"
                r"|拟购买[^，：。]*?股权评估值"
                r"|股权收购[^，：。]*?对价"
                r")[^，：。]*?(?P<target>\d{1,3}(,\d{3})*(\.\d{2})?\s*万?元)"
            ),
            re.compile(r"剩余[^，：。]*?(?P<target>\d{1,3}(,\d{3})*(\.\d{2})?\s*万?元)以发行股份(的)?方式支付"),
        ],
    },
    "现金支付金额": {
        # 'default': re.compile(r'支付现金金额'),
        "tbl": [
            [re.compile(r"合计"), re.compile(r"支付方式|支付对价|取得对价|支付总金额|支付现金"), re.compile(r"现金")],
            [re.compile(r"合计"), re.compile(r"现金"), re.compile(r"金额|现金")],
            [re.compile(r"合计"), re.compile(r"现金")],  # exclude YEAR '合计|小计' reverse Positionning IDX
        ],
        "para": [
            re.compile(
                r"(?P<target>\d{1,3}(,\d{3})*(\.\d{2,4})?\s*(万|亿)?元)[^，：；。]*?("
                r"以现金(方式|形式)?支付"
                r"|支付[^，；：。]*?现金对价"
                r")"
            ),
            re.compile(
                r"("
                r"现金总?(对价|作价|支付)"
                r"|以全?现金(方式|形式)?(支付)?"
                r"|支付的?(现金|对价)"
                r"|派发现金"
                r")[^，：；。]*?(，(总计|即|合计|共计))?[^，：；。]*?(?P<target>\d{1,3}(,\d{3})*(\.\d{2,4})?\s*(万|亿)?元)"
            ),
        ],
    },
    "证券代码": re.compile(r"(证券|股票)代码"),
    "公司名称": re.compile(r"(证券|股票)简称"),
    "注册地": re.compile(r"注册地址?"),
    "经营场所": re.compile(r"(公司|经营|办公)?([场住]所|地[点址])"),
    "评估方法": re.compile(r"(资产基础法|收益法)"),
    "溢价率": re.compile(r"(增值率|溢价率)约?[为是]?\s*(\d[\d,]*(\.\d*)?\s*%)"),
    "标的行业": re.compile(r"(所(在|属|处|从事)(.*?)?(行业|业务)(为|是|属于)|属[为于])(?P<target>.*?)[，。；]"),
}
