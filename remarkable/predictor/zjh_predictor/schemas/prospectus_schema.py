"""
证监会招股说明书信息抽取导出json
"""

predictor_options = [
    {
        "path": ["释义"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["发行人基本情况"],
        "models": [
            {
                "name": "partial_text",
            },
        ],
    },
    {
        "path": ["控股股东简要情况"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["实际控制人简要情况"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["股权结构"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["发行人员工及结构情况"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["发行人所处行业"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["主要客户"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["主要供应商"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["专利"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["关联交易"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["董监高核心人员基本情况"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["审计意见"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["合并资产负债表"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["合并利润表"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["合并现金流量表"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["基本财务指标"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["非经常性损益情况"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["税款缴纳情况"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["盈利能力"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["财务报表附注"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["应收账款"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["预付账款"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["存货减值"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["固定资产折旧"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["无形资产"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["商誉减值准备"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["净利润与经营活动净现金流量差异"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["募集资金与运用"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["重大合同"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
    {
        "path": ["重大诉讼事项"],
        "models": [
            {
                "name": "table_tuple",
            },
        ],
    },
]

prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
