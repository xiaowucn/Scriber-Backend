"""
调整募集期公告
"""

from remarkable.predictor.cmbchina_predictor.schemas import get_predictor_options
from remarkable.predictor.cmbchina_predictor.schemas.cmbchina_rate_adjustment_schema import (
    R_DATE,
    R_FUND_SUFFIX,
    R_SINCE,
)

p_fund_abbr = [
    r"(?P<dst>债券.[类级]?)[:：]\d+",
    r"(?P<dst>.[类级])份额(?:基金代码)?\d+",
    r"(?P<dst>[ABC][类级])(?:基金份额|份额基金)",
    r"(?P<dst>.[类级])基金份额.{,5}代码",
    r"(?P<dst>.[类级])基金份额\d+",
    r"(?P<dst>.[类级])[:：]\d+",
    r"(?P<dst>.[类级])(?:份额)?基金代码",
    r"(?P<dst>债券|混合.[类级]?)[:：]",
    r"(?P<dst>[ABC][类级])(?:份额)?\d{6}",
    r"(代码.\d+\D?|基金简称.)(?P<dst>.*?混合发起[ABC])[类级]?",
]

p_fund_code = [
    r"(?P<dst>\d{6})[（(].[类级]",
    r"[ABC][类级，].*?代码为?[:：（(](?P<dst>\d+)",
    r"[类级](基金)?份额(?P<dst>\d+)",
    r"[ABC][类级][:：](?P<dst>\d+)",
    r"(?:债券|混合).[类级]?[:：](?P<dst>\d+)",
    r"[ABC][类级](?:份额)?(?P<dst>\d{6})",
]
P_LEFT_QUOTE = r"[(（]"

predictor_options = [
    {
        "path": ["分级基金"],
        "sub_primary_key": ["基金简称", "基金代码"],
        "divide_answers": True,
        "models": [
            {
                "name": "partial_text",
                "merge_char_result": False,
                "neglect_patterns": [r"升级"],
                "multi_elements": True,
                "multi": True,
                "regs": {
                    "基金简称": p_fund_abbr,
                    "基金代码": p_fund_code,
                },
            },
        ],
    },
    {
        "path": ["募集开始时间"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    rf"{R_SINCE}{R_DATE}起?(?:开始|启动|向全社会公开)募集",
                    rf"(开放|募集)期限?为?{R_SINCE}?{R_DATE}起?至",
                ],
            },
        ],
    },
    {
        "path": ["调整或延长后时间"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    rf"{R_DATE}定为.{{0,5}}(开放|募集)期最后一日",
                    # http://100.64.0.9:55842/scriber/#/project/remark/10802?projectId=40&treeId=68&fileId=1331&schemaId=6
                    rf"基金的?(?:募集截止日提前|最后一个募集日).?{R_DATE}",
                    # http://100.64.0.9:55842/scriber/#/project/remark/10800?projectId=40&treeId=68&fileId=1333&schemaId=6
                    rf"(提前结束.*?募集.?|提前.|募集期截止日.?){R_DATE}",
                    # http://100.64.0.9:55842/scriber/#/project/remark/10856?projectId=40&treeId=68&fileId=1277&schemaId=6
                    rf"{R_DATE}.*?最后认购日",
                ],
            },
        ],
    },
    {
        "path": ["基金名称"],
        "models": [
            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/4996
            {
                "name": "middle_paras",
                "top_anchor_content_regs": [
                    r"^(.*?公司)?(关于)?(?P<content>.*)",
                ],
                "bottom_anchor_content_regs": [r"(?P<content>.*?基?金)"],
                "top_anchor_regs": [r"^(.*?公司)?关于", r"优选混合型"],
                "bottom_anchor_regs": [r"(?:结束募集|募集期提前结束)的?公告$"],
                "include_bottom_anchor": True,
                "elements_in_page_range": [0],
            },
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    rf"关于(?P<dst>.*?基金(中基金{R_FUND_SUFFIX}?)?)提前结束",
                    rf"公司(?P<dst>.*?基金(中基金{R_FUND_SUFFIX}?)?)提前结束",
                    r"^(?:关于)?(?P<dst>.*?基金)(?:公众投资者|公众发售|募集期)?.*提前结束",
                ],
            },
        ],
    },
    {
        "path": ["基金代码"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "neglect_patterns": [r"[ABC]类"],
                "regs": [
                    # http://100.64.0.9:55842/scriber/#/project/remark/9695?treeId=23&fileId=400&schemaId=6
                    r"代码[:：](?P<dst>\d{6})\s*.{0,5}简称.?本基金",
                    rf"^.*?基金{P_LEFT_QUOTE}以下简称.*?(?:基金|认购)代码为?[^\d]?(?P<dst>\d+)",
                    rf"^.*?基金{P_LEFT_QUOTE}(?:基金|认购)代码为?[^\d]?(?P<dst>\d+)",
                ],
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": get_predictor_options(predictor_options),
}
