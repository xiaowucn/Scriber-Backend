"""
产品发售公告
"""

from remarkable.predictor.cmbchina_predictor.schemas import (
    R_PLATFORM_KEYWORDS,
    gen_fund_name_regex,
    gen_platform_regex,
    get_predictor_options,
    p_fund_abbr,
    p_fund_code,
)
from remarkable.predictor.common_pattern import R_CN, R_CONJUNCTION, R_HYPHENS

r_graded_fund = [
    r"基金代码.*基金代码",
    r"基金份额.*基金份额",
    r"[A-Z][,，、]基金代码",
    r"[A-Z][类级]",
    r"发起式[A-Z]$",
]


def product_sales_target():
    return [
        {
            "name": "partial_text",
            "regs": [
                r"(?P<dst>本基金的?(募集|发售|销售|发行)对象(包括|为)符合法律法规.*?其他投资人.)$",
                r"(?P<dst>^本基金(募集|发售|销售|发行)对象(包括|为)符合法律法规.*?其他投资人.)个人",
                r"(?P<dst>本基金(募集|发售|销售|发行)对象(包括|为)符合法律法规.*?其他投资人.)(\d+[、.])",
                r"(?P<dst>^符合法律法规规定的.*?其他投资人.)(\d+[、.])",
                r"(?P<dst>在募集期内面向符合法律法规.*?其他投资人.)(\d+[、.])",
            ],
        },
        {
            "name": "partial_text",
            "order_by_index": True,
            "multi_elements": True,
            "regs": [
                r"(?P<dst>[^。]*(募集|发售|销售|发行)对象为符合法律法规规定.*?)本基金单一投资者.*?不超过1000万元",
                r"(?P<dst>[^。]*(募集|发售|销售|发行)对象为符合法律法规规定.*?)(\d+[、.]|个人投资者是?指)",
                r"(?P<dst>.*《发售指引》规定的.*证监会.*)",
            ],
        },
        {
            "name": "para_match",
            "paragraph_pattern": [
                r"满足《基础设施基金指引》",
            ],
        },
        {
            "name": "elements_collector_based",
            "elements_collect_model": "middle_paras",
            "elements_collect_config": {
                "use_top_crude_neighbor": False,
                "top_anchor_regs": [r"基金[^,，。；;]*对象(为|包括|符合)"],
                "bottom_anchor_regs": [
                    r"^\d+[、.]",
                ],
            },
            "paragraph_model": "para_match",
            "para_config": {
                "combine_paragraphs": True,
                "multi_elements": True,
                "paragraph_pattern": [
                    r"基金[^,，。；;]*对象(为|包括|符合)",
                    r"暂不向.*机构.*账户.*?销售",
                    r"合格境外投资者以及法律法规或中国证监会允许购买证券投资基金",
                ],
            },
        },
    ]


predictor_options = [
    {
        "path": ["分级基金"],
        "sub_primary_key": ["基金简称", "基金代码"],
        "divide_answers": True,
        "models": [
            {
                "name": "table_row",
                "neglect_row": [r"基金[名简]称", r"基金代码"],
                "feature_black_list": {
                    "基金简称": [r"__regex__.*"],
                    "基金代码": [r"__regex__.*"],
                },
                "feature_white_list": {
                    "基金简称": [r"__regex__基金[名简]称"],
                    "基金代码": [r"__regex__基金代码"],
                },
            },
            {
                "name": "cell_partial_text",
                "merge_char_result": False,
                "from_cell": False,
                "regs": {
                    "基金简称": [
                        r"(?P<dst>.[类级](基金份额|份额基金)).{,5}代码",
                        r"(?P<dst>.[类级](基金份额|份额基金))\d+",
                    ],
                    "基金代码": [
                        r"代码[:：（(](?P<dst>\d+)",
                        r"[类级](基金份额|份额基金)(?P<dst>\d+)",
                    ],
                },
                "multi": True,
            },
            {
                "name": "classified_fund_partial_text",
                "order_by_index": True,
                "merge_char_result": False,
                "multi_elements": True,
                "multi": True,
                "neglect_patterns": [r"升级"],
                "syllabus_regs": [
                    r"基本(情况|信息)",
                    rf"基金(?:(?:(名|简)称|代码)[{R_CONJUNCTION}]?){{1,2}}",
                    r"基金代码",
                ],
                "neglect_syllabus_regs": [
                    r"份额的?类别",
                    r"投资者认购",
                ],
                "regs": {
                    "基金简称": p_fund_abbr,
                    "基金代码": [
                        *p_fund_code,
                        r"基金代码[:：](?P<dst>\d+)($|[;；])",
                        r"[A-Z][,，、](?P<dst>\d{6})[;；。]",
                    ],
                },
                "neglect_answer_patterns": {
                    "基金简称": [
                        r"^\d{6}$",
                        r"[:：]",
                        r"证券代码|认购代码|基金代码",
                    ],
                },
            },
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_top_crude_neighbor": False,
                    "top_anchor_regs": [r"(发售|募集)的?基本情况"],
                    "bottom_anchor_regs": [
                        r"基金份额的?类别设置",
                        r"发售规模和发售结构",
                        r"基金的?类型$",
                        r"基金存续期限$",
                    ],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "merge_char_result": False,
                    "multi_elements": True,
                    "multi": True,
                    "neglect_patterns": [r"升级"],
                    "neglect_syllabus_regs": [r"份额的?类别"],
                    "regs": {
                        "基金简称": [*p_fund_abbr, r"^农.*投资基金$"],
                        "基金代码": [*p_fund_code, r"^(?P<dst>\d+)$"],
                    },
                    "neglect_answer_patterns": {
                        "基金简称": [
                            r"^\d{6}$",
                            r"[:：]",
                            r"证券代码|认购代码|基金代码",
                        ],
                    },
                },
            },
            {
                "name": "partial_text",
                "order_by_index": True,
                "merge_char_result": False,
                "multi_elements": True,
                "multi": True,
                "regs": {
                    "基金简称": p_fund_abbr,
                    "基金代码": p_fund_code,
                },
                "neglect_answer_patterns": {
                    "基金简称": [
                        r"^\d{6}$",
                        r"[:：]",
                        r"证券代码|认购代码|基金代码",
                    ],
                },
            },
        ],
    },
    {
        "path": ["募集开始-结束日"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["首次认购下限-原文"],
        "models": [
            {
                "name": "middle_paras",
                "use_top_crude_neighbor": False,
                "top_anchor_regs": [
                    r"(?<!投资者在)(?<!调整)(首[次笔](单笔)?(提交)?(最[低高])?认购|认购(金额)?起点)[^。;；,，]*(最.)?(金|限)额(?!限制)",
                    r"认购(金额)?起点",
                    r"首次认购.*?单笔最低限额",
                ],
                "bottom_anchor_regs": [
                    r"恪尽职守",
                    r"^[（(]?[一二三四五六七八九十零〇\d]+",
                    r"累计认购",
                ],
                "neglect_bottom_anchor": [
                    r"(首次认购|认购起点)",
                ],
                "ignore_pattern": [
                    r"^本基金单一投资者单日认购金额不超过1000万元",  # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/10917?projectId=41&treeId=66&fileId=1272&schemaId=5
                    r"^资者避免短期频繁操作，坚持长期投资",
                ],
                "top_anchor_content_regs": [
                    r"(?P<content>[^。]*?(首[次笔](单笔)?(提交)?(最[低高])?认购|认购(金额)?起点).*单独计算.)$",
                    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/5208#note_572644
                    r"(?P<content>[^。]*?(首[次笔](单笔)?(提交)?(最[低高])?认购|认购(金额)?起点).*)。.*不设上限",
                    r"(?P<content>[^。]*?(首[次笔](单笔)?(提交)?(最[低高])?认购|认购(金额)?起点).*?)[（(]?[一二三四五六七八九十零〇\d]+[.、](?!\d+)",
                    r"(?P<content>[^。]*?(首[次笔](单笔)?(提交)?(最[低高])?认购|认购(金额)?起点).*)",
                    r"(?P<content>.*)",
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
                    "最低限额": True,
                    "销售平台": False,
                },
                "regs": {
                    "基金名称": gen_fund_name_regex("首[次笔]认购"),
                    "最低限额": [
                        r"(起点|首[次笔])[^,.。；;]*?(?P<dst>[\d.\s,，]+千?百?万?元)",
                        r"(?<!追加)(?<!追加[认申]购)(?<!追加[认申]购的)[单每首]笔(认购)?的?最.(认购)?金额为?(人民币)?(?P<dst>[\d.\s,，]+千?百?万?元)",
                    ],
                    "销售平台": [
                        "有限公司(?P<dst>直销机构)认购",
                        *gen_platform_regex("((办理基金)?认购(?!金额)|首[次笔])"),
                        rf"管理人(本基金)?(?P<dst>[^。;；,，]*?{R_PLATFORM_KEYWORDS})",
                    ],
                },
                "para_regs": [
                    r"(起点|首[次笔])[^,.。；;]*?(?P<dst>[\d.\s,，]+千?百?万?元)",
                    r"单笔最.认购金额为?(?P<dst>[\d.\s,，]+千?百?万?元)",
                ],
                "neglect_answer_patterns": {
                    "销售平台": [
                        r"可以?多次",
                    ]
                },
            },
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
                "ignore_pattern": [
                    r"^本基金单一投资者单日认购金额不超过1000万元",  # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/10917?projectId=41&treeId=66&fileId=1272&schemaId=5
                    r"^资者避免短期频繁操作，坚持长期投资",
                ],
                "top_anchor_content_regs": [
                    r"(?P<content>[^。]*?(首[次笔](单笔)?(提交)?(最[低高])?认购|认购(金额)?起点).*单独计算.)$",
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
                        r"追加[^,.，。；;]*?(?P<dst>[\d.\s,，]+千?百?万?元)",
                        r"追加认购(?P<dst>不受首次[^,.，。；;]*?限制)",
                    ],
                    "销售平台": [
                        r"基金管理人(?P<dst>直销中心[（(].*[））]以及其他销售机构)认购",
                        r"基金管理人(?P<dst>直销柜台以及其他销售机构)",
                        *gen_platform_regex("(认购(?!金额)|首次)"),
                        rf"管理人(本基金)?(?P<dst>[^。;；,，]*{R_PLATFORM_KEYWORDS})",
                    ],
                },
                "para_regs": [
                    r"追加[^,.，。；;]*?(?P<dst>[\d.\s,，]+千?百?万?元)",
                    r"追加认购(?P<dst>不受首次[^,.，。；;]*?限制)",
                ],
                "neglect_answer_patterns": {
                    "销售平台": [
                        r"无法通过网上直销",
                        r"及各家销售机构",  # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/5777#note_629119
                    ]
                },
            },
        ],
    },
    {
        "path": ["基金名称"],
        "models": [
            {
                "name": "middle_paras",
                "elements_in_page_range": [0],
                "top_default": True,
                "bottom_anchor_regs": [r"发售公告$"],
                "top_anchor_content_regs": [
                    r"基金管理([(（]中国[）)])?有限公司(?P<content>.*)",
                    r"(?P<content>.*)",
                ],
                "bottom_anchor_content_regs": [
                    r"(?P<content>.*基金([(（][a-zA-Z]+[）)])?)基金份额发售公告",
                    r"(?P<content>.*?(基金)?)份额发售公告",
                ],
                "include_bottom_anchor": True,
            },
            {
                "name": "partial_text",
                "page_range": [0],
                "model_alternative": True,
                "regs": [
                    r"基金管理([(（]中国[）)])?有限公司(?P<dst>.*基金([(（][a-zA-Z]+[）)])?)基金份额发售公告",
                    r"基金管理([(（]中国[）)])?有限公司(?P<dst>.*基金([(（][a-zA-Z]+[）)])?)份额发售公告",
                    r"(?P<dst>.*?基金([(（][a-zA-Z]+[）)])?).*?基金份额发售公告",
                    r"(?P<dst>.*基金([(（][a-zA-Z]+[）)])?)份额发售公告",
                ],
            },
            {
                "name": "partial_text",
                "regs": [
                    r"[名全]称[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["基金代码"],
        "models": [
            {
                "name": "partial_text",
                "syllabus_regs": [r"基本情况", r"基金简称和代码"],
                "elements_nearby": {
                    "neglect_regs": r_graded_fund,
                    "amount": 2,
                    "step": -1,
                },
                "neglect_patterns": r_graded_fund,
                "regs": [r"基金代码[:：](?P<dst>\d+)"],
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": ["__regex__基金代码"],
                "only_inject_features": True,
                "paragraph_model": "partial_text",
                "para_config": {
                    "elements_nearby": {
                        "neglect_regs": r_graded_fund,
                        "amount": 2,
                        "step": -1,
                    },
                    "regs": [r"(?P<dst>\d{2,})"],
                },
            },
        ],
    },
    {
        "path": ["产品销售对象"],
        "models": [
            *product_sales_target(),
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_top_crude_neighbor": False,
                    "top_anchor_regs": [r"重要提示$", r"发售公告"],
                    "bottom_anchor_regs": [
                        r"基本(信息|情况)$",
                    ],
                },
                "paragraph_model": "para_match",
                "para_config": {
                    "combine_paragraphs": True,
                    "multi_elements": True,
                    "paragraph_pattern": [
                        r"(募集|发售|销售)对象.+",
                        r"符合法律法规规定的可投资于",
                    ],
                },
            },
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_top_crude_neighbor": False,
                    "top_anchor_regs": [
                        r"基本(信息|情况)$",
                    ],
                    "bottom_default": True,
                },
                "paragraph_model": "para_match",
                "para_config": {
                    "combine_paragraphs": True,
                    "multi_elements": True,
                    "paragraph_pattern": [
                        r"(募集|发售|销售)对象.+",
                        r"符合法律法规规定的可投资于",
                    ],
                },
            },
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__(募集|发售)对象$",
                ],
                "break_para_pattern": [
                    r"^\d+[、.]",
                ],
            },
            {
                "name": "para_match",
                "syllabus_regs": [
                    r"选择标准|参与对象",
                ],
                "paragraph_pattern": [
                    r"符合《发售指引》规定的[^。；;]*、",
                    r"参与基金份额战略配售的投资者应当满足",
                ],
            },
        ],
    },
    {
        "path": ["产品户类型"],
        "models": [
            *product_sales_target(),
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_top_crude_neighbor": False,
                    "top_anchor_regs": [r"重要提示$", r"发售公告"],
                    "bottom_anchor_regs": [
                        r"基本(信息|情况)$",
                    ],
                },
                "paragraph_model": "para_match",
                "para_config": {
                    "combine_paragraphs": True,
                    "multi_elements": True,
                    "paragraph_pattern": [
                        r"基金[^,，。；;]*对象(是|为|包括|符合)",
                        r"暂不向.*机构.*账户销售",
                        r"符合法律法规规定的可投资于",
                    ],
                },
            },
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_top_crude_neighbor": False,
                    "top_anchor_regs": [
                        r"基本(信息|情况)$",
                    ],
                    "bottom_default": True,
                },
                "paragraph_model": "para_match",
                "para_config": {
                    "combine_paragraphs": True,
                    "multi_elements": True,
                    "paragraph_pattern": [
                        r"参与(基金份额|基础设施基金的)战略配售",
                    ],
                },
            },
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__募集对象$",
                ],
                "break_para_pattern": [
                    r"^\d+[、.]",
                ],
            },
        ],
    },
    {
        "path": ["募集开始日期"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_top_crude_neighbor": False,
                    "top_anchor_regs": [r"重要提示"],
                    "bottom_anchor_regs": [
                        r"基本情况",
                    ],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        rf"(募集|发售)期限?[于自为]+?(?P<dst>\d{{4}}年\d{{1,2}}月\d{{1,2}}日([（(]含[）)])?)[{R_HYPHENS}至起当]",
                        rf"基金(份额)?将?[于自为]?(?P<dst>\d{{4}}年\d{{1,2}}月\d{{1,2}}日([（(]含[）)])?)[{R_HYPHENS}至起当][^。]*发售",
                    ],
                },
            },
            {
                "name": "partial_text",
                "regs": [
                    rf"(募集|发售)期[于自为]+?(?P<dst>\d{{4}}年\d{{1,2}}月\d{{1,2}}日([（(]含[）)])?)[{R_HYPHENS}至起当]",
                    rf"基金(份额)?将?[于自为]?(?P<dst>\d{{4}}年\d{{1,2}}月\d{{1,2}}日([（(]含[）)])?)[{R_HYPHENS}至起当][^。]*发售",
                ],
            },
        ],
    },
    {
        "path": ["募集结束日期"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_top_crude_neighbor": False,
                    "top_anchor_regs": [r"重要提示"],
                    "bottom_anchor_regs": [
                        r"基本情况",
                    ],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [
                        rf"(募集|发售)期.*?[{R_HYPHENS}至](?P<dst>\d{{4}}年\d{{1,2}}月\d{{1,2}}日([（(]含[）)])?)",
                        rf"基金.*?[{R_HYPHENS}至](?P<dst>\d{{4}}年\d{{1,2}}月\d{{1,2}}日([（(]含[）)])?)[^。]*发售",
                    ],
                },
            },
            {
                "name": "partial_text",
                "regs": [
                    rf"(募集|发售)期.*?[{R_HYPHENS}至](?P<dst>\d{{4}}年\d{{1,2}}月\d{{1,2}}日([（(]含[）)])?)",
                    rf"基金.*?[{R_HYPHENS}至](?P<dst>\d{{4}}年\d{{1,2}}月\d{{1,2}}日([（(]含[）)])?)[^。]*发售",
                ],
            },
        ],
    },
    {
        "path": ["产品简称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "neglect_syllabus_regs": [r"本次募集基本情况"],
                "neglect_answer_patterns": [
                    r"(债券|指数|基金|[）])[A-Z]",
                    r"^[A-Z]类",
                    r"[A-Z]类[）]?$",
                    r"[^A-Z][A-Z]$",
                ],
                "regs": [
                    r"(基金|场外)简称[:：](?P<dst>.+?)[A-Z]类基金份额",
                    r"[(（][^）)]*(基金|场外)简称[:：](?P<dst>[^,，。；;]+)[）)]",
                    r"(基金|场外)简称[:：](?P<dst>[^,，。；;]+)",
                    r"^简称[:：](?P<dst>[^,，。；;]+)",
                ],
            },
            {
                "name": "table_kv",
                "feature_white_list": [
                    "__regex__基金简称[:：]?",
                ],
            },
        ],
    },
    {
        "path": ["托管机构"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "model_alternative": True,
                "regs": [
                    r"托管人[:：为是](?P<dst>.*公司)二〇二.年",
                    r"托管人[:：为是](?P<dst>[^,，。；;]*)登记机构",
                    r"托管人[:：为是](?P<dst>[^,，。；;]*)",
                ],
            },
        ],
    },
    {
        "path": ["认购交易确认日期"],
        "models": [
            {
                "name": "partial_text",
                "multi_elements": True,
                "model_alternative": True,
                "text_regs": [
                    r"T([+＋\d]+)?日",
                    r"生效后第\d个工作日",
                ],
                "regs": [
                    r".*T([+＋\d]+)?日.*查询认购申请[^。]*",
                ],
            },
        ],
    },
    {
        "path": ["单笔认购上限"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
    {
        "path": ["单笔认购下限-原文"],
        "models": [
            {
                "name": "middle_paras",
                "use_top_crude_neighbor": False,
                "top_anchor_regs": [
                    # http://scriber-cmbchina.test.paodingai.com/scriber/#/project/remark/9545?projectId=6&treeId=16&fileId=373&schemaId=5&schemaKey=%E5%8D%95%E7%AC%94%E8%AE%A4%E8%B4%AD%E4%B8%8B%E9%99%90-%E5%8E%9F%E6%96%87
                    r"(?<!投资者在)(?<!调整)([单每][笔次](提交)?(最低)?认购|认购(金额)?起点)[^。;；,，]*((最.)?(金|限)额(?!限制)|[\d,万]+[份元]以上)",
                    r"(?<!追加)认购[^。;；,，]*[单每][笔次](最.)?(金|限)额(?!限制)",
                    r"认购[^。;；,，]*[单每][笔次][^。;；,，]*[\d,万]+[份元]或其整数倍",
                    r"(?<!基金的)认购(金额)?起点",
                    r"首笔认购的(单笔)?最低[金限]额为",
                    r"最低认购[金限]额为单笔",
                ],
                "bottom_anchor_regs": [
                    r"恪尽职守",
                    r"^[（(]?[一二三四五六七八九十零〇\d]+",
                    r"累计认购",
                    r"^参与本次询价",
                ],
                "neglect_top_anchor": [
                    r"^当发生部分确认时",
                ],
                "neglect_bottom_anchor": [
                    r"(首次认购|认购起点)",
                ],
            },
        ],
    },
    {
        "path": ["单笔认购下限"],
        "sub_primary_key": ["基金名称", "最低限额", "销售平台"],
        "strict_group": True,
        "models": [
            {
                "name": "subscription",
                "main_column": "销售平台",
                "depends": ["单笔认购下限-原文"],
                "multi_config": {
                    "基金名称": True,
                    "最低限额": False,
                    "销售平台": False,
                },
                "regs": {
                    "基金名称": gen_fund_name_regex("首[次笔]认购"),
                    "最低限额": [
                        r"每笔认购份额(须|需)[为在](?P<dst>[\d.\s,，]+千?百?万?份)(或其整数倍|以上)",
                        r"(?<!追加)(?<!追加[认申]购)(?<!追加[认申]购本基金基金份额的)(起点|[单每][次笔])(?!追加)[^,.。；;]*?(?P<dst>[\d.\s,，]+千?百?万?元)",
                        r"(?<!追加)(?<!追加[认申]购)(?<!追加[认申]购本基金基金份额的)[单每][次笔](认购)?的?最.(认购)?金额为?(人民币)?(?P<dst>[\d.\s,，]+千?百?万?元)",
                    ],
                    "销售平台": [
                        rf"基金管理人(?P<dst>直销机构[（(][{R_CN}]+[）)]及(非直销销售机构|代销机构))",
                        r"(?P<dst>发售代理机构(办理网下现金认购)?)",
                        r"已在(?P<dst>.*)有认/申购",
                        *gen_platform_regex("((办理基金)?认购(?!金额)|单[次笔])"),
                        rf"管理人(本基金)?(?P<dst>[^。;；,，]*?{R_PLATFORM_KEYWORDS})",
                    ],
                },
                "neglect_patterns": [
                    r"^追加[认申]购",
                ],
                "para_regs": [
                    r"(起点|[单每][次笔])(?!追加)[^,.。；;]*?(?P<dst>[\d.\s,，]+(千?百?万?元|份))",
                    r"[单每][次笔]最.(认购)?金额为?(人民币)?(?P<dst>[\d.\s,，]+千?百?万?元)",
                    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/6609#note_686552
                    r"首笔认购的([单每][次笔])最低[金限]额为",
                    r"[单每][次笔]认购份额须[为在][\d.\s,，]+千?百?万?份(或其整数倍|以上)",
                ],
                "neglect_answer_patterns": {
                    "销售平台": [
                        r"可以?多次",
                        r"要求无法通过",
                    ]
                },
            },
        ],
    },
    {
        "path": ["单客户每日累计认购限额"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"(?P<content>[^。]*(单[一个]?(投资[人者]|客户|账户))([（].*[）])?的?([每单]日)?累计认购(.*认购申请不受上述比例的?限制[^。]*|.*基金合同生效后登记机构的确认为准[^。]*|[^。]*))",
                    r"(?P<content>[^。]*(单[一个]?(投资[人者]|客户|账户)).*(基金份额|认购份额).*(达到|超过|不设上限).*(法律法规.*另有规定的.*|拒绝该投资者的认购申请[^。]*))",
                ],
            },
        ],
    },
    {
        "path": ["首次认购上限"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": get_predictor_options(predictor_options),
}
