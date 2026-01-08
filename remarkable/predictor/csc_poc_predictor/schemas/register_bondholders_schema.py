"""中信建投 《【深中登】债券持有人名册》"""

predictor_options = [
    {
        "path": ["文档标题"],
        "models": [
            {
                "name": "partial_text",
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>证券持有人名册)",
                    r"(?P<dst>明细数据表)",
                ],
            },
        ],
    },
    {
        "path": ["债券简称"],
        "models": [
            {
                "name": "partial_text",
                "use_answer_pattern": False,
            },
            {
                "name": "fake_table",
                "pattern": [
                    r"(证券简称|债券简称)\s*?[:：](?P<dst>.*?)\s*?[(证券代码|债券代码)|\s]",
                    r"(证券简称|债券简称)\s*?[:：](?P<dst>\w*\d$)",
                ],
            },
        ],
    },
    {
        "path": ["债券代码"],
        "models": [
            {
                "name": "partial_text",
            },
            {
                "name": "fake_table",
                "pattern": [
                    r"(证券代码|债券代码)[:：]\s*?(?P<dst>\d+)\s*?",
                ],
            },
        ],
    },
    {
        "path": ["权益登记日"],
        "models": [
            {
                "name": "partial_text",
            },
            {
                "name": "fake_table",
                "pattern": [
                    r"(权益登记日)[:：]\s*?(?P<dst>.*)\s*?",
                ],
            },
        ],
    },
    {
        "path": ["前N名证券持有人名册"],
        "sub_primary_key": ["一码通账户号码", "持有人名称"],
        "models": [
            {
                "name": "register_holders",
                "multi_elements": True,
                "lazy_match": True,
                "feature_black_list": [r""],
                "neglect_patterns": [
                    r"^$",
                    r"第.*?页",
                ],
                "ignore_header_regs": [
                    r"证券代码",
                    r"证券简称",
                    r"权益登记日",
                ],
                "neglect_header_regs": [
                    r"证券总数量",
                    r"总户数",
                    r"序号",
                ],
                #  因为表格解析问题 将文章中的证券简称 证券全称等识别成表格的第一行 所以加了下面的正则
                "持有人名称": {
                    "feature_white_list": [r"__regex__持有人名称|简称"],
                },
                "一码通账户号码": {
                    "feature_white_list": [r"__regex__码通账户号码|简称"],
                },
                "证券账户号码": {
                    "feature_white_list": [r"__regex__证券账户号码|简称"],
                },
                "证件号码": {
                    "feature_white_list": [r"__regex__证件号码|简称"],
                },
                "持有金额（元）": {
                    "feature_white_list": [r"__regex__持有数量|简称"],
                },
                "持有比例": {
                    "feature_white_list": [r"__regex__持有比例|简称"],
                    "feature_black_list": [r"质押/冻结总数"],
                },
                "质押/冻结总数": {
                    "feature_white_list": [r"__regex__(质押|冻结)总数|简称|登记日"],
                },
                "联系电话": {
                    "feature_white_list": [r"__regex__联系电话|简称|登记日"],
                },
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
