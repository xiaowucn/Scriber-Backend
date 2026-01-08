# -*- coding: utf-8 -*-
SPECIAL_ATTR_PATTERNS = {
    "date": [
        r"(?P<dst>[\d一二三四五六七八九〇○OＯ零]{4}(?:年[度初中末]?|\.|-|/)([\d一元二三四五六七八九十零〇○Ｏ]{1,2}(?:月份?|\.|-|/)?(?:[\d一二三四五六七八九十零〇○Ｏ]{"
        r"1,3}[日号]?)?)?)"
    ],
    "number": [r"[\d一二三四五六七八九〇零○Ｏ]+"],
    "<金额单位>": [r"(?P<dst>\w?元)"],
    "<数量单位>": [r"单位[:：](.*?)(?P<dst>[百千万亿]?股)", r"数.*?\w?(?P<dst>股)", r"(?P<dst>人)数"],
    "<百分比单位>": [r"(?P<dst>%)"],
    "<每股收益单位>": [r"每.*?(?P<dst>元)"],
    "币种": [r"(?P<dst>人民币|美元)"],
    "anno_time": [
        r"(?P<dst>^[\d一二三四五六七八九〇○OＯ零]{4}(?:年|\.|-|/)([\d一元二三四五六七八九十零〇○Ｏ]{1,2}(?:月份?|\.|-|/)?(?:[\d一二三四五六七八九十零〇○Ｏ]{"
        r"1,3}[日号]?)?)?)"
    ],
}
NOTICE_BASE_PREDICTORS = [
    {
        "path": ["公司全称"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(-10, 0))[::-1],
                "regs": [r"(?P<dst>.*?公司)"],  # 尽可能少匹配，去掉xx公司xx子公司的情况
                "anchor_regs": SPECIAL_ATTR_PATTERNS["date"],
            }
        ],
    },
    {
        "path": ["公司简称"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(0, 3)),
                "regs": [
                    r"(?<=简称[:：])(?P<dst>.*?)(?=\s?(公告|证券|股票|编[号码]))",
                    r"简称[:：](?P<dst>.+)(?!\s+$)",
                ],
            }
        ],
    },
    {
        "path": ["公司代码"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(0, 3)),
                "regs": [r"(?<=代码[:：])(?P<dst>\d{6})", r"代码[:：](?P<dst>\d{6})"],
            }
        ],
    },
    {
        "path": ["公告编号"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(0, 3)),
                "regs": [r"(公告)?编号[:：](?P<dst>临?[\d\-\s－—]*)"],
            }
        ],
    },
    {
        "path": ["公告时间"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(-10, 0))[::-1],
                "regs": SPECIAL_ATTR_PATTERNS["date"],
            }
        ],
    },
]


def filter_predictors(predictors=tuple(NOTICE_BASE_PREDICTORS), exclude=()):
    return [p for p in predictors if p.get("path")[0] not in exclude]
