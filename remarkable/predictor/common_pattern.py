from itertools import product

ZH_NUMBER_CHAR_PATTERN = r"[零一二三四五六七八九十百千万]"
NUMBER_CHAR_PATTERN = r"[零一二三四五六七八九十百千万\d]"


UNIT_LIST = [
    "吨",
    "升",
    "方",
    "立方",
    "立方米",
    "家",
    "公吨",
    "期",
    "头",
    "片",
    "股",
    "套",
    "克",
    "千克",
    "间",
    "桶",
    "单位注册资本",
    "人",
    "户",
    "辆",
    "车次",
    "台",
    "人次",
    "公斤",
    "斤",
    "平米",
    "平方米",
    "亩",
    "公顷",
    "度",
    "瓦",
    "瓦时",
    "千瓦",
    "千瓦时",
    "千千瓦时",
    "兆瓦时",
    "兆瓦",
    "kwh",
    "KWH",
    "分钟",
    "小时",
    "时",
    "年",
    "月",
    "日",
    "天",
    "元",
    "次",
    "倍",
    "％",
    "个百分点",
    "笔",
]
slash_unit_prefix = [
    "元",
    "元次",
    "平米",
    "平方米",
    "次",
]

slash_unit_suffix = [
    "天",
    "月",
    "年",
    "半年",
    "吨",
    "期",
    "股",
]

slash_unit = list(product(slash_unit_prefix, slash_unit_suffix))
UNIT_LIST += [f"{pre}/{suffix}" for (pre, suffix) in slash_unit]
UNIT_LIST += [f"{pre}⁄{suffix}" for (pre, suffix) in slash_unit]

UNIT_PATTERN = "|".join([r"[十百千万亿]*" + u for u in sorted(UNIT_LIST, key=len, reverse=True)])
CURRENCY = r"(人民币|美元|日元|欧元|英镑|德国马克|瑞士法郎|法国法郎|加拿大元|菲律宾比索|俄罗斯卢布|新加坡元|韩国元|泰国铢|爱尔兰镑|意大利里拉|卢森堡法郎|荷兰盾|葡萄牙埃斯库多|西班牙比塞塔|印尼盾|马来西亚林吉特|澳大利亚元|港币|奥地利先令|芬兰马克|比利时法郎|新西兰元)"
DIGITAL = r"[-+]?[\d]+[\d,×.百千万亿]*[多余]?[百千万亿]*"
CHINESE_DIGITAL = "(?:零|(?:[一二三四五六七八九十零壹贰叁肆伍陆柒捌玖拾]+[佰仟百千万亿])+[多余]?[佰仟百千万亿]*)"
DATE_PATTERN = (
    r"(?P<dst>[\d一二三四五六七八九〇○OＯ零]{4}\s?(?:半?年[度初中末]?(（?/?年?末）?)?/?|\.|-|/)\s?([\d正元一二三四五六七八九十零〇○Ｏ—~-]{1,4}\s?"
    r"(?:月份?（?/?末?）?|\.|-|/|季度)?(?:([\d]{1,2}|[一二三四五六七八九十零〇○Ｏ]{1,3})[日号]?)?)?)"
)
PERCENT_PATTERN = "[%％]"

R_COLON = r":："
R_SEMICOLON = r"；;"
R_COMMA = "，,"
R_NOT_SENTENCE_END = f"[^。{R_COMMA}{R_SEMICOLON}]"

R_UNSELECTED = r"□"

R_CN = "\u4e00-\u9fa5"

R_HYPHEN = r"[-—–－‐]"
R_HYPHENS = r"-—–－‐"
R_CONJUNCTION = r"与和及或、/"
R_LEFT_BRACKET = r"[{〔【（(]"
R_RIGHT_BRACKET = r"[)）】〕}]"
