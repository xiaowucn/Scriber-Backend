"""
schema id: 112
schema name: "0901 实施利润分配和资本公积金转增"
"""

from remarkable.predictor.sse_predictor.predictor_config import filter_predictors

predictor_options = filter_predictors()

predictor_options.extend(
    [
        {
            "path": ["公告发布主体"],
            "models": [
                {
                    "name": "fixed_position",
                    "positions": (0,),
                    "regs": [r"(?P<dst>.*?公司)"],
                    "use_crude_answer": True,
                }
            ],
        },
        {
            "path": ["利润分配具体方案"],
            "models": [{"name": "partial_text"}],
        },
        {
            "path": ["利润分配发放年度及发放名称", "年度"],
            "models": [{"name": "partial_text"}],
        },
        {
            "path": ["利润分配发放年度及发放名称", "名称"],
            "models": [{"name": "partial_text"}],
        },
        {
            "path": ["新增无限售流通股份上市日"],
            "models": [{"name": "partial_text"}],
        },
        {
            "path": ["现金红利发放日"],
            "models": [{"name": "partial_text"}],
        },
        {
            "path": ["股权登记日"],
            "models": [{"name": "partial_text"}],
        },
        {
            "path": ["除权除息日"],
            "models": [{"name": "partial_text"}],
        },
        {
            "path": ["审议程序情况（是否要上股东大会决议）"],
            "models": [{"name": "partial_text"}],
        },
        {
            "path": ["董事会反对及弃权情况", "投票情况", "反对"],
            "models": [{"name": "partial_text"}],
        },
        {
            "path": ["董事会反对及弃权情况", "投票情况", "弃权"],
            "models": [{"name": "partial_text"}],
        },
        {
            "path": ["董事会反对及弃权情况", "姓名"],
            "models": [{"name": "partial_text"}],
        },
        {
            "path": ["董事会反对及弃权情况", "理由"],
            "models": [{"name": "partial_text"}],
        },
    ]
)

prophet_config = {"depends": {}, "predictor_options": predictor_options}
