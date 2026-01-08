"""申万宏源
2: 	募集说明书
"""

report_year_pattern = r"(?:1\d|20|21)\d{2}.*"
amount_pattern = r"[\s\d.,，〇一二三四五六七八九零壹贰貳叁肆伍陆柒捌玖貮两十拾百佰千仟]+"

predictor_options = [
    {
        "path": ["发行起始日"],
        "models": [
            {
                "name": "table_kv",
                "regs": {
                    "发行起始日": [r"(?P<dst>.*)[至-]"],
                },
            },
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["发行截止日"],
        "models": [
            {
                "name": "table_kv",
                "regs": {
                    "发行截止日": [r"[至-](?P<dst>.*)"],
                },
            },
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["债券全称"],
        "models": [
            {
                "name": "table_kv",
            },
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["发行主体"],
        "models": [
            {
                "name": "table_kv",
            },
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["计划发行量"],
        "models": [
            {
                "name": "table_kv",
                "regs": {
                    "币种": [rf"(?P<dst>人民币)￥?{amount_pattern}[亿万]?元"],
                    "数额": [rf"(基础发行规模)?(?P<dst>{amount_pattern})[亿万]?元"],
                    "单位": [rf"(人民币)?(基础发行规模)?{amount_pattern}(?P<dst>[亿万]?元)"],
                },
            },
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["计划发行量上限"],
        "models": [
            {
                "name": "planned_circulation_cap",
                "regs": {
                    "币种": [rf"(?P<dst>人民币)￥?{amount_pattern}[亿万]?元"],
                    "数额": [rf"(发行金额上限|不超过)为?(人民币)?(?P<dst>{amount_pattern})[亿万]?元"],
                    "单位": [rf"(人民币)?(发行金额上限)?{amount_pattern}(?P<dst>[亿万]?元)"],
                },
            },
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["债券期限"],
        "models": [
            {
                "name": "table_kv",
                "regs": {
                    "债券期限": [r"(?P<dst>[\d\+]+年)"],
                },
            },
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["主体评级"],
        "models": [
            {
                "name": "table_kv",
                "regs": {
                    "主体评级": [
                        r"信用(级别|等级)[为：:](?P<dst>A+\+?)",
                        r"(?P<dst>不进行).*?主体评级",
                        r"主体评级[:：]?(?P<dst>.*)评级",
                    ],
                },
                "主体评级": {
                    "feature_black_list": [r"信用评级机构"],
                    "feature_white_list": [r"发行人主体评级"],
                },
            },
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["评级机构"],
        "models": [
            {
                "name": "table_kv",
                "regs": {
                    "评级机构": [
                        r"(?P<dst>.*)(给予发行人的主体信用级别为|评定发行人)",
                        r"经(?P<dst>.*)综合评定",
                        r"根据(?P<dst>.*)出具的",
                        r"(?P<dst>.*评估有限公司)",
                    ],
                },
                "评级机构": {
                    "feature_black_list": [r"__regex__发行人长期主体信用等级[：:]", "__regex__发行人主体评级[：:]"],
                },
            },
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["债项评级"],
        "models": [
            {
                "name": "table_kv",
                "regs": {
                    "债项评级": [
                        r"(?P<dst>不进行).*?债项评级",
                        r"债项(?P<dst>无评级)",
                        r"(本期定向债务融资工具|本次债项)(?P<dst>[未无](信用)?评级)",
                    ],
                },
                "债项评级": {
                    "feature_black_list": [r"__regex__信用评级[：:]"],
                },
            },
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["发行方式"],
        "models": [
            {
                "name": "table_kv",
            },
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["缴款日"],
        "models": [
            {
                "name": "table_kv",
            },
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["主承销商"],
        "models": [
            {
                "name": "table_kv",
            },
            {"name": "partial_text"},
        ],
    },
    {
        "path": ["担保"],
        "models": [
            {
                "name": "table_kv",
                "regs": {
                    "担保": [r"(?P<dst>(不设|无)担保)"],
                },
            },
            {"name": "partial_text"},
        ],
    },
]


prophet_config = {"depends": {}, "predictor_options": predictor_options}
