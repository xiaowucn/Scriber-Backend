"""华夏营销部-托管协议V1"""

from remarkable.predictor.common_pattern import R_COLON
from remarkable.predictor.eltype import ElementClass

INVESTMENT_LIMIT_REGS = [
    r"基金管理人应当[自在]基金合同生效(后|之日起)[6六]个月",
    r"其他有关法律法规或监管部门取消上述限制的",
    r"本部分约定的投资组合比例、组合限制等约定仅适用于主袋账户",
    r"对于因基金份额拆分、大比例分红等集中持续营销活动引起的基金净资产规模在",
]

INVESTMENT_RATIO_TOP_REGS = [
    r"投资组合比例",
    r"投资比例范围为",
    r"基金投资于.*?的比例",
    r"占基金资产的比例范围为",
]

INVESTMENT_SCOPE_BOTTOM_REGS = [
    r"投资组合比例|(资产|融资)比例|备选成份股的比例|投资.*?比例(为|不低于)基金资产|投资策略|比例",
]

predictor_options = [
    {
        "path": ["001基金名称"],
        "models": [
            {
                "name": "middle_paras",
                "elements_in_page_range": [0],
                "top_anchor_regs": [
                    r"^华夏",
                ],
                "bottom_anchor_regs": [r"托管协议"],
                "top_anchor_content_regs": [
                    r"(?P<content>^华夏.*)",
                ],
                "bottom_anchor_content_regs": [
                    r"(?P<content>.*)托管协议",
                ],
                "include_bottom_anchor": True,
            },
            {
                "name": "auto",
                "page_range": [0],
            },
            {
                "name": "partial_text",
                "page_range": [0],
                "regs": [
                    r"(?P<dst>.*?)托管协议",
                    r"(?P<dst>.*基金([(（][a-zA-Z]+[）)])?)",
                ],
                "neglect_patterns": [
                    rf"[{R_COLON}]",
                ],
            },
        ],
    },
    {"path": ["002管理人"], "models": [{"name": "auto"}]},
    {
        "path": ["003托管人"],
        "models": [
            {
                "name": "auto",
                "model_alternative": True,  # 配置的regs未能提取时用模型提
                "custom_regs": [
                    r"基金托管人[：:](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["004基金名称"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"(?P<dst>.*?)托管协议",
                    r"(?P<dst>.*基金([(（][a-zA-Z]+[）)])?)",
                ],
                "target_element": [ElementClass.PAGE_HEADER.value],
            },
        ],
    },
    {
        "path": ["005管理人"],
        "models": [
            {
                "name": "auto",
                "model_alternative": True,
                "custom_regs": [
                    r"鉴于(?P<dst>.*?公司).*管理人.*资格",
                ],
            }
        ],
    },
    {
        "path": ["006基金名称"],
        "models": [
            {
                "name": "auto",
                "model_alternative": True,
                "custom_regs": [
                    r"鉴于.*?拟募集(发行)?(?P<dst>.*?)([（(]以下|；)",
                ],
            },
        ],
    },
    {
        "path": ["007托管人"],
        "models": [
            {
                "name": "auto",
                "model_alternative": True,
                "custom_regs": [
                    r"鉴于(?P<dst>.*?公司).*托管人.*资格",
                ],
            },
        ],
    },
    {
        "path": ["008管理人"],
        "models": [
            {
                "name": "auto",
                "model_alternative": True,
                "custom_regs": [
                    r"鉴于(?P<dst>.*?)拟担任.*?基金管理人",
                ],
            },
        ],
    },
    {
        "path": ["009基金名称"],
        "models": [
            {
                "name": "auto",
                "model_alternative": True,
                "custom_regs": [
                    r"(拟担任|公司为)(?P<dst>.*?)的?基金管理人",
                ],
            },
        ],
    },
    {
        "path": ["010托管人"],
        "models": [
            {
                "name": "auto",
                "model_alternative": True,
                "custom_regs": [
                    r"，(?!按照)(?P<dst>.*?)拟担任.*?的基金托管人",
                ],
            },
        ],
    },
    {
        "path": ["011基金名称"],
        "models": [
            {
                "name": "auto",
                "model_alternative": True,
                "custom_regs": [
                    r"基金管理人.*?拟担任(?P<dst>.*?)的?基金托管人",
                ],
            },
        ],
    },
    {
        "path": ["012基金名称"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(5, 100)),
                "regs": [
                    # 为明确华夏稳兴增益一年持有期混合型证券投资基金（以下简称“本基金”或“基金”）的基金份额持有人
                    r"明确(?P<dst>.*?基金)[(（]以下",
                    # 为明确华夏标普500交易型开放式指数证券投资基金发起式联接基金（QDII）的基金管理人
                    r"明确(?P<dst>.*?基金([(（][a-zA-Z]+[）)])?)的?基金管理人",
                ],
            },
            {"name": "auto"},
        ],
    },
    {
        "path": ["013基金名称"],
        "models": [
            {
                "name": "auto",
                "model_alternative": True,
                "custom_regs": [
                    r"除非.*?(约定|所指).*?《(?P<dst>[^《]*?)基金合同》",
                ],
            },
        ],
    },
    {"path": ["014管理人"], "models": [{"name": "auto"}]},
    {
        "path": ["015托管人"],
        "models": [
            {
                "name": "syllabus_based",
                "include_title": False,
                "only_inject_features": True,
                "inject_syllabus_features": [r"__regex__基金托管人$"],
                "table_model": "row_match",
                "table_config": {
                    "row_pattern": ["名称"],
                    "content_pattern": [
                        r"名称[:：](?P<dst>.*)",
                    ],
                },
            },
            {"name": "auto"},
            {
                "name": "partial_text",
                "regs": [r"名称[:：](?P<dst>.*)"],
            },
        ],
    },
    {
        "path": ["016投资范围"],
        "models": [
            {
                "name": "middle_paras",
                "top_anchor_regs": [
                    r"投资范围(?!([、。对中]|为[：:]))",
                ],
                "bottom_anchor_regs": INVESTMENT_SCOPE_BOTTOM_REGS,
            },
            {
                "name": "middle_paras",
                "top_anchor_regs": [
                    r"基金.{,2}投资于",
                ],
                "bottom_anchor_regs": INVESTMENT_SCOPE_BOTTOM_REGS,
            },
        ],
    },
    {
        "path": ["017投资比例"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [
                    r"__regex__基金托管人对基金管理人的?业务(监督|核查)"
                ],  # 基金托管人对基金管理人的业务监督和核查
                "include_bottom_anchor": True,
                "top_anchor_regs": INVESTMENT_RATIO_TOP_REGS,
                "bottom_anchor_regs": [
                    r"法律法规.*?变更.*?比例限制",
                ],
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"基金托管人对基金管理人的业务监督和核查"],
                "top_anchor_regs": INVESTMENT_RATIO_TOP_REGS,
                "bottom_anchor_regs": [r"各类品种的.*?投资限制为", r"按下述比例和调整期限进行监督"],
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "inject_syllabus_features": [r"基金托管人对基金管理人的业务监督和核查"],
                "include_bottom_anchor": True,
                "top_anchor_regs": [
                    r"基金投资标.*?不低于基金资产净值",
                ],
                "bottom_anchor_regs": [
                    r"法律法规.*?变更.*?比例限制",
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": ("投资.*?比例(为|不低于)",),
            },
            {
                "name": "kmeans_classification",
                "multi": True,
                "threshold": 0.6,
            },
        ],
    },
    {
        "path": ["018投资限制"],
        "models": [
            # 容易多框选一行 精确正则优先匹配
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4643#note_523295
            # "投资组合应?遵循以下(投资)?限制" 和 "基金各类品种的投资比例、(投资)?限制为" 锚点同时出现，优先第一个锚点
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "include_top_anchor": False,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__基金托管人对基金管理人的业务监督和核查",
                ],
                "top_anchor_regs": [
                    r"投资组合应?遵循以下(投资)?限制",
                ],
                "bottom_anchor_regs": INVESTMENT_LIMIT_REGS,
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "include_top_anchor": False,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__基金托管人对基金管理人的业务监督和核查",
                ],
                "top_anchor_regs": [
                    r"基金投资组合比例应符合以下规定",
                    r"基金各类品种的投资比例、(投资)?限制为",
                ],
                "bottom_anchor_regs": INVESTMENT_LIMIT_REGS,
            },
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "include_top_anchor": False,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__基金托管人对基金管理人的业务监督和核查",
                ],
                "top_anchor_regs": [
                    r"基金托管人按下述比例和调整期限进行监督",
                    r"对?(下述)?基金(投融?资|投资、融资)比例进行监督",
                ],
                "bottom_anchor_regs": INVESTMENT_LIMIT_REGS,
            },
        ],
    },
    {
        "path": ["019估值对象"],
        "models": [
            {"name": "auto"},
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    "__regex__估值对象$",
                ],
            },
        ],
    },
    {
        "path": ["020估值方法"],
        "models": [
            {
                "name": "middle_paras",
                "use_syllabus_model": True,
                "include_top_anchor": False,
                "inject_syllabus_features": [
                    r"__regex__基金(资产)?净值计算和会计核算",
                ],
                "top_anchor_regs": [
                    r"\d.?估值方法$",
                    r"本基金按以下方法估值",
                ],
                "bottom_anchor_regs": [r"特殊情形的处理$", r"(差错|错误)的?处理$", r"实施侧袋机制期间的基金资产估值$"],
            },
            {
                "name": "syllabus_elt_v2",
                "neglect_patterns": [
                    r"基金资产净值及基金份额净值的计算与复核",
                    r"证券交易所上市的有价证券的估值",
                ],
                "inject_syllabus_features": [
                    "__regex__基金资产估值方法和特殊情形的处理",
                ],
            },
        ],
    },
    {
        "path": ["021收益分配原则"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    "__regex__收益分配.*?原则",
                ],
            },
        ],
    },
    {
        "path": ["022管理费率计提方法"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": (r"(?P<content>管理费按前一日.*?年费率计提)",),
            },
            {
                "name": "auto",
                "multi": True,
                "use_answer_pattern": True,
            },
            {
                "name": "para_match",
                "paragraph_pattern": (r"本基金(?P<content>\w\d类基金份额的管理费率为.*/年)",),
            },
        ],
    },
    {
        "path": ["023管理费率"],
        "models": [
            {
                "name": "partial_text",
                "multi": True,
                "syllabus_regs": ["管理费"],
                "model_alternative": True,  # 配置的regs未能提取时用模型提
                "regs": ["H＝E×(?P<dst>.*?[%％])[÷/∕／]", r"\w\d类基金份额的管理费率为(?P<dst>.*?[%％])/年"],
            },
        ],
    },
    {
        "path": ["024托管费率计提方法"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": (r"(?P<content>托管费按(前一|当)日.*?计提)",),
            },
            {
                "name": "auto",
                "multi": True,
                "use_answer_pattern": True,
            },
        ],
    },
    {"path": ["025托管费率"], "models": [{"name": "auto"}]},
    {
        "path": ["026销售服务费"],
        "models": [
            {
                "name": "auto",
                "model_alternative": True,
                "regs": [
                    r"其中.(?P<dst>[^。]*[ACE]类[^。]*)",
                ],
            },
        ],
    },
    {
        "path": ["027基金名称"],
        "models": [
            {"name": "auto"},
            {
                "name": "fixed_position",
                "pages": [-1],
                "regs": [
                    r"本页.*(?P<dst>华夏.*?基金([(（]?[a-zA-Z]+[）)])?)托",
                ],
            },
            {
                "name": "middle_paras",
                "page_range": [-1],
                "top_anchor_regs": [
                    r"本页",
                ],
                "bottom_anchor_regs": [r"托管协议"],
                "top_anchor_content_regs": [
                    r"本页.*(?P<content>华夏.*)",
                ],
                "bottom_anchor_content_regs": [
                    r"(?P<content>.*)托管协议",
                ],
                "include_bottom_anchor": True,
            },
        ],
    },
    {
        "path": ["028管理人"],
        "models": [
            {"name": "auto"},
            {
                "name": "fixed_position",
                "pages": [-1],
                "regs": [r"基金管理人[:：](?P<dst>.*?公司)"],
            },
        ],
    },
    {
        "path": ["029托管人"],
        "models": [
            {"name": "auto"},
            {
                "name": "fixed_position",
                "pages": [-1],
                "regs": [r"基金托管人[:：](?P<dst>.*?公司)"],
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
