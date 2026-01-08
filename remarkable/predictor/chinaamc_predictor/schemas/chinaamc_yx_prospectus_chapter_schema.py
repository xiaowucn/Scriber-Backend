"""华夏营销部-标注章节比对 招募说明书V1"""

from remarkable.plugins.cgs.common.patterns_util import R_CONJUNCTION

R_ANNEX_1 = {
    "top_chapter_anchor_regs": [
        r"基金合同摘要$",
    ],
    "bottom_chapter_anchor_regs": [
        r"基金托管协议摘要$",
    ],
}

R_ANNEX_2 = {
    "top_chapter_anchor_regs": [
        r"基金托管协议摘要$",
    ],
    "bottom_chapter_anchor_regs": [
        r"标的指数编制方案$",
    ],
}

predictor_options = [
    {
        "path": ["001基金份额持有人、基金管理人和基金托管人的权利、义务"],
        "models": [
            {
                "name": "middle_syllabus",
                **R_ANNEX_1,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    rf"__regex__((基金份额持有人|基金管理人|基金托管人)[{R_CONJUNCTION}]?){{3}}.?(权利|义务)",
                    rf"__regex__基金合同当事人.?((权利|义务)[{R_CONJUNCTION}]?){{2}}",
                ],
            },
        ],
    },
    {
        "path": ["002基金份额持有人大会召集、议事及表决的程序和规则"],
        "models": [
            {
                "name": "middle_syllabus",
                **R_ANNEX_1,
                # "only_inject_features": True,
                # "inject_syllabus_features": [
                #     rf"__regex__基金份额持有人大会(((召集|议事|表决)[{R_CONJUNCTION}]?){{3}}.?((程序和规则)[{R_CONJUNCTION}]?){{2}})?",
                # ],
            },
        ],
    },
    {
        "path": ["003基金收益分配原则、执行方式"],
        "models": [
            {
                "name": "middle_syllabus",
                **R_ANNEX_1,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    rf"__regex__基金收益((分配原则|执行方式)[{R_CONJUNCTION}]?){{2}}",
                ],
            },
        ],
    },
    {
        "path": ["004与基金财产管理、运用有关费用的提取、支付方式与比例"],
        "models": [
            {
                "name": "middle_syllabus",
                **R_ANNEX_1,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    rf"__regex__与基金财产((管理|运用)[{R_CONJUNCTION}]?){{2}}有关费用.?((提取|支付方式|比例)[{R_CONJUNCTION}]?){{3}}",
                ],
            },
        ],
    },
    {
        "path": ["005基金财产的投资方向和投资限制"],
        "models": [
            {
                "name": "middle_syllabus",
                **R_ANNEX_1,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    rf"__regex__基金财产.?((投资方向|投资限制)[{R_CONJUNCTION}]?){{2}}",
                ],
            },
        ],
    },
    {
        "path": ["006基金资产净值的计算方法和公告方式"],
        "models": [
            {
                "name": "middle_syllabus",
                **R_ANNEX_1,
                # "only_inject_features": True,
                # "inject_syllabus_features": [
                #     rf"__regex__基金资产净值.?((计算方法|公告方式)[{R_CONJUNCTION}]?){{2}}",
                # ],
            },
        ],
    },
    {
        "path": ["007基金合同解除和终止的事由、程序以及基金财产清算方式"],
        "models": [
            {
                "name": "middle_syllabus",
                **R_ANNEX_1,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    rf"__regex__基金合同((解除|终止)[{R_CONJUNCTION}]?){{2}}.?((事由|程序)[{R_CONJUNCTION}]?){{2}}以及基金财产清算方式",
                ],
            },
        ],
    },
    {
        "path": ["008争议解决方式"],
        "models": [
            {
                "name": "middle_syllabus",
                **R_ANNEX_1,
            },
        ],
    },
    {
        "path": ["009基金合同存放地和投资者取得基金合同的方式"],
        "models": [
            {
                "name": "middle_syllabus",
                **R_ANNEX_1,
                # "only_inject_features": True,
                # "inject_syllabus_features": [
                #     r"__regex__基金合同存放地.?投资者取.?基金合同.?方式$",
                #     r"__regex__基金合同.?效力$",
                # ],
            },
        ],
    },
    {
        "path": ["010托管协议当事人"],
        "models": [
            {
                "name": "middle_syllabus",
                **R_ANNEX_2,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__托管协议当事人$",
                ],
            },
        ],
    },
    {
        "path": ["011基金托管人对基金管理人的业务监督和核查"],
        "models": [
            {
                "name": "middle_syllabus",
                **R_ANNEX_2,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    rf"__regex__托管人对(基金)?管理人的业务((监督|核查)[{R_CONJUNCTION}]?){{2}}$",
                ],
            },
        ],
    },
    {
        "path": ["012基金管理人对基金托管人的业务核查"],
        "models": [
            {
                "name": "middle_syllabus",
                **R_ANNEX_2,
                # "only_inject_features": True,
                # "inject_syllabus_features": [
                #     r"__regex__管理人对(基金)?托管人的?业务核查$",
                # ],
            },
        ],
    },
    {
        "path": ["013基金财产的保管"],
        "models": [
            {
                "name": "middle_syllabus",
                **R_ANNEX_2,
                "include_title": True,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__基金财产.?保管的?原则",
                ],
            },
        ],
    },
    {
        "path": ["014基金资产净值计算与复核"],
        "models": [
            {
                "name": "middle_syllabus",
                **R_ANNEX_2,
                "only_inject_features": True,
                "inject_syllabus_features": [
                    rf"__regex__净值.?((计算|复核|(会计)?核算)[{R_CONJUNCTION}]?){{2}}",
                ],
            },
        ],
    },
    {
        "path": ["015基金份额持有人名册的登记与保管"],
        "models": [
            {
                "name": "middle_syllabus",
                **R_ANNEX_2,
                "inject_syllabus_features": [
                    r"__regex__份额持有人名册.?((登记|保管)[与和及、]?){2}",
                ],
            },
        ],
    },
    {
        "path": ["016争议解决方式"],
        "models": [
            {
                "name": "middle_syllabus",
                **R_ANNEX_2,
                # "only_inject_features": True,
                "inject_syllabus_features": [
                    r"__regex__争议解决方式",
                ],
            },
        ],
    },
    {
        "path": ["017托管协议的变更、终止"],
        "models": [
            {
                "name": "middle_syllabus",
                **R_ANNEX_2,
                "only_inject_features": True,
                "include_title": True,
                "multi": True,
                "inject_syllabus_features": [
                    # rf"__regex__协议.?((变更|终止|修改)[{R_CONJUNCTION}]?){{2}}",
                    r"__regex__托管协议的?(变更|修改)(程序|$)",
                    r"__regex__托管协议的?终止((出现)?的?情形|$)",
                ],
                "break_para_pattern": [r"基金产品资料概要|^附件"],
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
