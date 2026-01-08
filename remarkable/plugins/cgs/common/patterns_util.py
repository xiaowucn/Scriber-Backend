# 替换模板中单选或多选项
import re

from remarkable.common.convert_number_util import NumberUtil
from remarkable.common.pattern import PatternCollection

R_CN_NUMBER = NumberUtil.R_CN_NUMBER
R_FLOAT_NUMBER = NumberUtil.R_FLOAT_NUMBER
R_PERCENT_UNIT = NumberUtil.R_PERCENT_UNIT
R_NEGATIVE_PREFIX = r"\-－—负"
R_INTERVAL = r"\-－—至到"
P_NEGATIVE_PREFIX = PatternCollection(rf"[{R_NEGATIVE_PREFIX}]")
P_NUMBER = PatternCollection(rf"[{R_NEGATIVE_PREFIX}]?{R_FLOAT_NUMBER}")
P_PERFECTLY_NUMBER = PatternCollection(rf"^[{R_NEGATIVE_PREFIX}]?{R_FLOAT_NUMBER}$")
P_DATE = PatternCollection(
    [
        rf"(?P<year>[{R_CN_NUMBER}]{{1,4}})\s*年(?:(?P<month>[{R_CN_NUMBER}]{{1,2}})\s*月)?(?:(?P<day>[{R_CN_NUMBER}]{{1,2}})\s*日)?",
        rf"(?P<c_month>[{R_CN_NUMBER}]+)个月",
    ]
)
P_PERCENTAGE = PatternCollection(
    [
        rf"[{R_NEGATIVE_PREFIX}]?{R_FLOAT_NUMBER}{R_PERCENT_UNIT}",
        rf"负?[{R_CN_NUMBER}]+分之[{R_CN_NUMBER}]+",
        rf"[{R_NEGATIVE_PREFIX}]?\d+/\d+",
    ]
)

P_BOURSE_SH = PatternCollection(r"上海证券交易所|上交所")
P_BOURSE_SZ = PatternCollection(r"深圳证券交易所|深交所")

P_SYMBOL_SPLIT = PatternCollection(r"[、,，]")

P_CATALOGUE = PatternCollection(r"^目\s*录$")

R_SYMBOL_BRACKETS_LEFT_CHARS = r"\[《<\(（{【［「〖『〈«＜〔〔"
R_SYMBOL_BRACKETS_RIGHT_CHARS = r"\]》>\)）}】］」〗』〉»＞〕〕"

R_PERCENTAGE = "|".join(P_PERCENTAGE.patterns)
R_PERCENTAGE_IGNORE_UNIT = "|".join(
    [rf"[{R_NEGATIVE_PREFIX}]?{R_FLOAT_NUMBER}{R_PERCENT_UNIT}?", *P_PERCENTAGE.patterns[1:]]
)

P_PERCENTAGE_UNIT = PatternCollection(rf"{R_PERCENT_UNIT}")
P_PURE_PERCENTAGE_WITHOUT_UNIT = PatternCollection(rf"^[{R_NEGATIVE_PREFIX}]?{R_FLOAT_NUMBER}$")

P_LINK_SENTENCE = PatternCollection(r"、|与|以?及|和|或|/")
P_EXCLUDE_SENTENCE = PatternCollection(r"[【{（(〔][^)）】〕}]+[)）】〕}]")

# https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/959#note_244082
# ①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳⑴⑵⑶⑷⑸⑹⑺⑻⑼⑽⑾⑿⒀⒁⒂⒃⒄⒅⒆⒇⒈⒉⒊⒋⒌⒍⒎⒏⒐⒑⒒⒓⒕⒔⒖⒗⒘⒙⒚⒛ \u2460-\u249B
# ㈠㈡㈢㈣㈤㈥㈦㈧㈨㈩ \u3220-\u3229
R_SERIAL_CN_NUMBER = r"\u2460-\u249B\u3220-\u3229"

P_PARA_PREFIX_NUM = PatternCollection(
    rf"^(?P<prefix>[\(（]?(?P<num>[\d一二三四五六七八九十{R_SERIAL_CN_NUMBER}]+)[\)）]?[\.、]?)"
)

R_NOT_CONJUNCTION_PUNCTUATION = ",，。;；"
R_PUNCTUATION = rf"{R_NOT_CONJUNCTION_PUNCTUATION}、"
R_CONJUNCTION = r"与和及或、"
R_MULTIPLICATION_SYMBOL = r"×xX"


R_FEES_PAYMENT_DATE = r"{name}每日计[算提].*?(?:管理人|托管人)[^{punctuation}]*?核.*?月(?:首日起|前|初)([{num}]+.)?(?P<val>[{num}]+)个工作日.*?支[取付]给?(?:(?:基金)?管理人)?"


P_BASE_SIMILARITY_PATTERNS = [
    re.compile(rf"[{R_SYMBOL_BRACKETS_LEFT_CHARS}]"),
    re.compile(rf"[{R_SYMBOL_BRACKETS_RIGHT_CHARS}]"),
    re.compile(r"[＝=]"),
    re.compile(r"[+＋]"),
    re.compile(rf"[{R_MULTIPLICATION_SYMBOL}]"),
    re.compile(r"[\-—一]+"),
]

# https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/959#note_234405
# 私募基金
P_PRIVATE_SIMILARITY_PATTERNS = [
    re.compile(r"(?:(?:私募)?基金)?管理人"),
    re.compile(r"(?:(?:私募)?基金)?托管人"),
    re.compile(r"(?:中国(?:证券投资)?)?基金业协会|协会"),
    re.compile(r"外包|基金服务"),
    re.compile(r"(?:(?:私募)?基金)?投资者|(?:(?:私募)?基金)?份额持有人|(?:(?:私募)?基金)?委托人"),
    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/959#note_245214
    re.compile(r"QD(?:[1lIL]{2}|Ⅱ)"),
    *P_BASE_SIMILARITY_PATTERNS,
]

# https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1149#note_259737
# 公募基金
P_PUBLIC_SIMILARITY_PATTERNS = [
    re.compile(r"(?:(?:公募)?基金)?管理人"),
    re.compile(r"(?:(?:公募)?基金)?托管人|托管机构"),
    re.compile(r"投资[者人]|(基金)?份额持有人"),
    re.compile(r"销售(?:机构|网点)"),
    re.compile(r"上海证券交易所|上交所"),
    re.compile(r"深圳证券交易所|深交所"),
    re.compile(r"[需须]"),
    re.compile(r"参[看见]"),
    re.compile(r"(?<!深圳|上海)(证券交易|证券/期货交易)(所|市场)"),
    re.compile(r"临时基金托管人或新任基金托管人|新任基金托管人或临时基金托管人"),
    re.compile(r"临时基金管理人或新任基金管理人|新任基金管理人或临时基金管理人"),
    re.compile(r"基金资产总值和基金资产净值|基金资产总值和净值"),
    re.compile(r"基金(?:份额)?登记机构"),
    re.compile(r"本基金基金份额持有人|本基金份额持有人"),
    re.compile(r"[签盖]章"),
    re.compile(r"份额持有人大会的决[议定]"),
    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2272#note_351390
    re.compile(r"(?:中国(?:证券投资)?)?基金业协会|协会"),
    re.compile("[及、]"),
    *P_BASE_SIMILARITY_PATTERNS,
]

P_STOCK_SIMILARITY_PATTERN = re.compile(r"证券(?:交易所)?[/、]期货交易所|证券交易所")


P_SUGGESTION = re.compile(r"\[(?P<schema_name>[^\[\]]+)\]\[(?P<anchor>[^\[\]]+)\]")

P_LINE_NUMBER = re.compile(
    r"(?P<number>^\s*[(（【]?\s*([➢0-9一二三四五六七八九十]+|[a-zA-Z]{1,2})\s*[)）】,.，、\s]+\s*|^[➢]+)"
)

P_CATALOG_TITLE = PatternCollection(
    [
        r"\s*(?P<content>.*?)(?P<tab_leader>[\s.·…—﹍\-]+)(?:(?P<no>\d[\s\d]*)\s*[—-]?\s*(?=$|第?[一二三四五六七八九十])|错误!未定义书签。?\s*|(?<=[\s.·…—﹍\-])$)",
        r"^(?P<content>[一二三四五六七八九十\d.]+、.*?)(?P<no>[\d]+)$",
    ]
)

# https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2012#note_341495
P_WITHOUT_HOLDER_MEETING = PatternCollection(
    [
        rf"不设[置立]?份额持有人大会[{R_CONJUNCTION}]日常机构",
        r"不设[置立]?份额持有人大会机制",
    ]
)
P_EMPLOY_INVESTMENT_ADVISER = PatternCollection(
    rf"聘[请任用][^{R_NOT_CONJUNCTION_PUNCTUATION}]*?作?为(本(?:投资)?计划)?的?投资顾问"
)
P_OPERATE_MODE_CLOSE = PatternCollection(r"封闭式")
P_NON_STANDARD_INVESTMENT = PatternCollection(
    r"新三板|全国中小企业股份转让系统挂牌股票|场外期权|益互换|收益凭证|资产管理计划|资产管理产品|私募证券投资基金|信托计划|未上市企业股权|股权|收益权|信贷|理财|债权融资计划|债权投资计划|资产支持计划"
)

P_ASSET_STOCK_RIGHT = PatternCollection(r"股权|收益权")
P_CUSTODY_STOCK = PatternCollection(r"沪深|上证|中证|深证|创业板|中小企业|恒生|A股|股票|北证|国证|中创")

P_IGNORE_TEXT = re.compile(r"\.{6,}[0-9]+$")

P_NUMBERING = PatternCollection(
    [
        r"^[(（【]?[a-zA-Z]+\s*[\.．、)）】]",
        r"^\s*[(（【]?\s*[➢0-9一二三四五六七八九十]+\s*[)）】]",
        r"^\s*[(（【]?\s*[➢0-9一二三四五六七八九十]+\s*[,.．，、\s]+[)）】]?\s*",
        r"^\s*[➢✓✔️■○·]+\s*",
        rf"^\s*[{R_SERIAL_CN_NUMBER}]+\s*",
        r"^\s*第\s*[0-9一二三四五六七八九十]+\s*(部分|章?节?)",
    ]
)

P_LANDLINE_NUMBER = PatternCollection(r"0\d{2,3}[—-]?\d{7,8}")

P_SELECT_ELE = PatternCollection(r"[■|◼|☑|√]")
