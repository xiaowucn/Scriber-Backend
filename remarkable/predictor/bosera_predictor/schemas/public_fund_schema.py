"""
博时基金 公募基金合同
"""

predictor_options = [
    {
        "path": ["投资范围"],
        "models": [
            {
                "name": "syllabus_elt_v2",
                "multi": False,
                "multi_elements": False,
                "only_first": False,
                "include_title": False,
                "break_para_pattern": [
                    "基金的投资组合比例为",
                    "本基金投资组合中股票投资比例为",
                    "基金投资于基础设施资产支持证券的资产比例",
                ],
            }
        ],
    },
    {
        "path": ["权益类比例限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
            },
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<content>股票资产占基金资产的比例为\d+[%％][-—]\d+[%％])",
                    r"(?P<content>本基金的股票资产投资比例为\d+[%％][-—]\d+[%％])",
                    r"(?P<content>本基金股票资产比例为基金资产的\s?\d+[%％][-—]\d+[%％])",
                    r"(?P<content>本基金的股票资产占基金资产的\d+[%％][-—]\d+[%％])",
                    r"(?P<content>本基金投资组合中股票等权益类资产投资比例为基金资产的\d+[%％][-—]\d+[%％])",
                    r"(?P<content>本基金的股票资产([（(]含存托凭证[）)])?投资比例为基金资产的\d+[%％][-—]\d+[%％])",
                    r"(?P<content>本基金的股票资产投资比例不低于基金资产的\d+[%％])",
                    r"(?P<content>本基金持有一家上市公司的股票([（(]含存托凭证[）)])?，其市值不超过基金资产净值的\d+[%％])",
                    # r'',
                ),
            },
        ],
    },
    {
        "path": ["港股通标的股票占股票资产比例限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
            },
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<content>港股通标的股票的投资比例为(股票资产|基金资产)的\s?0[%％]?-\d+[%％])",
                    r"(?P<content>投资于港股通标的股票占股票资产的比例为\s?0[%％]?-\d+[%％])",
                ),
            },
        ],
    },
    {
        "path": ["现金类比例限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
                "neglect_answer_patterns": [
                    "^本基金每个交易日日终在扣除.*?交易保证金后，应当保持不低于交易保证金一倍的现金"
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": ("现金.*?不低于基金资产净值|不低于基金资产净值.*?现金",),
            },
        ],
    },
    {
        "path": ["同一发行人持仓市值比例限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
            },
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<content>本?基金持有一家(公司发行|上市公司)的(证券|股票).*?[AH]?.*?不超过基金资产净值的\s?\d+[%％])",
                    r"(?P<content>本基金持有一家公司发行的证券，其市值不超过基金净资产的\d+[%％]，直接或间接持有基础设施资产支持证券的除外)",
                ),
            },
        ],
    },
    {
        "path": ["管理人管理的全部基金同一发行人持仓数量占规模比例限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>本?基金管理人管理的全部基金持有一家公司发行的证券.*?不超过该证券.*?\d+[%％])",
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<content>本?基金管理人管理的全部基金持有一家公司发行的证券.*?不超过该证券.*?\d+[%％])",
                    r"(?P<content>本?基金管理人管理的全部基金持有的同一权证.*?不得超过该权证的.*?\d+[%％])",
                    r"(?P<content>本?基金管理人管理的全部基金.*?不超过该证券的.*?\d+[%％].*?除外)",
                    r"(?P<content>本基金与由本?基金管理人管理的其他基金持有一家公司发行的证券（含存托凭证），不超过该证券的\d+[%％])",
                ),
            },
        ],
    },
    {
        "path": ["同一原始权益人ABS持仓比例限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
            },
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<content>本?基金投资于同一原始权益人的各类资产支持证券的比例，不得超过该?基金资产净值的\d+[%％])",
                ),
            },
        ],
    },
    {
        "path": ["ABS持仓总市值比例限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>本基金持有的全部资产支持证券，其市值不得超过基金资产净值的\d+[%％])",
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<content>本基金持有的全部资产支持证券，其市值不得超过该?基金资产净值的\d+[%％])",
                ),
            },
        ],
    },
    {
        "path": ["持有同一信用级别的ABS占ABS规模限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
            },
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<content>本基金持有的同一[（(]指同一信用级别[)）]资产支持证券的比例，不得超过该资产支持证券规模的\d+[%％])",
                ),
            },
        ],
    },
    {
        "path": ["管理人管理的全部基金持有同一原始权益人的ABS占ABS合计规模限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
            },
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<content>本?基金管理人管理的全部(证券投资)?基金投资于同一原始权益人的各类资产支持证券，不得超过其各类资产支持证券合计规模的\d+[%％])",
                    # '(?P<content>基金管理人管理的全部证券投资基金投资于同一原始权益人的各类资产支持证券，不得超过其各类资产支持证券合计规模的10%)',
                ),
            },
        ],
    },
    {
        "path": ["投资ABS的信用级别限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
            },
            {
                "name": "para_match",
                "paragraph_pattern": (
                    "(?P<content>本基金应投资于信用级别评级为[AB]{3}以上[(（]含[AB]{3}[)）]的资产支持证券)",
                ),
            },
        ],
    },
    {
        "path": ["杠杆比例限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
            },
            {
                "name": "para_match",
                "paragraph_pattern": ("资产总值不得超过基金资产净值",),
            },
        ],
    },
    {
        "path": ["回购比例限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
            },
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<content>本基金进入全国银行间同业市场进行债券回购的资金余额不得超过基金资产净值的\d+[%％])",
                    r"(?P<content>进入全国银行间同业市场的债券回购融入的资金余额不得超过基金资产净值的\d+[%％])",
                    r"(?P<content>债券正回购的资金余额占基金资产净值的比例不得超过\d+[%％])",
                    r"(?P<content>在银行间市场进行债券回购融入的资金余额不超过基金资产净值的\d+[%％])",
                    r"(?P<content>除发生巨额赎回的情形外，本基金债券正回购的资金余额在每个交易日均不得超过基金资产净值的\d+[%％].*?\d+个交易日内进行调整)",
                ),
            },
        ],
    },
    {
        "path": ["回购期限限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
            }
        ],
    },
    {
        "path": ["流动受限资产比例限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>本基金主动投资于流动性受限资产的市值合计不得超过[该本]?基金资产净值的\d+[%％])",
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<content>本基金主动投资于流动性受限资产的市值合计不得超过[该本]?基金资产净值的\d+[%％])",
                    r"(?P<content>到期日在\d+个交易日以上的逆回购、银行定期存款等流动性受限资产投资占基金资产净值的比例合计不得超过\d+[%％])",
                ),
            },
        ],
    },
    {
        "path": ["管理人管理的全部开放式基金持有同一家公司的股票数量占流通股本比例限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
            },
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<content>本?基金管理人管理的全部开放式基金持有一家上市公司发行的可流通股票，不得超过该?上市公司可流通股票的\d+[%％])",
                ),
            },
        ],
    },
    {
        "path": ["管理人管理的全部基金持有同一家公司的股票数量占流通股本比例限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
            }
        ],
    },
    {
        "path": ["新股申购的金额限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>本基金(财产)?参与股票发行申购，(本基金)?所申报的金额不超过本基金的?总资产)",
                ],
            },
            {
                "name": "para_match",
                "paragraph_pattern": (
                    "(?P<content>本基金(财产)?参与股票发行申购，(本基金)?所申报的金额不超过本基金的?总资产)",
                ),
            },
        ],
    },
    {
        "path": ["新股申购的数量限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
            },
            {
                "name": "para_match",
                "paragraph_pattern": ("(?P<content>本基金所申报的股票数量不超过拟发行股票公司本次发行股票的总量)",),
            },
        ],
    },
    {
        "path": ["持有买入股指期货比例限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
            },
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<content>(本基金)?在任何交易日日终，(本基金)?持有的?买入股指期货合约价值.*?不得?超过基金资产净值的\d+[%％])",
                ),
            },
        ],
    },
    {
        "path": ["买入股指期货和有价证券汇总比例限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
            },
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<content>((本基金)?在任何交易日日终|每个交易日日终)，持有的买入期货合约价值与有价证券市值.*?不得超过基金资产净值的\d+[%％])",
                    # '(?P<content>((本基金)?在任何交易日日终|每个交易日日终).*?买入(股指期货|期货合约|国债期货).*?有价证券.*?不得超过基金资产净值的\d+[%％])',
                ),
            },
        ],
    },
    {
        "path": ["持有卖出股指期货比例限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
                "neglect_answer_patterns": ["卖出国债期货合约"],
            },
            {
                "name": "para_match",
                "paragraph_pattern": (
                    r"(?P<content>(本基金)?在任何交易日日终，持有的卖出(股指)?期货合约价值不得?超过基金持有的股票总市值的\d+[%％])",
                ),
            },
        ],
    },
    {
        "path": ["股票和买入卖出股指期货轧差合计比例限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
            }
        ],
    },
    {
        "path": ["持有买入国债期货合约比例限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
                "neglect_answer_patterns": ["买入股指期货合约"],
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>(本基金)?在任何交易日日终，持有的买入国债期货合约价值，不得超过基金资产净值的?\d+[%％])",
                ],
            }
        ],
    },
    {
        "path": ["持有卖出国债期货合约比例限制"],
        "models": [
            {
                "name": "partial_text",
                "multi": False,
                "multi_elements": False,
                "use_answer_pattern": True,
                "neglect_answer_patterns": ["卖出(股指)?期货合约"],
                "model_alternative": True,
                "regs": [
                    r"(?P<dst>(本基金)?在任何交易日日终，持有的卖出国债期货合约价值不得超过基金持有的债券总市值的?\d+[%％])",
                ],
            }
        ],
    },
]
prophet_config = {
    "depends": {},
    "predictor_options": predictor_options,
}
