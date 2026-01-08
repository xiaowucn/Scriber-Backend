"""
申购调整公告
"""

from remarkable.predictor.cmbchina_predictor import R_CONTAIN_DATE, R_DATE
from remarkable.predictor.cmbchina_predictor.schemas import (
    R_AMOUNT,
    R_FUND_SHORT_NAME,
    R_PLATFORM_KEYWORDS,
    R_SINGLE_DAY,
    gen_fund_name_regex,
    gen_platform_regex,
    get_predictor_options,
    p_holding_period,
    p_holding_period_unit,
)
from remarkable.predictor.cmbchina_predictor.schemas.cmbchina_prospectus_schema import gen_table_subscription
from remarkable.predictor.common_pattern import R_CN, R_CONJUNCTION, R_HYPHENS
from remarkable.predictor.eltype import ElementClass


def get_start_end_data(key):
    dst_0 = "dst"
    dst_1 = "non"
    if key == "结束日期":
        dst_0 = "non"
        dst_1 = "dst"
    return [
        rf"开放(期|时间)(内办理.*?的时间)?(为)?(?P<{dst_0}>{R_DATE})起?{R_CONTAIN_DATE}?起?至(?P<{dst_1}>{R_DATE})",
        rf"(?P<{dst_0}>{R_DATE})起?{R_CONTAIN_DATE}?起?至(?P<{dst_1}>{R_DATE}){R_CONTAIN_DATE}?为[{R_CN}]+开放(期|时间)",
        rf"本基金(本次|第).*?开放(期|时间)(为)?{R_DATE}之后.*?期间.即(?P<{dst_0}>{R_DATE})起?{R_CONTAIN_DATE}?起?至(?P<{dst_1}>{R_DATE})",
        rf"基金管理人决定自(?P<{dst_0}>{R_DATE})起?{R_CONTAIN_DATE}?起?至(?P<{dst_1}>{R_DATE}){R_CONTAIN_DATE}?期间的工作日.本基金.*业务申请",
    ]


predictor_options = [
    {
        "path": ["产品销售对象"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"本基金(?P<dst>暂不向金融机构自营账户销售)",
                    r"投资者范围.(?P<dst>.*其他投资人)",
                ],
            },
        ],
    },
    {
        "path": ["分级基金"],
        "sub_primary_key": ["基金简称"],
        "divide_answers": True,
        "models": [
            {
                "name": "table_header",
                "header_patterns": {
                    "基金简称": [
                        r"分级|下属|各基金",
                        r"简称|",
                    ],
                    "基金代码": [
                        r"分级|下属|各基金",
                        r"代码|",
                    ],
                    "是否暂停、恢复大额申购、转换转入、定期定额投资": [
                        r"分级|下属|^该分?类?别?基金",
                        r"是否|",
                    ],
                    "限制申购金额": [
                        r"分级|下属|调整后|该类",
                        r"(限制|暂停)(大额)?申购.*[限金]额",
                    ],
                    "限制转换转入金额": [
                        r"分级|下属|调整后|该类",
                        r"(限制|暂停).*转换转入.*[限金]额",
                    ],
                    "限制定期定额投资金额": [
                        # r"分级|下属|调整后|该类",
                        r"(?<!是否)(限制|暂停).*定期定额投资.*([限金]额|[(（]单位.元[）)])?",
                    ],
                    "分级基金持有份额限制金额": [
                        r"分级|下属|调整后|该类",
                        r"((份|金)额限制|限制(持有)?(份|金)额).*[）)]?",
                    ],
                },
                "value_patterns": {
                    "基金简称": [
                        r"(?P<dst>.*[A-Z].*)",
                    ],
                    "基金代码": [r"(?P<dst>\d{6})"],
                    "是否暂停、恢复大额申购、转换转入、定期定额投资": [
                        rf"(?P<dst>([{R_HYPHENS}是否]|不适用))$",
                    ],
                    "限制申购金额": [],
                    "限制转换转入金额": [],
                    "限制定期定额投资金额": [],
                    "分级基金持有份额限制金额": [],
                },
                "neglect_header_patterns": {
                    "限制定期定额投资金额": [r"暂停相关业务"],
                    "分级基金持有份额限制金额": [r"是否"],
                    "是否暂停、恢复大额申购、转换转入、定期定额投资": [r"单位"],
                },
            },
            {
                "name": "subscription",
                "multi_config": {
                    "基金简称": True,
                    "基金代码": True,
                },
                "regs": {
                    "基金简称": [
                        r"(?<!降.|调整)(?P<dst>[A-Z][类级]((基金)?份额)?)",
                    ],
                    "基金代码": [
                        r"代码[:：为]?(?P<dst>\d{6})",
                        r"新增(?P<dst>\d{6})",
                    ],
                },
                "splits": [r"。"],
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"公告基本信息"],
                "extract_from": "same_type_elements",
                "only_inject_features": True,
                "paragraph_model": "partial_text",
                "para_config": {
                    "merge_char_result": False,
                    "multi_elements": True,
                    "multi": True,
                    "regs": {
                        "基金简称": [
                            r"下属分级基金的基金简称(?P<dst>.*?债券[A-z])",
                            r"债券[A-z](?P<dst>.*债券[A-z])",
                        ],
                        "基金代码": [
                            r"下属分级基金的交易代码(?P<dst>\d{6})",
                            r"\d{6}(?P<dst>\d{6})",
                        ],
                        "是否暂停、恢复大额申购、转换转入、定期定额投资": [
                            r"该分级基金是否开放申购和定期定额投资(?P<dst>[是否])",
                            r"定额投资[是否](?P<dst>[是否])",
                        ],
                    },
                },
            },
        ],
    },
    {
        "path": ["暂停、恢复申购起始日"],
        "models": [
            {
                "name": "cell_partial_text",
                "from_cell": False,
                "regs": [
                    rf"(恢复|暂停)(个人投资者)?大额申购.*?(起始)?日(?P<dst>[{R_HYPHENS}年月日\d/]+)",
                ],
            },
            {
                "name": "cell_partial_text",
                "from_cell": False,
                "regs": [
                    rf"申购起始日(?P<dst>[{R_HYPHENS}年月日\d/]+)",
                    rf"(恢复|暂停)(个人投资者)?(大额)?申购.*?(起始)?日(?P<dst>[{R_HYPHENS}年月日\d/]+)",
                    rf"申购(、定期定额申购)(、赎回、转换|及转换转入)起始日(?P<dst>[{R_HYPHENS}年月日\d/]+)",
                ],
            },
            {
                "name": "partial_text",
                "regs": [
                    rf"(?P<dst>[{R_HYPHENS}年月日\d/]+)起?(调整|暂停)了?本基金的?大额申购",
                    rf"自(?P<dst>[{R_HYPHENS}年月日\d/]+)起?(调整|暂停).*申购、(定期定额|转换转入)",
                ],
            },
        ],
    },
    {
        "path": ["暂停、恢复赎回起始日"],
        "models": [
            {
                "name": "cell_partial_text",
                "from_cell": False,
                "regs": [
                    rf"赎回起始日(?P<dst>[{R_HYPHENS}年月日\d/]+)",
                    rf"申购、赎回、转换起始日(?P<dst>[{R_HYPHENS}年月日\d/]+)",
                ],
            },
        ],
    },
    {
        "path": ["暂停、恢复转换转入起始日"],
        "models": [
            {
                "name": "cell_partial_text",
                "from_cell": False,
                "regs": [
                    rf"大额转换转入.*?(起始)?日(?P<dst>[{R_HYPHENS}年月日\d/]+)",
                ],
            },
            {
                "name": "cell_partial_text",
                "from_cell": False,
                "regs": [
                    rf"转换转入(起始)?日(?P<dst>[{R_HYPHENS}年月日\d/]+)",
                    rf"转换转入.*?(起始)?日(?P<dst>[{R_HYPHENS}年月日\d/]+)",
                    rf"申购(、定期定额申购)(、赎回、转换|及转换转入)起始日(?P<dst>[{R_HYPHENS}年月日\d/]+)",
                ],
            },
            {
                "name": "partial_text",
                "regs": [
                    rf"转换转入(起始)?日(?P<dst>[{R_HYPHENS}年月日\d/]+)",
                    r"(?P<dst>[年月日\d]+)暂停了?本基金的.*?大额转换转入",
                    rf"自(?P<dst>[{R_HYPHENS}年月日\d/]+)起调整.*申购、定期定额申购及转换转入业务上限",
                ],
            },
        ],
    },
    {
        "path": ["暂停、恢复转换转出起始日"],
        "models": [
            {
                "name": "cell_partial_text",
                "from_cell": False,
                "regs": [
                    rf"转换转出(起始)?日(?P<dst>[{R_HYPHENS}年月日\d/]+)",
                    rf"申购、赎回、转换起始日(?P<dst>[{R_HYPHENS}年月日\d/]+)",
                ],
            },
        ],
    },
    {
        "path": ["暂停、恢复定期定额投资起始日"],
        "models": [
            {
                "name": "cell_partial_text",
                "from_cell": False,
                "regs": [
                    rf"(大额定投|定期定额(和不定额)?(投资(业务)?|申购))(及转换转入)?(金额限制)?(起始)?日(?P<dst>[{R_HYPHENS}年月日\d/]+)",
                    rf"恢复大额申购.*?业务起始日(?P<dst>[{R_HYPHENS}年月日\d/]+)",
                ],
            },
            {
                "name": "partial_text",
                "regs": [
                    rf"(大额定投|定期定额(和不定额)?投资)起始日.?(?P<dst>[{R_HYPHENS}年月日\d/]+)",
                    rf"(?P<dst>[{R_HYPHENS}年月日\d/]+)暂停了?本基金的大额申购",
                    rf"自(?P<dst>[{R_HYPHENS}年月日\d/]+)起调整.*申购、定期定额申购及转换转入业务上限",
                ],
            },
        ],
    },
    {
        "path": ["持有份额限制起始日"],
        "models": [
            {
                "name": "cell_partial_text",
                "from_cell": False,
                "regs": [
                    rf"持有[份金]额限制起始日(?P<dst>[{R_HYPHENS}年月日\d/]+)",
                ],
            },
        ],
    },
    {
        "path": ["是否升降级"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["是否共用限额"],
        "models": [
            {
                "name": "para_match",
                "multi_elements": True,
                "neglect_regs": [r"费率"],
                "paragraph_pattern": [
                    r"[限份金]额(合并|单独)",
                    r"[限份金]额[^。]*(合并?|单独|分别)(进行)?(计算?|限制|判断)",
                ],
            },
        ],
    },
    {
        "path": ["限额控制模式"],
        "models": [
            {
                "name": "para_match",
                "order_by_index": True,
                "multi_elements": True,
                "combine_paragraphs": True,
                "neglect_regs": [r"费率", r"^([(（]?\d[)）、\s])?如单[个日]"],
                "paragraph_pattern": [
                    r"[限份]额(合并|单独)",
                    r"[限份]额[^。]*(合并|单独|分别)(计算|进行限制|判断)",
                ],
            },
        ],
    },
    {
        "path": ["赎回限制类型"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>[\d一二三四五六七八九十天日月年]+的.?(滚动|锁定)(运作|持有)期)",
                ],
            },
        ],
    },
    {
        "path": ["赎回限制"],
        "models": [
            {
                "name": "reference",
                "from_path": ["赎回限制类型"],
            },
        ],
    },
    {
        "path": ["单笔申购下限-原文"],
        "models": [
            {
                "name": "para_match",
                "syllabus_regs": [
                    r"[金数][额量]限制",
                    r"(申购|赎回)的限制",
                ],
                "multi_elements": True,
                "order_by_index": True,
                "combine_paragraphs": True,
                "neglect_syllabus_regs": [
                    r"单笔申购(?!限制)",
                ],
                "paragraph_pattern": [
                    rf"(基金|[A-Z]类)份额.*单笔最低(限额|金额|申购).*{R_AMOUNT}",
                    rf"(基金|[A-Z]类)份额.*(单笔|追加)申购(（.*）)?的?(最低|调整为|降至).*{R_AMOUNT}",
                    rf"(基金|[A-Z]类)份额.*(单笔|追加)申购.*(调整|降至|起点)为?{R_AMOUNT}",
                    rf"((单|每)[次笔]|首笔)(最.)?申购(?!各类)([^,.，。；;]*?|金额([(（].*[）)]为)){R_AMOUNT}",
                    rf"(?<!含)申购[^。，,]*?((单|每)[次笔]|首笔)([^,.，。；;]*?|金额([(（].*[）)]为)){R_AMOUNT}",
                    r"份额(?P<dst>(无|不设)单笔最低限额)",
                    rf"申购(金额)?下限为{R_AMOUNT}",
                    rf"首次申购(本?基金?)?{R_FUND_SHORT_NAME}的?单笔最.[限金]额",
                ],
            },
        ],
    },
    {
        "path": ["单笔申购下限"],
        "sub_primary_key": ["基金名称", "最低限额", "销售平台"],
        "post_process": "post_process_sale_platform",
        "models": [
            {
                "name": "subscription",
                "main_column": "销售平台",
                "depends": ["单笔申购下限-原文"],
                "multi_config": {
                    "基金名称": True,
                    "最低限额": False,
                    "销售平台": False,
                },
                "neglect_patterns": [
                    rf"^本?基金([{R_CN}]+)?.笔申购最低金额([{R_CN}]+)?管理人([{R_CN}]+)?调整",
                    r"已持有基金份额的投资者不受上述首笔申购最低金额的限制.单笔申购最低金额为",
                ],
                "regs": {
                    "基金名称": [
                        r"本基金(?P<dst>[A-Z]类(基金)?份额)",
                        r"申购(?P<dst>[A-Z]类基金份额)",
                        r"[A-Z]类基金份额或(?P<dst>[A-Z]类基金份额)",
                    ],
                    "最低限额": [
                        rf"(追加申购[{R_CN}]{{,2}})((单|每)[次笔]|首笔)(首次)?(最.)?(申购(?!各类)[^,.，。；;]*?(人民币)?|金额(起点|下限)?为?){R_AMOUNT}(?!降至|调整为)",
                        rf"追加申购[^。，,]*?((单|每)[次笔]|首笔)[^,.，。；;]*?{R_AMOUNT}(?!降至|调整为)",
                        rf"追加((单|每)[次笔]|首笔)?申购[^,.，。；;]*?{R_AMOUNT}(?!降至|调整为)",
                        rf"追加申购的?((单|每)[次笔])?((金额)?下限|最低金额)均?为{R_AMOUNT}",
                        rf"首次申购或追加申购各类基金份额时[,，]单笔最低金额为{R_AMOUNT}",
                        rf"首次最低金额及追加申购最低金额分别为.*?和{R_AMOUNT}",
                        # 优先提取追加申购的
                        rf"[单首][笔次]([^,.，。；;]*?|.*金额([(（].*[）)]为)){R_AMOUNT}",
                    ],
                    "销售平台": [
                        r"(?P<dst>直销电子交易系统[(（].*?[）)][或及]本基金其他销售机构)",
                        r"基金份额通过(?P<dst>本公司直销机构及其他销售机构)",
                        *gen_platform_regex("(((单|每)[次笔]|首笔)?(追加)?申购|每个账户)"),
                    ],
                },
                "销售平台": {
                    "split_pattern": r"[或及]本基金",
                },
            },
        ],
    },
    {
        "path": ["单客户每日累计申购、转入限额"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "include_title": True,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__申购业务限额进行以下调整",
                ],
                "break_para_pattern": [
                    r"服务热线",
                ],
            },
            {
                "name": "para_match",
                "order_by_index": True,
                "multi_elements": True,
                "combine_paragraphs": True,
                "paragraph_pattern": [
                    rf"{R_SINGLE_DAY}[每单]个基金账户[多单或笔]+(累计(高于.*)?的?申购|申购后的累计)",
                    rf"{R_SINGLE_DAY}[每单]个基金账户的?申购[^,，。；;]*累计",
                    rf"{R_SINGLE_DAY}([每单]个基金账户)?的?累计的?申购",
                    r"单日单个基金账户申购[^,，。；;]*转入",
                    rf"单一投资者单日(认购[{R_CONJUNCTION}])?申购[^,，。；;]*金额不超过\d+",
                    # r"(?<!仅)(取消|暂停|恢复)[^,，。；;]*(申购|转换转入)[^,，。；;]*(限制|上限|业务)(金额)?[,，。；;]",
                    r"调整[^,，。；;]*(申购|转换转入)[^,，。；;]*(限制|上限|业务)(金额)?[,，。；;][如即]单日[每单]个基金账户[^,，。；;]*累计金额",
                    rf"(?:(申购|转入|转换)[{R_CONJUNCTION}]?){{2,3}}业务(合并)?进行限制",
                    rf"(?:(大额申购|大额定期定额投资|大额转换转入)[{R_CONJUNCTION}]?){{2,3}}的?限额为\d+",
                ],
            },
        ],
    },
    {
        "path": ["首次申购下限-原文"],
        "models": [
            {
                "name": "para_match",
                "order_by_index": True,
                "multi_elements": True,
                "syllabus_regs": [
                    r"申购金额限制",
                ],
                "paragraph_pattern": [
                    rf"[首每单][次笔](最.)?申购.*{R_AMOUNT}",
                ],
            },
            {
                "name": "partial_text",
                "syllabus_regs": [
                    r"日常申购、赎回等业务的办理时间",
                ],
                "regs": [
                    r"\d+、(?P<dst>.*?[首每单][次笔](最.)?申购.*[\d.\s,，]+千?百?万?元.*?)\d+、",
                ],
            },
        ],
    },
    {
        "path": ["首次申购下限"],
        "sub_primary_key": ["基金名称", "最低限额", "销售平台"],
        "post_process": "post_process_sale_platform",
        "models": [
            {
                "name": "subscription",
                "main_column": "销售平台",
                "depends": ["首次申购下限-原文"],
                "multi_config": {
                    "基金名称": True,
                    "最低限额": False,
                    "销售平台": False,
                },
                "para_regs": [
                    rf"(申购[^,.，。；;]*?[首每单][次笔](?!追加)|[首每单][次笔](?!追加)[^,.，。；;]*?申购)([^,.，。；;]*?|金额([(（].*[）)]为)){R_AMOUNT}",
                ],
                "regs": {
                    "基金名称": [
                        r"(?<!追加)申购(本基金)?(?P<dst>[A-Z]类)",
                        r"(?P<dst>[A-Z]类)基金份额或[A-Z]类",
                        r"或(?P<dst>[A-Z]类)",
                    ],
                    "最低限额": [
                        rf"(?<!追加申购)(?<!追加)[首][次笔](?!追加)(?!最低追加)[^,.，。；;]*?{R_AMOUNT}(?!.自{R_DATE}起)(?!降至|.?调整为)",
                        r"(?P<dst>无单笔最低限额)",
                        rf"(?<!追加申购)(?<!追加)[每单][次笔](?!追加)(?!最低追加)[^,.，。；;]*?{R_AMOUNT}(?!.自{R_DATE}起)(?!降至|.?调整为)",
                    ],
                    "销售平台": [
                        r"(?P<dst>直销电子交易系统[(（].*?[）)][或及]本基金其他销售机构)",
                        *gen_platform_regex(
                            "((?<!追加)申购(?!金额)|[首每单][次笔](?!追加)(?!最低追加)|，每个基金账户首次最低申购)"
                        ),
                    ],
                },
                "销售平台": {
                    "split_pattern": r"[或及]本基金",
                },
            },
        ],
    },
    {
        "path": ["追加申购下限-原文"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [r"追加[^,.，。；;]*申购"],
                "multi_elements": True,
                "order_by_index": True,
                "combine_paragraphs": True,
            },
        ],
    },
    {
        "path": ["追加申购下限"],
        "sub_primary_key": ["基金名称", "最低限额", "销售平台"],
        "models": [
            {
                "name": "subscription",
                "main_column": "销售平台",
                "depends": ["追加申购下限-原文"],
                "multi_config": {
                    "基金名称": True,
                    "最低限额": False,
                    "销售平台": False,
                },
                "regs": {
                    "基金名称": [
                        r"申购(?P<dst>[A-Z]类)或[A-Z]类",
                        r"(?P<dst>[A-Z]类基金份额)",
                        r"[A-Z]类(?P<dst>.+基金份额)",
                        r"申购(?P<dst>[A-Z]类基金份额)",
                        r"申购本基金(?P<dst>[A-Z]类份额)",
                    ],
                    "最低限额": [
                        rf"追加[^,.，。；;]*?{R_AMOUNT}",
                    ],
                    "销售平台": [
                        r"(?P<dst>在其他销售机构[或及]基金管理人网上直销系统)",
                        *gen_platform_regex("([认申]购(?!金额)|首次)"),
                    ],
                },
                "neglect_answer_patterns": {
                    "销售平台": [
                        r"转入",
                    ]
                },
                "para_regs": [
                    rf"追加[^,.，。；;]*?{R_AMOUNT}",
                    r"追加申购金额不限",
                ],
                "销售平台": {
                    "split_pattern": r"[或及]本基金",
                },
            },
        ],
    },
    {
        "path": ["单客户持仓上限"],
        "models": [
            {
                "name": "partial_text",
                "neglect_text_regs": [
                    r"本基金的其他业务仍正常办理.$",
                    r"本基金.*类份额自.*日起暂停.*以上大额.*投资业务.*日起恢复上述业务.$",
                    r"不再设置金额限制.届时将不再另行公告。$",
                    r"单个基金账户对本基金日累计金额超过",
                    r"投资者单日单个基金账户",
                ],
                "model_alternative": True,
                "multi_elements": True,
                "regs": [
                    rf".*(单[个一]投资者|[人单每]个基金账户)[^。]*(累计|最高)([{R_CN}]+)?持有[份金]额.*",
                ],
            },
        ],
    },
    {
        "path": ["单客户持仓上限单位"],
        "models": [
            {
                "name": "partial_text",
            },
            {
                "name": "elements_collector_based",
                "elements_collect_model": "elements_from_depends",
                "elements_collect_config": {
                    "depends": ["单客户持仓上限"],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        rf".*(单[个一]投资者|[人单每]个基金账户)[^。]*(累计|最高)([{R_CN}]+)?持有[份金]额上限由.*调整为[\d.,，]+(?P<dst>[十百千万亿元]+)",
                    ],
                },
            },
        ],
    },
    {
        "path": ["恢复大额申购、转换转入及定期定额投资业务时间"],
        "models": [
            {
                "name": "partial_text",
                "order_by_index": True,
                "multi_elements": True,
                "regs": [
                    rf".*恢复([{R_CN}]+)?(大额申购|转换|转入|定期定额投资)[^。]*业务(?!的公告)(?!公告).*",
                    r".*(?<!开放赎回、)(大额申购|转换|转入|定期定额投资|恢复上述相关)[^。]*(业务|限额为).*另行公告.*",
                ],
            },
        ],
    },
    {
        "path": ["单笔赎回下限-原文"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r".*(每次|单笔)赎回.*",
                ],
            },
        ],
    },
    {
        "path": ["单笔赎回下限"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": {
                    "基金名称": [],
                    "最低限额": [
                        r"(每次|单笔)赎回不得少于(?P<dst>\d+份)",
                        r"每个交易账户赎回的基金份额不得[少低]于(?P<dst>\d+份)",
                    ],
                    "销售平台": [],
                },
            },
        ],
    },
    {
        "path": ["公告类型"],
        "models": [
            {
                "name": "middle_paras",
                "use_top_crude_neighbor": False,
                "top_default": True,
                "bottom_anchor_regs": [
                    "公告送出日期",
                ],
                "include_bottom_anchor": True,
                "bottom_anchor_content_regs": [
                    r"(?P<content>.*)公告送出日期",
                ],
                "top_anchor_content_regs": [
                    r"(?P<content>.*)\d公告基本信息",
                    r"(?P<content>.*)",
                ],
            },
            {
                "name": "middle_paras",
                "use_top_crude_neighbor": False,
                "top_default": True,
                "bottom_anchor_regs": [
                    "公告基本信息",
                ],
                "ignore_pattern": [
                    r"公告送出日期",
                ],
            },
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>.*)\d公告基本信息",
                    r"(?P<dst>.*)公告送出日期",
                ],
            },
        ],
    },
    {
        "path": ["产品户类型"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["主基金基金名称"],
        "models": [
            {
                "name": "cell_partial_text",
                "from_cell": False,
                "neglect_patterns": [r"下属|分级"],
                "regs": [
                    r"基金名称(?P<dst>.*)",
                ],
            },
            {
                "name": "partial_text",
                "regs": [
                    r"关于取消(?P<dst>.+基金)[A-Z]类",
                    r"关于取消(?P<dst>.+基金)",
                    r"(?P<dst>.+基金)调整申购",
                ],
            },
        ],
    },
    {
        "path": ["主基金基金代码"],
        "models": [
            {
                "name": "cell_partial_text",
                "from_cell": False,
                "neglect_patterns": [r"下属|分级"],
                "regs": [
                    r"基金主代码(?P<dst>.*)",
                ],
            },
            {
                "name": "partial_text",
                "regs": [
                    r"基金代码[:：](?P<dst>\d{6})",
                ],
            },
        ],
    },
    {
        "path": ["主基金持有份额限制金额"],
        "models": [
            {
                "name": "cell_partial_text",
                "from_cell": False,
                "neglect_patterns": [
                    r"下属|分级",
                    r"\d{2,4}年\d{1,2}月\d{1,2}日",
                ],
                "regs": [
                    r"持有(份额限制数量|金额限制).*?(?P<dst>[\d.,，]+)",
                ],
            },
        ],
    },
    {
        "path": ["主基金限制申购金额"],
        "models": [
            {
                "name": "cell_partial_text",
                "from_cell": False,
                "break_pattern": [r"下属|分级"],
                "neglect_patterns": [
                    r"下属|分级",
                    r"[.]\d{2}.*[.]\d{2}",
                ],
                "regs": [
                    r"(限制|调整)申购(投资)?金额.*?(?P<dst>[\d.,，十千万亿]{2,})",
                    r"限制大额申购.转换转入及.*金额.*?(?P<dst>[\d.,，十千万亿]{2,})",
                ],
            },
        ],
    },
    {
        "path": ["主基金限制转换转入金额"],
        "models": [
            {
                "name": "cell_partial_text",
                "from_cell": False,
                "neglect_patterns": [r"下属|分级"],
                "regs": [
                    r"(限制|调整)转换转入(投资)?金额.*?(?P<dst>[\d.,，]+)",
                    r"限制大额申购.转换转入及.*金额.*?(?P<dst>[\d.,，]+)",
                ],
            },
        ],
    },
    {
        "path": ["主基金限制定期定额投资金额"],
        "models": [
            {
                "name": "cell_partial_text",
                "from_cell": False,
                "neglect_patterns": [r"下属|分级"],
                "regs": [
                    r"(限制|调整)定期定额(投资|申购)金额.*?(?P<dst>[\d.,，]+)",
                    r"限制大额申购.转换转入及.*金额.*?(?P<dst>[\d.,，]+)",
                ],
            },
            {
                "name": "partial_text",
                "regs": [
                    r"限制定期定额投资金额.(?P<dst>[\d.,，元]+)",
                ],
            },
        ],
    },
    {
        "path": ["产品持有期"],
        "models": [
            {
                "name": "fixed_position",
                "target_element": [ElementClass.PARAGRAPH.value],
                "pages": [0],
                "neglect_patterns": [
                    r"^公告送出日期",
                ],
                "regs": p_holding_period,
            }
        ],
    },
    {
        "path": ["产品持有期单位"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "elements_from_depends",
                "elements_collect_config": {
                    "depends": ["产品持有期"],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": p_holding_period_unit,
                },
            },
        ],
    },
    {
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4822#note_595140
        "path": ["首次认购下限-原文"],
        "models": [
            {
                "name": "para_match",
                "syllabus_regs": [
                    r"基金的?募集",
                ],
                "combine_paragraphs": True,
                "multi_elements": True,
                "order_by_index": True,
                "paragraph_pattern": [
                    rf"(起点|首[次笔])认购[^,.。；;]*?{R_AMOUNT}",
                    rf"单笔最.认购金额为?{R_AMOUNT}",
                ],
            },
            {
                "name": "para_match",
                "combine_paragraphs": True,
                "multi_elements": True,
                "order_by_index": True,
                "neglect_syllabus_regs": [
                    r"申购金额的限制",
                ],
                "paragraph_pattern": [
                    rf"(起点|首[次笔])认购[^,.。；;]*?{R_AMOUNT}",
                    rf"单笔最.认购金额为?{R_AMOUNT}",
                ],
            },
        ],
    },
    {
        "path": ["首次认购下限"],
        "sub_primary_key": ["基金名称", "最低限额", "销售平台"],
        "strict_group": True,
        "models": [
            {
                "name": "subscription",
                "main_column": "销售平台",
                "depends": ["首次认购下限-原文"],
                "multi_config": {
                    "基金名称": True,
                    "最低限额": False,
                    "销售平台": False,
                },
                "para_regs": [
                    rf"(起点|首[次笔])[^,.。；;]*?{R_AMOUNT}",
                    rf"单笔最.(认购)?金额为?{R_AMOUNT}",
                ],
                "regs": {
                    "基金名称": gen_fund_name_regex("首[次笔]认购"),
                    "最低限额": [
                        rf"(起点|首[次笔])[^,.。；;]*?{R_AMOUNT}",
                        rf"单笔最.(认购)?金额为?{R_AMOUNT}",
                    ],
                    "销售平台": [
                        *gen_platform_regex("(认购(?!金额)|首次)"),
                        rf"管理人(本基金)?(?P<dst>[^。;；,，]*{R_PLATFORM_KEYWORDS})",
                    ],
                },
                "neglect_answer_patterns": {
                    "销售平台": [
                        r"可以?多次",
                    ]
                },
            },
            gen_table_subscription("首[次笔].*认.*购"),
        ],
    },
    {
        "path": ["追加认购最低金额-原文"],
        "models": [
            {
                "name": "middle_paras",
                "use_top_crude_neighbor": False,
                "top_anchor_regs": [
                    r"(?<!低|高)追加认购",
                    r"追加(最[低高])?金额",
                ],
                "bottom_anchor_regs": [
                    r"恪尽职守",
                    r"^[（(]?[一二三四五六七八九十零〇\d]+",
                    r"累计认购",
                ],
                "neglect_bottom_anchor": [
                    r"追加认购",
                ],
                "top_anchor_content_regs": [
                    r"(?P<content>[^。]*?追加.*?)[^。]*累计认购",
                    r"(?P<content>[^。]*?追加.*?)[（(]?[一二三四五六七八九十零〇\d]+[.、](?!\d+)",
                    r"(?P<content>[^。]*?追加.*)",
                    r"(?P<content>.*)",
                ],
            },
        ],
    },
    {
        "path": ["追加认购最低金额"],
        "sub_primary_key": ["基金名称", "最低限额", "销售平台"],
        "strict_group": True,
        "models": [
            {
                "name": "subscription",
                "main_column": "销售平台",
                "depends": ["追加认购最低金额-原文"],
                "multi_config": {
                    "基金名称": True,
                    "最低限额": False,
                    "销售平台": False,
                },
                "regs": {
                    "基金名称": gen_fund_name_regex("追加"),
                    "最低限额": [
                        rf"追加[^,.，。；;]*?{R_AMOUNT}",
                        r"追加认购(?P<dst>不受首次[^,.，。；;]*?限制)",
                    ],
                    "销售平台": [
                        *gen_platform_regex("(认购(?!金额)|首次)"),
                        rf"管理人(本基金)?(?P<dst>[^。;；,，]*{R_PLATFORM_KEYWORDS})",
                    ],
                },
                "para_regs": [
                    rf"追加[^,.，。；;]*?{R_AMOUNT}",
                    r"追加认购(?P<dst>不受首次[^,.，。；;]*?限制)",
                ],
                "neglect_answer_patterns": {
                    "销售平台": [
                        r"无法通过网上直销",
                    ]
                },
            },
        ],
    },
    {
        "path": ["单客户持仓下限"],
        "models": [
            {
                "name": "partial_text",
                "multi": True,
                "multi_elements": True,
                "model_alternative": True,
                "regs": {
                    "最低限额": [
                        r"最低持有(基金)?份额为(?P<dst>[\d.]+)份",
                        r"份额(余额)?(不足|少于)(?P<dst>[\d.]+)份.*(一起|全部)赎回",
                    ],
                    "单客户持仓下限单位": [
                        r"最低持有份额为[\d.]+(?P<dst>份)",
                        r"份额(余额)?(不足|少于)[\d.]+(?P<dst>份).*(一起|全部)赎回",
                    ],
                },
            },
        ],
    },
    {
        "path": ["基金转出最低份额"],
        "models": [
            {
                "name": "table_tuple",
            },
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": {
                    "最低限额": [r"(每次赎回|单笔赎回|转换转出).*?(?P<dst>[\d.]+份)"],
                    "基金名称": [r"(?P<dst>[A-Z]类基金份额)(每次赎回|单笔赎回|转换转出).*?[\d.]+份"],
                },
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"赎回份额限制"],
                "extract_from": "same_type_elements",
                "only_inject_features": True,
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": {
                        "最低限额": [
                            r"((每次|单笔|最低)赎回|转换转出).*?(?P<dst>[\d.]+份)",
                        ]
                    }
                },
            },
        ],
    },
    {
        "path": ["恢复大额申购、转换起始日"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    rf"(?P<dst>20[{R_HYPHENS}年月日\d/]+)起?[{R_CN}]*?恢复[{R_CN}(（）)\d]*?(大额)?申购",
                    rf"恢复大额申购.*?业务起始日(?P<dst>20[{R_HYPHENS}年月日\d/]+)",
                    r"恢复.*(上述业务|申购).*将另行公告",
                    r"本基金恢复办理个人投资者申购及转换转入业务的具体时间.*将另行公告",
                    r"有关本基金开放申购.*业务的具体规定若发生变化.*将另行公告",
                ],
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"公告基本信息"],
                "extract_from": "same_type_elements",
                "only_inject_features": True,
                "table_model": "cell_partial_text",
                "table_config": {
                    "regs": [
                        rf"恢复大额申购.*?日(?P<dst>20[{R_HYPHENS}年月日\d/]+)",
                    ]
                },
            },
        ],
    },
    {
        "path": ["恢复大额申购、转换金额"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"恢复办理.*?金额超过.*?的业务申请.(?P<dst>不再设置金额限制)",
                    r"基金将恢复.*投资限额为(?P<dst>.*?)[、]",
                    r"取消.*累计申购.*金额不超过(?P<dst>.*?)的限制",
                    r"基金大额申购限额为(?P<dst>.*?)[、）)]",
                    r"恢复.*[）)](?P<dst>\d+.*?)以上的大额申购",
                    r"恢复.*?投资(大额)?限额.*?金额超过(?P<dst>[\d.,元万]+).*?有权予以拒绝",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["产品简称"],
        "models": [
            {
                "name": "table_kv",
            },
        ],
    },
    {
        "path": ["申购开放周期-开始日期"],
        "models": [
            {
                "name": "partial_text",
                "regs": get_start_end_data("开始日期"),
                "model_alternative": True,
            },
            {
                "name": "fixed_position",
                "positions": list(range(0, 20)),
                "regs": [
                    rf"申购起始日(为)?(?P<dst>{R_DATE})",
                ],
            },
        ],
    },
    {
        "path": ["申购开放周期-结束日期"],
        "models": [
            {
                "name": "partial_text",
                "regs": get_start_end_data("结束日期"),
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["赎回开放周期-开始日期"],
        "models": [
            {
                "name": "partial_text",
                "regs": get_start_end_data("开始日期"),
                "model_alternative": True,
            },
            {
                "name": "fixed_position",
                "positions": list(range(0, 20)),
                "regs": [
                    rf"赎回起始日(为)?(?P<dst>{R_DATE})",
                ],
            },
        ],
    },
    {
        "path": ["赎回开放周期-结束日期"],
        "models": [
            {
                "name": "partial_text",
                "regs": get_start_end_data("结束日期"),
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["滚动期开放天数"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__日常申购.赎回等?业务的办理时间"],
                "extract_from": "same_type_elements",
                "only_inject_features": True,
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [r"(?P<dst>\d+[天日])的滚动运作期"],
                },
            },
        ],
    },
    {
        "path": ["单笔申购上限"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__申购金额限制"],
                "extract_from": "same_type_elements",
                "only_inject_features": True,
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        r"(每次|单笔)申购金额不得超过人民币(?P<dst>[\d.,万元]+)",
                    ],
                },
            },
        ],
    },
    {
        "path": ["申购基数"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["单笔赎回上限"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["赎回基数"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["基金转出最高份额"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
]


prophet_config = {
    "depends": {},
    "predictor_options": get_predictor_options(predictor_options),
}
