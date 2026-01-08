from remarkable.predictor.common_pattern import R_CN, R_CONJUNCTION, R_HYPHEN, R_HYPHENS

p_sale_platform = [r"代销机构及直销网上交易平台|直销柜台"]

R_FUND_SHORT_NAME = r"[A-ZＣ](?![A-Z）])[类级]?((份额)?(基金)?(份额)?)?"

R_SINGLE_REDEMPTION = r"((单|每|首)[次笔])(对?本?基金的?)?赎回"

R_SINGLE_DAY = r"单个?(基金账户单日|开放日|日)"

P_ABBR_EXIST_CODE = [
    r"\d{6}[（(](?P<dst>.[类级])",
    r"(?P<dst>.[类级]基金份额).{,5}(?<!设置)代码",
    r"(?P<dst>.[类级]基金份额)\d{6}",
    r"(?P<dst>.[类级])[:：]?\d{6}",
    r"(?P<dst>.[类级](份额)?)[(（]?基金代码",
    r"((?<![A-Z][类级](份额|基金)(份额|基金)简称)(?<![A-Z][类级](份额|基金)简称)[;；:：]|^)(?P<dst>[^;；:：“]*?[A-Z])[^类]基金代码[：:]\d{6}",
    r"[:：][,，。；;“]*(?P<dst>.*?[A-Z])(代码)?[:：]?\d{6}",
    r"(?P<dst>[^,，。；;“]*[A-Z])(代码)?[:：]?\d{6}",
    r"(?P<dst>[^,，。；;“]*[A-Z])[，,]\d{6}(\.[A-Z]{2})?$",
    rf"(^|本基金)(?P<dst>{R_FUND_SHORT_NAME})的?简称[:：为]",
    r"(?P<dst>[^,，。；;“]*)(?<!代码)[:：]\d{6}(\.[A-Z]{2})?$",
]

p_fund_abbr = [
    *P_ABBR_EXIST_CODE,
    r"^称[:：](?P<dst>[^,，、）)]*)",
    r"(基金|份额|^)简称[“](?P<dst>.*?)[”]",
    r"(基金|份额|^)简称[:：](?P<dst>(.*?[A-Z]$|[^,，、）)]*))",
    r"(基金|份额|^)简称[:：].*?[,，、](?P<dst>.*?)[,，、](基金)?份额",
    r"(基金|份额|^)简称[:：](?P<dst>.*?)(基金)?份额",
    r"[A-Z][类级][:：](?!\d)(?P<dst>[^；，)）]*)",
    rf"基金(?P<dst>{R_FUND_SHORT_NAME})",
    r"[:：；](?P<dst>[^；,，、）)]*)[,，，、]\d{6}",
]

P_CODE_EXIST_ABBR = [
    rf"{R_FUND_SHORT_NAME}([，,(（]基金)?[:：（(]?((?<!证券|认购|上市)代码)?[:：（(]?(?P<dst>\d{{6}}(\.[A-Z]{{2}})?)",
    r"(?P<dst>\d{6})[（(].[类级]",
    r"[A-Z][，,](?P<dst>\d{6}(\.[A-Z]{2})?)$",
    r"(?<!证券代码|认购代码|基金代码)(?<![A-Z][，,]基金代码)(?<![A-Z][，,]代码)(?<![A-Z]代码)[:：](?P<dst>\d{6}(\.[A-Z]{2})?)$",
]

p_fund_code = [
    *P_CODE_EXIST_ABBR,
    r"(?<!证券|认购|上市)代码[:：（(][\"“]?(?P<dst>\d+(\.[A-Z]{2})?)",
    r"[类级](份额)?(基金)?(份额)?(?P<dst>\d+(\.[A-Z]{2})?)",
    r"[类级](份额)?(基金)?(份额)?[:：].*?[A-Z][、](?P<dst>\d{6})$",
]

R_PERIOD = rf"([-一二两三四五六七八九十]+|[{R_HYPHENS}\d+]+)"
r_holding_period_tail = rf"((滚动)?持有|定?期|国开行|[{R_CN}]+债|[{R_CN}]+证券)"
p_holding_period = [rf"(?P<dst>{R_PERIOD})个?[年月周天日]{r_holding_period_tail}"]
p_holding_period_unit = [rf"(?P<dst>{R_PERIOD}个?[年月周天日]){r_holding_period_tail}"]

R_AMOUNT = r"(人民币)?(?P<dst>[\d.\s,，]+[十百千万亿]*[元份]|不设限制|无单笔最低限额)"
R_FIRST = r"([首每][次笔](单笔)?|起点)"


def get_predictor_options(predictor_options):
    for option in predictor_options:
        models = option["models"]
        models.append({"name": "empty"})
        option["models"] = models
    return predictor_options


R_NON_PUNCTUATION = r"[^。;；,，）)]"
# http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/11170?projectId=36&treeId=59&fileId=853&schemaId=2
R_PLATFORM_KEYWORDS = rf"(?<!^)((场[内外](?!份额)(代销机构)?(?!申购时[，,]即)|(?<!各销售)机构(.?(销售)?网点)?|中心(?!柜台)|系统|(?<!不受直销)网点|平台|柜台|直销(?!系统|网点|中心|柜台|平台|网上|销售|机构|交易))([(（]{R_NON_PUNCTUATION}*?)?[）)]?)(?!或|和|与|、|及)"

R_INTERVAL_START = [
    r"持有时间(?P<dst>.*)及?以上",
    r"^(?P<dst>[\d.\s,，万元份日天个月年(个封闭期)]+)([（(]含[)）])?[＜<≤至]",
    r"[≥＞>](?P<dst>[\d.\s,，万元份日天个月年(个封闭期)]+)$",
    r"(?P<dst>.*?)及?([（(]含[)）])?以上",
    rf"(?P<dst>.*){R_HYPHEN}",
    r".*",
]

R_INTERVAL_END = [
    r"持有时间(?P<dst>.*)以内",
    r"[<≤＜〈至](?P<dst>[\d.\s,，万元份日天个月年(个封闭期)]+)$",
    rf"{R_HYPHEN}(?P<dst>[\d.\s,，万元份日天个月年]+)",
    r"(?P<dst>.*)以[下内]",
    r".*",
]


def gen_platform_regex(keyword: str):
    return [
        r"(?P<dst>线上直销渠道或基金管理人指定的其他销售机构|具有基金销售资格的上交所会员单位|网上现金认购|网下现金认购)",
        rf"(?P<dst>其他销售机构(的销售网点)?及(基金)?(管理人)?网上直销(交易)?系统).*?{keyword}",
        r"(?P<dst>其他销售机构.基金管理人直销机构[（(].*?[)）])",
        rf"投资者通过(?P<dst>其他场外销售机构.*?{keyword})",
        rf"办理((基金)?(份额)?)?(?P<dst>{R_NON_PUNCTUATION}*?{R_PLATFORM_KEYWORDS}){keyword}",
        rf"((基金)?投资[者人]|(通过)?本?基金|(^|。)通过)(通过)?在?(本公司)?的?(?P<dst>((基金)?管理人(以外)?)?的?(其[他它])?{R_NON_PUNCTUATION}*?{R_PLATFORM_KEYWORDS}){R_NON_PUNCTUATION}*的?{keyword}",
        rf"(?<!交易级差以)各(?P<dst>{R_NON_PUNCTUATION}*?{R_PLATFORM_KEYWORDS})(对本基金最.认购金额|的?具体规定为准)",
        rf"{keyword}金额以各家?(基金)?(?P<dst>{R_NON_PUNCTUATION}*?{R_PLATFORM_KEYWORDS})的?公告为准",
        rf"{keyword}本?基金(?P<dst>{R_NON_PUNCTUATION}*?{R_PLATFORM_KEYWORDS})份额",
        rf"(?P<dst>(基金管理人)?(电子直销系统|直销中心)（.*?）(或|及)(非直销销售机构|其他销售机构)).*?{keyword}",
        rf"(通过)?(?P<dst>[^。;；,，）)、]*?{R_PLATFORM_KEYWORDS}){R_NON_PUNCTUATION}*?的?{keyword}",
        rf"(管理人)?(?P<dst>{R_NON_PUNCTUATION}*?{R_PLATFORM_KEYWORDS})接受",
        rf"相关(?P<dst>{R_NON_PUNCTUATION}*?{R_PLATFORM_KEYWORDS})公告",
    ]


def gen_fund_name_regex(keyword: str, non_keyword: str = ""):
    if non_keyword:
        return [
            rf"({keyword}|[{R_CONJUNCTION}]|(?<!{non_keyword})基金){R_NON_PUNCTUATION}*?(?P<dst>{R_FUND_SHORT_NAME})[{R_CONJUNCTION}][A-Z][类级]",
            rf"({keyword}|[{R_CONJUNCTION}]|(?<!{non_keyword})基金){R_NON_PUNCTUATION}*?(?P<dst>{R_FUND_SHORT_NAME})(?!(类?(份额)?(基金)?(份额)?)?最.申购金额[，,]?将本基金[A-Z][类级])",
            rf"({keyword}|[{R_CONJUNCTION}]|(?<!{non_keyword})基金){R_NON_PUNCTUATION}*?(?P<dst>[^,.，。；;申购]*?货币[A-Z])",
            rf"(?P<dst>{R_FUND_SHORT_NAME})([\/、和或与]{R_FUND_SHORT_NAME})?{R_NON_PUNCTUATION}*?{keyword}",
            rf"通过[^;；。]*?(?P<dst>(?<!{non_keyword}){R_FUND_SHORT_NAME})[^;；。]*?{keyword}",
        ]
    else:
        return [
            rf"({keyword}|[{R_CONJUNCTION}]|基金){R_NON_PUNCTUATION}*?(?P<dst>{R_FUND_SHORT_NAME})[{R_CONJUNCTION}][A-Z][类级]",
            rf"({keyword}|[{R_CONJUNCTION}]|基金){R_NON_PUNCTUATION}*?(?P<dst>{R_FUND_SHORT_NAME})",
            rf"({keyword}|[{R_CONJUNCTION}]|基金){R_NON_PUNCTUATION}*?(?P<dst>[^,.，。；;申购]*?货币[A-Z])",
            rf"(?P<dst>{R_FUND_SHORT_NAME})([\/、和或与]{R_FUND_SHORT_NAME})?{R_NON_PUNCTUATION}*?{keyword}",
            rf"通过[^;；。]*?(?P<dst>{R_FUND_SHORT_NAME})[^;；。]*?{keyword}",
        ]
