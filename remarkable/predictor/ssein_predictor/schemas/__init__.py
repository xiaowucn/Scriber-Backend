DATE_REGS = [
    r"(?P<dst>[\d一二三四五六七八九〇○OＯ零]{4}(?:年[度初中末]?|\.|-|/)([\d一元二三四五六七八九十零〇○Ｏ]{1,2}(?:月份?|\.|-|/)?(?:[\d一二三四五六七八九十零〇○Ｏ]{"
    r"1,3}[日号]?)?)?)"
]

NOTICE_BASE_PREDICTORS = [
    {
        "path": ["公司全称"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(-10, 0))[::-1],
                "regs": [r"(?P<dst>.*?公司)"],  # 尽可能少匹配，去掉xx公司xx子公司的情况
                "anchor_regs": DATE_REGS,
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
        "path": ["公告日期"],
        "models": [
            {
                "name": "fixed_position",
                "positions": list(range(-10, 0))[::-1],
                "regs": DATE_REGS,
            }
        ],
    },
]


def filter_predictors(predictors=tuple(NOTICE_BASE_PREDICTORS), exclude=()):
    return [p for p in predictors if p.get("path")[0] not in exclude]
