from remarkable.plugins.cgs.common.chapters_patterns import ChapterPattern
from remarkable.plugins.cgs.common.template_condition import AssetTemplateConditional, ContentConditional, TemplateName

"""
单个句子至少需要匹配一次
可以存在多种表述的模板，每种模板仅支持一段
"""

example = [
    {
        "label": "",
        "related_name": "",
        "name": "",
        "from": "",
        "origin": "",
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE],
                        "items": [
                            "混合类单一资产管理计划。",
                        ],
                    },
                ],
            },
        ],
    },
]

TEMPLATE_WITH_SENTENCE_MULTIPLE_COMPARE = [
    {
        "label": "template_1051",
        "related_name": "资产管理计划的投资",
        "name": "投资-同一资产投资比例限制",
        "from": "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）",
        "origin": [
            "第十五条 一个集合资产管理计划投资于同一资产的资金，不得超过该计划资产净值的25%。除以收购公司为目的设立的资产管理计划、专门投资于未上市企业股权的资产管理计划外，同一证券期货经营机构管理的全部集合资产管理计划投资于同一资产的资金，不得超过该资产的25%。银行活期存款、国债、中央银行票据、政策性金融债、地方政府债券等中国证监会认可的投资品种除外。",
            "全部投资者均为符合中国证监会规定的专业投资者且单个投资者投资金额不低于1000万元的封闭式集合资产管理计划，以及完全按照有关指数的构成比例进行证券投资的资产管理计划等中国证监会认可的其他集合资产管理计划，不受前款规定的投资比例限制。",
            "同一证券期货经营机构管理的全部资产管理计划及公开募集证券投资基金（以下简称公募基金）合计持有单一上市公司发行的股票不得超过该上市公司可流通股票的30%。完全按照有关指数的构成比例进行证券投资的资产管理计划、公募基金，以及中国证监会认定的其他投资组合可不受前述比例限制。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_INVEST,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_POOLED],
                        "items": [
                            "投资于同一资产的资金，不得超过计划资产净值的25%；管理人管理的全部集合资产管理计划投资于同一资产的资金，不得超过该资产的25%。银行活期存款、国债、中央银行票据、政策性金融债、地方政府债券等中国证监会认可的投资品种除外。",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1052",
        "related_name": "资产管理计划的投资",
        "name": "投资-证券发行申购的申报比例",
        "from": "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）",
        "origin": [
            "第十六条 资产管理计划参与股票、债券、可转换公司债券、可交换公司债券等证券发行申购时，单个资产管理计划所申报的金额原则上不得超过该资产管理计划的总资产，单个资产管理计划所申报的数量原则上不得超过拟发行公司本次发行的总量。",
            "同一证券期货经营机构管理的全部资产管理计划投资于非标准化债权类资产的资金不得超过其管理的全部资产管理计划净资产的35%。因证券市场波动、资产管理计划规模变动等客观因素导致前述比例被动超标的，证券期货经营机构应当及时报告中国证监会相关派出机构，且在调整达标前不得新增投资于非标准化债权类资产。",
            "同一证券期货经营机构管理的全部资产管理计划投资于同一非标准化债权类资产的资金合计不得超过300亿元。",
            "证券期货经营机构依照《管理办法》第十条、本规定第十七条设立的子公司，按照其与证券期货经营机构合并计算的口径，适用本条第二款、第三款的规定。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_INVEST,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            [
                                "参与股票、债券、可转换公司债券/可转换债券/可转债、可交换公司债券/可交换债券/可交债等证券发行申购时，本计划所申报的金额不得超过本计划总资产，本计划所申报的数量不得超过拟发行公司本次发行的总量。",
                                "参与股票、债券、可转换公司债券、可交换公司债券等证券发行申购时，单个资产管理计划所申报的金额不得超过该资产管理计划的总资产，单个资产管理计划所申报的数量不得超过拟发行公司本次发行的总量。",
                                "本计划参与证券发行申购时，所申报的金额不得超过本计划的总资产，本计划所申报的证券数量不得超过拟发行公司本次发行的总量。",
                            ],
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1053",
        "related_name": "资产管理计划的投资",
        "name": "投资-开放退出期内可变现资产的比例",
        "from": "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）",
        "origin": "第二十五条 证券期货经营机构应当确保集合资产管理计划开放退出期内，其资产组合中7个工作日可变现资产的价值，不低于该计划资产净值的10%。",
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_INVEST,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_POOLED],
                        "items": [
                            "本计划开放退出期内，其资产组合中7个工作日可变现资产的价值，不低于该计划资产净值的10%",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1054",
        "related_name": "资产管理计划的投资",
        "name": "投资-资产负债比例限制",
        "from": [
            "关于规范金融机构资产管理业务的指导意见（银发〔2018〕106号 2018年4月27日）",
            "证券期货经营机构私募资产管理业务管理办法（证监会令第203号修订 2023年1月12日）",
            "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）",
        ],
        "origin": [
            "二十、资产管理产品应当设定负债比例（总资产/净资产）上限，同类产品适用统一的负债比例上限。每只开放式公募产品的总资产不得超过该产品净资产的140%，每只封闭式公募产品、每只私募产品的总资产不得超过该产品净资产的200%。计算单只产品的总资产时应当按照穿透原则合并计算所投资资产管理产品的总资产。金融机构不得以受托管理的资产管理产品份额进行质押融资，放大杠杆。",
            "第四十三条 资产管理计划应当设定合理的负债比例上限，确保其投资杠杆水平与投资者风险承受能力相匹配，并保持充足的现金或者其他高流动性金融资产偿还到期债务。",
            "资产管理计划的总资产不得超过该计划净资产的200%，分级资产管理计划的总资产不得超过该计划净资产的140%。",
            "第二十九条 资产管理计划投资于同一发行人及其关联方发行的债券的比例超过其净资产50%的，该资产管理计划的总资产不得超过其净资产的120%。资产管理计划投资于国债、中央银行票据、政策性金融债、地方政府债券等中国证监会认可的投资品种不受前述规定限制。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_INVEST,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            "【1】资产管理计划的总资产不得超过净资产的200%。",
                        ],
                    }
                ],
            },
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_INVEST,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            "【2】投资于同一发行人及其关联方发行的债券的比例超过其净资产50%的，本计划的总资产不得超过其净资产的120%。投资于国债、中央银行票据、政策性金融债、地方政府债券等中国证监会认可的投资品种不受前述规定限制。",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1056",
        "related_name": "资产管理计划的投资",
        "name": "投资-持有一家上市公司股票的比例",
        "from": "关于规范金融机构资产管理业务的指导意见（银发〔2018〕106号 2018年4月27日）",
        "origin": [
            "十六、金融机构应当做到每只资产管理产品所投资资产的风险等级与投资者的风险承担能力相匹配，做到每只产品所投资资产构成清晰，风险可识别。",
            "金融机构应当控制资产管理产品所投资资产的集中度：",
            "……",
            "（三）同一金融机构全部资产管理产品投资单一上市公司发行的股票不得超过该上市公司可流通股票的30%。",
            "金融监督管理部门另有规定的除外。",
            "非因金融机构主观因素导致突破前述比例限制的，金融机构应当在流动性受限资产可出售、可转让或者恢复交易的10个交易日内调整至符合相关要求。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_INVEST,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            [
                                "管理人管理的全部资产管理计划及公开募集证券投资基金合计持有单一上市公司发行的股票不得超过该上市公司可流通股票的30%。",
                                "管理人管理的全部资产管理计划合计持有一家上市公司发行的股票不得超过该上市公司可流通股票的30%。",
                            ]
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1057",
        "related_name": "资产管理计划的投资",
        "name": "投资-比例限制被动超限的处理方式",
        "from": "证券期货经营机构私募资产管理业务管理办法（证监会令第203号修订 2023年1月12日）",
        "origin": [
            "第四十一条 资产管理计划存续期间，证券期货经营机构应当严格按照法律、行政法规、中国证监会规定以及合同约定的投向和比例进行资产管理计划的投资运作。",
            "资产管理计划改变投向和比例的，应当事先取得投资者同意，并按规定履行合同变更程序。",
            "因证券期货市场波动、证券发行人合并、资产管理计划规模变动等证券期货经营机构之外的因素导致资产管理计划投资不符合法律、行政法规和中国证监会规定的投资比例或者合同约定的投资比例的，证券期货经营机构应当在流动性受限资产可出售、可转让或者恢复交易的二十个交易日内调整至符合相关要求。确有特殊事由未能在规定时间内完成调整的，证券期货经营机构应当及时向中国证监会相关派出机构报告。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "content_condition": ContentConditional.TRADING_DAY,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_INVEST,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            "因证券期货市场波动、证券发行人合并、资产管理计划规模变动等证券期货经营机构之外的因素导致资产管理计划投资不符合法律、行政法规和中国证监会规定的投资比例或者合同约定的投资比例的，管理人应当在流动性受限资产可出售、可转让或者恢复交易的{X1}个交易日内调整至符合相关要求。确有特殊事由未能在规定时间内完成调整的，管理人应当及时向中国证监会相关派出机构报告。",
                        ],
                    }
                ],
            },
        ],
    },
]
