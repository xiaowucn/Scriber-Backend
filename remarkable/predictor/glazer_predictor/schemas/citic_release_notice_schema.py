"""
中信-发行公告
"""

predictor_options = [
    {
        "path": ["封面", "债券简称详情"],
        "models": [
            {
                "name": "fixed_position",
                "positions": [0],
                "regs": [
                    r"[债证]券简称[:：](?P<dst>.*)",
                ],
            },
        ],
    },
    {
        "path": ["重要提示", "发行人"],
        "models": [
            {"name": "partial_text", "regs": [r"(?P<dst>[\u4e00-\u9fa5]+?公司)"]},
        ],
    },
    {
        "path": ["重要提示", "证监许可号"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"(?P<dst>(证监许可|上证函|深证函).*号)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["重要提示", "本次发行规模"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"本次债券.*?发行总?规模[为余额]*不超过(人民币|美元)?\s?(?P<dst>[\d.,]+)",
                    r"公司面向合格投资者公开发行不超过(人民币|美元)?\s?(?P<dst>[\d.,]+).*的公司债券",
                    r"非?公开发行面值不超过(?P<dst>[\d.,]+).*的公司债券",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["重要提示", "评级机构"],
        "models": [
            {
                "name": "syllabus_based",
                "paragraph_model": "partial_text",
                "use_crude_answer": True,
                "para_config": {
                    "use_answer_pattern": False,
                },
            },
        ],
    },
    {
        "path": ["重要提示", "发行人主体评级"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"发行人的主体信用(等|评级)级为?(?P<dst>[ABCD+-]+)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["重要提示", "债项评级"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["重要提示", "债券简称详情"],
        "sub_primary_key": ["债券简称", "债券品种"],
        "models": [
            {
                "name": "group_by_position",
                "neglect_patterns": [r"本期发行"],
                "group_by_position_on": "债券简称",
                "use_crude_answer": True,
                "ignore_syllabus_children": True,
                "skip_merged_para": True,
                "para_config": {
                    "债券简称": {
                        "regs": [
                            r"(债券|品种[一二三四五六七八九]|公司债券（第[一二三]期）.*?，|债券代码.{5,15}品种[二三四五六七八九])"
                            r"简称为?[:：“\"]*(?P<dst>[\u4e00-\u9fa5\w【】]{2,})",
                        ],
                        "use_answer_pattern": False,
                    },
                    "债券品种": {"regs": [r"(?P<dst>品种[一二三四五六七八九])"]},
                    "multi": True,
                    "merge_char_result": False,
                },
            }
        ],
    },
    {
        "path": ["本期发行的基本情况", "评级机构"],
        "models": [
            {
                "name": "syllabus_based",
                "ignore_syllabus_children": True,
                "paragraph_model": "partial_text",
                "max_syllabus_range": 100,
                "use_crude_answer": True,
                "para_config": {
                    "use_answer_pattern": False,
                },
            },
        ],
    },
    {
        "path": ["本期发行的基本情况", "发行人主体评级"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"发行人的主体信用(等|评级)级为?(?P<dst>[ABCD+-]+)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["本期发行的基本情况", "债项评级"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["本期发行的基本情况", "债券全称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    r"(?:^[(（]?[一二三四五六七八九0-9]*[)）]?[、.．\s]*"
                    r"(?:本期)?(?<!本次)债券(名|全)称(?:及代码)?[:：](?!本次债券)(?!本期债券分.个)"
                    r"|^[(（]?[一二三四五六七八九0-9]*[)）]?[、.．\s]*(?:本期)?(?<!本次)债券(名|全)称(?:及代码)?[:：]"
                    r'.*?债券全称为[：:"“])'
                    r"(?:品种.{,2}[:：]\s*)?"
                    r"(?P<dst>[^:，：]+?(?:[(（](?!品种)(?!简称)(?!债券代码)(?!债券简称)(?!债券品种)[^）)]+?[)）])?)"
                    r'(?:[(（](?:(?:债?券?品种|债?券?简称|债?券?代码))?|[;；。，,”"]|$)'
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["本期发行的基本情况", "债券简称详情"],
        "sub_primary_key": ["债券简称", "债券品种"],
        "models": [
            {
                "name": "group_by_position",
                "neglect_patterns": [r"重要(事项)?提示", "释义"],
                "syllabus_level": 1,
                "min_level": 1,
                "group_by_position_on": "债券简称",
                "max_syllabus_range": 100,
                "use_crude_answer": True,
                "ignore_syllabus_children": True,
                "skip_merged_para": True,
                "para_config": {
                    "债券简称": {
                        "regs": [
                            r"(债券|品种[一二三四五六七八九]|公司债券（第[一二三]期）.*?，|债券代码.{5,15}品种[二三四五六七八九])"
                            r"简称为?[:：“【]*(?P<dst>[\u4e00-\u9fa5\w]+)",
                        ],
                        "use_answer_pattern": False,
                    },
                    "债券品种": {"regs": [r"(?P<dst>品种[一二三四五六七八九])"]},
                    "multi": True,
                    "merge_char_result": False,
                },
            }
        ],
    },
    {
        "path": ["本期发行的基本情况", "债券代码详情"],
        "sub_primary_key": ["债券代码", "债券品种"],
        "models": [
            {
                "name": "group_by_position",
                "neglect_patterns": [r"重要(事项)?提示", "释义"],
                "syllabus_level": 1,
                "min_level": 1,
                "group_by_position_on": "债券代码",
                "max_syllabus_range": 100,
                # 'use_crude_answer': True,
                "ignore_syllabus_children": True,
                "skip_merged_para": True,
                "para_config": {
                    "债券代码": {
                        "regs": [r"(债券|债券全称.*?简称.*?)代码[为:：“【]*(?P<dst>\d+)"],
                        "use_answer_pattern": False,
                    },
                    "债券品种": {"regs": [r"(?P<dst>品种[一二三四五六七八九])(?![)）])"]},
                    "multi": True,
                    "merge_char_result": False,
                },
            }
        ],
    },
    {
        "path": ["本期发行的基本情况", "本期发行规模"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"本期债券.*?(?:发行(?:总?规模|总额))为*(?:不超过)?(人民币|美元)?\s?(?P<dst>[\d.,]+)"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["本期发行的基本情况", "债券期限详情"],
        "sub_primary_key": ["债券期限", "债券品种"],
        "models": [
            {
                "name": "group_by_position",
                "neglect_patterns": [r"重要(事项)?提示", "释义"],
                "syllabus_level": 1,
                "min_level": 1,
                "group_by_position_on": "债券期限",
                "max_syllabus_range": 100,
                "use_crude_answer": True,
                "ignore_syllabus_children": True,
                "skip_merged_para": True,
                "para_config": {
                    "债券期限": {
                        "neglect_patterns": [r"选择权"],
                        "regs": [r"债券(?:发行)?期限为(?P<dst>\d年期)", r"债券(?:发行)?期限为?(?P<dst>不超过\d+年?)"],
                        "model_alternative": True,
                        "use_answer_pattern": False,
                    },
                    "债券品种": {"regs": [r"(?P<dst>品种[一二三四五六七八九])"]},
                    "multi": True,
                    "merge_char_result": False,
                },
            }
        ],
    },
    {
        "path": ["本期发行的基本情况", "交易场所"],
        "models": [
            {
                "name": "partial_text",
                "regs": [r"(交易|上市)(场所|地)[:：](?P<dst>.*?)[;；。，,”]", r"[深上][圳海]?(证券交易|交)所"],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["本期发行的基本情况", "付息频率详情"],
        "sub_primary_key": ["付息频率", "债券品种"],
        "models": [
            {
                "name": "group_by_position",
                "neglect_patterns": [r"重要(事项)?提示", "释义"],
                "syllabus_level": 1,
                "min_level": 1,
                "group_by_position_on": "付息频率",
                "max_syllabus_range": 100,
                "use_crude_answer": True,
                "ignore_syllabus_children": True,
                "skip_merged_para": True,
                "para_config": {
                    "付息频率": {
                        "use_answer_pattern": False,
                    },
                    "债券品种": {"regs": [r"(?P<dst>品种[一二三四五六七八九])"]},
                    "multi": True,
                    "merge_char_result": False,
                },
            }
        ],
    },
    {
        "path": ["本期发行的基本情况", "起息日详情"],
        "sub_primary_key": ["起息日", "债券品种"],
        "models": [
            {
                "name": "group_by_position",
                "neglect_patterns": [r"重要(事项)?提示", "释义"],
                "syllabus_level": 1,
                "min_level": 1,
                "group_by_position_on": "起息日",
                "max_syllabus_range": 100,
                "use_crude_answer": True,
                "ignore_syllabus_children": True,
                "skip_merged_para": True,
                "para_config": {
                    "起息日": {
                        "regs": [r"起息日[为:：]?自?(?P<dst>[0-9一二三四五六七八九十年月日]*)"],
                        "model_alternative": True,
                        "use_answer_pattern": False,
                    },
                    "债券品种": {"regs": [r"(?P<dst>品种[一二三四五六七八九])"]},
                    "multi": True,
                    "merge_char_result": False,
                },
            }
        ],
    },
    {
        "path": ["本期发行的基本情况", "到期日详情"],
        "sub_primary_key": ["到期日", "债券品种"],
        "models": [
            {
                "name": "group_by_position",
                "neglect_patterns": [r"重要(事项)?提示", "释义"],
                "syllabus_level": 1,
                "min_level": 1,
                "group_by_position_on": "到期日",
                "max_syllabus_range": 100,
                "use_crude_answer": True,
                "ignore_syllabus_children": True,
                "skip_merged_para": True,
                "para_config": {
                    "到期日": {
                        "neglect_patterns": [r"选择权"],
                        "use_answer_pattern": False,
                    },
                    "债券品种": {"regs": [r"(?P<dst>品种[一二三四五六七八九])"]},
                    "multi": True,
                    "merge_char_result": False,
                },
            }
        ],
    },
    {
        "path": ["本期发行的基本情况", "债券品种"],
        "models": [{"name": "partial_text", "multi": True, "regs": [r'(?<![”"“])品种[一二三四五六七八九]']}],
    },
    {
        "path": ["网下利率询价", "利率询价区间详情"],
        "sub_primary_key": ["利率询价区间", "债券品种"],
        "models": [
            {
                "name": "group_by_position",
                "syllabus_level": 2,
                "min_level": 1,
                "group_by_position_on": "利率询价区间",
                "use_crude_answer": True,
                "ignore_syllabus_children": True,
                "skip_merged_para": True,
                "para_config": {
                    "利率询价区间": {
                        "regs": [
                            r"利率(询价|预设|簿记建档)?区间[为:：]*(?P<dst>[0-9.%-]+)",
                        ],
                        "model_alternative": True,
                        "use_answer_pattern": False,
                    },
                    "债券品种": {"regs": [r"(?P<dst>品种[一二三四五六七八九])"]},
                    "multi": True,
                    "merge_char_result": False,
                },
            }
        ],
    },
    {
        "path": ["网下发行-发行时间", "发行起始日"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["网下发行-发行时间", "发行截止日"],
        "models": [
            {"name": "partial_text", "regs": [r".*年.*月.*日.*?(?P<dst>\d+年\d+月\d+日)"]},
        ],
    },
    {
        "path": ["发行人和主承销商", "主承销商"],
        "models": [
            {
                "name": "notice_consignee_info",
                "ignore_syllabus_children": True,
                "max_syllabus_range": 100,
                "min_level": 1,
                "syllabus_level": 1,
                "multi": True,
                "neglect_patterns": [
                    r"副主承销商",
                    r"风险提示|厉害关系|备查文件|释义|重要(事项)?提示",
                    r"以?及其他承销机构",
                ],
                "para_config": {"regs": [r"(?P<dst>(牵头|联席)?主承销商(?:(?!以?及其他承销机构).)*)$"]},
            },
        ],
        "sub_primary_key": ["主承销商"],
    },
]


prophet_config = {"depends": {}, "predictor_options": predictor_options}
