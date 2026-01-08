"""
基金合同生效公告
"""

from remarkable.predictor.cmbchina_predictor.schemas import (
    get_predictor_options,
)

predictor_options = [
    {
        "path": ["基金名称"],
        "models": [
            {
                "name": "partial_text",
                "neglect_text_regs": [r"本基金"],
                "merge_neighbor": [
                    {
                        "amount": 2,
                        "aim_types": [
                            "PARAGRAPH",
                            "PAGE_HEADER",
                        ],
                    },
                    {
                        "amount": 2,
                        "step": -1,
                        "aim_types": [
                            "PARAGRAPH",
                            "PAGE_HEADER",
                        ],
                    },
                ],
                "regs": [
                    r"关于(?P<dst>.*)基金合同",
                    r"(?P<dst>.*(投资|联接)基金)",
                    r"(?P<dst>.*)基金合同",
                ],
                "model_alternative": True,
            },
        ],
    },
    {
        "path": ["基金代码"],
        "models": [
            {
                "name": "table_kv",
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["分级基金"],
        "divide_answers": True,
        "sub_primary_key": ["基金简称", "基金代码"],
        "models": [
            {
                "name": "table_header",
                "header_patterns": {
                    "基金简称": [
                        r"分[级类]|下属|各基金",
                        r"简称|",
                    ],
                    "基金代码": [
                        r"分[级类]|下属|各基金",
                        r"代码|",
                    ],
                },
                "value_patterns": {
                    "基金简称": [
                        r"(?P<dst>.*[A-Z].*)",
                    ],
                    "基金代码": [r"(?P<dst>\d{6})"],
                },
            },
            {
                "name": "partial_text",
                "clean_text": False,
                "text_regs": [r"分[级类]|下属|各基金"],
                "split_pattern": {
                    "基金简称": r"[ABC]",
                    "基金代码": r"[\s]",
                },
                "keep_separator": {
                    "基金简称": True,
                    "基金代码": False,
                },
                "merge_char_result": False,
                "neglect_patterns": [r"升级"],
                "multi_elements": True,
                "multi": True,
                "regs": {
                    "基金简称": [r"分[级类].*基金简称\s*(?P<dst>.+)"],
                    "基金代码": [r"交易代码\s*(?P<dst>.+)"],
                },
            },
            {
                "name": "partial_text",
                "text_regs": [r"分[级类]|下属|各基金"],
                "merge_char_result": False,
                "multi_elements": True,
                "multi": True,
                "regs": {
                    "基金简称": [
                        r"(?<!降.|调整)(?P<dst>[A-Z][类级]((基金)?份额)?)",
                    ],
                    "基金代码": [
                        r"代码[:：为]?(?P<dst>\d{6})",
                        r"新增(?P<dst>\d{6})",
                    ],
                },
            },
        ],
    },
    {
        "path": ["产品成立日"],
        "models": [
            {
                "name": "table_kv",
            },
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["产品简称"],
        "models": [
            {
                "name": "table_kv",
                "regs": [r"(?P<dst>.*)[(（](证券|基金|场内|扩位)简称"],
            },
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"基金简称(?P<dst>.*)",
                ],
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": get_predictor_options(predictor_options),
}
