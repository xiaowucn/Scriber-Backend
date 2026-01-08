"""银河证券 17 公募-基金合同-二"""

HUGE_REDEMPTION = (
    r"__regex__部分基金份额的(运作方式、)?申购[与、]赎回__regex__巨额赎回的情形及处理方式__regex__巨额赎回的处理方式"
)
FUND_MANAGER = [r"基金管理人"]
FUND_CUSTODIAN = [r"基金托管人"]


predictor_options = [
    {
        "path": ["前言"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["订立本基金合同的目的、依据和原则"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__前言$"],
                "only_inject_features": True,
                "paragraph_model": "middle_paras",
                "extract_from": "same_type_elements",
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": False,
                    "top_anchor_regs": [r"订立本基金合同的目的、依据和原则"],
                    "bottom_anchor_regs": [
                        r"二.基金合同",
                    ],
                },
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__前言$"],
                "only_inject_features": True,
                "paragraph_model": "middle_paras",
                "extract_from": "same_type_elements",
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": False,
                    "top_anchor_regs": [r"订立.*?本基金合同.*?的目的、依据和原则"],
                    "bottom_default": True,
                    "include_bottom_anchor": True,
                },
            },
        ],
    },
    {
        "path": ["释义"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["摆动定价机制-释义"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [r"摆动定价机制"],
            },
        ],
    },
    {
        "path": ["标的指数"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__释义$"],
                "only_inject_features": True,
                "ignore_syllabus_range": True,
                "paragraph_model": "partial_text",
                "extract_from": "same_type_elements",
                "para_config": {
                    "regs": [
                        r"标的指数[:：].*编制并发布的(?P<dst>.*?指数)",
                        r"标的指数[:：]指(?P<dst>.*?指数A?)",
                        r"标的指数[:：]本基金的?标的指数为(?P<dst>.*?指数)",
                        r"^创业板指数$",
                        r"本基金的?标的指数为(?P<dst>.*?指数)",
                    ],
                },
            },
        ],
    },
    {
        "path": ["最低募集金额"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金份额面值和认购费用"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": ["__regex__基金份额初始面值"],
            },
        ],
    },
    {
        "path": ["发行联接基金或增设新的基金份额类别"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"发行联接基金",
                    r"增.新的(基金)?份额类别",
                    r"增加本基金新的基金份额类别",
                    r"若未来基金管理人在本基金基金合同生效后管理本基金的联接基金，该联接基金将投资于本基金，与本基金跟踪同一标的指数",
                ],
            },
        ],
    },
    {
        "path": ["发售时间"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["发售方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["发售对象"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["认购费用"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["认购份额余额的处理方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["募集期利息的处理方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金认购份额的计算"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金认购申请的确认"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "neglect_patterns": [r"发售方式"],
            },
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"对认购申请的受理.*仅代表销售机构确实接收到认购申请.*对于认购申请及认购份额的确认情况"
                ],
            },
        ],
    },
    {
        "path": ["募集期认购资金的处理方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金份额认购的其他具体规定"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金份额认购金额的限制"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金备案的条件"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金合同不能生效时募集资金的处理方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["申购和赎回场所"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["开放日及开放时间"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["申购、赎回开始日及业务办理时间"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["申购与赎回的原则"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["申购与赎回的程序"],
        "models": [
            {"name": "syllabus_elt_v2", "inject_syllabus_features": [r"申购与赎回的程序"]},
        ],
    },
    {
        "path": ["申购和赎回的申请方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["申购和赎回申请的确认"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["申购和赎回申请的清算交收与登记"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "neglect_patterns": [r"申购和赎回申请的确认"],
            },
        ],
    },
    {
        "path": ["申购和赎回的数量限制"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["申购和赎回的价格、费用及其用途"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["拒绝或暂停申购的情形"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["暂停赎回或延缓支付赎回款项的情形"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["暂停申购或赎回的公告和重新开放申购或赎回的公告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金清算交收与登记模式的切换"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金的质押"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["集合申购和其他服务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["联接基金的投资"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["实物申购与赎回"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["其他申购赎回方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["巨额赎回的认定"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["巨额赎回的比例"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__巨额赎回的认定"],
                "paragraph_model": "partial_text",
                "para_config": {
                    "regs": [r"超过.*?基金总?份额的(?P<dst>[\d.]+[%％])"],
                },
            },
        ],
    },
    {
        "path": ["巨额赎回的情形及处理方式"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__基金份额的(运作方式、)?申购[与、]赎回__regex__巨额赎回的情形及处理方式",
                ],
                "only_inject_features": True,
            },
        ],
    },
    {
        "path": ["巨额赎回的处理方式", "全额赎回"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [HUGE_REDEMPTION],
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [r"(?P<dst>全额赎回[:：].*)"],
                },
            },
        ],
    },
    {
        "path": ["巨额赎回的处理方式", "部分延期赎回"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [HUGE_REDEMPTION],
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [r"(?P<dst>部分延期赎回[:：].*)"],
                },
            },
        ],
    },
    {
        "path": ["巨额赎回的处理方式", "赎回申请延期办理"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [HUGE_REDEMPTION],
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [
                        r"巨额赎回.*延期(赎回|办理).{2,}",
                        r"超过.*?比例的赎回申请实施延期办理",
                    ]
                },
            },
        ],
    },
    {
        "path": ["巨额赎回的处理方式", "暂停赎回"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [HUGE_REDEMPTION],
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [r"(?P<dst>巨额赎回.*暂停.*)"],
                },
            },
        ],
    },
    {
        "path": ["巨额赎回的公告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金转换"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金的非交易过户"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金的转托管"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金份额的转让"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["定期定额投资计划"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金的冻结、解冻与其他基金业务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金清算交收与登记模式的调整或新增"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__基金份额的申购与赎回"],
                "ignore_syllabus_children": True,
                "ignore_syllabus_range": True,
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [
                        r"修改现有的清算交收与登记模式或推出新的清算交收与登记模式",
                    ],
                },
            },
        ],
    },
    {
        "path": ["基金推出新业务或服务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金管理人"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": FUND_MANAGER,
                "table_regarded_as_paras": True,
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "model_alternative": True,
                    "名称": {
                        "regs": [r"名称[:：](?P<dst>.*)"],
                    },
                    "住所": {
                        "regs": [r"(住所|注册地址)[:：](?P<dst>.*)"],
                    },
                    "联系电话": {
                        "regs": [r"联系电话[:：](?P<dst>.*)"],
                    },
                },
            },
        ],
    },
    {
        "path": ["基金托管人"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": FUND_CUSTODIAN,
                "table_regarded_as_paras": True,
                "paragraph_model": "partial_text",
                "para_config": {
                    "use_answer_pattern": False,
                    "model_alternative": True,
                    "名称": {
                        "regs": [r"名称[:：](?P<dst>.*)"],
                    },
                    "住所": {
                        "regs": [r"(住所|注册地址)[:：](?P<dst>.*)"],
                    },
                    "通讯地址": {
                        "regs": [r"通讯地址[:：](?P<dst>.*)"],
                        "feature_black_list": [r"住所"],
                    },
                    "联系电话": {
                        "regs": [r"电话[:：](?P<dst>.*)"],
                    },
                },
            },
        ],
    },
    {
        "path": ["份额持有人的权利"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["份额持有人的义务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金份额持有人大会关于联接基金的安排"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__基金份额持有人大会$"],
                "only_inject_features": True,
                "paragraph_model": "middle_paras",
                "extract_from": "same_type_elements",
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": True,
                    "top_anchor_regs": [
                        r"联接基金的基金合同",
                        r"基金管理人管理本基金的联接基金",
                        r"鉴于本基金是目标ETF的联接基金",
                        r"鉴于本基金和本基金的联接基金",
                    ],
                    "bottom_anchor_regs": [
                        r"日常机构",
                        r"召开事由",
                    ],
                },
            },
        ],
    },
    {
        "path": ["基金份额持有人日常机构"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"本?(基金)?基金份额持有人大会[暂不未设立]+日常机构",
                    r"本基金未设立基金份额持有人大会的日常机构",
                ],
            },
        ],
    },
    {
        "path": ["无需召开基金份额持有人大会的情形"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"召开事由"],
                "ignore_syllabus_children": True,
                "ignore_syllabus_range": True,
                "paragraph_model": "middle_paras",
                "extract_from": "same_type_elements",
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": True,
                    "include_bottom_anchor": True,
                    "top_anchor_regs": [r"不需召开基金份额持有人大会"],
                    "bottom_default": True,
                },
            }
        ],
    },
    {
        "path": ["基金份额持有人大会一般规定"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__基金份额持有人大会$"],
                "only_inject_features": True,
                "paragraph_model": "middle_paras",
                "extract_from": "same_type_elements",
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": False,
                    "top_default": True,
                    "bottom_anchor_regs": [
                        r"召开事由$",
                    ],
                },
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__基金份额持有人大会$"],
                "only_inject_features": True,
                "paragraph_model": "middle_paras",
                "extract_from": "same_type_elements",
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": False,
                    "top_default": True,
                    "bottom_anchor_regs": [
                        r"本基金份额持有人大会不设日常机构。",
                    ],
                    "include_bottem_anchor": True,
                },
            },
        ],
    },
    {
        "path": ["基金份额持有人大会", "现场开会"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__基金份额持有人出席会议的方式$"],
                "only_inject_features": True,
                "paragraph_model": "middle_paras",
                "extract_from": "same_type_elements",
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": True,
                    "top_anchor_regs": [
                        r"现场开会。",
                    ],
                    "bottom_anchor_regs": [
                        r"通讯开会",
                    ],
                },
            },
        ],
    },
    {
        "path": ["基金份额持有人大会", "通讯开会"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金份额持有人大会", "其他方式"],
        "models": [
            {
                "name": "score_filter",
                "threshold": 0.2,
                "aim_types": ["PARAGRAPH"],
                "multi_elements": False,
            }
        ],
    },
    {
        "path": ["基金份额持有人大会", "议事内容及提案权"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金份额持有人大会", "议事程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"议事程序"],
            },
        ],
    },
    {
        "path": ["基金份额持有人大会", "一般决议"],
        "models": [
            {
                "name": "syllabus_based",
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [r"一般决议.*"],
                    "neglect_regs": [
                        r"分为一般决议和特别决议.?$",
                    ],
                },
            },
        ],
    },
    {
        "path": ["基金份额持有人大会", "特别决议"],
        "models": [
            {
                "name": "syllabus_based",
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [r"特别决议.*"],
                    "neglect_regs": [
                        r"分为一般决议和特别决议.?$",
                        r"须以特别决议通过",
                    ],
                },
            },
        ],
    },
    {
        "path": ["基金份额持有人大会", "现场开会计票"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__基金份额持有人大会__regex__计票__regex__现场开会",
                ],
                "keep_parent": True,
            },
        ],
    },
    {
        "path": ["基金份额持有人大会", "通讯开会计票"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__部分基金份额持有人大会__regex__计票__regex__通讯(方式)?开会",
                    r"__regex__基金份额持有人大会__regex__计票__regex__通讯开会",
                ],
                "only_inject_features": True,
                "include_title": True,
            },
        ],
    },
    {
        "path": ["基金份额持有人大会", "生效与公告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金份额持有人大会", "其他约定"],
        "models": [
            {
                "name": "syllabus_based",
                "only_inject_features": True,
                "inject_syllabus_features": [r"__regex__基金份额持有人大会$"],
                "syllabus_level": 1,
                "ignore_children": True,
                "paragraph_model": "para_match",
                "para_config": {
                    "multi_elements": True,
                    "paragraph_pattern": [
                        r"本部分关于基金份额持有人大会.*凡是直接引用法律法规.*的部分",
                    ],
                },
            },
        ],
    },
    {
        "path": ["更换管理人与托管人的其他约定"],
        "models": [
            {
                "name": "syllabus_based",
                "only_inject_features": True,
                "inject_syllabus_features": [r"__regex__基金(管理|托管)人的更换条件和程序"],
                "paragraph_model": "para_match",
                "para_config": {
                    "multi_elements": True,
                    "paragraph_pattern": [
                        r"本部分关于基金管理人、基金托管人更换条件和程序的约定，凡是直接引用法律法规(或监管规则)?的部分",
                        r"新任基金管理人或临时基金管理人接收基金管理业务",
                    ],
                },
            },
        ],
    },
    {
        "path": ["基金的托管"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金的份额登记业务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金登记业务办理机构"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金登记机构的权利"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金登记机构的义务"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["投资目标"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["投资策略"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["禁止行为"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["业绩比较基准"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["风险收益特征"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金管理人代表基金行使股东或债权人权利的处理原则及方法"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金资产总值"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金资产净值"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金财产的账户"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金财产的保管和处分"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["估值对象"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["估值程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["估值错误的处理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["估值错误类型"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["估值错误处理原则"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["估值错误处理程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金份额净值估值错误处理的方法"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": ["__regex__估值错误处理的方法如下"],
            },
        ],
    },
    {
        "path": ["特殊情况的处理"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金净值的确认"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金费用的种类"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["不列入基金费用的项目"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金税收"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金利润的构成"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": ["__regex__基金收益的构成"],
            },
        ],
    },
    {
        "path": ["基金可供分配利润"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["收益分配方案的确定、公告与实施"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金收益分配中发生的费用"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["实施侧袋机制期间的收益分配"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金会计政策"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金的年度审计"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__基金的审计",
                ],
            },
        ],
    },
    {
        "path": ["信息披露", "基金招募说明书、基金合同、基金托管协议、基金产品资料概要"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__基金招募说明书.基金合同.基金托管协议",
                ],
            },
        ],
    },
    {
        "path": ["信息披露", "基金份额发售公告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["信息披露", "基金合同生效公告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["信息披露", "基金净值信息"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["信息披露", "基金份额申购、赎回价格"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["信息披露", "基金份额折算日和折算结果公告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["信息披露", "基金份额上市交易公告书"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["信息披露", "基金份额开始申购赎回公告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["信息披露", "申购赎回清单公告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["信息披露", "基金定期报告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["信息披露", "澄清公告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["信息披露", "清算报告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["信息披露", "基金份额持有人大会决议"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"(?P<content>.*基金份额持有人大会决定的事项，应当依法报中国证监会备案，并予以公告.)"
                ],
                "content_pattern": [
                    r"(?P<content>.*基金份额持有人大会决定的事项，应当依法报中国证监会备案，并予以公告.)"
                ],
            },
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["信息披露", "投资品种相关公告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "multi": True,
                # "only_inject_features": True,
                "inject_syllabus_features": [  # 要提多条,下面的特征不能合并
                    r"__regex__投资股指期货的?(相关公告|信息披露)",
                    r"__regex__投资国债期货的?(相关公告|信息披露)",
                    r"__regex__投资股票期权的?(相关公告|信息披露)",
                    r"__regex__投资资产支持[债证]券的?(相关公告|信息披露)",
                    r"__regex__投资港股通标的股票的?(相关公告|信息披露)",
                    r"__regex__投资非公开发行股票的?(相关公告|信息披露)",
                    r"__regex__投资流通受限证券的?(相关公告|信息披露)",
                    r"__regex__参与融资和转融通证券出借业务的?(相关公告|信息披露)",
                    r"__regex__基金投资基金的?(相关公告|信息披露)",
                ],
            },
        ],
    },
    {
        "path": ["暂停或延迟信息披露的情形"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金财产清算小组"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__基金合同的变更、终止与基金财产的清算__regex__基金财产的清算",
                ],
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [r"基金财产清算小组[:：].*"],
                },
            },
        ],
    },
    {
        "path": ["基金财产清算小组组成"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__基金合同的变更、终止与基金财产的清算__regex__基金财产的清算",
                ],
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [r"基金财产清算小组组成[:：].*"],
                },
            },
        ],
    },
    {
        "path": ["基金财产清算小组职责"],
        "models": [
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [
                    r"__regex__基金合同的变更、终止与基金财产的清算__regex__基金财产的清算",
                ],
                "paragraph_model": "para_match",
                "para_config": {
                    "paragraph_pattern": [r"(?P<dst>基金财产清算小组职责[:：]?.*)"],
                },
            },
        ],
    },
    {
        "path": ["基金财产清算程序"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": ["__regex__基金财产清算程序"],
                "only_inject_features": True,
            },
            {
                "name": "syllabus_based",
                "inject_syllabus_features": [r"__regex__基金财产的清算"],
                "only_inject_features": True,
                "paragraph_model": "middle_paras",
                "extract_from": "same_type_elements",
                "para_config": {
                    "use_direct_elements": True,
                    "include_top_anchor": False,
                    "top_anchor_regs": [
                        r"基金财产清算程序",
                    ],
                    "bottom_anchor_regs": [
                        r"\d+.基金财产清算的?期限",
                        r"召开事由",
                    ],
                },
            },
        ],
    },
    {
        "path": ["基金财产清算期限"],
        "models": [
            {
                "name": "para_match",
                "paragraph_pattern": [r"基金财产清算的?期限"],
            },
        ],
    },
    {
        "path": ["违约责任"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["争议的处理和适用的法律"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金份额折算的时间"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金份额折算的原则"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金份额折算的方法"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [
                    r"__regex__基金份额折算方式",
                ],
            },
        ],
    },
    {
        "path": ["基金份额的上市"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金份额的上市交易"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "keep_parent": True,
                "neglect_patterns": [r"基金的基本情况"],
            },
        ],
    },
    {
        "path": ["停牌、复牌、暂停上市、恢复上市及终止上市交易"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "multi": True,
            },
        ],
    },
    {
        "path": ["终止上市交易的情形"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["基金份额参考净值的计算与公告"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
            {
                "name": "para_match",
                "paragraph_pattern": [
                    r"基金份额参考净值的计算与公告",
                    r"基金份额参考净值（IOPV）的计算与公告",
                    r"基金份额参考净值(IOPV)的计算与公告",
                ],
            },
        ],
    },
    {
        "path": ["基金份额上市交易的其他约定"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "inject_syllabus_features": [r"__regex__基金份额的上市交易$__regex__.*"],
                "one_result_per_feature": False,
                "only_inject_features": True,
                "syllabus_black_list": [
                    r"基金(份额的)?(上市|交易|上市交易)$",
                    r"终止上市交易$",
                    r"(停复牌|暂停上市|恢复上市|终止上市)$",
                    r"计算与公告$",
                ],
                "include_title": True,
            },
        ],
    },
    {
        "path": ["其他事项"],
        "models": [
            {
                "name": "syllabus_elt_v2",
            },
        ],
    },
    {
        "path": ["上市交易所"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"本基金上市交易的地点为(?P<dst>(上海?|深圳?)(证券)?交易?所)"],
                "model_alternative": True,
            },
        ],
    },
]


def get_predictor_options():
    for option in predictor_options:
        models = option["models"]
        if [x for x in models if x["name"] in ["partial_text", "para_match"]]:
            models.append(
                {
                    "name": "score_filter",
                    "threshold": 0.2,
                    "aim_types": ["PARAGRAPH"],
                    "multi_elements": False,
                }
            )
        for model in models:
            if model["name"] in ["syllabus_elt_v2", "middle_paras"]:
                model["page_header_patterns"] = [r"^\d+[/]\d+$"]
            if model.get("paragraph_model") in ["middle_paras"]:
                model["para_config"]["page_header_patterns"] = [r"^\d+[/]\d+$"]

        option["models"] = models
    return predictor_options


prophet_config = {
    "depends": {},
    "predictor_options": get_predictor_options(),
}
