"""华夏营销部-基金合同V1"""

from remarkable.predictor.common_pattern import R_NOT_SENTENCE_END

predictor_options = [
    {
        "path": ["001基金名称"],
        "models": [
            {
                "name": "middle_paras",
                "page_range": [0],
                "top_anchor_regs": [
                    r"^华夏",
                ],
                "bottom_anchor_regs": [r"基金合同"],
                "top_anchor_content_regs": [
                    r"(?P<content>^华夏.*)",
                ],
                "bottom_anchor_content_regs": [
                    r"(?P<content>.*)基金合同",
                ],
                "include_bottom_anchor": True,
            },
            {
                "name": "fund_name",
                "page_range": [0],
                "regs": [
                    r"(?P<dst>华夏.*基金([(（][a-zA-Z]+[）)])?)基金合同",
                    r"(?P<dst>华夏.*)合同",
                    r"(?P<dst>华夏.+基金([(（][a-zA-Z]+[）)])?)",
                    r"(?<![：:])(?P<dst>华夏.*)",
                ],
                "neglect_patterns": [
                    r"[:：]",
                ],
            },
        ],
    },
    {
        "path": ["002管理人"],
        "models": [
            {
                "name": "auto",
                "page_range": [0],
                "regs": [
                    r"管理人[：:](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["003托管人"],
        "models": [
            {
                "name": "auto",
                "page_range": [0],
                "regs": [
                    r"托管人[：:](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["004基金名称"],
        "models": [
            {
                "name": "auto",
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>.*基金([(（][a-zA-Z]+[）)])?)基金合同",
                    r"(?P<dst>.*)合同",
                ],
            },
        ],
    },
    {
        "path": ["005基金名称"],
        "models": [
            {
                "name": "table_kv",
                "regs": [
                    rf"指(?P<dst>{R_NOT_SENTENCE_END}*)",
                ],
            },
            {
                "name": "auto",
                "model_alternative": True,
                "regs": [
                    rf"[:：]指?(?P<dst>{R_NOT_SENTENCE_END}*)",
                ],
            },
        ],
    },
    {
        "path": ["006管理人"],
        "models": [
            {
                "name": "table_kv",
                "regs": [
                    rf"指(?P<dst>{R_NOT_SENTENCE_END}*)",
                ],
            },
            {
                "name": "auto",
                "model_alternative": True,
                "regs": [
                    rf"[:：]指?(?P<dst>{R_NOT_SENTENCE_END}*)",
                ],
            },
        ],
    },
    {
        "path": ["007托管人"],
        "models": [
            {
                "name": "table_kv",
                "regs": [
                    rf"指(?P<dst>{R_NOT_SENTENCE_END}*)",
                ],
            },
            {
                "name": "auto",
                "model_alternative": True,
                "regs": [
                    rf"[:：]指?(?P<dst>{R_NOT_SENTENCE_END}*)",
                ],
            },
        ],
    },
    {
        "path": ["008基金名称"],
        "models": [
            {
                "name": "table_kv",
                "regs": [
                    r"指[<《]?(?P<dst>[^》>]*基金([(（][a-zA-Z]+[）)])?)基金合同",
                    r"指[<《]?(?P<dst>[^》>]*)合同",
                ],
            },
            {
                "name": "auto",
                "model_alternative": True,
                "regs": [
                    r"指[<《]?(?P<dst>[^》>]*基金([(（][a-zA-Z]+[）)])?)基金合同",
                    r"指[<《]?(?P<dst>[^》>]*)合同",
                ],
            },
        ],
    },
    {
        "path": ["009基金名称"],
        "models": [
            {
                "name": "table_kv",
                "regs": [
                    r"[<《](?P<dst>[^》>]*基金([(（][a-zA-Z]+[）)])?)基金托管协议",
                    r"[<《](?P<dst>[^》>]*)托管协议",
                ],
            },
            {
                "name": "auto",
                "model_alternative": True,
                "regs": [
                    r"[<《](?P<dst>[^》>]*基金([(（][a-zA-Z]+[）)])?)基金托管协议",
                    r"[<《](?P<dst>[^》>]*)托管协议",
                ],
            },
        ],
    },
    {
        "path": ["010基金名称"],
        "models": [
            {
                "name": "table_kv",
                "regs": [
                    r"[<《](?P<dst>[^》>]*基金([(（][a-zA-Z]+[）)])?)基金招募说明书",
                    r"[<《](?P<dst>[^》>]*)招募说明书",
                ],
            },
            {
                "name": "auto",
                "model_alternative": True,
                "regs": [
                    r"[<《](?P<dst>[^》>]*基金([(（][a-zA-Z]+[）)])?)基金招募说明书",
                    r"[<《](?P<dst>[^》>]*)招募说明书",
                ],
            },
        ],
    },
    {
        "path": ["011基金名称"],
        "models": [
            {
                "name": "table_kv",
                "regs": [
                    r"[<《](?P<dst>[^》>]*基金([(（][a-zA-Z]+[）)])?)基金产品",
                    r"[<《](?P<dst>[^》>]*)产品",
                ],
            },
            {
                "name": "auto",
                "model_alternative": True,
                "regs": [
                    r"[<《](?P<dst>[^》>]*基金([(（][a-zA-Z]+[）)])?)基金产品",
                    r"[<《](?P<dst>[^》>]*)产品",
                ],
            },
        ],
    },
    {
        "path": ["012基金名称"],
        "models": [
            {
                "name": "table_kv",
                "regs": [
                    r"[<《](?P<dst>[^》>]*基金([(（][a-zA-Z]+[）)])?)集中申购期",
                    r"[<《](?P<dst>[^》>]*基金([(（][a-zA-Z]+[）)])?)基金份额",
                    r"[<《](?P<dst>[^》>]*)份额",
                ],
            },
            {
                "name": "auto",
                "model_alternative": True,
                "regs": [
                    r"[<《](?P<dst>[^》>]*基金([(（][a-zA-Z]+[）)])?)集中申购期",
                    r"[<《](?P<dst>[^》>]*基金([(（][a-zA-Z]+[）)])?)基金份额",
                    r"[<《](?P<dst>[^》>]*)份额",
                ],
            },
        ],
    },
    {
        "path": ["013基金名称"],
        "models": [
            {
                "name": "auto",
            },
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__基本情况__regex__名称",
                ],
            },
        ],
    },
    {
        "path": ["014运作方式"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "only_inject_features": True,
                    "inject_syllabus_features": [
                        r"__regex__基本情况__regex__运作方式",
                    ],
                    "use_syllabus_model": True,
                    "include_bottom_anchor": True,
                    "top_anchor_regs": [
                        r"定期开放式",
                    ],
                    "bottom_anchor_regs": [
                        r"开放期的具体时间以(基金)?管理人届时公告为准",
                    ],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "multi_elements": True,
                    "regs": [
                        r".*采取.*运作方式.*",
                        r".*进入下一个封闭期.*",
                        r".*?开放期的具体时间以(基金)?管理人届时公告为准.",
                    ],
                },
            },
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__基本情况__regex__运作方式__regex__持有期",
                ],
                "ignore_pattern": [
                    r"提前公告",
                    r"^契约型开放式。$",
                    r"^\d+、",
                ],
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "include_top_anchor": False,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__基本情况__regex__运作方式",
                ],
                "top_anchor_regs": [
                    r"(运作期|开放期).?$",
                    r"^(\d+、)\W{0,4}持有期",
                    r"契约型开放式",
                ],
                "bottom_anchor_regs": [
                    r"根据(法律法规|(中国)?证监会)",
                    r"开放日及开放时间",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__基本情况__regex__运作方式",
                ],
                "ignore_pattern": [
                    r"提前公告",
                    r"^契约型开放式。$",
                ],
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["015投资目标"],
        "models": [
            {
                "name": "auto",
            },
            {
                "name": "syllabus_elt_v2",
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__基金的?投资目标",
                ],
            },
        ],
    },
    {
        "path": ["016运作方式"],
        "models": [
            {
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "use_syllabus_model": True,
                    "include_title": True,
                    "only_inject_features": True,
                    "inject_syllabus_features": [
                        r"__regex__份额的申购与赎回__regex__开放日及时间__regex__封闭期",
                    ],
                    "top_anchor_regs": [
                        r"封闭期",
                    ],
                    "bottom_anchor_regs": [
                        r"开放日及开放时间$",
                    ],
                },
                "paragraph_model": "partial_text",
                "para_config": {
                    "multi_elements": True,
                    "regs": [
                        r".*采取.*运作方式.*",
                        r".*进入下一个封闭期.*",
                        rf".*进入开放期.*具体时间{R_NOT_SENTENCE_END}*",
                    ],
                },
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__份额的申购与赎回__regex__开放日及时间",
                ],
                "top_anchor_regs": [
                    r"(运作期|持有期|开放期).?$",
                ],
                "bottom_anchor_regs": [
                    # r"运作期到期日.*赎回申请",
                    r"开放日及开放时间$",
                    r"不违反(法律法规|(中国)?证监会)",
                ],
                "include_top_anchor": False,
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["017管理人"],
        "models": [
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["018托管人"],
        "models": [
            {
                "name": "auto",
                "model_alternative": True,
                "regs": [
                    r"[：:](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["019投资目标"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["020投资范围"],
        "models": [
            {
                "name": "middle_paras",
                "include_top_anchor": False,
                "top_anchor_regs": [
                    r"投资范围$",
                ],
                "bottom_anchor_regs": [
                    r"比例(为|不|范围)",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "break_para_pattern": [
                    r"比例(为|不|范围)",
                ],
            },
            {
                "name": "auto",
                "multi": True,
            },
        ],
    },
    {
        "path": ["021投资比例"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "top_anchor_regs": [
                    r"比例(为|不|范围)",
                ],
                "bottom_anchor_regs": [
                    r"投资策略",
                    r"纳入本?(基金)?的?投资范围",
                ],
            },
            {
                "name": "auto",
                "multi": True,
            },
        ],
    },
    {
        "path": ["022投资策略"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__投资策略$",
                ],
                "ignore_pattern": [r"(调整|更[换新])相关投资策略"],
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["023投资限制"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "include_top_anchor": False,
                "top_anchor_regs": [
                    r"限制[:：]",
                ],
                "bottom_anchor_regs": [r"合同生效之日起"],
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "include_top_anchor": True,
                "top_default": True,
                "bottom_anchor_regs": [r"合同生效之日起"],
            },
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__投资(组合)?比例限制",
                ],
            },
        ],
    },
    {
        "path": ["024业绩比较基准"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "only_first": True,
                "only_use_syllabus_elements": True,
                "ignore_pattern": [
                    r"标的指数",
                    r"比较基准构成为[：:]$",
                ],
                "top_default": True,
                "bottom_default": True,
                "top_anchor_content_regs": [
                    r"比较基准[为:：](?P<content>.*)",
                    r"(?P<content>.*)",
                ],
            },
            {
                "name": "syllabus_elt_v2",
                "only_first": True,
                "ignore_pattern": [
                    r"标的指数",
                    r"比较基准构成为[：:]$",
                ],
            },
            {
                "name": "auto",
            },
        ],
    },
    {
        "path": ["025估值对象"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["026估值方法"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"估值方法",
                ],
            },
        ],
    },
    {
        "path": ["027管理费率"],
        "models": [
            {
                "name": "auto",
                "neglect_answer_patterns": [
                    r"如下[:：]",
                ],
                "multi": True,
                "regs": [r"管理费按.*?(?P<dst>[\d\.]+[%％])"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["028管理费率"],
        "models": [
            {
                "name": "auto",
                "model_alternative": True,
                "custom_regs": [
                    r"[H][＝=][E]×(?P<dst>[\d\.]+[%％])[÷/]",
                ],
            },
        ],
    },
    {
        "path": ["029托管费率"],
        "models": [
            {
                "name": "auto",
                "neglect_answer_patterns": [
                    r"如下[:：]",
                ],
                "multi": True,
                "regs": [r"托管费按.*?(?P<dst>[\d\.]+[%％])"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["030托管费率"],
        "models": [
            {
                "name": "auto",
                "model_alternative": True,
                "custom_regs": [
                    r"[H][＝=][E]×(?P<dst>[\d\.]+[%％])[÷/]",
                ],
            },
        ],
    },
    {
        "path": ["031销售服务费"],
        "models": [
            {
                "name": "auto",
                "regs": [r"销售服务费.*其中.(?P<dst>[A-Z]类.*销售服务费.费率为[\d.%％]+)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["032收益分配原则"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["033基金名称"],
        "models": [
            {
                "name": "auto",
                "page_range": [-1],
                "regs": [
                    r"(?P<dst>华夏.*基金([(（][a-zA-Z]+[）)])?)基金合同",
                    r"(?P<dst>华夏.*)合同",
                    r"(?P<dst>华夏.+基金)",
                ],
            },
        ],
    },
    {
        "path": ["034管理人"],
        "models": [
            {
                "name": "auto",
                "page_range": [-1],
                "regs": [
                    r"管理人[：:](?P<dst>.*)[（(](法人)?盖?章",
                    r"管理人[：:](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["035托管人"],
        "models": [
            {
                "name": "auto",
                "page_range": [-1],
                "regs": [
                    r"托管人[：:](?P<dst>.*)[（(](法人)?盖?章",
                    r"托管人[：:](?P<dst>.*)",
                ],
            },
        ],
    },
]
prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
