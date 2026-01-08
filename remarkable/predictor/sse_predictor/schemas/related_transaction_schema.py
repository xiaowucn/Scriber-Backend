"""
schema id: 61
schema name: "18 年报半年报-关联交易"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors(exclude=("公司全称",))

predictor_options.extend(
    [
        {
            "path": ["公司全称"],
            "models": [
                {"name": "fixed_position", "positions": (0,), "regs": [r"(?P<dst>.*?公司)"], "use_crude_answer": True}
            ],
        },
        {
            "path": ["关联方", "本企业的母公司"],
            "models": [{"name": "table_row", "multi": True}, {"name": "partial_text"}],
        },
        {
            "path": ["关联方", "本企业的子公司"],
            "models": [
                {"name": "table_row", "multi": True, "multi_elements": True},
                {"name": "partial_text", "multi": True},
            ],
            "pick_answer_strategy": "all",
        },
        {
            "path": ["关联方", "本企业合营和联营企业"],
            "models": [
                {"name": "table_row", "multi": True, "multi_elements": True},
                {"name": "partial_text", "multi": True},
            ],
        },
        {
            "path": ["关联方", "其它关联方"],
            "models": [{"name": "table_row", "multi": True}, {"name": "partial_text", "multi": True}],
        },
        {"path": ["币种"], "models": [{"name": "partial_text", "regs": [r"币种[:：]?(?P<dst>(人民币|美元))"]}]},
        {"path": ["单位"], "models": [{"name": "partial_text", "regs": [r"单位[:：]?(?P<dst>.*元)"]}]},
        {
            "path": ["采购商品/接受劳务"],
            "sub_primary_key": ["关联方", "关联交易内容"],
            "models": [{"name": "table_row", "multi": True}],
            "anchor_regs": [r"采购商品/接受劳务情况表.*?√适用"],
        },
        {
            "path": ["销售商品/提供劳务"],
            "sub_primary_key": ["关联方", "关联交易内容"],
            "models": [{"name": "table_row", "multi": True}],
            "anchor_regs": [r"[出销]售商品/提供劳务情况表.*?√适用"],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
