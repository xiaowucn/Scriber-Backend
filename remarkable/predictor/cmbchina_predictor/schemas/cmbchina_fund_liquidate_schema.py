"""
基金清算报告
"""

from remarkable.predictor.cmbchina_predictor.schemas import get_predictor_options

graded_fund_regs = {
    "基金简称": [
        r"(基金简称及基金代码[:：]|\d{6}[)）][;；])(?P<dst>.*?[A-Z])[(（]",
        r"基金(代码|份额)[:：](?P<dst>[^；]+[A-Z])",
        r"(?P<dst>^[^:：,，,]+[A-Z])[:：,，,]",
        r"(?P<dst>^[^:：,，,]+[A-Z]类)基金份额代码[:：,，,]",
        r"(?P<dst>^[A-Z]类)份额基金代码[:：,，,]",
        r"(基金交易代码[:：]|\d{6}[;；])(?P<dst>[A-Z]类)",
        r"类基金份额简称[:：](?P<dst>.+[A-Z])",
        r"(?P<dst>[A-Z]类)(基金份额)?(代码)?[:：]\d{6}",
        r"基金简称及基金代码[:：](?P<dst>^[A-Z])[(（]",
    ],
    "基金代码": [
        r"[A-Z][(（](?P<dst>\d{6})",
        r"[A-Z]类?(基金份额(代码)?)?[:：，,](?P<dst>\d{6})",
        r"基金代码[:：，,](?P<dst>\d{6})",
    ],
}


predictor_options = [
    {
        "path": ["基金名称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
                "regs": [
                    r"关于(?P<dst>.*?投资基金)",
                    r"关于(?P<dst>.*?)(发生|终止)?基金合同",
                    r"(?P<dst>.*?)(发生|终止)?基金合同",
                    r"(?P<dst>.*?投资基金)",
                ],
                "model_alternative": True,
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
            },
        ],
    },
    {
        "path": ["基金代码"],
        "models": [
            {
                "name": "table_kv",
                "neglect_row": [
                    r"\d{12}",
                ],
            },
            {
                "name": "partial_text",
                "regs": [r"基金代码[:：，,](?P<dst>\d{6}$)"],
            },
        ],
    },
    {
        "path": ["分级基金"],
        "divide_answers": True,
        "sub_primary_key": ["基金简称"],
        "models": [
            {
                "name": "table_header",
                "header_patterns": {
                    "基金简称": [
                        r"分级|下属|各基金|各份额类别",
                        r"简称|",
                    ],
                    "基金代码": [
                        r"分级|下属|各基金|各份额类别",
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
                "name": "table_header",
                "cells_count": 3,
                "header_patterns": {
                    "基金简称": [
                        r"基金简称",
                    ],
                    "基金代码": [
                        r"基金代码",
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
                "name": "elements_collector_based",
                "elements_collect_model": "middle_paras",
                "elements_collect_config": {
                    "table_regarded_as_paras": True,
                    "include_top_anchor": False,
                    "top_anchor_regs": [r"基金简称", r"基金名称"],
                    "bottom_anchor_regs": [
                        r"基金运作方式",
                    ],
                },
                "paragraph_model": "classified_fund_partial_text",
                "para_config": {
                    "merge_char_result": False,
                    "multi_elements": True,
                    "multi": True,
                    "neglect_patterns": [
                        r"升级",
                        r"^基金代码[:：，,]\d{6}$",
                    ],
                    "neglect_syllabus_regs": [r"份额的?类别"],
                    "regs": graded_fund_regs,
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
                "name": "classified_fund_partial_text",
                "multi": True,
                "merge_char_result": False,
                "neglect_patterns": [
                    r"升级",
                    r"^基金代码[:：，,]\d{6}$",
                ],
                "regs": graded_fund_regs,
            },
        ],
    },
    {
        "path": ["单笔申购上限"],  # 无明确规则
        "models": [],
    },
    {
        "path": ["产品到期日"],
        "models": [
            {
                "name": "partial_text",
                "regs": [
                    r"最后(一个)?运作日定?为(?P<dst>[\d年月日]+)",
                    r"(?P<dst>[\d年月日]+)为本基金最后运作日",
                ],
                "model_alternative": True,
            },
            {
                "name": "maturity_date",
                "regs": [
                    r"[自从](?P<dst>[\d年月日]+)([(（].*?[)）])?起?.?(本基金)?进入清算",
                ],
                "model_alternative": True,
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": get_predictor_options(predictor_options),
}
