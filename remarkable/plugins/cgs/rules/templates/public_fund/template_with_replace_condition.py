# 替换模板中单选或多选项
from remarkable.common.constants import RuleType
from remarkable.common.pattern import PatternCollection
from remarkable.plugins.cgs.common.chapters_patterns import (
    R_CONJUNCTION,
    ChapterPattern,
)
from remarkable.plugins.cgs.common.enum_utils import TemplateCheckTypeEnum
from remarkable.plugins.cgs.common.patterns_util import P_PARA_PREFIX_NUM, R_NOT_CONJUNCTION_PUNCTUATION, R_PUNCTUATION
from remarkable.plugins.cgs.common.template_condition import (
    TemplateConditional,
    TemplateName,
)

# example
example = {
    "templates": [
        {
            # items内多个类型可以嵌套、组合
            "items": [
                # 段内替换
                # 文中固定位置提取（属性），一般为提取交易所、基金类型，
                # 配置为指定提取函数字符串,及默认值, 配置的函数需要添加至ExtractFundBasicInfo类中
                {
                    "type": "inner_replace",
                    "rules": {"IRP_1": {"func": "get_fund_bourse_name"}},
                    "items": ["{IRP_1}证券投资基金（基金名称）由基金管理人依照《基金法》"],
                },
                # 段内重组
                {
                    "type": "inner_recombination",
                    "rules": {
                        "IR_1": {
                            "para_pattern": PatternCollection(r"工作日[:：](?P<content>.*)的正常交易日"),
                            "default": "上海证券交易所、深圳证券交易所、北京证券交易所",
                            "patterns": [
                                {
                                    "pattern": PatternCollection(r"北京证券交易所|北交所"),
                                    "value": "北京证券交易所",
                                    # condition内条件为TemplateConditional
                                    "conditions": [],
                                },
                            ],
                        },
                    },
                    "items": ["工作日：指{IR_1}的正常交易日"],
                },
                # 多段重组
                {
                    "type": "recombination",
                    "patterns": [
                        PatternCollection(r"基金份额持有人大会的召开"),
                        PatternCollection(r"更换基金管理人、基金托管人、基金份额登记机构，基金改聘会计师事务所；"),
                    ],
                    # 头部添加自增序号1、2、
                    "with_serial_num": True,
                    "items": [
                        "基金份额持有人大会的召开；",
                        {
                            "type": "inner_recombination",
                            "rules": [
                                {
                                    "IR_1": {
                                        "para_pattern": PatternCollection(r"更换"),
                                        "default": "基金管理人、基金托管人",
                                        "patterns": [
                                            {
                                                "pattern": PatternCollection(r"(?:基金)?托管人"),
                                                "value": "基金托管人",
                                                # condition内条件为TemplateConditional
                                                "conditions": [],
                                            },
                                        ],
                                    },
                                },
                            ],
                            "items": [
                                "更换{R_1}；",
                            ],
                        },
                    ],
                },
                # 段内引用，引用数量超过1种，则生成两种引用类型： 1、2、3/ 1-3(数字必须全部连续递增)
                {
                    "type": "inner_refer",
                    "rules": {
                        "IR_1": {
                            "default": "1",
                            "refer_chapters": None,
                            # 多次匹配
                            "multiple": True,
                            # 配置所引用段落正则
                            "patterns": [
                                PatternCollection(r"不可抗力导致基金无法正常运作"),
                                PatternCollection(r"可暂停接受投资人的申购申请"),
                                PatternCollection(r"管理人无法找到合适的投资品种.*?损害现有基金份额持有人利益的?情形"),
                                PatternCollection(r"法律法规规定或中国证监会认定的其他情形"),
                            ],
                        },
                    },
                    "items": [
                        "发生上述第{IR_1}项暂停申购情形之一，基金管理人应当根据有关规定在规定媒介上刊登暂停申购公告"
                    ],
                },
                {
                    "type": "single_select",
                    "rules": {
                        "IR_1": {
                            "para_pattern": PatternCollection(r"(?P<content>[\u4e00-\u9fa5]+)管理人负责计算"),
                            "default": "基金份额净值（基金净值信息）",
                            "patterns": [
                                {
                                    "pattern": PatternCollection(r"份额净值"),
                                    "content": "基金份额净值",
                                    # condition内条件为TemplateConditional
                                    "conditions": [],
                                },
                                {
                                    "pattern": PatternCollection(r"净值信息"),
                                    "content": "基金净值信息",
                                },
                            ],
                        },
                    },
                    "items": ["{IS_1}由基金管理人负责计算"],
                },
                # 小标题忽略顺序
                {
                    "type": "chapter_recombination",
                    "patterns": [
                        PatternCollection(r"(?<!非)上市基金"),
                        PatternCollection(r"非上市基金"),
                    ],
                    "with_serial_num": True,
                    "items": [
                        "上市基金；",
                        "非上市基金；",
                    ],
                    "child_items": [
                        "上市标题下的内容",
                        "非上市标题下的内容",
                    ],
                },
            ],
        }
    ],
}

TEMPLATE_WITH_REPLACE_CONDITIONS = [
    {
        "label": "template_600",
        "schema_fields": ["申购和赎回场所"],
        "related_name": "基金份额的申购与赎回",
        "name": "申购和赎回的场所",
        "from": "",
        "origin": [
            "一、申购和赎回场所",
            "本基金的申购与赎回将通过销售机构进行。具体的销售网点将由基金管理人在招募说明书或其他相关公告中列明。",
            "基金管理人可根据情况变更或增减销售机构，并予以公告。基金投资者应当在销售机构办理基金销售业务的营业场所或按销售机构提供的其他方式办理基金份额的申购与赎回。",
        ],
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "一、申购和赎回场所",
            "本基金的申购与赎回将通过销售机构进行。具体的销售网点将由基金管理人在招募说明书或其他相关公告中列明。",
            "基金管理人可根据情况变更或增减销售机构，并予以公告。基金投资者应当在销售机构办理基金销售业务的营业场所或按销售机构提供的其他方式办理基金份额的申购与赎回。",
        ],
        "templates": [
            {
                "name": "法规",
                "content_title": "法规条款",
                "chapter": ChapterPattern.CHAPTER_FUND_SUBSCRIPTION_PLACE,
                "items": [
                    {
                        "conditions": [TemplateConditional.SPECIAL_TYPE_LOF_NO],
                        "items": [
                            "一、申购和赎回场所",
                            "本基金的申购与赎回将通过销售机构进行。具体的销售网点将由基金管理人在招募说明书或其他相关公告中列明。",
                        ],
                    },
                    "基金管理人可根据情况变更或增减销售机构，并予以公告。基金投资者应当在销售机构办理基金销售业务的营业场所或按销售机构提供的其他方式办理基金份额的申购与赎回。",
                ],
            },
            {
                "name": "范文",
                "content_title": "合同范文",
                "chapter": ChapterPattern.CHAPTER_FUND_SUBSCRIPTION_PLACE,
                "rule_fields": [("上市交易所", [TemplateConditional.SPECIAL_TYPE_LOF])],
                "items": [
                    {
                        "single_optional": [
                            {
                                "conditions": [TemplateConditional.SPECIAL_TYPE_LOF],
                                "items": [
                                    {
                                        "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                                        "rules": {"IRP_1": {"func": "get_fund_bourse_name"}},
                                        "items": [
                                            {
                                                "conditions": [TemplateConditional.SHARE_CLASSIFY_YES],
                                                "items": [
                                                    "本基金的申购与赎回将通过销售机构进行。投资人可通过场内、场外两种渠道申购与赎回A类基金份额；可通过场外渠道申购与赎回C类基金份额。"
                                                    "本基金场外申购和赎回场所为基金管理人的直销网点及各场外销售机构的基金销售网点，A类基金份额场内申购和赎回场所为{IRP_1}内具有相应业务资格的会员单位，"
                                                    "具体的销售机构将由基金管理人在招募说明书或其他相关公告中列明。",
                                                ],
                                            },
                                            {
                                                "conditions": [TemplateConditional.SHARE_CLASSIFY_NO],
                                                "items": [
                                                    "本基金的申购与赎回将通过销售机构进行。本基金场外申购和赎回场所为基金管理人的直销网点及各场外销售机构的基金销售网点，"
                                                    "场内申购和赎回场所为{IRP_1}内具有相应业务资格的会员单位，具体的销售网点将由基金管理人在招募说明书或其他相关公告中列明。",
                                                ],
                                            },
                                        ],
                                    },
                                ],
                            },
                            {
                                "single_optional": [
                                    {
                                        "conditions": [TemplateConditional.LISTED_TRANSACTION_YES],
                                        "items": [
                                            "本基金的申购与赎回将通过销售机构进行。具体的销售网点将由基金管理人在招募说明书或其他相关公告中或管理人网站列明。"
                                        ],
                                    },
                                    {
                                        "items": [
                                            "本基金的申购与赎回将通过销售机构进行。具体的销售网点将由基金管理人在招募说明书或管理人网站列明。"
                                        ],
                                    },
                                ]
                            },
                        ],
                    },
                    "基金管理人可根据情况变更或增减销售机构，并在管理人网站公告。基金投资者应当在销售机构办理基金销售业务的营业场所或按销售机构提供的其他方式办理基金份额的申购与赎回。",
                ],
            },
        ],
    },
    {
        "label": "template_654",
        "related_name": "基金的信息披露",
        "name": "信息披露-股指期货/国债期货/股票期权",
        "from": [
            "证券投资基金参与股指期货交易指引（证监会公告〔2010〕13号 2010年4月21日）",
            "公开募集证券投资基金参与国债期货交易指引（证监会公告〔2013〕37号 2013年9月3日）",
            "证券期货经营机构参与股票期权交易试点指引（证监会公告[2015]1号 2015年01月09日 ）",
        ],
        "origin": [
            "第七条 本指引施行后申请募集的基金，拟参与股指期货交易的，应当在基金合同、招募说明书、产品方案等募集申报材料中列明股指期货交易方案等相关内容。",
            "第八条 基金应当在季度报告、半年度报告、年度报告等定期报告和招募说明书（更新）等文件中披露股指期货交易情况，"
            "包括投资政策、持仓情况、损益情况、风险指标等，并充分揭示股指期货交易对基金总体风险的影响以及是否符合既定的投资政策和投资目标。",
            "第八条基金应当在季度报告、半年度报告、年度报告等定期报告和招募说明书（更新）等文件中披露国债期货交易情况，"
            "包括投资政策、持仓情况、损益情况、风险指标等，并充分揭示国债期货交易对基金总体风险的影响以及是否符合既定的投资政策和投资目标。",
            "第二十一条 基金参与股票期权交易的，应当在定期信息披露文件中披露参与股票期权交易的有关情况，"
            "包括投资政策、持仓情况、损益情况、风险指标、估值方法等，并充分揭示股票期权交易对基金总体风险的影响以及是否符合既定的投资政策和投资目标。",
        ],
        "templates": [
            {
                "name": "范文",
                "content_title": "合同范文",
                "chapter": ChapterPattern.CHAPTER_FUND_INFORMATION_DISCLOSURE,
                "items": [
                    {
                        "type": TemplateCheckTypeEnum.INNER_RECOMBINATION.value,
                        "conditions": [TemplateConditional.SPECIAL_TYPE_STOCK_INDEX_DEBT_FEATURES],
                        "rules": {
                            "IRB_1": {
                                "para_pattern": PatternCollection(
                                    r"管理人[^,，。]*?报告[^,，。]*?文件中披露(?P<content>(股指期货|国债期货|股票期权)[^,，。；;]+)"
                                ),
                                "default": "股指期货、国债期货、股票期权",
                                "patterns": [
                                    {
                                        "pattern": PatternCollection(r"股指期货"),
                                        "value": "股指期货",
                                        "conditions": [TemplateConditional.SPECIAL_TYPE_STOCK_INDEX_FEATURES],
                                    },
                                    {
                                        "pattern": PatternCollection(r"国债期货"),
                                        "value": "国债期货",
                                        "conditions": [TemplateConditional.SPECIAL_TYPE_DEBT_FEATURES],
                                    },
                                    {
                                        "pattern": PatternCollection(r"股票期权"),
                                        "value": "股票期权",
                                        "conditions": [TemplateConditional.SPECIAL_TYPE_STOCK_FEATURES],
                                    },
                                ],
                            },
                            "IRB_2": {
                                "para_pattern": PatternCollection(
                                    r"管理人[^,，。]*?报告[^,，。]*?文件中披露.+揭示(?P<content>(股指期货|国债期货|股票期权).*?)基金(?:总体)?风险的影响"
                                ),
                                "default": "股指期货、国债期货、股票期权",
                                "patterns": [
                                    {
                                        "pattern": PatternCollection(r"股指期货"),
                                        "value": "股指期货",
                                        "conditions": [TemplateConditional.SPECIAL_TYPE_STOCK_INDEX_FEATURES],
                                    },
                                    {
                                        "pattern": PatternCollection(r"国债期货"),
                                        "value": "国债期货",
                                        "conditions": [TemplateConditional.SPECIAL_TYPE_DEBT_FEATURES],
                                    },
                                    {
                                        "pattern": PatternCollection(r"股票期权"),
                                        "value": "股票期权",
                                        "conditions": [TemplateConditional.SPECIAL_TYPE_STOCK_FEATURES],
                                    },
                                ],
                            },
                        },
                        "items": [
                            "基金管理人应当在基金季度报告、中期报告、年度报告等定期报告和招募说明书（更新）等文件中披露{IRB_1}交易情况，"
                            "包括投资政策、持仓情况、损益情况、风险指标等，并充分揭示{IRB_2}交易对基金总体风险的影响以及是否符合既定的投资政策和投资目标等。",
                        ],
                    },
                ],
            }
        ],
    },
    {
        "label": "template_651",
        "related_name": "基金的信息披露",
        "name": "信息披露-融资/转融通",
        "from": [
            "《公开募集证券投资基金参与转融通证券出借业务指引（试行）（证监会公告〔2019〕15号 2019年6月14日）》",
        ],
        "origin": [
            "第十五条 基金管理人应当在基金定期报告等文件中披露基金参与出借业务的情况，并就报告期内发生的重大关联交易事项做详细说明。",
        ],
        "templates": [
            {
                "name": "范文",
                "content_title": "合同范文",
                "chapter": ChapterPattern.CHAPTER_FUND_INFORMATION_DISCLOSURE,
                "items": [
                    {
                        "type": TemplateCheckTypeEnum.INNER_RECOMBINATION.value,
                        "conditions": [TemplateConditional.SPECIAL_TYPE_FINANCING_OR_RE_FINANCE],
                        "rules": {
                            "IRB_1": {
                                "para_pattern": PatternCollection(
                                    r"管理人[^,，。]*?报告[^,，。]*?文件中披露.*?(?P<content>(融资|转融通)[^,，。；;]+)"
                                ),
                                "default": "融资及转融通",
                                "patterns": [
                                    {
                                        "pattern": PatternCollection(r"融资"),
                                        "value": "融资",
                                        "conditions": [TemplateConditional.SPECIAL_TYPE_FINANCING],
                                    },
                                    {
                                        "pattern": PatternCollection(r"转融通"),
                                        "value": "转融通",
                                        "conditions": [TemplateConditional.SPECIAL_TYPE_RE_FINANCE],
                                    },
                                ],
                            },
                        },
                        "items": [
                            "管理人应当在季度报告、中期报告、年度报告等定期报告和招募说明书（更新）等文件中披露参与{IRB_1}证券出借交易的情况，"
                            "包括投资策略、业务开展情况、损益情况、风险及其管理情况等，并就报告期内本基金参与{IRB_1}证券出借业务发生的重大关联交易事项做详细的说明。",
                        ],
                    },
                ],
            }
        ],
    },
    {
        "label": "template_673",
        "schema_fields": ["基金份额上市交易的其他约定"],
        "related_name": "基金份额的上市交易",
        "name": "基金份额的上市交易-其他约定",
        "from": "",
        "origin": "",
        "templates": [
            {
                "name": "范文",
                "content_title": "合同范文",
                "chapter": ChapterPattern.CHAPTER_FUND_LISTED_LISTED_TRANSACTION,
                "rule_fields": [("上市交易所", [TemplateConditional.LISTED_TRANSACTION_YES])],
                "items": [
                    {
                        "conditions": [TemplateConditional.LISTED_TRANSACTION_YES],
                        "items": [
                            "五、上市交易的费用",
                            {
                                "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                                "rules": {"IRP_1": {"func": "get_fund_bourse_name"}},
                                "items": [
                                    "本基金上市交易的费用按照{IRP_1}的有关规定办理。",
                                ],
                            },
                            [
                                "六、在不违反法律法规并且不损害届时基金份额持有人利益的前提下，基金管理人在与基金托管人协商一致后，"
                                "可申请在其他证券交易所（含境外证券交易所）同时挂牌交易，而无需召开基金份额持有人大会审议。",
                                "六、在不违反法律法规强制性规定并履行适当程序的前提下，本基金可以申请在其他证券交易所（含境外证券交易所）上市交易，而无需召开基金份额持有人大会审议。",
                                "六、在不违反法律法规且不损害基金份额持有人利益的前提下，本基金可以申请在包括境外交易所在内的其他证券交易所上市交易，无需召开基金份额持有人大会。",
                            ],
                            {
                                "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                                "rules": {"IRP_1": {"func": "get_fund_bourse_name"}},
                                "items": [
                                    [
                                        "七、相关法律法规、中国证监会及{IRP_1}对基金上市交易的规则等相关规定内容进行调整的，"
                                        "本基金按照新规定执行，由此对基金合同进行修订的，无须召开基金份额持有人大会。",
                                        "七、相关法律法规、中国证监会、登记机构及{IRP_1}对基金上市交易的规则等相关规定内容进行调整的，"
                                        "本基金合同相应予以修改，并按照新规定执行，且此项修改无须召开基金份额持有人大会。",
                                        "七、法律法规、监管部门和登记结算机构、{IRP_1}业务规则对上市交易的规定内容进行调整的，本基金参照执行，而无需召开基金份额持有人大会审议。",
                                        "七、法律法规、监管部门和{IRP_1}对上市交易另有规定的，从其规定。",
                                    ],
                                ],
                            },
                            {
                                "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                                "rules": {"IRP_1": {"func": "get_fund_bourse_name"}},
                                "items": [
                                    "八、若{IRP_1}、中国证券登记结算有限责任公司增加了基金上市交易的新功能，基金管理人可以在履行适当的程序后增加相应功能。",
                                ],
                            },
                        ],
                    }
                ],
            }
        ],
    },
    {
        "label": "template_671",
        "related_name": "基金份额的上市交易",
        "name": "基金份额的上市交易-暂停或终止上市",
        "from": [
            "《深圳证券交易所证券投资基金上市规则（2006年02月13日 深证会[2006]3号）》",
            "《上海证券交易所证券投资基金上市规则（修订稿）（2007年08月29日 债券基金部[2007]62号）》",
        ],
        "origin": [
            "第二十一条 基金上市期间出现下列情形之一的，本所决定其暂停上市：",
            "（一）不再具备本规则第五条规定的上市条件；",
            "（二）违反法律、行政法规，中国证监会决定暂停其上市；",
            "（三）严重违反本规则的；",
            "（四）本所认为应当暂停上市的其他情形。",
            "第二十三条 基金出现下列情形之一的，本所决定其终止上市：",
            "（一）自暂停上市之日起半年内未能消除暂停上市原因的；",
            "（二）基金合同期限届满未获准续期的；",
            "（三）基金份额持有人大会决定提前终止上市；",
            "（四）基金合同约定的终止上市的其他情形；",
            "（五）本所认为应当终止上市的其它情形。",
            "第三十三条 基金上市期间出现下列情况之一时，本所将终止其上市：",
            "（一）不再具备本规则第四条规定的上市条件；",
            "（二）基金合同期限届满未获准续期的；",
            "（三）基金份额持有人大会决定提前终止上市；",
            "（四）基金合同约定的终止上市的其他情形；",
            "（五）本所认为应当终止上市的其他情形。",
        ],
        "templates": [
            {
                "name": "范文",
                "content_title": "合同范文",
                "chapter": ChapterPattern.CHAPTER_FUND_LISTED_LISTED_TRANSACTION,
                "rule_fields": [("上市交易所", [TemplateConditional.LISTED_TRANSACTION_YES])],
                "items": [
                    {
                        "conditions": [TemplateConditional.LISTED_TRANSACTION_YES],
                        "items": [
                            "三、上市交易的停复牌、暂停上市、恢复上市和终止上市",
                            {
                                "single_optional": [
                                    {
                                        "conditions": [TemplateConditional.SPECIAL_TYPE_ETF],
                                        "items": [
                                            {
                                                "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                                                "rules": {"IRP_1": {"func": "get_fund_bourse_name"}},
                                                "items": [
                                                    "基金份额在{IRP_1}的停复牌、暂停上市、恢复上市和终止上市应遵照《{IRP_1}证券投资基金上市规则》的相关规定执行。",
                                                    "当本基金发生{IRP_1}相关规定所规定的因不再具备上市条件而应当终止上市的情形时，",
                                                ],
                                            },
                                            "本基金将由交易型开放式基金变更为跟踪标的指数的非上市的开放式基金，无需召开基金份额持有人大会。"
                                            "届时，基金管理人将按照非上市的开放式基金调整相应的业务规则，并提前公告。",
                                            [
                                                "若届时本基金管理人已有以该指数作为标的指数的指数基金，则基金管理人将本着维护基金份额持有人合法权益的原则，"
                                                "履行适当的程序后与该指数基金合并或者选取其他合适的指数作为标的指数。",
                                                "若届时本基金管理人已有以该指数作为标的指数的指数增强型证券投资基金，基金管理人将本着维护基金份额持有人合法权益的原则，"
                                                "履行适当的程序后与该指数增强型证券投资基金合并或者选取其他合适的指数作为标的指数。具体情况见基金管理人届时公告。",
                                            ],
                                        ],
                                    },
                                    {
                                        "items": [
                                            {
                                                "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                                                "rules": {"IRP_1": {"func": "get_fund_bourse_name"}},
                                                "items": [
                                                    "本基金的停复牌、暂停上市、恢复上市和终止上市按照相关法律法规、中国证监会及{IRP_1}的相关规定执行。"
                                                    "当本基金发生{IRP_1}相关业务规则规定的因不再具备上市条件而应当终止上市的情形时，本基金将变更为非上市的证券投资基金，"
                                                    "无需召开基金份额持有人大会。基金变更并终止上市后，对于本基金场内份额的处理规则由基金管理人制定并按规定公告。",
                                                ],
                                            },
                                        ],
                                    },
                                ]
                            },
                        ],
                    },
                ],
            }
        ],
    },
    {
        "label": "template_679",
        "rule_type": RuleType.SCHEMA.value,
        "related_name": "释义",
        "schema_fields": ["释义"],
        "name": "释义-联接基金及其目标ETF",
        "from": "",
        "origin": "",
        "templates": [
            {
                "name": "范文",
                "content_title": "合同范文",
                "rule_fields": [("基金名称", [TemplateConditional.SPECIAL_TYPE_LINKED_FUND])],
                "chapter": ChapterPattern.CHAPTER_FUND_PARAPHRASE,
                "items": [
                    {
                        "conditions": [TemplateConditional.SPECIAL_TYPE_LINKED_FUND],
                        "items": [
                            [
                                "17、ETF联接基金：指将绝大多数基金财产投资于目标ETF，与目标ETF的投资目标类似，紧密跟踪业绩比较基准，追求跟踪偏离度和跟踪误差最小化，采用（契约型）开放式运作方式的基金；",
                                "17、ETF联接基金：指将绝大多数基金财产投资于目标ETF，与目标ETF的投资目标类似，紧密跟踪业绩比较基准，追求跟踪偏离度和跟踪误差最小化，采用开放式运作方式的基金；",
                            ],
                            {
                                "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                                "rules": {"IRP_1": {"func": "get_fund_name"}},
                                "items": [
                                    [
                                        "18、目标ETF：指另一获中国证监会注册的交易型开放式证券投资基金（以下简称“ETF”），该ETF和本基金所跟踪的标的相同，"
                                        "并且该ETF的投资目标和本基金的投资目标类似，本基金主要投资于该ETF以求达到投资目标。本基金以{IRP_1}为目标ETF；",
                                        "18、目标ETF：指另一获中国证监会注册的交易型开放式证券投资基金，该ETF和本基金所跟踪的标的相同，"
                                        "并且该ETF的投资目标和本基金的投资目标类似，本基金主要投资于该ETF以求达到投资目标。本基金以{IRP_1}为目标ETF；",
                                        "18、目标ETF：{IRP_1}；",
                                    ],
                                ],
                            },
                        ],
                    }
                ],
            }
        ],
    },
    {
        "label": "template_713",
        "schema_fields": ["前言"],
        "related_name": "前言",
        "name": "前言-当事人承诺事项",
        "from": "《中华人民共和国证券投资基金法（主席令第23号 2015年4月24日修订）》",
        "origin": [
            "第五十条 公开募集基金，应当经国务院证券监督管理机构注册。未经注册，不得公开或者变相公开募集基金。",
            "第九条 基金管理人、基金托管人管理、运用基金财产，基金服务机构从事基金服务活动，应当恪尽职守，履行诚实信用、谨慎勤勉的义务。 "
            "基金管理人运用基金财产进行证券投资，应当遵守审慎经营规则，制定科学合理的投资策略和风险管理制度，有效防范和控制风险。",
            "第十七条 基金销售机构应当按照中国证监会的规定了解投资人信息，坚持投资人利益优先和风险匹配原则，根据投资人的风险承担能力销售不同风险等级的产品，"
            "把合适的基金产品销售给合适的投资人。",
            "基金销售机构应当加强投资者教育，引导投资人充分认识基金产品的风险收益特征。"
            "投资人购入基金前，基金销售机构应当提示投资人阅读基金合同、招募说明书、基金产品资料概要，提供有效途径供投资人查询，并以显著、清晰的方式向投资人揭示投资风险。",
        ],
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "三、xxxxxx证券投资基金由基金管理人依照《基金法》、基金合同及其他有关规定募集，并经中国证券监督管理委员会(以下简称“中国证监会”)注册。",
            "A中国证监会对本基金募集的注册，并不表明其对本基金的投资价值和市场前景做出实质性判断或保证，也不表明投资于本基金没有风险。",
            "基金管理人依照恪尽职守、诚实信用、谨慎勤勉的原则管理和运用基金财产，但不保证投资于本基金一定盈利，也不保证最低收益。",
            "B投资者应当认真阅读基金招募说明书、基金合同等信息披露文件，自主判断基金的投资价值，自主做出投资决策，自行承担投资风险。",
        ],
        "templates": [
            {
                "name": "法规",
                "content_title": "法规条款",
                "rule_fields": ["基金名称"],
                "chapter": ChapterPattern.CHAPTER_FUND_FOREWORD,
                "items": [
                    {
                        "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                        "rules": {"IRP_1": {"func": "get_fund_name"}},
                        "items": [
                            "三、{IRP_1}由基金管理人依照《基金法》、基金合同及其他有关规定募集，并经中国证券监督管理委员会(以下简称“中国证监会”)注册。",
                        ],
                    },
                    [
                        "中国证监会对本基金募集的注册，并不表明其对本基金的投资价值和市场前景做出实质性判断或保证，也不表明投资于本基金没有风险。",
                        "中国证监会对本基金募集的注册，并不表明其对本基金的价值和收益作出实质性判断或保证，也不表明投资于本基金没有风险。",
                    ],
                    "基金管理人依照恪尽职守、诚实信用、谨慎勤勉的原则管理和运用基金财产，但不保证投资于本基金一定盈利，也不保证最低收益。",
                    {
                        "type": TemplateCheckTypeEnum.INNER_RECOMBINATION.value,
                        "rules": {
                            "IRB_2": {
                                "para_pattern": PatternCollection(r"阅读(?P<content>.*)等(信息披露|销售)文件"),
                                "default": "基金招募说明书、基金合同、基金产品资料概要",
                                "patterns": [
                                    {
                                        "pattern": PatternCollection(r"基金招募说明书"),
                                        "value": "基金招募说明书",
                                    },
                                    {
                                        "pattern": PatternCollection(r"基金合同"),
                                        "value": "基金合同",
                                    },
                                    {
                                        "pattern": PatternCollection(r"基金产品资料概要"),
                                        "required": False,
                                        "value": "基金产品资料概要",
                                    },
                                ],
                            },
                        },
                        "items": [
                            [
                                "投资者应当认真阅读{IRB_2}等信息披露文件，自主判断基金的投资价值，自主做出投资决策，自行承担投资风险。",
                                "作出投资决定前，投资者应当认真阅读{IRB_2}等信息披露文件和销售文件，自主判断基金的投资价值，自主做出投资决策，自行承担投资风险。",
                            ],
                        ],
                    },
                ],
            },
            {
                "name": "范文",
                "content_title": "合同范文",
                "rule_fields": ["基金名称"],
                "chapter": ChapterPattern.CHAPTER_FUND_FOREWORD,
                "items": [
                    {
                        "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                        "rules": {"IRP_1": {"func": "get_fund_name"}},
                        "items": [
                            "三、{IRP_1}由基金管理人依照《基金法》、基金合同及其他有关规定募集，并经中国证券监督管理委员会(以下简称“中国证监会”)注册。",
                        ],
                    },
                    [
                        "中国证监会对本基金募集的注册，并不表明其对本基金的投资价值和市场前景做出实质性判断或保证，也不表明投资于本基金没有风险。",
                        "中国证监会对本基金募集的注册，并不表明其对本基金的价值和收益作出实质性判断或保证，也不表明投资于本基金没有风险。",
                    ],
                    "基金管理人依照恪尽职守、诚实信用、谨慎勤勉的原则管理和运用基金财产，但不保证投资于本基金一定盈利，也不保证最低收益。",
                    {
                        "type": TemplateCheckTypeEnum.INNER_RECOMBINATION.value,
                        "rules": {
                            "IRB_2": {
                                "para_pattern": PatternCollection(r"阅读(?P<content>.*)等(信息披露|销售)文件"),
                                "default": "基金招募说明书、基金合同、基金产品资料概要",
                                "patterns": [
                                    {
                                        "pattern": PatternCollection(r"基金招募说明书"),
                                        "value": "基金招募说明书",
                                    },
                                    {
                                        "pattern": PatternCollection(r"基金合同"),
                                        "value": "基金合同",
                                    },
                                    {
                                        "pattern": PatternCollection(r"基金产品资料概要"),
                                        "required": False,
                                        "value": "基金产品资料概要",
                                    },
                                ],
                            },
                        },
                        "items": [
                            [
                                "投资者应当认真阅读{IRB_2}等信息披露文件，自主判断基金的投资价值，自主做出投资决策，自行承担投资风险。",
                                "作出投资决定前，投资者应当认真阅读{IRB_2}等信息披露文件和销售文件，自主判断基金的投资价值，自主做出投资决策，自行承担投资风险。",
                            ],
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_722",
        "schema_fields": ["释义"],
        "related_name": "释义",
        "name": "释义-LOF的登记结算和基金账户",
        "from": "",
        "origin": "",
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_FOREWORD,
                "rule_fields": [("上市交易所", [TemplateConditional.SPECIAL_TYPE_LOF])],
                "items": [
                    {
                        "conditions": [TemplateConditional.SPECIAL_TYPE_LOF],
                        "items": [
                            {
                                "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                                "rules": {"IRP_1": {"func": "get_fund_bourse_name"}},
                                "items": [
                                    "27、场外：指通过{IRP_1}外的销售机构进行基金份额认购、申购和赎回等业务的场所。通过该等场所办理基金份额的认购、"
                                    "申购、赎回也称为场外认购、场外申购、场外赎回；",
                                    {
                                        "single_optional": [
                                            {
                                                "conditions": [TemplateConditional.STOCK_BOURSE_SH],
                                                "items": [
                                                    "28、场内：指通过{IRP_1}内具有基金销售业务资格的会员单位通过{IRP_1}开放式基金销售系统进行基金份额认购、申购、赎回以及上市交易的场所。通过该等场所办理基金份额的认购、申购、赎回也称为场内认购、场内申购、场内赎回；",
                                                ],
                                            },
                                            {
                                                "conditions": [TemplateConditional.STOCK_BOURSE_SZ],
                                                "items": [
                                                    "28、场内：指通过{IRP_1}具有相应业务资格的会员单位利用交易所开放式基金交易系统办理基金份额认购、申购、赎回和上市交易的场所。通过该等场所办理基金份额的认购、申购、赎回也称为场内认购、场内申购、场内赎回；",
                                                ],
                                            },
                                        ],
                                    },
                                    "29、登记业务：指基金登记、存管、过户、清算和结算业务，具体内容包括投资人开放式基金账户和/或{IRP_1}的建立和管理、"
                                    "基金份额登记、基金销售业务的确认、清算和结算、代理发放红利、建立并保管基金份额持有人名册和办理非交易过户等；",
                                ],
                            },
                            "30、开放式基金账户：指投资人通过场外销售机构在中国证券登记结算有限责任公司注册的开放式基金账户、用于记录其持有的、"
                            "基金管理人所管理的基金份额余额及其变动情况的账户；",
                            {
                                "single_optional": [
                                    {
                                        "conditions": [TemplateConditional.STOCK_BOURSE_SH],
                                        "items": [
                                            "31、上海证券账户：指在中国证券登记结算有限责任公司上海分公司开设的上海证券交易所人民币普通股票账户（即A股账户）或证券投资基金账户；",
                                        ],
                                    },
                                    {
                                        "conditions": [TemplateConditional.STOCK_BOURSE_SZ],
                                        "items": [
                                            "31、深圳证券账户：指在中国证券登记结算有限责任公司深圳分公司开设的深圳证券交易所人民币普通股票账户（即A股账户）或证券投资基金账户；",
                                        ],
                                    },
                                ],
                            },
                            "32、登记结算系统：指中国证券登记结算有限责任公司开放式基金登记结算系统。投资人通过场外基金销售机构认购、申购所得的基金份额登记在本系统下；",
                            {
                                "single_optional": [
                                    {
                                        "conditions": [TemplateConditional.STOCK_BOURSE_SH],
                                        "items": [
                                            "33、证券登记结算系统/证券登记系统：指中国证券登记结算有限责任公司上海分公司证券登记结算系统。"
                                            "投资人通过场内会员单位认购、申购或买入所得的基金份额登记在本系统下；",
                                        ],
                                    },
                                    {
                                        "conditions": [TemplateConditional.STOCK_BOURSE_SZ],
                                        "items": [
                                            "33、证券登记结算系统/证券登记系统：指中国证券登记结算有限责任公司深圳分公司证券登记结算系统。"
                                            "投资人通过场内会员单位认购、申购或买入所得的基金份额登记在本系统下；",
                                        ],
                                    },
                                ],
                            },
                            "34、场外份额：指登记在登记结算系统下的基金份额；",
                            "35、场内份额：指登记在证券登记系统下的基金份额；",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_662",
        "schema_fields": ["违约责任"],
        "related_name": "违约责任",
        "name": "合同违约责任",
        "from": "",
        "origin": [
            "一、基金管理人、基金托管人在履行各自职责的过程中，违反《基金法》等法律法规的规定或者《基金合同》约定，"
            "给基金财产或者基金份额持有人造成损害的，应当分别对各自的行为依法承担赔偿责任；"
            "因共同行为给基金财产或者基金份额持有人造成损害的，应当承担连带赔偿责任，对损失的赔偿，仅限于直接损失。",
            "二、在发生一方或多方违约的情况下，在最大限度地保护基金份额持有人利益的前提下，《基金合同》能够继续履行的应当继续履行。"
            "非违约方当事人在职责范围内有义务及时采取必要的措施，防止损失的扩大。没有采取适当措施致使损失进一步扩大的，"
            "不得就扩大的损失要求赔偿。非违约方因防止损失扩大而支出的合理费用由违约方承担。",
            "三、由于基金管理人、基金托管人不可控制的因素导致业务出现差错，基金管理人和基金托管人虽然已经采取必要、适当、合理的措施进行检查，"
            "但是未能发现错误的，由此造成基金财产或投资人损失，基金管理人和基金托管人免除赔偿责任。"
            "但是基金管理人和基金托管人应积极采取必要的措施消除由此造成的影响。",
        ],
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "一、基金管理人、基金托管人在履行各自职责的过程中，违反《基金法》等法律法规的规定或者《基金合同》约定，给基金财产或者基金份额持有人造成损害的，应当分别对各自的行为依法承担赔偿责任；因共同行为给基金财产或者基金份额持有人造成损害的，应当承担连带赔偿责任，对损失的赔偿，仅限于直接损失。",
            "二、在发生一方或多方违约的情况下，在最大限度地保护基金份额持有人利益的前提下，《基金合同》能够继续履行的应当继续履行。非违约方当事人在职责范围内有义务及时采取必要的措施，防止损失的扩大。没有采取适当措施致使损失进一步扩大的，不得就扩大的损失要求赔偿。非违约方因防止损失扩大而支出的合理费用由违约方承担。",
            "三、由于基金管理人、基金托管人不可控制的因素导致业务出现差错，基金管理人和基金托管人虽然已经采取必要、适当、合理的措施进行检查，但是未能发现错误的，由此造成基金财产或投资人损失，基金管理人和基金托管人免除赔偿责任。但是基金管理人和基金托管人应积极采取必要的措施消除由此造成的影响。",
        ],
        "templates": [
            {
                "name": "法规",
                "content_title": "法规条款",
                "chapter": ChapterPattern.CHAPTER_FUND_BREAK_CONTACT_DUTY,
                "items": [
                    "一、基金管理人、基金托管人在履行各自职责的过程中，违反《基金法》等法律法规的规定或者《基金合同》约定，"
                    "给基金财产或者基金份额持有人造成损害的，应当分别对各自的行为依法承担赔偿责任；"
                    "因共同行为给基金财产或者基金份额持有人造成损害的，应当承担连带赔偿责任，对损失的赔偿，仅限于直接损失。",
                    "二、在发生一方或多方违约的情况下，在最大限度地保护基金份额持有人利益的前提下，《基金合同》能够继续履行的应当继续履行。"
                    "非违约方当事人在职责范围内有义务及时采取必要的措施，防止损失的扩大。没有采取适当措施致使损失进一步扩大的，"
                    "不得就扩大的损失要求赔偿。非违约方因防止损失扩大而支出的合理费用由违约方承担。",
                    "三、由于基金管理人、基金托管人不可控制的因素导致业务出现差错，基金管理人和基金托管人虽然已经采取必要、适当、合理的措施进行检查，"
                    "但是未能发现错误的，由此造成基金财产或投资人损失，基金管理人和基金托管人免除赔偿责任。"
                    "但是基金管理人和基金托管人应积极采取必要的措施消除由此造成的影响。",
                ],
            },
            {
                "name": "范文",
                "content_title": "合同范文",
                "chapter": ChapterPattern.CHAPTER_FUND_BREAK_CONTACT_DUTY,
                "items": [
                    "一、基金管理人、基金托管人在履行各自职责的过程中，违反《基金法》等法律法规的规定或者《基金合同》约定，"
                    "给基金财产或者基金份额持有人造成损害的，应当分别对各自的行为依法承担赔偿责任；因共同行为给基金财产或者基金份额持有人造成损害的，"
                    "应当承担连带赔偿责任，对损失的赔偿，仅限于直接损失。但是发生下列情况的，当事人免责：",
                    {
                        "type": TemplateCheckTypeEnum.RECOMBINATION.value,
                        "patterns": [
                            PatternCollection(r"不可抗力"),
                            PatternCollection(r"((?:作为|不作为)[或、]?){1,2}而造成的损失"),
                            PatternCollection(r"((?:行使|不行使)[或、]?){1,2}其?投资权"),
                        ],
                        "serial_num_pattern": P_PARA_PREFIX_NUM,
                        "default_prefix_type": "{num}",
                        "items": [
                            "不可抗力；",
                            "基金管理人和/或基金托管人按照届时有效的法律法规或中国证监会的规定作为或不作为而造成的损失等；",
                            "基金管理人由于按照《基金合同》规定行使或不行使其投资权而造成的损失等。",
                        ],
                    },
                    "三、由于基金管理人、基金托管人不可控制的因素导致业务出现差错，基金管理人和基金托管人虽然已经采取必要、适当、合理的措施进行检查，"
                    "但是未能发现错误的，由此造成基金财产或投资人损失，基金管理人和基金托管人免除赔偿责任。但是基金管理人和基金托管人应积极采取必要的措施减轻或消除由此造成的影响。",
                ],
            },
        ],
    },
    {
        "label": "template_747",
        "schema_fields": ["投资限制"],
        "related_name": "基金的投资",
        "name": "投资限制-转融通",
        "from": "公开募集证券投资基金参与转融通证券出借业务指引（试行）（证监会公告〔2019〕15号 2019年6月14日）",
        "origin": [
            "第六条 处于封闭期的基金出借证券资产不得超过基金资产净值的50%，出借到期日不得超过封闭期到期日，中国证监会认可的特殊情形除外。",
            "第七条 开放式股票指数基金及相关联接基金参与出借业务应当符合以下要求：",
            "（一）出借证券资产不得超过基金资产净值的30%，出借期限在10个交易日以上的出借证券应纳入《公开募集开放式证券投资基金流动性风险管理规定》所述流动性受限证券的范围；",
            "（二）交易型开放式指数基金参与出借业务的单只证券不得超过基金持有该证券总量的30%；其他开放式股票指数基金、交易型开放式指数基金的联接基金参与出借业务的单只证券不得超过基金持有该证券总量的50%；",
            "（三）最近6个月内日均基金资产净值不得低于2亿元；",
            "（四）证券出借的平均剩余期限不得超过30天，平均剩余期限按照市值加权平均计算。",
            "第八条 因证券市场波动、上市公司合并、基金规模变动等基金管理人之外的因素致使基金投资不符合本公告第六条、第七条规定的，基金管理人不得新增出借业务。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_INVEST_SCOPE_INVESTMENT_RESTRICTION,
                "items": [
                    {
                        "conditions": [TemplateConditional.SPECIAL_TYPE_RE_FINANCE],
                        "items": [
                            {
                                "single_optional": [
                                    {
                                        "conditions": [
                                            TemplateConditional.SIDE_TYPE_REGULAR_OPEN_NO,
                                            TemplateConditional.SIDE_TYPE_CLOSE_NO,
                                        ],
                                        "items": [
                                            {
                                                "conditions": [TemplateConditional.SIDE_TYPE_OPEN],
                                                "items": [
                                                    "本基金参与转融通证券出借业务，应当符合下列投资限制",
                                                    "①出借证券资产不得超过基金资产净值的0%，出借期限在10个交易日以上的出借证券应纳入《流动性风险管理规定》所述流动性受限证券的范围；",
                                                    {
                                                        "conditions": [TemplateConditional.SPECIAL_TYPE_ETF],
                                                        "items": [
                                                            "②本基金参与出借业务的单只证券不得超过基金持有该证券总量的30%；",
                                                        ],
                                                    },
                                                    {
                                                        "conditions": [TemplateConditional.SPECIAL_TYPE_ETF_NO],
                                                        "items": [
                                                            "②本基金参与出借业务的单只证券不得超过基金持有该证券总量的50%；",
                                                        ],
                                                    },
                                                    "③最近6个月内日均基金资产净值不得低于2亿元；",
                                                    "④证券出借的平均剩余期限不得超过30天，平均剩余期限按照市值加权平均计算；",
                                                    {
                                                        "type": TemplateCheckTypeEnum.INNER_REFER.value,
                                                        "rules": {
                                                            "IRF_1": {
                                                                "default": "x",
                                                                "patterns": [
                                                                    PatternCollection(
                                                                        r"转融通证券出借业务.*?(投资限制|要求)"
                                                                    )
                                                                ],
                                                            },
                                                        },
                                                        "items": [
                                                            [
                                                                "因证券市场波动、上市公司合并、基金规模变动等基金管理人之外的因素致使基金投资不符合上述规定的，基金管理人不得新增出借业务；",
                                                                "因证券市场波动、上市公司合并、基金规模变动等基金管理人之外的因素致使基金投资不符合第{IRF_1}条规定的，基金管理人不得新增出借业务；",
                                                            ],
                                                        ],
                                                    },
                                                ],
                                            },
                                        ],
                                    },
                                    {
                                        "items": [
                                            "封闭期内，本基金参与转融通证券出借业务将遵守下列要求：出借证券资产不得超过基金资产净值的50%，出借到期日不得超过封闭期到期日，中国证监会认可的特殊情形除外；",
                                            {
                                                "type": TemplateCheckTypeEnum.INNER_REFER.value,
                                                "rules": {
                                                    "IRF_1": {
                                                        "default": "x",
                                                        "patterns": [
                                                            PatternCollection(
                                                                r"转融通证券出借业务.*?证券资产不得超过基金资产净值"
                                                            )
                                                        ],
                                                    },
                                                },
                                                "items": [
                                                    [
                                                        "因证券市场波动、上市公司合并、基金规模变动等基金管理人之外的因素致使基金投资不符合上述规定的，基金管理人不得新增转融通证券出借业务。",
                                                        "因证券市场波动、上市公司合并、基金规模变动等基金管理人之外的因素致使基金投资不符合第{IRF_1}条规定的，"
                                                        "基金管理人不得新增转融通证券出借业务。",
                                                    ],
                                                ],
                                            },
                                        ]
                                    },
                                ]
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_620",
        "schema_fields": ["管理人的权利"],
        "related_name": "基金合同当事人及权利义务",
        "name": "管理人的权利",
        "from": "",
        "origin": [
            "（二）基金管理人的权利与义务",
            "1、根据《基金法》、《运作办法》及其他有关规定，基金管理人的权利包括但不限于：",
            "（1）依法募集资金；",
            "（2）自《基金合同》生效之日起，根据法律法规和《基金合同》独立运用并管理基金财产；",
            "（3）依照《基金合同》收取基金管理费以及法律法规规定或中国证监会批准的其他费用；",
            "（4）销售基金份额；",
            "（5）按照规定召集基金份额持有人大会；",
            "（6）依据《基金合同》及有关法律规定监督基金托管人，如认为基金托管人违反了《基金合同》及国家有关法律规定，应呈报中国证监会和其他监管部门，并采取必要措施保护基金投资者的利益；",
            "（7）在基金托管人更换时，提名新的基金托管人；",
            "（8）选择、更换基金销售机构，对基金销售机构的相关行为进行监督和处理；",
            "（9）担任或委托其他符合条件的机构担任基金登记机构办理基金登记业务并获得《基金合同》规定的费用；",
            "（10）依据《基金合同》及有关法律规定决定基金收益的分配方案；",
            "（11）在《基金合同》约定的范围内，拒绝或暂停受理申购与赎回申请；",
            "（12）依照法律法规为基金的利益对被投资公司行使股东权利，为基金的利益行使因基金财产投资于证券所产生的权利；",
            "（13）在法律法规允许的前提下，为基金的利益依法为基金进行融资；",
            "（14）以基金管理人的名义，代表基金份额持有人的利益行使诉讼权利或者实施其他法律行为；",
            "（15）选择、更换律师事务所、会计师事务所、证券经纪商或其他为基金提供服务的外部机构；",
            "（16）在符合有关法律、法规的前提下，制订和调整有关基金认购、申购、赎回、转换和非交易过户的业务规则；",
            "（17）法律法规及中国证监会规定的和《基金合同》约定的其他权利。",
        ],
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "（二）基金管理人的权利与义务",
            "1、根据《基金法》、《运作办法》及其他有关规定，基金管理人的权利包括但不限于：",
            "（1）依法募集资金；",
            "（2）自《基金合同》生效之日起，根据法律法规和《基金合同》独立运用并管理基金财产；",
            "（3）依照《基金合同》收取基金管理费以及法律法规规定或中国证监会批准的其他费用；",
            "（4）销售基金份额；",
            "（5）按照规定召集基金份额持有人大会；",
            "（6）依据《基金合同》及有关法律规定监督基金托管人，如认为基金托管人违反了《基金合同》及国家有关法律规定，应呈报中国证监会和其他监管部门，并采取必要措施保护基金投资者的利益；",
            "（7）在基金托管人更换时，提名新的基金托管人；",
            "（8）选择、更换基金销售机构，对基金销售机构的相关行为进行监督和处理； ",
            "（9）担任或委托其他符合条件的机构担任基金登记机构办理基金登记业务并获得《基金合同》规定的费用；",
            "（10）依据《基金合同》及有关法律规定决定基金收益的分配方案；",
            "（11）在《基金合同》约定的范围内，拒绝或暂停受理申购与赎回申请； ",
            "（12）依照法律法规为基金的利益对被投资公司行使股东权利，为基金的利益行使因基金财产投资于证券所产生的权利；",
            "（13）在法律法规允许的前提下，为基金的利益依法为基金进行融资； ",
            "（14）以基金管理人的名义，代表基金份额持有人的利益行使诉讼权利或者实施其他法律行为；",
            "（15）选择、更换律师事务所、会计师事务所、证券经纪商或其他为基金提供服务的外部机构；",
            "（16）在符合有关法律、法规的前提下，制订和调整有关基金认购、申购、赎回、转换和非交易过户的业务规则；",
            "（17）法律法规及中国证监会规定的和《基金合同》约定的其他权利。",
        ],
        "templates": [
            {
                "name": "法规",
                "content_title": "法规条款",
                "chapter": ChapterPattern.CHAPTER_FUND_RIGHT_OBLIGATION_MANAGER_DUTY,
                "items": [
                    "（二）基金管理人的权利与义务",
                    "1、根据《基金法》、《运作办法》及其他有关规定，基金管理人的权利包括但不限于：",
                    "（1）依法募集资金；",
                    "（2）自《基金合同》生效之日起，根据法律法规和《基金合同》独立运用并管理基金财产；",
                    "（3）依照《基金合同》收取基金管理费以及法律法规规定或中国证监会批准的其他费用；",
                    "（4）销售基金份额；",
                    "（5）按照规定召集基金份额持有人大会；",
                    "（6）依据《基金合同》及有关法律规定监督基金托管人，如认为基金托管人违反了《基金合同》及国家有关法律规定，应呈报中国证监会和其他监管部门，并采取必要措施保护基金投资者的利益；",
                    "（7）在基金托管人更换时，提名新的基金托管人；",
                    "（8）选择、更换基金销售机构，对基金销售机构的相关行为进行监督和处理；",
                    "（9）担任或委托其他符合条件的机构担任基金登记机构办理基金登记业务并获得《基金合同》规定的费用；",
                    "（10）依据《基金合同》及有关法律规定决定基金收益的分配方案；",
                    "（11）在《基金合同》约定的范围内，拒绝或暂停受理申购与赎回申请；",
                    "（12）依照法律法规为基金的利益对被投资公司行使股东权利，为基金的利益行使因基金财产投资于证券所产生的权利；",
                    "（13）在法律法规允许的前提下，为基金的利益依法为基金进行融资；",
                    "（14）以基金管理人的名义，代表基金份额持有人的利益行使诉讼权利或者实施其他法律行为；",
                    "（15）选择、更换律师事务所、会计师事务所、证券经纪商或其他为基金提供服务的外部机构；",
                    "（16）在符合有关法律、法规的前提下，制订和调整有关基金认购、申购、赎回、转换和非交易过户的业务规则；",
                    "（17）法律法规及中国证监会规定的和《基金合同》约定的其他权利。",
                ],
            },
            {
                "name": "范文",
                "content_title": "合同范文",
                "chapter": ChapterPattern.CHAPTER_FUND_RIGHT_OBLIGATION_MANAGER_DUTY,
                "min_ratio": 0.3,
                "items": [
                    "（二）基金管理人的权利与义务",
                    "（1）依法募集资金，办理基金份额的发售和登记事宜；",
                    "（11）在《基金合同》约定的范围内，拒绝或暂停受理申购、赎回与转换申请；",
                    [
                        "（13）在法律法规允许的前提下，为基金的利益依法进行融资及转融通证券出借业务;",
                        "（13）在法律法规允许的前提下，为基金的利益依法进行融资、融券及转融通证券出借业务；",
                    ],
                    [
                        "（15）选择、更换律师事务所、会计师事务所、证券/期货经纪商或其他为基金提供服务的外部机构;",
                        "（15）选择、更换律师事务所、会计师事务所、证券、期货经纪商或其他为基金提供服务的外部机构;",
                        "（15）选择、更换律师事务所、会计师事务所、证券经纪商、期货经纪商或其他为基金提供服务的外部机构;",
                    ],
                    {
                        "type": TemplateCheckTypeEnum.INNER_RECOMBINATION.value,
                        "rules": {
                            "IR_1": {
                                "para_pattern": PatternCollection(r"(?:制订|调整)有关基金(?P<content>.*)业务的?规则"),
                                "default": "",
                                "patterns": [
                                    {
                                        "pattern": PatternCollection(r"转换"),
                                        "value": "转换",
                                        "conditions": [TemplateConditional.DISCLOSURE_FUND_SUBSCRIPTION_CONVERT],
                                    },
                                    {
                                        "pattern": PatternCollection(r"定期定额投资"),
                                        "value": "定期定额投资",
                                        "conditions": [TemplateConditional.DISCLOSURE_FUND_SUBSCRIPTION_PERIOD_INVEST],
                                    },
                                    {
                                        "pattern": PatternCollection(r"转托管"),
                                        "value": "转托管",
                                        "conditions": [
                                            TemplateConditional.DISCLOSURE_FUND_SUBSCRIPTION_TRANSFER_CUSTODY
                                        ],
                                    },
                                    {
                                        "pattern": PatternCollection(r"非交易过户"),
                                        "value": "非交易过户",
                                        "conditions": [
                                            TemplateConditional.DISCLOSURE_FUND_SUBSCRIPTION_NON_TRANSACTION_TRANSFER
                                        ],
                                    },
                                ],
                            },
                        },
                        "items": [
                            "（16）在符合有关法律、法规的前提下，制订和调整有关基金认购、申购、赎回、{IR_1}的业务规则；"
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_627",
        "schema_fields": ["基金的份额登记业务", "基金登记业务办理机构"],
        "related_name": "基金份额的登记",
        "name": "份额登记-一般规定和登记机构",
        "from": "公开募集证券投资基金销售机构监督管理办法（证监会令第175号 2020年08月28日）",
        "origin": [
            "第四十一条 基金管理人可以依照中国证监会的规定委托基金份额登记机构办理基金份额登记业务。基金份额登记机构应当确保基金份额的登记、存管和结算业务处理安全、准确、及时、高效，其主要职责包括：",
            "（一）建立并管理投资人基金份额账户；",
            "（二）负责基金份额的登记；",
            "（三）基金交易确认；",
            "（四）代理发放红利；",
            "（五）建立并保管基金份额持有人名册；",
            "（六）服务协议约定的其他职责；",
            "（七）中国证监会规定的其他职责。",
            "基金管理人变更基金份额登记机构的，应当在变更完成10个工作日内向中国证监会报告。",
        ],
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "一、基金的份额登记业务",
            "本基金的登记业务指本基金登记、存管、过户、清算和结算业务，具体内容包括投资人基金账户的建立和管理、基金份额登记、基金销售业务的确认、清算和结算、代理发放红利、建立并保管基金份额持有人名册和办理非交易过户等。",
            "二、基金登记业务办理机构",
            "本基金的登记业务由基金管理人或基金管理人委托的其他符合条件的机构办理。基金管理人委托其他机构办理本基金登记业务的，应与代理人签订委托代理协议，以明确基金管理人和代理机构在投资者基金账户管理、基金份额登记、清算及基金交易确认、发放红利、建立并保管基金份额持有人名册等事宜中的权利和义务，保护基金份额持有人的合法权益。",
        ],
        "templates": [
            {
                "name": "法规",
                "content_title": "法规条款",
                "chapter": ChapterPattern.CHAPTER_FUND_REGISTER_PORTION,
                "items": [
                    {
                        # 非ETF且非LOF
                        "conditions": [
                            TemplateConditional.SPECIAL_TYPE_ETF_NO,
                            TemplateConditional.SPECIAL_TYPE_LOF_NO,
                        ],
                        "items": [
                            "一、基金的份额登记业务",
                            "本基金的登记业务指本基金登记、存管、过户、清算和结算业务，具体内容包括投资人基金账户的建立和管理、基金份额登记、基金销售业务的确认、"
                            "清算和结算、代理发放红利、建立并保管基金份额持有人名册和办理非交易过户等。",
                        ],
                    },
                    {
                        "conditions": [TemplateConditional.LISTED_TRANSACTION_NO],
                        "items": [
                            "二、基金登记业务办理机构",
                            "本基金的登记业务由基金管理人或基金管理人委托的其他符合条件的机构办理。基金管理人委托其他机构办理本基金登记业务的，应与代理人签订委托代理协议，"
                            "以明确基金管理人和代理机构在投资者基金账户管理、基金份额登记、清算及基金交易确认、发放红利、建立并保管基金份额持有人名册等事宜中的权利和义务，保护基金份额持有人的合法权益。",
                        ],
                    },
                ],
            },
            {
                "name": "范文",
                "content_title": "合同范文",
                "rule_fields": [("上市交易所", [TemplateConditional.SPECIAL_TYPE_ETF_LOF_TRANSACTION_YES])],
                "chapter": ChapterPattern.CHAPTER_FUND_REGISTER_PORTION,
                "items": [
                    {
                        "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                        "rules": {"IRP_1": {"func": "get_fund_settlement_name"}},
                        "items": [
                            {
                                "single_optional": [
                                    {
                                        "conditions": [TemplateConditional.SPECIAL_TYPE_ETF],
                                        "items": [
                                            "一、基金份额的登记业务",
                                            "本基金的登记业务指本基金登记、存管、过户、清算和结算业务，具体内容包括投资人相关账户的建立和管理、基金份额登记、基金销售业务的确认、"
                                            "基金交易的确认、清算和结算、代理发放红利、建立并保管基金份额持有人名册和办理非交易过户等。",
                                        ],
                                    },
                                    {
                                        "conditions": [TemplateConditional.SPECIAL_TYPE_LOF],
                                        "items": [
                                            "一、基金份额的登记业务",
                                            [
                                                "本基金的登记业务指本基金登记、存管、过户、清算和结算业务，具体内容包括投资人开放式基金账户/{IRP_1}的建立和管理、基金份额登记、"
                                                "基金销售业务的确认、清算和结算、代理发放红利、建立并保管基金份额持有人名册和办理非交易过户等。",
                                                "本基金的登记业务指本基金登记、存管、过户、清算和结算业务，具体内容包括投资人相关账户的建立和管理、基金份额登记、基金销售业务的确认、"
                                                "清算和结算、代理发放红利、建立并保管基金份额持有人名册和办理非交易过户等。",
                                            ],
                                        ],
                                    },
                                ],
                            },
                            "二、基金登记业务办理机构",
                            {
                                "single_optional": [
                                    {
                                        "conditions": [TemplateConditional.LISTED_TRANSACTION_NO],
                                        "items": [
                                            "本基金的登记业务由基金管理人或基金管理人委托的其他符合条件的机构负责办理。基金管理人委托其他机构代为办理本基金登记业务的，应与有关机构签订委托代理协议，"
                                            "以明确基金管理人和代理机构在登记业务中的权利义务，保护基金份额持有人的合法权益。",
                                        ],
                                    },
                                    {
                                        "conditions": [
                                            TemplateConditional.SPECIAL_TYPE_LOF_NO,
                                            TemplateConditional.LISTED_TRANSACTION_YES,
                                        ],
                                        "items": [
                                            [
                                                (
                                                    "本基金的登记业务由基金管理人或基金管理人委托的其他符合条件的机构办理。基金管理人委托其他机构代为办理本基金登记业务的，"
                                                    "应与有关机构签订委托代理协议，以明确基金管理人和代理机构在登记业务中的权利义务，保护基金份额持有人的合法权益。"
                                                    "本基金的登记业务由中国证券登记结算有限责任公司负责办理。"
                                                ),
                                                (
                                                    "本基金的登记业务由基金管理人或基金管理人委托的其他符合条件的机构办理。基金管理人委托其他机构办理本基金登记业务的，"
                                                    "应与代理人签订委托代理协议，以明确基金管理人和代理机构在投资者基金账户/{IRP_1}、基金份额登记、清算及基金交易确认、"
                                                    "发放红利、建立并保管基金份额持有人名册等事宜中的权利和义务，保护基金份额持有人的合法权益。本基金的登记业务由中国证券登记结算有限责任公司负责办理。"
                                                ),
                                                (
                                                    "本基金的登记业务由基金管理人或基金管理人委托的其他符合条件的机构办理。基金管理人委托其他机构办理本基金登记业务的，"
                                                    "应与代理人签订委托代理协议，以明确基金管理人和代理机构在投资者相关账户管理、基金份额登记、清算及基金交易确认、发放红利、"
                                                    "建立并保管基金份额持有人名册等事宜中的权利和义务，保护基金份额持有人的合法权益。本基金的登记业务由中国证券登记结算有限责任公司负责办理。"
                                                ),
                                            ],
                                        ],
                                    },
                                    {
                                        "conditions": [
                                            TemplateConditional.SPECIAL_TYPE_LOF,
                                            TemplateConditional.LISTED_TRANSACTION_YES,
                                        ],
                                        "items": [
                                            [
                                                (
                                                    "本基金的登记业务由基金管理人或基金管理人委托的其他符合条件的机构办理，但基金管理人依法应当承担的责任不因委托而免除。"
                                                    "基金管理人委托其他机构办理本基金登记业务的，应与代理人签订委托代理协议，以明确基金管理人和代理机构在投资者开放式基金账户/{IRP_1}、"
                                                    "基金份额登记、清算和结算及基金交易确认、发放红利、建立并保管基金份额持有人名册和办理非交易过户等事宜中的权利和义务，保护基金份额持有人的合法权益。"
                                                ),
                                                (
                                                    "本基金的登记业务由基金管理人或基金管理人委托的其他符合条件的机构办理，但基金管理人依法应当承担的责任不因委托而免除。"
                                                    "基金管理人委托其他机构办理本基金登记业务的，应与代理人签订委托代理协议，以明确基金管理人和代理机构在投资者相关账户、"
                                                    "基金份额登记、清算和结算及基金交易确认、发放红利、建立并保管基金份额持有人名册和办理非交易过户等事宜中的权利和义务，保护基金份额持有人的合法权益。"
                                                ),
                                            ],
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_755",
        "schema_fields": ["投资限制"],
        "related_name": "基金的投资",
        "name": "投资限制-被动违规调整期限、建仓期",
        "from": "公开募集证券投资基金运作管理办法（证监会令第104号 2014年7月7日）",
        "origin": [
            "第三十四条 基金管理人应当自基金合同生效之日起六个月内使基金的投资组合比例符合基金合同的有关约定。期间，基金的投资范围、投资策略应当符合基金合同的约定。",
            "第三十五条 因证券市场波动、上市公司合并、基金规模变动等基金管理人之外的因素致使基金投资不符合本办法第三十二条规定的比例或者基金合同约定的投资比例的，"
            "基金管理人应当在十个交易日内进行调整，但中国证监会规定的特殊情形除外。",
        ],
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "（19）法律法规及中国证监会规定的和《基金合同》约定的其他投资限制。",
            "（公司结合产品实际情况及法规要求，可选择、增加或删除相应条款。）",
            "除上述（2）、（12）、（16）、（17）情形之外，因证券市场波动、上市公司合并、基金规模变动等基金管理人之外的因素致使基金投资比例不符合上述规定投资比例的，基金管理人应当在10个交易日内进行调整，但中国证监会规定的特殊情形除外。",
            "基金管理人应当自基金合同生效之日起6个月内使基金的投资组合比例符合基金合同的有关约定。在上述期间内，本基金的投资范围、投资策略应当符合基金合同的约定。基金托管人对基金的投资的监督与检查自本基金合同生效之日起开始。",
            "法律法规或监管部门取消上述限制，如适用于本基金，基金管理人在履行适当程序后，则本基金投资不再受相关限制。",
        ],
        "templates": [
            {
                "name": TemplateName.LAW_NAME,
                "content_title": TemplateName.LAW_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_INVEST_SCOPE_INVESTMENT_RESTRICTION,
                "items": [
                    "（19）法律法规及中国证监会规定的和《基金合同》约定的其他投资限制。",
                    {
                        "type": TemplateCheckTypeEnum.INNER_REFER.value,
                        "conditions": [
                            TemplateConditional.FUND_TYPE_STOCK_MIXTURE_BOND,
                            TemplateConditional.FUND_TYPE_INDEX_NO,
                        ],
                        "rules": {
                            "IRF_1": {
                                "default": "（2）、（12）、（16）、（17）",
                                "patterns": [
                                    PatternCollection(
                                        r"应?(?:不低于|不少于)基金资产净值.*?现金不包[括|含](?:结算备付金|存出保证金|应收申购款)"
                                    ),
                                    PatternCollection(r"投资于信用级别评级为.*?资产支持证券"),
                                    PatternCollection(
                                        r"流动性受限资产的?市值合计不得?超过.*?不符合该?比例限制.*?新增流动性受限资产"
                                    ),
                                    PatternCollection(r"交易对手开展逆回购交易.*?质押品的资质[^,。；]+约定的投资范围"),
                                ],
                            },
                        },
                        "items": [
                            "除上述{IRF_1}情形之外，因证券市场波动、上市公司合并、基金规模变动等基金管理人之外的因素致使基金"
                            "投资比例不符合上述规定投资比例的，基金管理人应当在10个交易日内进行调整，但中国证监会规定的特殊情形除外。",
                        ],
                    },
                    "基金管理人应当自基金合同生效之日起6个月内使基金的投资组合比例符合基金合同的有关约定。在上述期间内，本基金的投资范围、"
                    "投资策略应当符合基金合同的约定。基金托管人对基金的投资的监督与检查自本基金合同生效之日起开始。",
                    "法律法规或监管部门取消上述限制，如适用于本基金，基金管理人在履行适当程序后，则本基金投资不再受相关限制。",
                ],
            },
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_INVEST_SCOPE_INVESTMENT_RESTRICTION,
                "items": [
                    {
                        "single_optional": [
                            {
                                "conditions": [TemplateConditional.SPECIAL_TYPE_LINKED_FUND],
                                "items": [
                                    {
                                        "type": TemplateCheckTypeEnum.INNER_REFER.value,
                                        "rules": {
                                            "IRF_1": {
                                                "default": "（2）、（7）、（13）、（14）",
                                                "patterns": [
                                                    PatternCollection(
                                                        r"应?(?:不低于|不少于)基金资产净值.*?现金不包[括|含](?:结算备付金|存出保证金|应收申购款)"
                                                    ),
                                                    PatternCollection(r"投资于信用级别评级为.*?资产支持证券"),
                                                    PatternCollection(
                                                        r"流动性受限资产的?市值合计不得?超过.*?不符合该?比例限制.*?新增流动性受限资产"
                                                    ),
                                                    PatternCollection(
                                                        r"交易对手开展逆回购交易.*?质押品的资质[^,。；]+约定的投资范围"
                                                    ),
                                                ],
                                            },
                                            "IRF_2": {
                                                "default": "（19）",
                                                "patterns": [PatternCollection(r"参与转融通证券出借业务的")],
                                            },
                                            "IRF_3": {
                                                "default": "（1）",
                                                "patterns": [
                                                    PatternCollection(r"资产比例应?(?:不低于|不少于)基金资产净值")
                                                ],
                                            },
                                        },
                                        "items": [
                                            "除上述{IRF_1}情形之外，因证券/期货市场波动、证券发行人合并、基金规模变动、标的指数成份股调整、"
                                            "标的指数成份股流动性限制、目标ETF暂停申购/赎回或二级市场交易停牌等基金管理人之外的因素致使基金投资比例不符合上述规定投资比例的，"
                                            "基金管理人应当在10个交易日内进行调整，但中国证监会规定的特殊情形除外。"
                                            "因证券市场波动、证券发行人合并、基金规模变动等基金管理人之外的因素致使基金投资不符合第{IRF_2}项规定的，基金管理人不得新增出借业务。"
                                            "因证券市场波动、标的指数成份股调整、标的指数成份股流动性限制、目标 ETF 暂停申购、赎回或二级市场交易停牌、"
                                            "基金规模变动等基金管理人之外的因素致使基金投资比例不符合第{IRF_3}项投资比例的，基金管理人应当在 20 个交易日内进行调整，"
                                            "但中国证监会规定的特殊情形除外。法律法规另有规定的，从其规定。",
                                        ],
                                    },
                                ],
                            },
                            {
                                "conditions": [TemplateConditional.FUND_TYPE_STOCK_MIXTURE_BOND_INDEX],
                                "items": [
                                    {
                                        "type": TemplateCheckTypeEnum.INNER_REFER.value,
                                        "rules": {
                                            "IRF_1": {
                                                "default": "（2）、（12）、（16）、（17）",
                                                "patterns": [
                                                    PatternCollection(
                                                        r"应?(?:不低于|不少于)基金资产净值.*?现金不包[括|含](?:结算备付金|存出保证金|应收申购款)"
                                                    ),
                                                    PatternCollection(r"投资于信用级别评级为.*?资产支持证券"),
                                                    PatternCollection(
                                                        r"流动性受限资产的?市值合计不得?超过.*?不符合该?比例限制.*?新增流动性受限资产"
                                                    ),
                                                    PatternCollection(
                                                        r"交易对手开展逆回购交易.*?质押品的资质[^,。；]+约定的投资范围"
                                                    ),
                                                ],
                                            },
                                        },
                                        "items": [
                                            {
                                                "single_optional": [
                                                    {
                                                        "conditions": [
                                                            TemplateConditional.FUND_TYPE_STOCK_MIXTURE_BOND
                                                        ],
                                                        "items": [
                                                            "对于除第{IRF_1}项外的其他比例限制，因证券/期货市场波动、证券发行人合并、"
                                                            "基金规模变动等基金管理人之外的因素致使基金投资比例不符合上述规定投资比例的，基金管理人应当在10个交易日内进行调整，"
                                                            "但中国证监会规定的特殊情形除外。法律法规另有规定的，从其规定。",
                                                        ],
                                                    },
                                                    {
                                                        "conditions": [TemplateConditional.FUND_TYPE_INDEX],
                                                        "items": [
                                                            [
                                                                "除上述{IRF_1}情形之外，因证券市场波动、上市公司合并、基金规模变动、标的指数成份券调整、"
                                                                "标的指数成份券流动性限制等基金管理人之外的因素致使基金投资比例不符合上述规定投资比例的，"
                                                                "基金管理人应当在10个交易日内进行调整，但中国证监会规定的特殊情形除外。",
                                                                "对于除第{IRF_1}项外的其他比例限制，因证券/期货市场波动、证券发行人合并、基金规模变动、"
                                                                "标的指数成份券调整、标的指数成份券流动性限制等基金管理人之外的因素致使基金投资比例不符合上述规定投资比例的，"
                                                                "基金管理人应当在10个交易日内进行调整，但中国证监会规定的特殊情形除外。法律法规另有规定的，从其规定。",
                                                            ],
                                                        ],
                                                    },
                                                ],
                                            }
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                    "法律法规或监管部门取消或调整上述限制，如适用于本基金，基金管理人在履行适当程序后，则本基金投资不再受相关限制或按照调整后的规定执行。",
                ],
            },
        ],
    },
    {
        "label": "template_734",
        "schema_fields": ["暂停赎回或延缓支付赎回款项的情形"],
        "related_name": "基金份额的申购与赎回",
        "name": "暂停赎回或延缓支付赎回款项的情形",
        "from": [
            "中华人民共和国证券投资基金法（主席令第23号 2015年4月24日修订）",
            "公开募集开放式证券投资基金流动性风险管理规定（证监会公告[2017]12号 2017年8月31日）",
        ],
        "origin": [
            "第六十七条 基金管理人应当按时支付赎回款项，但是下列情形除外：",
            "（一）因不可抗力导致基金管理人不能支付赎回款项；",
            "（二）证券交易场所依法决定临时停市，导致基金管理人无法计算当日基金资产净值；",
            "（三）基金合同约定的其他特殊情形。",
            "发生上述情形之一的，基金管理人应当在当日报国务院证券监督管理机构备案。",
            "本条第一款规定的情形消失后，基金管理人应当及时支付赎回款项。",
            "第二十四条 基金管理人应当按照最大限度保护基金份额持有人利益的原则处理基金估值业务，加强极端市场条件下的估值业务管理。",
            "当前一估值日基金资产净值50%以上的资产出现无可参考的活跃市场价格且采用估值技术仍导致公允价值存在重大不确定性时，经与基金托管人协商确认后，"
            "基金管理人应当暂停基金估值，并采取延缓支付赎回款项或暂停接受基金申购赎回申请的措施。前述情形及处理方法应当在基金合同中事先约定。",
        ],
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "八、暂停赎回或延缓支付赎回款项的情形",
            "发生下列情形时，基金管理人可暂停接受投资人的赎回申请或延缓支付赎回款项：",
            "1、因不可抗力导致基金管理人不能支付赎回款项。",
            "2、发生基金合同规定的暂停基金资产估值情况时，基金管理人可暂停接受投资人的赎回申请或延缓支付赎回款项。",
            "3、证券交易所交易时间非正常停市，导致基金管理人无法计算当日基金资产净值。",
            "4、连续两个或两个以上开放日发生巨额赎回。",
            "5、发生继续接受赎回申请将损害现有基金份额持有人利益的情形时，基金管理人可暂停接受基金份额持有人的赎回申请。",
            "6、当前一估值日基金资产净值50%以上的资产出现无可参考的活跃市场价格且采用估值技术仍导致公允价值存在重大不确定性时，经与基金托管人协商确认后，基金管理人应当延缓支付赎回款项或暂停接受基金赎回申请。",
            "7、法律法规规定或中国证监会认定的其他情形。",
            "发生上述情形之一且基金管理人决定暂停赎回或延缓支付赎回款项时，基金管理人应在当日报中国证监会备案，已确认的赎回申请，基金管理人应足额支付；如暂时不能足额支付，应将可支付部分按单个账户申请量占申请总量的比例分配给赎回申请人，未支付部分可延期支付。若出现上述第4项所述情形，按基金合同的相关条款处理。基金份额持有人在申请赎回时可事先选择将当日可能未获受理部分予以撤销。在暂停赎回的情况消除时，基金管理人应及时恢复赎回业务的办理并公告。",
        ],
        "templates": [
            {
                "name": TemplateName.LAW_NAME,
                "content_title": TemplateName.LAW_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_SUBSCRIPTION_SUSPEND_RANSOM_PAY,
                "items": [
                    {
                        "conditions": [TemplateConditional.SIDE_TYPE_MONEY_NO, TemplateConditional.SPECIAL_TYPE_ETF_NO],
                        "items": [
                            "八、暂停赎回或延缓支付赎回款项的情形",
                            "发生下列情形时，基金管理人可暂停接受投资人的赎回申请或延缓支付赎回款项：",
                            "1、因不可抗力导致基金管理人不能支付赎回款项。",
                            "2、发生基金合同规定的暂停基金资产估值情况时，基金管理人可暂停接受投资人的赎回申请或延缓支付赎回款项。",
                            "3、证券交易所交易时间非正常停市，导致基金管理人无法计算当日基金资产净值。",
                            "4、连续两个或两个以上开放日发生巨额赎回。",
                            "5、发生继续接受赎回申请将损害现有基金份额持有人利益的情形时，基金管理人可暂停接受基金份额持有人的赎回申请。",
                            "6、当前一估值日基金资产净值50%以上的资产出现无可参考的活跃市场价格且采用估值技术仍导致公允价值存在重大不确定性时，"
                            "经与基金托管人协商确认后，基金管理人应当延缓支付赎回款项或暂停接受基金赎回申请。",
                            "7、法律法规规定或中国证监会认定的其他情形。",
                            {
                                "type": TemplateCheckTypeEnum.INNER_REFER.value,
                                "rules": {
                                    "IRF_1": {
                                        "default": "4",
                                        "patterns": [
                                            PatternCollection(r"开放日发生巨额赎回"),
                                        ],
                                    },
                                },
                                "items": [
                                    "发生上述情形之一且基金管理人决定暂停赎回或延缓支付赎回款项时，基金管理人应在当日报中国证监会备案，已确认的赎回申请，"
                                    "基金管理人应足额支付；如暂时不能足额支付，应将可支付部分按单个账户申请量占申请总量的比例分配给赎回申请人，未支付部分可延期支付。"
                                    "若出现上述第{IRF_1}项所述情形，按基金合同的相关条款处理。基金份额持有人在申请赎回时可事先选择将当日可能未获受理部分予以撤销。"
                                    "在暂停赎回的情况消除时，基金管理人应及时恢复赎回业务的办理并公告。",
                                ],
                            },
                        ],
                    },
                ],
            },
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_SUBSCRIPTION_SUSPEND_RANSOM_PAY,
                "items": [
                    {
                        "conditions": [TemplateConditional.SIDE_TYPE_MONEY_NO, TemplateConditional.SPECIAL_TYPE_ETF_NO],
                        "items": [
                            "3、证券、期货交易所交易时间非正常停市，导致基金管理人无法计算当日基金资产净值。",
                            "5、发生继续接受赎回申请可能会影响或损害现有基金份额持有人利益的情形时，基金管理人可暂停接受基金份额持有人的赎回申请。",
                            {
                                "conditions": [TemplateConditional.INVESTMENT_SCOPE_HK_STOCK],
                                "items": [
                                    "发生证券交易服务公司等机构认定的交易异常情况并决定暂停提供部分或者全部港股通服务，或者发生其他影响通过内地与香港股票市场交易互联互通机制进行正常交易的情形。",
                                ],
                            },
                            {
                                "conditions": [TemplateConditional.SPECIAL_TYPE_LINKED_FUND],
                                "items": ["7、目标ETF暂停基金资产估值，导致基金管理人无法计算当日基金资产净值时。"],
                            },
                            "8、目标ETF暂停赎回、暂停上市或目标ETF停牌等基金管理人认为有必要暂停本基金赎回的情形。",
                            {
                                "conditions": [
                                    TemplateConditional.SPECIAL_TYPE_ETF_NO,
                                ],
                                "items": [
                                    {
                                        "type": TemplateCheckTypeEnum.INNER_REFER.value,
                                        "rules": {
                                            "IRF_1": {
                                                "default": "4",
                                                "patterns": [
                                                    PatternCollection(r"开放日发生巨额赎回"),
                                                ],
                                            },
                                        },
                                        "items": [
                                            "发生上述情形之一且基金管理人决定暂停赎回或延缓支付赎回款项时，基金管理人应按规定报中国证监会备案，已确认的赎回申请，基金管理人应足额支付；"
                                            "如暂时不能足额支付，应将可支付部分按单个账户申请量占申请总量的比例分配给赎回申请人，未支付部分可延期支付。"
                                            "若出现上述第{IRF_1}项所述情形，按基金合同的相关条款处理。基金份额持有人在申请赎回时可事先选择将当日可能未获受理部分予以撤销。"
                                            "在暂停赎回的情况消除时，基金管理人应及时恢复赎回业务的办理并公告。",
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_736",
        "schema_fields": ["基金登记机构的权利", "基金登记机构的义务"],
        "related_name": "基金份额的登记",
        "name": "份额登记-登记机构的权利和义务",
        "from": "中华人民共和国证券投资基金法（主席令第23号 2015年4月24日修订）",
        "origin": [
            "第一百零二条 基金份额登记机构以电子介质登记的数据，是基金份额持有人权利归属的根据。基金份额持有人以基金份额出质的，质权自基金份额登记机构办理出质登记时设立。",
            "基金份额登记机构应当妥善保存登记数据，并将基金份额持有人名称、身份信息及基金份额明细等数据备份至国务院证券监督管理机构认定的机构。其保存期限自基金账户销户之日起不得少于二十年。",
            "基金份额登记机构应当保证登记数据的真实、准确、完整，不得隐匿、伪造、篡改或者毁损。",
        ],
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "三、基金登记机构的权利",
            "基金登记机构享有以下权利：",
            "1、取得登记费；",
            "2、建立和管理投资者基金账户；",
            "3、保管基金份额持有人开户资料、交易资料、基金份额持有人名册等；",
            "4、在法律法规允许的范围内，对登记业务的办理时间进行调整，并依照有关规定于开始实施前在指定媒介上公告；",
            "5、法律法规及中国证监会规定的和《基金合同》约定的其他权利。",
            "四、基金登记机构的义务",
            "基金登记机构承担以下义务：",
            "1、配备足够的专业人员办理本基金份额的登记业务；",
            "2、严格按照法律法规和《基金合同》规定的条件办理本基金份额的登记业务；",
            "3、妥善保存登记数据，并将基金份额持有人名称、身份信息及基金份额明细等数据备份至中国证监会认定的机构。其保存期限自基金账户销户之日起不得少于20年；",
            "4、对基金份额持有人的基金账户信息负有保密义务，因违反该保密义务对投资者或基金带来的损失，须承担相应的赔偿责任，但司法强制检查情形及法律法规及中国证监会规定的和《基金合同》约定的其他情形除外；",
            "5、按《基金合同》及招募说明书规定为投资者办理非交易过户业务、提供其他必要的服务；",
            "6、接受基金管理人的监督；",
            "7、法律法规及中国证监会规定的和《基金合同》约定的其他义务。",
        ],
        "templates": [
            {
                "name": TemplateName.LAW_NAME,
                "content_title": TemplateName.LAW_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_REGISTER_PORTION_INSTITUTION_RIGHT,
                "items": [
                    "三、基金登记机构的权利",
                    "基金登记机构享有以下权利：",
                    "1、取得登记费；",
                    {
                        "conditions": [TemplateConditional.SPECIAL_TYPE_LOF_NO],
                        "items": ["2、建立和管理投资者基金账户；"],
                    },
                    "3、保管基金份额持有人开户资料、交易资料、基金份额持有人名册等；",
                    "5、法律法规及中国证监会规定的和《基金合同》约定的其他权利。",
                    "四、基金登记机构的义务",
                    "基金登记机构承担以下义务：",
                    "1、配备足够的专业人员办理本基金份额的登记业务；",
                    "2、严格按照法律法规和《基金合同》规定的条件办理本基金份额的登记业务；",
                    "3、妥善保存登记数据，并将基金份额持有人名称、身份信息及基金份额明细等数据备份至中国证监会认定的机构。其保存期限自基金账户销户之日起不得少于20年；",
                    "4、对基金份额持有人的基金账户信息负有保密义务，因违反该保密义务对投资者或基金带来的损失，须承担相应的赔偿责任，"
                    "但司法强制检查情形及法律法规及中国证监会规定的和《基金合同》约定的其他情形除外；",
                    "5、按《基金合同》及招募说明书规定为投资者办理非交易过户业务、提供其他必要的服务；",
                    "6、接受基金管理人的监督；",
                    "7、法律法规及中国证监会规定的和《基金合同》约定的其他义务。",
                ],
            },
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "rule_fields": [("上市交易所", [TemplateConditional.SPECIAL_TYPE_LOF])],
                "chapter": ChapterPattern.CHAPTER_FUND_REGISTER_PORTION_INSTITUTION_RIGHT,
                "items": [
                    {
                        "single_optional": [
                            {
                                "conditions": [TemplateConditional.SPECIAL_TYPE_LOF],
                                "items": [
                                    {
                                        "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                                        "rules": {"IRP_1": {"func": "get_fund_settlement_name"}},
                                        "items": ["2、建立和管理投资者开放式基金账户和/或{IRP_1}；"],
                                    },
                                ],
                            },
                            {"items": ["2、建立和管理投资者相关账户；"]},
                        ]
                    },
                    [
                        "4、在法律法规允许的范围内，对登记业务的办理时间进行调整，并依照有关规定于开始实施前在规定媒介上公告；",
                        "4、在法律法规允许的范围内，制定和调整登记业务相关规则，并依照有关规定于开始实施前在规定媒介上公告；",
                        "4、在法律法规允许的范围内，对登记业务的办理时间和相关业务规则进行调整，并依照有关规定于开始实施前在规定媒介上公告；",
                    ],
                    "四、基金登记机构的义务",
                    "2、严格按照法律法规和《基金合同》以及登记机构业务规则规定的条件办理本基金份额的登记业务；",
                    "4、对基金份额持有人的相关账户信息负有保密义务，因违反该保密义务对投资者或基金带来的损失，须承担相应的赔偿责任，"
                    "但司法强制检查情形及法律法规及中国证监会规定的和《基金合同》约定的其他情形除外；",
                    "5、按《基金合同》及招募说明书规定为投资者办理非交易过户业务、基金收益分配、提供其他必要的服务；",
                ],
            },
        ],
    },
    {
        "label": "template_610",
        "schema_fields": ["发售时间", "发售方式", "发售对象"],
        "related_name": "基金份额的发售",
        "name": "基金份额的发售时间、发售方式、发售对象",
        "from": "公开募集证券投资基金运作管理办法 证监会令第104号 2014年7月7日",
        "origin": "第十一条基金募集期限自基金份额发售之日起不得超过三个月。",
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "一、基金份额的发售时间、发售方式、发售对象",
            "1、发售时间",
            "自基金份额发售之日起最长不得超过3个月，具体发售时间见基金份额发售公告。",
            "2、发售方式",
            "通过各销售机构的基金销售网点公开发售，各销售机构的具体名单见基金份额发售公告以及基金管理人届时发布的调整销售机构的相关公告。",
            "3、发售对象",
            "符合法律法规规定的可投资于证券投资基金的个人投资者、机构投资者、合格境外机构投资者和人民币合格境外机构投资者以及法律法规或中国证监会允许购买证券投资基金的其他投资人。",
        ],
        "templates": [
            {
                "name": "法规",
                "content_title": "法规条款",
                "chapter": ChapterPattern.CHAPTER_FUND_SELL_MODE,
                "items": [
                    "一、基金份额的发售时间、发售方式、发售对象",
                    "1、发售时间",
                    "自基金份额发售之日起最长不得超过3个月，具体发售时间见基金份额发售公告。",
                    {
                        # 非ETF且非LOF
                        "conditions": [
                            TemplateConditional.SPECIAL_TYPE_ETF_NO,
                            TemplateConditional.SPECIAL_TYPE_LOF_NO,
                        ],
                        "items": [
                            "2、发售方式",
                            "通过各销售机构的基金销售网点公开发售，"
                            "各销售机构的具体名单见基金份额发售公告以及基金管理人届时发布的调整销售机构的相关公告。",
                        ],
                    },
                    {
                        "conditions": [TemplateConditional.SPECIAL_TYPE_INITIATE_NO],
                        "items": [
                            "3、发售对象",
                            "符合法律法规规定的可投资于证券投资基金的个人投资者、机构投资者、合格境外机构投资者和人民币合格境外机构投资者以及法律法规或中国证监会允许购买证券投资基金的其他投资人。",
                        ],
                    },
                ],
            },
            {
                "name": "范文",
                "content_title": "合同范文",
                "rule_fields": [("上市交易所", [TemplateConditional.SPECIAL_TYPE_ETF_LOF])],
                "chapter": ChapterPattern.CHAPTER_FUND_SELL_MODE,
                "items": [
                    {
                        "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                        "rules": {
                            "IRP_1": {"func": "get_fund_bourse_name"},
                            "IRP_2": {"func": "get_fund_settlement_name"},
                        },
                        "items": [
                            {
                                "single_optional": [
                                    {
                                        "conditions": [TemplateConditional.SPECIAL_TYPE_ETF],
                                        "items": [
                                            "2、发售方式",
                                            "投资人可选择网上现金认购、网下现金认购和网下股票认购三种方式认购本基金。",
                                            [
                                                "网上现金认购是指投资人通过基金管理人指定的发售代理机构利用{IRP_1}网上系统以现金进行认购。",
                                                "网上现金认购是指投资者通过具有基金销售业务资格的{IRP_1}会员用{IRP_1}网上系统以现金进行的认购；",
                                            ],
                                            "网下现金认购是指投资人通过基金管理人及其指定的发售代理机构以现金进行的认购。",
                                            "网下股票认购是指投资人通过基金管理人及其指定的发售代理机构以股票进行的认购。",
                                            "投资人应当在基金管理人及其指定发售代理机构办理基金发售业务的营业场所，或者按基金管理人或发售代理机构提供的方式办理基金份额的认购。",
                                            "基金管理人、发售代理机构办理基金发售业务的具体情况和联系方式，请参见基金份额发售公告。",
                                            "基金管理人可以根据情况调整销售机构，并在基金管理人网站公示。",
                                            "基金投资者在募集期内可多次认购，认购一经受理不得撤销。",
                                            "本基金将通过基金销售机构公开发售。基金销售机构对认购申请的受理并不代表该申请一定成功，而仅代表销售机构确实接收到认购申请。"
                                            "认购的确认以登记机构的确认结果为准。对于认购申请及认购份额的确认情况，投资人应及时查询并妥善行使合法权利。",
                                            "基金管理人或发售代理机构提供的方式办理基金份额的认购。基金管理人、发售代理机构办理基金发售业务的具体情况和联系方式，请参见基金份额发售公告。",
                                            "基金管理人可依据实际情况增减、变更销售机构，并在基金管理人网站公示。",
                                        ],
                                    },
                                    {
                                        "conditions": [TemplateConditional.SPECIAL_TYPE_LOF],
                                        "items": [
                                            "2、发售方式",
                                            "本基金可通过场外、场内两种方式公开发售。场外通过各销售机构的基金销售网点或以销售机构提供的其他方式公开发售，"
                                            "具体名单见基金份额发售公告以及基金管理人届时发布的调整销售机构的相关公告。场内通过具有基金销售业务资格的{IRP_1}会员单位发售，"
                                            "尚未取得基金销售业务资格、但属于{IRP_1}会员单位的其他机构，可在基金份额上市后，代理投资者通过{IRP_1}交易系统参与本基金的上市交易。",
                                            {
                                                "single_optional": [
                                                    {
                                                        "conditions": [TemplateConditional.SHARE_CLASSIFY_YES],
                                                        "items": [
                                                            "通过场外认购的A类基金份额登记在登记结算系统基金份额持有人开放式基金账户下；"
                                                            "通过场内认购的A类基金份额登记在证券登记结算系统基金份额持有人{IRP_2}下。",
                                                        ],
                                                    },
                                                    {
                                                        "items": [
                                                            "通过场外认购的基金份额登记在登记结算系统基金份额持有人开放式基金账户下；"
                                                            "通过场内认购的基金份额登记在证券登记结算系统基金份额持有人{IRP_2}下。"
                                                        ],
                                                    },
                                                ]
                                            },
                                        ],
                                    },
                                ],
                            },
                            {
                                "single_optional": [
                                    {
                                        "conditions": [TemplateConditional.SPECIAL_TYPE_INITIATE_NO],
                                        "items": [
                                            "3、发售对象",
                                            [
                                                "符合法律法规规定的可投资于证券投资基金的个人投资者、机构投资者、合格境外机构资者以及法律法规或中国证监会允许购买证券投资基金的其他投资人。",
                                                "本基金的发售对象为个人投资者、机构投资者、合格境外机构投资者、人民币合格境外机构投资者和法律法规或中国证监会允许购买证券投资基金的其他投资者。",
                                                "本基金的发售对象为个人投资者、机构投资者、合格境外机构投资者和法律法规或中国证监会允许购买证券投资基金的其他投资者。",
                                            ],
                                        ],
                                    },
                                    {
                                        "items": [
                                            "3、发售对象",
                                            "符合法律法规规定的可投资于证券投资基金的个人投资者、机构投资者、合格机构投资者、发起资金提供方以及法律法规或中国证监会允许购买证券投资基金的其他投资人。",
                                        ],
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_638",
        "schema_fields": ["基金份额持有人大会召开事由"],
        "related_name": "基金份额持有人大会",
        "name": "份额持有人大会-召开事由",
        "from": "中华人民共和国证券投资基金法（主席令第23号 2015年4月24日修订）",
        "origin": [
            "第四十七条 基金份额持有人大会由全体基金份额持有人组成，行使下列职权：",
            "（一）决定基金扩募或者延长基金合同期限；",
            "（二）决定修改基金合同的重要内容或者提前终止基金合同；",
            "（三）决定更换基金管理人、基金托管人；",
            "（四）决定调整基金管理人、基金托管人的报酬标准；",
            "（五）基金合同约定的其他职权。",
        ],
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "一、召开事由",
            "1、当出现或需要决定下列事由之一的，应当召开基金份额持有人大会：",
            "（1）终止《基金合同》；",
            "（2）更换基金管理人；",
            "（3）更换基金托管人；",
            "（4）转换基金运作方式；",
            "（5）调整基金管理人、基金托管人的报酬标准；",
            "（6）变更基金类别；",
            "（7）本基金与其他基金的合并；",
            "（8）变更基金投资目标、范围或策略；",
            "（9）变更基金份额持有人大会程序；",
            "（10）基金管理人或基金托管人要求召开基金份额持有人大会；",
            "（11）单独或合计持有本基金总份额10%以上（含10%）基金份额的基金份额持有人（以基金管理人收到提议当日的基金份额计算，下同）就同一事项书面要求召开基金份额持有人大会；",
            "（12）对基金当事人权利和义务产生重大影响的其他事项；",
            "（13）法律法规、《基金合同》或中国证监会规定的其他应当召开基金份额持有人大会的事项。",
        ],
        "templates": [
            {
                "name": TemplateName.LAW_NAME,
                "content_title": TemplateName.LAW_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_SHARE_HOLDER_CAUSE,
                "items": [
                    "一、召开事由",
                    "1、当出现或需要决定下列事由之一的，应当召开基金份额持有人大会：",
                    "（1）终止《基金合同》；",
                    "（2）更换基金管理人；",
                    "（3）更换基金托管人；",
                    "（4）转换基金运作方式；",
                    "（5）调整基金管理人、基金托管人的报酬标准；",
                    "（6）变更基金类别；",
                    "（7）本基金与其他基金的合并；",
                    "（8）变更基金投资目标、范围或策略；",
                    "（9）变更基金份额持有人大会程序；",
                    "（10）基金管理人或基金托管人要求召开基金份额持有人大会；",
                    "（11）单独或合计持有本基金总份额10%以上（含10%）基金份额的基金份额持有人（以基金管理人收到提议当日的基金份额计算，下同）就同一事项书面要求召开基金份额持有人大会；",
                    "（12）对基金当事人权利和义务产生重大影响的其他事项；",
                    "（13）法律法规、《基金合同》或中国证监会规定的其他应当召开基金份额持有人大会的事项。",
                ],
            },
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "rule_fields": [("上市交易所", [TemplateConditional.LISTED_TRANSACTION_YES])],
                "chapter": ChapterPattern.CHAPTER_FUND_SHARE_HOLDER_CAUSE,
                "items": [
                    "1、除法律法规、中国证监会和基金合同另有规定外，当出现或需要决定下列事由之一的，应当召开基金份额持有人大会：",
                    [
                        "（5）提高基金管理人、基金托管人的报酬标准；",
                        "（5）提高基金管理人、基金托管人的报酬标准或提高销售服务费；",
                    ],
                    "（12）对基金合同当事人权利和义务产生重大影响的其他事项；",
                    {
                        "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                        "rules": {
                            "IRP_1": {"func": "get_fund_bourse_name"},
                        },
                        "items": [
                            {
                                "conditions": [
                                    TemplateConditional.LISTED_TRANSACTION_YES,
                                ],
                                "items": [
                                    [
                                        "终止基金上市，但因基金不再具备上市条件而被相关证券交易所终止上市的情形除外；",
                                        "终止基金上市，但因本基金不再具备上市条件而被{IRP_1}终止上市的除外；",
                                    ],
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_771",
        "schema_fields": ["估值方法"],
        "related_name": "基金资产估值",
        "name": "估值方法-证券投资基金的估值",
        "from": [
            "《公开募集证券投资基金运作指引第2号——基金中基金指引（证监会公告〔2016〕20号 2016年9月11日）》",
            "《基金中基金（FOF）审核指引（证监会机构部2017年4月24日）》",
        ],
        "origin": [
            "第八条 基金中基金应当采用公允的估值方法，及时、准确地反映基金资产的价值变动。基金管理人应当在基金中基金所投资基金披露净值的次日，及时披露基金中基金份额净值和份额累计净值。",
            "七、估值方法及时效",
            "（一）FOF的估值按照《基金中基金估值业务指引》执行。",
            "（二）若FOF投资范围中明确不投资QDII，则T日的基金份额净值应不迟于T+2日公告；若投资范围包括QDII，则T日的基金份额净值应不迟于T+3日公告。",
            "（三）若占相当比例的被投资基金暂停估值，FOF也可相应暂停。",
        ],
        "templates": [
            {
                # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2194#note_328845
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_ASSET_VALUATION,
                "items": [
                    {
                        "conditions": [TemplateConditional.SIDE_TYPE_FOF],
                        "items": [
                            [
                                "证券投资基金的估值",
                                "基金份额的估值",
                            ],
                            {
                                "type": TemplateCheckTypeEnum.CHAPTER_COMBINATION.value,
                                "patterns": [
                                    PatternCollection(r"非上市基金的估值"),
                                    PatternCollection(r"(?<!非)上市基金的估值"),
                                    PatternCollection(r"特殊情况.*?根据以下原则进行估值"),
                                ],
                                "serial_num_pattern": P_PARA_PREFIX_NUM,
                                "default_prefix_type": "（{num}）",
                                "items": [
                                    "非上市基金的估值",
                                    "上市基金的估值",
                                    "如遇所投资基金不公布基金份额净值、进行折算或拆分、估值日无交易等特殊情况，基金管理人根据以下原则进行估值：",
                                ],
                                "child_items": [
                                    {
                                        "type": TemplateCheckTypeEnum.RECOMBINATION.value,
                                        "patterns": [
                                            PatternCollection(r"非货币市场"),
                                            PatternCollection(r"(?<!非)货币市场"),
                                        ],
                                        # 头部添加自增序号1、2、
                                        "serial_num_pattern": P_PARA_PREFIX_NUM,
                                        "default_prefix_type": "{num}）",
                                        "items": [
                                            "境内非货币市场基金按其估值日的份额净值估值；",
                                            "境内货币市场基金，如其披露份额净值，则按其估值日的份额净值估值；如其披露万份（百份）收益，按其前一估值日后至估值日期间（含节假日）的万份（百份）收益计提估值日基金收益。",
                                        ],
                                    },
                                    {
                                        "type": TemplateCheckTypeEnum.RECOMBINATION.value,
                                        "patterns": [
                                            PatternCollection(r"ETF基金"),
                                            PatternCollection(r"(?<!定期)开放式基金"),
                                            PatternCollection(r"定期开放式基金"),
                                            PatternCollection(r"交易型货币市场基金"),
                                        ],
                                        "serial_num_pattern": P_PARA_PREFIX_NUM,
                                        "default_prefix_type": "{num}）",
                                        "items": [
                                            "ETF基金按其估值日的收盘价估值；",
                                            "境内上市开放式基金（LOF）按其估值日的份额净值估值；",
                                            "境内上市定期开放式基金、封闭式基金按其估值日的收盘价估值；",
                                            "对于境内上市交易型货币市场基金，如其披露份额净值，则按其估值日的份额净值估值；如其披露万份（百份）收益，则按其前一估值日后至估值日期间（含节假日）的万份（百份）收益计提估值日基金收益。",
                                        ],
                                    },
                                    {
                                        "type": TemplateCheckTypeEnum.RECOMBINATION.value,
                                        "patterns": [
                                            PatternCollection(r"未公布估值日基金份额净值"),
                                            PatternCollection(r"交易日的收盘价估值.*?调整最近交易市价"),
                                            PatternCollection(
                                                r"(?:基金份额净值或收盘价|单位基金份额分红金额|折算拆分比例|持仓份额)等因素合理确定公允价值"
                                            ),
                                        ],
                                        "serial_num_pattern": P_PARA_PREFIX_NUM,
                                        "default_prefix_type": "{num}）",
                                        "items": [
                                            "以所投资基金的基金份额净值估值的，若所投资基金与本基金估值频率一致但未公布估值日基金份额净值，按其最近公布的基金份额净值为基础估值；",
                                            "以所投资基金的收盘价估值的，若估值日无交易，且最近交易日后市场环境未发生重大变化，按最近交易日的收盘价估值；"
                                            "如最近交易日后市场环境发生了重大变化的，可使用最新的基金份额净值为基础或参考类似投资品种的现行市价及重大变化因素调整最近交易市价，确定公允价值；",
                                            "如果所投资基金前一估值日至估值日期间发生分红除权、折算或拆分，基金管理人应根据基金份额净值或收盘价、单位基金份额分红金额、折算拆分比例、持仓份额等因素合理确定公允价值。",
                                        ],
                                    },
                                ],
                            },
                            "（4）当基金管理人认为所投资基金按上述第（1）至第（3）项进行估值存在不公允时，应与基金托管人协商一致采用合理的估值技术或估值标准确定其公允价值。",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_807",
        "schema_fields": ["临时报告或信息披露"],
        "related_name": "基金的信息披露",
        "name": "信息披露-临时报告",
        "from": [
            "《公开募集证券投资基金信息披露管理办法（证监会令第166号修订 2020年3月20日）》",
            "《证监会关于实施<公开募集证券投资基金信息披露管理办法>有关问题的规定（证监会公告 2019年07月26日）》",
        ],
        "origin": [
            "第二十一条 基金发生重大事件，有关信息披露义务人应当在两日内编制临时报告书，并登载在规定报刊和规定网站上。",
            "前款所称重大事件，是指可能对基金份额持有人权益或者基金份额的价格产生重大影响的下列事件：",
            "（一）基金份额持有人大会的召开及决定的事项；",
            "（二）基金终止上市交易、基金合同终止、基金清算；",
            "（三）基金扩募、延长基金合同期限；",
            "（四）转换基金运作方式、基金合并；",
            "（五）更换基金管理人、基金托管人、基金份额登记机构，基金改聘会计师事务所；",
            "（六）基金管理人委托基金服务机构代为办理基金的份额登记、核算、估值等事项，基金托管人委托基金服务机构代为办理基金的核算、估值、复核等事项；",
            "（七）基金管理人、基金托管人的法定名称、住所发生变更；",
            "（八）基金管理公司变更持有百分之五以上股权的股东、变更公司的实际控制人；",
            "（九）基金募集期延长或提前结束募集；",
            "（十）基金管理人高级管理人员、基金经理和基金托管人专门基金托管部门负责人发生变动；",
            "（十一）基金管理人的董事在最近12个月内变更超过百分之五十，基金管理人、基金托管人专门基金托管部门的主要业务人员在最近12个月内变动超过百分之三十；",
            "（十二）涉及基金财产、基金管理业务、基金托管业务的诉讼或仲裁；",
            "（十三）基金管理人或其高级管理人员、基金经理因基金管理业务相关行为受到重大行政处罚、刑事处罚，基金托管人或其专门基金托管部门负责人因基金托管业务相关行为受到重大行政处罚、刑事处罚；",
            "（十四）基金管理人运用基金财产买卖基金管理人、基金托管人及其控股股东、实际控制人或者与其有重大利害关系的公司发行的证券或者承销期内承销的证券，或者从事其他重大关联交易事项，中国证监会另有规定的情形除外；",
            "（十五）基金收益分配事项，货币市场基金等中国证监会另有规定的特殊基金品种除外；",
            "（十六）管理费、托管费、销售服务费、申购费、赎回费等费用计提标准、计提方式和费率发生变更；",
            "（十七）基金份额净值计价错误达基金份额净值百分之零点五；",
            "（十八）开放式基金开始办理申购、赎回；",
            "（十九）开放式基金发生巨额赎回并延期办理；",
            "（二十）开放式基金连续发生巨额赎回并暂停接受赎回申请或延缓支付赎回款项；",
            "（二十一）开放式基金暂停接受申购、赎回申请或重新接受申购、赎回申请；",
            "（二十二）基金信息披露义务人认为可能对基金份额持有人权益或者基金份额的价格产生重大影响的其他事项或中国证监会规定的其他事项。",
            "【五、《办法》第二十一条第（十四）项所称“中国证监会另有规定的情形”包括但不限于：",
            "（一）基金管理人运用基金财产买卖基金管理人、基金托管人及其控股股东、实际控制人或者与其有重大利害关系的公司非主承销的证券；",
            "（二）完全按照有关指数的构成比例进行证券投资的基金品种涉及的重大关联交易。",
            "基金发生重大关联交易事项依规披露的临时报告书的内容应当包括但不限于：交易事项概述、交易标的基本情况、交易数量、交易金额、交易定价依据、关联方名称、交易各方的关联关系等，若成交价格与公允价格差异较大的，应当说明原因。】",
        ],
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "（七）临时报告",
            "本基金发生重大事件，有关信息披露义务人应当在2日内编制临时报告书，予以公告，并在公开披露日分别报中国证监会和基金管理人主要办公场所所在地的中国证监会派出机构备案。",
            "前款所称重大事件，是指可能对基金份额持有人权益或者基金份额的价格产生重大影响的下列事件：",
            "1、基金份额持有人大会的召开；",
            "2、终止《基金合同》；",
            "3、转换基金运作方式；",
            "4、更换基金管理人、基金托管人；",
            "5、基金管理人、基金托管人的法定名称、住所发生变更；",
            "6、基金管理人股东及其出资比例发生变更；",
            "7、基金募集期延长；",
            "8、基金管理人的董事长、总经理及其他高级管理人员、基金经理和基金托管人基金托管部门负责人发生变动；",
            "9、基金管理人的董事在一年内变更超过百分之五十；",
            "10、基金管理人、基金托管人基金托管部门的主要业务人员在一年内变动超过百分之三十；",
            "11、涉及基金管理人、基金财产、基金托管业务的诉讼或仲裁；",
            "12、基金管理人、基金托管人受到监管部门的调查；",
            "13、基金管理人及其董事、总经理及其他高级管理人员、基金经理受到严重行政处罚，基金托管人及其基金托管部门负责人受到严重行政处罚；",
            "14、重大关联交易事项；",
            "15、基金收益分配事项；",
            "16、管理费、托管费等费用计提标准、计提方式和费率发生变更；",
            "17、基金份额净值计价错误达基金份额净值百分之零点五；",
            "18、基金改聘会计师事务所；",
            "19、变更基金销售机构；",
            "20、更换基金登记机构；",
            "21、本基金开始办理申购、赎回；",
            "22、本基金申购、赎回费率及其收费方式发生变更；",
            "23、本基金发生巨额赎回并延期办理；",
            "24、本基金连续发生巨额赎回并暂停接受赎回申请；",
            "25、本基金暂停接受申购、赎回申请后重新接受申购、赎回；",
            "26、发生涉及基金申购、赎回事项调整或潜在影响投资者赎回等重大事项时；",
            "27、基金管理人采用摆动定价机制进行估值；",
            "28、本基金连续X-20、X-10、X-5（将前值X代入）个工作日出现基金份额持有人数量不满200人或者基金资产净值低于5000万元情形的。（若公司选择“连续X（可选30、40、50）个工作日出现前述情形的，基金合同终止，不需召开基金份额持有人大会”，则填写）；",
            "29、其他（公司可增加）；",
            "30、中国证监会规定的其他事项。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_INFORMATION_DISCLOSURE_PROVISIONAL_REPORT,
                "items": [
                    "本基金发生重大事件，有关信息披露义务人应在2日内编制临时报告书，并登载在规定报刊和规定网站上。",
                    "前款所称重大事件，是指可能对基金份额持有人权益或者基金份额的价格产生重大影响的下列事件：",
                    {
                        "type": TemplateCheckTypeEnum.RECOMBINATION.value,
                        "patterns": [
                            PatternCollection(r"基金份额持有人大会的召开及决定的事项"),  # 1、
                            PatternCollection(rf"(?:(?:上市交易|《?基金合同》?终止|基金清算)[{R_CONJUNCTION}]?){{2,}}"),
                            PatternCollection(rf"转换(?:(?:基金运作方式|基金合并)[{R_CONJUNCTION}]?){{2}}"),
                            PatternCollection(
                                rf"(?:(?:基金管理人|基金托管人|基金份额登记机构)[{R_CONJUNCTION}]?){{3}}"
                            ),
                            PatternCollection(r"委托.{2,20}办理"),
                            PatternCollection(r"法定.{2,10}发生变更"),
                            PatternCollection(r"(百分之五|5%)以上.{2,20}实际控制人"),
                            PatternCollection(rf"募集期(?:(?:延长|提前结束)[{R_CONJUNCTION}]?){{2}}募集"),
                            PatternCollection(r"负责人发生变动"),
                            PatternCollection(
                                rf"基金管理人.{{2,20}}变更超过.{{2,10}}(?:(?:基金管理人|基金托管人)[{R_CONJUNCTION}]?){{2}}专门基金托管部门.{{2,25}}"
                            ),
                            # 10
                            PatternCollection(rf"涉及.{{2,30}}诉讼[{R_CONJUNCTION}]仲裁"),
                            PatternCollection(r"因.{2,20}受到.{2,20}处罚"),
                            PatternCollection(r"基金管理人运用.{2,100}中国证监会另有规定的情形除外"),
                            PatternCollection(r"基金收益分配事项"),
                            PatternCollection(
                                r"(?:基金管理费|基金托管费|申购费|赎回费).{2,30}(?:计提标准|计提方式|费率)发生变更"
                            ),
                            PatternCollection(r"基金份额净值.{2,10}错误达(该类)?基金份额净值"),
                            PatternCollection(rf"开始办理(?:(?:申购|赎回)[{R_CONJUNCTION}]?){{2,}}"),  # 17
                            PatternCollection(
                                rf"基金份额(?:(?:停牌|复牌|暂停上市|恢复上市|终止上市交易)[{R_CONJUNCTION}]?){{2,}}"
                            ),
                            PatternCollection(r"本基金发生(?:(?:巨额赎回|延期办理)[并]?){2,}"),
                            PatternCollection(r"连续发生巨额赎回并(?:暂停接受赎回申请|延缓支付赎回款项).{2,20}"),
                            PatternCollection(
                                r"暂停接受(?:(?:申购|赎回申请|重新接受申购|重新接受赎回申请|延缓支付赎回对价|赎回|)[、或后]?){2,5}"
                            ),
                            PatternCollection(r"发生涉及.{2,25}等重大事项"),
                            PatternCollection(r"摆动定价机制"),
                            PatternCollection(r"变更标的指数"),
                            PatternCollection(r"调整基金份额类别(的设置)?"),
                            PatternCollection(r"调整最小.{2,25}组成"),
                            PatternCollection(
                                rf"本基金(?:(?:停复牌|暂停上市|恢复上市|终止上市)[{R_CONJUNCTION}]?){{2,4}}"
                            ),
                            PatternCollection(r"变更目标ETF"),
                            PatternCollection(r"计算.{2,40}0.5%的情形"),
                            PatternCollection(r"《?基金合同》?生效后.连续.{2,20}个工作日出现.{2,30}情形"),
                            PatternCollection(r"推出(新业务|服务)"),
                            PatternCollection(r"实施基金份额折算"),
                            PatternCollection(r"中国证监会规定的其他事项"),
                        ],
                        "serial_num_pattern": P_PARA_PREFIX_NUM,
                        "default_prefix_type": "{num}",
                        "items": [
                            "基金份额持有人大会的召开及决定的事项；",
                            {
                                "single_optional": [
                                    {
                                        "conditions": [TemplateConditional.LISTED_TRANSACTION_NO],
                                        "items": [
                                            "《基金合同》终止、基金清算；",
                                        ],
                                    },
                                    {
                                        "conditions": [TemplateConditional.LISTED_TRANSACTION_YES],
                                        "items": [
                                            "基金终止上市交易、《基金合同》终止、基金清算；",
                                        ],
                                    },
                                ]
                            },
                            "转换基金运作方式、基金合并；",
                            "更换基金管理人、基金托管人、基金份额登记机构，基金改聘会计师事务所；",
                            "基金管理人委托基金服务机构代为办理基金的份额登记、核算、估值等事项，基金托管人委托基金服务机构代为办理基金的核算、估值、复核等事项；",
                            "基金管理人、基金托管人的法定名称、住所发生变更；",
                            "基金管理人变更持有百分之五以上股权的股东、变更公司的实际控制人；",
                            "基金募集期延长或提前结束募集；",
                            "基金管理人高级管理人员、基金经理和基金托管人专门基金托管部门负责人发生变动；",
                            "基金管理人的董事在最近12个月内变更超过百分之五十；基金管理人、基金托管人专门基金托管部门的主要业务人员在最近12个月内变动超过百分之三十；",
                            "涉及基金财产、基金管理业务、基金托管业务的诉讼或仲裁；",
                            "基金管理人或其高级管理人员、基金经理因基金管理业务相关行为受到重大行政处罚、刑事处罚，基金托管人或其专门基金托管部门负责人因基金托管业务相关行为受到重大行政处罚、刑事处罚；",
                            "基金管理人运用基金财产买卖基金管理人、基金托管人及其控股股东、实际控制人或者与其有重大利害关系的公司发行的证券或者承销期内承销的证券，或者从事其他重大关联交易事项，中国证监会另有规定的情形除外；",
                            {
                                "conditions": [TemplateConditional.SIDE_TYPE_MONEY_NO],
                                "items": [
                                    "基金收益分配事项；",
                                ],
                            },
                            "基金管理费、基金托管费、申购费、赎回费等费用计提标准、计提方式和费率发生变更；",
                            {
                                "single_optional": [
                                    {
                                        "conditions": [TemplateConditional.SHARE_CLASSIFY_YES],
                                        "items": [
                                            "任一类基金份额净值估值错误达该类基金份额净值百分之零点五；",
                                        ],
                                    },
                                    {
                                        "items": [
                                            "基金份额净值计价错误达基金份额净值百分之零点五；",
                                        ]
                                    },
                                ]
                            },
                            "开始办理申购、赎回；",
                            {
                                "conditions": [TemplateConditional.LISTED_TRANSACTION_YES],
                                "items": [
                                    "基金份额停牌、复牌、暂停上市、恢复上市或终止上市交易；",
                                ],
                            },
                            {
                                "conditions": [TemplateConditional.SIDE_TYPE_OPEN_REGULAR_OPEN],
                                "items": [
                                    "本基金发生巨额赎回并延期办理；",
                                ],
                            },
                            {
                                "conditions": [TemplateConditional.SIDE_TYPE_OPEN_REGULAR_OPEN],
                                "items": [
                                    "本基金连续发生巨额赎回并暂停接受赎回申请或延缓支付赎回款项；",
                                ],
                            },
                            {
                                "single_optional": [
                                    {
                                        "conditions": [
                                            TemplateConditional.SPECIAL_TYPE_ETF,
                                            TemplateConditional.SIDE_TYPE_CLOSE_NO,
                                        ],
                                        "items": [
                                            "本基金暂停接受申购、赎回申请或重新接受申购、赎回申请或延缓支付赎回对价；",
                                        ],
                                    },
                                    {
                                        "conditions": [
                                            TemplateConditional.SIDE_TYPE_OPEN_REGULAR_OPEN,
                                            TemplateConditional.SIDE_TYPE_CLOSE_NO,
                                        ],
                                        "items": [
                                            "本基金暂停接受申购、赎回申请后重新接受申购、赎回；",
                                        ],
                                    },
                                    {
                                        "conditions": [
                                            TemplateConditional.SPECIAL_TYPE_ETF_NO,
                                            TemplateConditional.SIDE_TYPE_CLOSE_NO,
                                        ],
                                        "items": [
                                            "本基金暂停接受申购、赎回申请后重新接受申购、赎回；",
                                        ],
                                    },
                                ]
                            },
                            {
                                "conditions": [TemplateConditional.SIDE_TYPE_OPEN_REGULAR_OPEN],
                                "items": [
                                    "发生涉及基金申购、赎回事项调整或潜在影响投资者赎回等重大事项时；",
                                ],
                            },
                            {
                                "conditions": [
                                    TemplateConditional.SIDE_TYPE_OPEN_REGULAR_OPEN,
                                    TemplateConditional.SPECIAL_TYPE_ETF_NO,
                                    TemplateConditional.SIDE_TYPE_CLOSE_NO,
                                    TemplateConditional.SIDE_TYPE_MONEY_NO,
                                ],
                                "items": [
                                    "基金管理人采用摆动定价机制进行估值；",
                                ],
                            },
                            {
                                "conditions": [TemplateConditional.FUND_TYPE_INDEX],
                                "items": [
                                    [
                                        "本基金变更标的指数；",
                                        "基金变更标的指数；",
                                        "变更标的指数；",
                                    ]
                                ],
                            },
                            {
                                "conditions": [TemplateConditional.SHARE_CLASSIFY_YES],
                                "items": [
                                    [
                                        "调整基金份额类别；",
                                        "调整基金份额类别的设置；",
                                    ]
                                ],
                            },
                            {
                                "conditions": [TemplateConditional.SPECIAL_TYPE_ETF],
                                "items": [
                                    [
                                        "调整最小申购、赎回单位、申购赎回方式及申购对价、赎回对价组成；",
                                        "调整最小申购赎回单位、申购赎回方式及申购对价、赎回对价组成；",
                                    ]
                                ],
                            },
                            {
                                "conditions": [TemplateConditional.LISTED_TRANSACTION_YES],
                                "items": [
                                    "本基金停复牌、暂停上市、恢复上市或终止上市；",
                                ],
                            },
                            {"conditions": [TemplateConditional.SPECIAL_TYPE_LINKED_FUND], "items": ["变更目标ETF；"]},
                            {
                                "conditions": [TemplateConditional.SIDE_TYPE_MONEY],
                                "items": [
                                    "当“摊余成本法”计算的基金资产净值与“影子定价”确定的基金资产净值偏离度绝对值达到或超过0.5%的情形；"
                                ],
                            },
                            "《基金合同》生效后，连续 30、40、45个工作日出现基金份额持有人数量不满二百人或者基金资产净值低于五千万元情形的；",
                            "本基金推出新业务或服务；",
                            "本基金实施基金份额折算；",
                            [
                                "基金信息披露义务人认为可能对基金份额持有人权益或者基金份额的价格产生重大影响的其他事项或中国证监会规定的其他事项。",
                                "中国证监会规定的其他事项。",
                            ],
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_800",
        "schema_fields": ["特殊情况的处理"],
        "related_name": "基金资产估值",
        "name": "估值-特殊情况的处理",
        "from": "",
        "origin": [],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_HANDLING_OF_SPECIAL_CASES,
                "items": [
                    {
                        "type": TemplateCheckTypeEnum.INNER_REFER.value,
                        "rules": {
                            "IRF_1": {
                                "refer_chapters": ChapterPattern.CHAPTER_FUND_ASSET_VALUATION_METHOD,
                                "default": "4",
                                "patterns": [
                                    PatternCollection(r"证据.*?不能(?:客观)?反映其?公允价值的"),
                                ],
                            },
                        },
                        "items": [
                            "十、特殊情况的处理",
                            "1、基金管理人或基金托管人按估值方法的第{IRF_1}项进行估值时，所造成的误差不作为基金资产估值错误处理。",
                            (
                                "2、由于证券交易所、期货交易所、登记机构及存款银行等第三方机构发送的数据错误，或国家会计政策变更、市场规则变更等非基金管理人与基金托管人原因，"
                                "或由于其他不可抗力原因，基金管理人和基金托管人虽然已经采取必要、适当、合理的措施进行检查，但未能发现错误或即使发现错误但因前述原因无法及时更正的，"
                                "由此造成的基金资产估值错误，基金管理人和基金托管人免除赔偿责任。但基金管理人、基金托管人应当积极采取必要的措施消除或减轻由此造成的影响。"
                            ),
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_735",
        "schema_fields": ["无需召开基金份额持有人大会的情形"],
        "related_name": "基金份额持有人大会",
        "name": "份额持有人大会-无需召开的情形",
        "from": "",
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "2、在法律法规规定和《基金合同》约定的范围内且对基金份额持有人利益无实质性不利影响的前提下，以下情况可由基金管理人和基金托管人协商后修改，不需召开基金份额持有人大会：",
            "（1）法律法规要求增加的基金费用的收取；",
            "（2）在法律法规和《基金合同》规定的范围内调整本基金的申购费率、调低赎回费率；",
            "（3）因相应的法律法规发生变动而应当对《基金合同》进行修改；",
            "（4）对《基金合同》的修改对基金份额持有人利益无实质性不利影响或修改不涉及《基金合同》当事人权利义务关系发生变化；",
            "（5）按照法律法规和《基金合同》规定不需召开基金份额持有人大会的其他情形。",
            "（公司可自行约定无需召开基金份额持有人大会的其他事项）",
        ],
        "origin": [
            "2、在法律法规规定和《基金合同》约定的范围内且对基金份额持有人利益无实质性不利影响的前提下，以下情况可由基金管理人和基金托管人协商后修改，不需召开基金份额持有人大会：",
            "（1）法律法规要求增加的基金费用的收取；",
            "（2）在法律法规和《基金合同》规定的范围内调整本基金的申购费率、调低赎回费率；",
            "（3）因相应的法律法规发生变动而应当对《基金合同》进行修改；",
            "（4）对《基金合同》的修改对基金份额持有人利益无实质性不利影响或修改不涉及《基金合同》当事人权利义务关系发生变化；",
            "（5）按照法律法规和《基金合同》规定不需召开基金份额持有人大会的其他情形。",
            "（公司可自行约定无需召开基金份额持有人大会的其他事项）",
        ],
        "templates": [
            {
                "name": TemplateName.LAW_NAME,
                "content_title": TemplateName.LAW_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_SHARE_HOLDER,
                "items": [
                    "2、在法律法规规定和《基金合同》约定的范围内且对基金份额持有人利益无实质性不利影响的前提下，以下情况可由基金管理人和基金托管人协商后修改，不需召开基金份额持有人大会：",
                    "（1）法律法规要求增加的基金费用的收取；",
                    "（2）在法律法规和《基金合同》规定的范围内调整本基金的申购费率、调低赎回费率；",
                    {
                        "conditions": [TemplateConditional.LISTED_TRANSACTION_NO],
                        "items": [
                            "（3）因相应的法律法规发生变动而应当对《基金合同》进行修改；",
                        ],
                    },
                    "（4）对《基金合同》的修改对基金份额持有人利益无实质性不利影响或修改不涉及《基金合同》当事人权利义务关系发生变化；",
                    "（5）按照法律法规和《基金合同》规定不需召开基金份额持有人大会的其他情形。",
                    "（公司可自行约定无需召开基金份额持有人大会的其他事项）",
                ],
            },
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "rule_fields": [("上市交易所", [TemplateConditional.LISTED_TRANSACTION_YES])],
                "chapter": ChapterPattern.CHAPTER_FUND_SHARE_HOLDER,
                "items": [
                    [
                        "（2）调整本基金的申购费率、调低赎回费率或者变更收费方式；",
                        "（2）在法律法规和《基金合同》规定的范围内，调整本基金的申购费率、调低赎回费率或调整收费方式、调整基金份额类别设置；",
                        "（2）调整本基金的申购费率、调低赎回费率、调低销售服务费率或变更收费方式，调整基金份额类别设置、对基金份额分类办法及规则进行调整；",
                    ],
                    {
                        "conditions": [TemplateConditional.LISTED_TRANSACTION_YES],
                        "items": [
                            {
                                "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                                "rules": {"IRP_1": {"func": "get_fund_bourse_name"}},
                                "items": [
                                    "（3）因相应的法律法规、{IRP_1}或者登记机构的相关业务规则发生变动而应当对《基金合同》进行修改；",
                                ],
                            },
                        ],
                    },
                    "（4）对《基金合同》的修改对基金份额持有人利益无实质性不利影响或修改不涉及《基金合同》当事人权利义务关系发生重大变化；",
                    {
                        "single_optional": [
                            {
                                "conditions": [TemplateConditional.SPECIAL_TYPE_ETF],
                                "items": [
                                    "（5）调整基金的申购赎回方式及申购对价、赎回对价组成；",
                                ],
                            },
                            {
                                "conditions": [TemplateConditional.FUND_TYPE_INDEX],
                                "items": [
                                    "（5）标的指数更名或调整指数编制方法，以及相应变更基金名称、业绩比较基准；",
                                ],
                            },
                            {
                                "conditions": [
                                    TemplateConditional.SPECIAL_TYPE_ETF_NO,
                                    TemplateConditional.FUND_TYPE_INDEX_NO,
                                ],
                                "items": [
                                    [
                                        "（5）基金推出新业务或服务；",
                                        "（5）在法律法规或中国证监会允许的范围内推出新业务或服务；",
                                        "",
                                    ]
                                ],
                            },
                        ],
                    },
                    {
                        "single_optional": [
                            {
                                "conditions": [TemplateConditional.SPECIAL_TYPE_ETF],
                                "items": [
                                    "（6）调整基金份额净值、申购赎回清单的内容、计算和公告的时间或频率；",
                                ],
                            },
                            {
                                "conditions": [
                                    TemplateConditional.SPECIAL_TYPE_ETF_NO,
                                    TemplateConditional.FUND_TYPE_INDEX_NO,
                                ],
                                "items": [
                                    [
                                        "（6）在法律法规和《基金合同》规定的范围内且在对基金份额持有人利益无实质性不利影响的前提下增加、调整基金份额类别设置或者停止现有基金份额类别的销售等，或对基金份额分类办法及规则进行调整；",
                                        "",
                                    ]
                                ],
                            },
                        ]
                    },
                    {
                        "conditions": [
                            TemplateConditional.SPECIAL_TYPE_ETF_NO,
                            TemplateConditional.FUND_TYPE_INDEX_NO,
                        ],
                        "items": [
                            [
                                "（7）基金管理人、销售机构、登记机构在法律法规规定的范围内调整有关基金认购、申购、赎回、转换、基金交易、非交易过户、转托管、转让、质押等业务的规则；",
                                "（7）基金管理人、登记机构、基金销售机构调整有关申购、赎回、转换、基金交易、非交易过户、转托管等业务规则；",
                                "（7）基金管理人、相关证券交易所、基金登记机构在法律法规规定或中国证监会许可的范围内调整或修改《业务规则》，"
                                "包括但不限于有关基金认购、申购、赎回、转换、基金交易、非交易过户、转托管等内容；",
                            ],
                            "（8）调整基金收益分配原则；",
                            "（9）变更业绩比较基准；",
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_732",
        "schema_fields": ["拒绝或暂停申购的情形"],
        "related_name": "基金份额的申购与赎回",
        "name": "【ETF】拒绝或暂停申购的情形",
        "from": "《公开募集开放式证券投资基金流动性风险管理规定（证监会公告[2017]12号 2017年8月31日）》",
        "origin": [
            "第十九条 基金管理人应当加强对开放式基金申购环节的管理，合理控制基金份额持有人集中度，审慎确认大额申购申请，在基金合同、招募说明书中应当对拒绝或暂停接受投资者申购申请的情形进行约定；"
            "除本规定第十四条、第二十八条约定的基金品种及中国证监会认定的特殊情形外，不得出现接受某一投资者申购申请后导致其份额超过基金总份额50%以上的情形。"
            "当接受申购申请对存量基金份额持有人利益构成潜在重大不利影响时，基金管理人应当采取设定单一投资者申购金额上限或基金单日净申购比例上限、拒绝大额申购、暂停基金申购等措施，"
            "切实保护存量基金份额持有人的合法权益。基金管理人基于投资运作与风险控制的需要，可采取上述措施对基金规模予以控制。",
            "第二十四条 基金管理人应当按照最大限度保护基金份额持有人利益的原则处理基金估值业务，加强极端市场条件下的估值业务管理。"
            "当前一估值日基金资产净值50%以上的资产出现无可参考的活跃市场价格且采用估值技术仍导致公允价值存在重大不确定性时，经与基金托管人协商确认后，"
            "基金管理人应当暂停基金估值，并采取延缓支付赎回款项或暂停接受基金申购赎回申请的措施。前述情形及处理方法应当在基金合同中事先约定。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_SUBSCRIPTION_REJECT_SUSPEND_SUBSCRIBE,
                "min_ratio": 0.4,
                "items": [
                    {
                        "type": TemplateCheckTypeEnum.INNER_REFER.value,
                        "rules": {
                            "IRF_1": {
                                "default": "6、7、8",
                                "patterns": [
                                    PatternCollection(r"接受(?:某笔|某些).*?(?:影响|损害).*?重大不利影响"),
                                    PatternCollection(
                                        r"基金管理人.*?(?:回清单中设置申购|当日总申购份额达到基金管理人所设定的)上限"
                                    ),
                                    PatternCollection(
                                        r"基金管理人.*?(?:基金份额|(单日[或]?单笔)申购份额|净申购比例).*?基金管理人所设定的上限"
                                    ),
                                ],
                            },
                        },
                        "conditions": [TemplateConditional.SPECIAL_TYPE_ETF],
                        "items": [
                            "七、拒绝或暂停申购的情形",
                            "发生下列情况时，基金管理人可拒绝或暂停接受投资人的申购申请：",
                            {
                                "type": TemplateCheckTypeEnum.RECOMBINATION.value,
                                "patterns": [
                                    PatternCollection(r"因不可抗力导致基金(无法正常运作|无法接受申购申请)"),  # 1
                                    PatternCollection(r"发生基金合同规定的?暂停基金资产估值情况时"),  # 2
                                    PatternCollection(
                                        r"交易所交易时间非正常停市.*导致.*管理人无法计算当日(基金资产净值|无法进行证券交易)"
                                    ),  # 3
                                    PatternCollection(
                                        rf"申购赎回清单.*开市后发现((申购赎回清单编制错误|基金份额参考净值计算错误)[{R_CONJUNCTION}]?){{1,}}"
                                    ),  # 4
                                    PatternCollection(
                                        rf"(((证券|期货)交易所|申购赎回代理券商|(基金)?管理人|(基金)?托管人|登记机构)[{R_CONJUNCTION}]?){{2,}}.*无法预见并不可控制的情形.*包括但不限于((系统故障|网络故障|通讯故障|电力故障|数据错误)[{R_CONJUNCTION}]?){{2,}}"
                                    ),  # 5
                                    PatternCollection(
                                        rf"接受((某笔|某些)[{R_CONJUNCTION}]?){{2}}申购申请可能会((影响|损害)[与和及或]?){{2}}((现有基金份额持有人利益|对存量基金份额持有人利益)[{R_CONJUNCTION}]?){{1,2}}"
                                    ),  # 6
                                    PatternCollection(r"管理人根据市场情况.*设置申购上限.*管理人所设定的上限"),  # 7
                                    PatternCollection(
                                        rf"管理人设定.*((上限|单日|单笔)[{R_CONJUNCTION}]?){{3}}((申购份额上限|净申购比例上限)[{R_CONJUNCTION}]?){{2}}管理人所设定的?上限"
                                    ),  # 8
                                    PatternCollection(
                                        r"规模过大.*管理人无法找到合适的?投资品种.*产生负面影响.*损害.*份额持有人利益"
                                    ),  # 9
                                    PatternCollection(r"托管人协商确认.*管理人.*暂停接受.*措施"),  # 10
                                    PatternCollection(
                                        rf"((中国证监会|法律法规规定|上海证券交易所|深圳证券交易所)[{R_CONJUNCTION+'/'}]?){{2,}}认定的?其他情形"
                                    ),  # 11
                                ],
                                "serial_num_pattern": P_PARA_PREFIX_NUM,
                                "default_prefix_type": "{num}",
                                "items": [
                                    "因不可抗力导致基金无法正常运作或无法接受申购申请；",
                                    "生基金合同规定的暂停基金资产估值情况时；",
                                    "证券/期货交易所交易时间非正常停市，导致基金管理人无法计算当日基金资产净值或无法进行证券交易。",
                                    "因异常情况，申购赎回清单无法编制、编制错误或无法公布，或基金管理人在开市后发现基金份额参考净值计算错误。",
                                    "相关证券、期货交易所、申购赎回代理券商、登记机构等因异常情况无法办理申购，或者指数编制机构、相关证券、期货交易所等因异常情况使申购赎回清单无法编制或编制不当。上述异常情况指基金管理人无法预见并不可控制的情形，包括但不限于系统故障、网络故障、通讯故障、电力故障、数据错误等。",
                                    "接受某笔或某些申购申请可能会影响或损害现有基金份额持有人利益或对存量基金份额持有人利益构成潜在重大不利影响时。",
                                    "基金管理人根据市场情况在申购赎回清单中设置申购上限且当日总申购份额达到基金管理人所设定的上限。",
                                    "基金管理人设定单个投资人累计持有的基金份额上限、单日或单笔申购份额上限和净申购比例上限且当日单个投资人的申购达到基金管理人所设定的上限。",
                                    "基金资产规模过大，使基金管理人无法找到合适的投资品种，或其他可能对基金业绩产生负面影响，或发生其他损害现有基金份额持有人利益的情形。",
                                    "当前一估值日基金资产净值 50%以上的资产出现无可参考的活跃市场价格且采用估值技术仍导致公允价值存在重大不确定性时，"
                                    "经与基金托管人协商确认后，基金管理人应当采取暂停接受基金申购申请的措施。",
                                    {
                                        "single_optional": [
                                            {
                                                "conditions": [TemplateConditional.LISTED_TRANSACTION_YES],
                                                "items": [
                                                    "法律法规规定、中国证监会或上海证券交易所/深圳证券交易所认定的其他情形。",
                                                ],
                                            },
                                            {
                                                "conditions": [TemplateConditional.LISTED_TRANSACTION_NO],
                                                "items": [
                                                    "法律法规规定、中国证监会认定的其他情形。",
                                                ],
                                            },
                                        ]
                                    },
                                ],
                            },
                            "发生上述除第{IRF_1}项以外的暂停申购情形之一且基金管理人决定暂停接受投资人的申购申请时，基金管理人应当根据有关规定在规定媒介上刊登暂停申购公告。"
                            "如果投资人的申购申请被全部或部分拒绝的，被拒绝的申购对价将退还给投资人。在暂停申购的情况消除时，基金管理人应及时恢复申购业务的办理。",
                            {
                                "conditions": [TemplateConditional.SPECIAL_TYPE_FEATURES_ETF],
                                "items": [
                                    "12、当发生指数标的成份期货合约市场价格异常波动（如连续涨/跌停）等异常情形时，或标的期货合约无法开平仓时，基金管理人可以暂停基金申购申请；",
                                    "13、本基金跟踪指数的成份期货合约出现连续多日同向单边市等情形时，基金管理人可以暂停基金申购申请；",
                                ],
                            },
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_733",
        "schema_fields": [("拒绝或暂停申购的情形", [TemplateConditional.SIDE_TYPE_MONEY])],
        "related_name": "基金份额的申购与赎回",
        "name": "【货币基金】拒绝或暂停申购的情形",
        "from": [
            "《货币市场基金监督管理办法（证监会令第120号 2015年12月17日）》",
            "《公开募集开放式证券投资基金流动性风险管理规定（证监会公告[2017]12号 2017年8月31日）》",
        ],
        "origin": [
            "第十二条 对于采用摊余成本法进行核算的货币市场基金，应当采用影子定价的风险控制手段，对摊余成本法计算的基金资产净值的公允性进行评估。"
            "当影子定价确定的基金资产净值与摊余成本法计算的基金资产净值的负偏离度绝对值达到0.25%时，基金管理人应当在5个交易日内将负偏离度绝对值调整到0.25%以内。"
            "当正偏离度绝对值达到0.5%时，基金管理人应当暂停接受申购并在5个交易日内将正偏离度绝对值调整到0.5%以内。……前述情形及处理方法应当事先在基金合同中约定并履行信息披露义务。",
            "第十四条 为了保护基金份额持有人的合法权益，基金管理人可以依照相关法律法规以及基金合同的约定，在特定市场条件下暂停或者拒绝接受一定金额以上的资金申购。",
            "第十九条 基金管理人应当加强对开放式基金申购环节的管理，合理控制基金份额持有人集中度，审慎确认大额申购申请，在基金合同、招募说明书中应当对拒绝或暂停接受投资者申购申请的情形进行约定；"
            "除本规定第十四条、第二十八条约定的基金品种及中国证监会认定的特殊情形外，不得出现接受某一投资者申购申请后导致其份额超过基金总份额50%以上的情形。"
            "当接受申购申请对存量基金份额持有人利益构成潜在重大不利影响时，基金管理人应当采取设定单一投资者申购金额上限或基金单日净申购比例上限、拒绝大额申购、暂停基金申购等措施，"
            "切实保护存量基金份额持有人的合法权益。基金管理人基于投资运作与风险控制的需要，可采取上述措施对基金规模予以控制。",
            "第十四条 基金管理人新设基金，拟允许单一投资者持有基金份额超过基金总份额50%的，应当采用封闭或定期开放运作方式且定期开放周期不得低于3个月（货币市场基金除外），"
            "并采用发起式基金形式，在基金合同、招募说明书等文件中进行充分披露及标识，且不得向个人投资者公开发售。交易型开放式指数基金及其联接基金可不受前款规定的限制。",
            "第二十八条 基金管理人新设货币市场基金，拟允许单一投资者持有基金份额比例超过基金总份额50%情形的，除应当符合本规定第十四条要求外，还应当至少符合以下情形之一：",
            "（一）不得采用摊余成本法对基金持有的组合资产进行会计核算；",
            "（二）80%以上的基金资产需投资于现金、国债、中央银行票据、政策性金融债券以及5个交易日内到期的其他金融工具。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_SUBSCRIPTION_REJECT_SUSPEND_SUBSCRIBE,
                "items": [
                    {
                        "type": TemplateCheckTypeEnum.INNER_REFER.value,
                        "rules": {
                            "IRF_1": {
                                "default": "1、2、3、4、9、10、11、13",
                                "patterns": [
                                    PatternCollection(r"不可抗力导致"),
                                    PatternCollection(r"暂停基金资产估值.*?暂停接受[\u4e00-\u9fa5]*?申购申请"),
                                    PatternCollection(r"导致[\u4e00-\u9fa5]*?无法计算[\u4e00-\u9fa5]*?资产净值"),
                                    PatternCollection(r".*?情形.*?保护.*?利益.*?暂停本基金的申购"),
                                    PatternCollection(
                                        r"基金资产规模过大.*?无法找到合适的投资品种.*?负面影响.*?损害.*?利益"
                                    ),
                                    PatternCollection(r"申购赎回(?:代理机构|登记机构).*?无法办理申购业务"),
                                    PatternCollection(
                                        r"(影子定价确定|摊余成本法计算)的基金资产净值.*?的正偏离度绝对值达到(\d*\.\d+)%"
                                    ),
                                    PatternCollection(
                                        r"当前.*?净值(\d*\.\d+)%以上的资产出现.*?重大不确定性时，经与.*?协商确认.*?采取.*?的措施"
                                    ),
                                ],
                            },
                        },
                        "conditions": [TemplateConditional.SIDE_TYPE_MONEY],
                        "items": [
                            "七、拒绝或暂停申购的情形",
                            "发生下列情况时，基金管理人可拒绝或暂停接受投资人的申购申请：",
                            "1、因不可抗力导致基金无法正常运作。",
                            "2、发生基金合同规定的暂停基金资产估值情况时，基金管理人可暂停接受投资人的申购申请。",
                            "3、证券交易所交易时间非正常停市，导致基金管理人无法计算当日基金资产净值。",
                            "4、本基金出现当日已实现收益或累计未分配已实现收益小于零的情形，为保护持有人的利益，基金管理人将暂停本基金的申购。",
                            "5、申购达到基金管理人设定的数额限制。",
                            "6、某笔申购超过基金管理人公告的单笔申购上限。",
                            "7、接受某笔或某些申购申请可能会影响或损害现有基金份额持有人利益时。",
                            "8、接受某笔或某些申购申请有可能导致单一投资者持有基金份额的比例超过50%，或者变相规避50%集中度的情形时。",
                            "9、基金资产规模过大，使基金管理人无法找到合适的投资品种，或其他可能对基金业绩产生负面影响，从而损害现有基金份额持有人利益的情形。",
                            "10、申购赎回代理机构、登记机构因异常情况无法办理申购业务。",
                            "11、当影子定价确定的基金资产净值与摊余成本法计算的基金资产净值的正偏离度绝对值达到0.5%时。",
                            "12、某笔或某些申购申请超过基金管理人设定的单日净申购比例上限、单一投资者单日或单笔申购金额上限的。",
                            "13、当前一估值日基金资产净值50%以上的资产出现无可参考的活跃市场价格且采用估值技术仍导致公允价值存在重大不确定性时，"
                            "经与基金托管人协商确认后，基金管理人应当采取暂停接受基金申购申请的措施。",
                            "14、法律法规规定或中国证监会认定的其他情形。",
                            "发生上述第{IRF_1}项暂停申购情形之一且基金管理人决定暂停申购时，基金管理人应当根据有关规定在规定媒介上刊登暂停申购公告。",
                            "如果投资人的申购申请被全部或部分拒绝的，被拒绝的申购款项本金将退还给投资人。在暂停申购的情况消除时，基金管理人应及时恢复申购业务的办理。",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_681",
        "related_name": "释义",
        "schema_fields": ["释义"],
        "name": "释义-销售和登记业务",
        "from": "《公开募集证券投资基金销售机构监督管理办法（证监会令第175号 2020年08月28日）》",
        "origin": [
            "第二条 本办法所称基金销售，是指为投资人开立基金交易账户，宣传推介基金，办理基金份额发售、申购、赎回及提供基金交易账户信息查询等活动。",
            "基金销售机构是指经中国证券监督管理委员会（以下简称中国证监会）或者其派出机构注册，取得基金销售业务资格的机构。未经注册，任何单位或者个人不得从事基金销售业务。",
            "基金服务机构从事与基金销售相关的支付、份额登记、信息技术系统等服务，适用本办法。",
            "第四十一条 基金管理人可以依照中国证监会的规定委托基金份额登记机构办理基金份额登记业务。基金份额登记机构应当确保基金份额的登记、存管和结算业务处理安全、准确、及时、高效，其主要职责包括：",
            "（一）建立并管理投资人基金份额账户；",
            "（二）负责基金份额的登记；",
            "（三）基金交易确认；",
            "（四）代理发放红利；",
            "（五）建立并保管基金份额持有人名册；",
            "（六）服务协议约定的其他职责；",
            "（七）中国证监会规定的其他职责。",
            "基金管理人变更基金份额登记机构的，应当在变更完成10个工作日内向中国证监会报告。",
        ],
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "23、基金销售业务：指基金管理人或销售机构宣传推介基金，发售基金份额，办理基金份额的申购、赎回、转换、非交易过户、转托管及定期定额投资等业务；",
            "24、销售机构：指 基金公司以及符合《销售办法》和中国证监会规定的其他条件，取得基金销售业务资格并与基金管理人签订了基金销售服务协议，办理基金销售业务的机构；",
            "25、登记业务：指基金登记、存管、过户、清算和结算业务，具体内容包括投资人基金账户的建立和管理、基金份额登记、基金销售业务的确认、清算和结算、代理发放红利、建立并保管基金份额持有人名册和办理非交易过户等；",
            "26、登记机构：指办理登记业务的机构。基金的登记机构为 或接受 委托代为办理登记业务的机构；",
            "27、基金账户：指登记机构为投资人开立的、记录其持有的、基金管理人所管理的基金份额余额及其变动情况的账户；",
            "28、基金交易账户：指销售机构为投资人开立的、记录投资人通过该销售机构办理认购、申购、赎回等业务而引起的基金份额变动及结余情况的账户（可根据实际情况增减业务类型）",
        ],
        "templates": [
            {
                "name": "范文",
                "content_title": "合同范文",
                "chapter": ChapterPattern.CHAPTER_FUND_PARAPHRASE,
                "rule_fields": ["基金管理人-名称"],
                "items": [
                    "23、基金销售业务：指基金管理人或销售机构宣传推介基金，发售基金份额，办理基金份额的申购、赎回、交易等业务；",
                    {
                        "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                        "rules": {"IRP_1": {"func": "get_fund_manage_name"}},
                        "items": [
                            [
                                "24、销售机构：指{IRP_1}以及符合《销售办法》和中国证监会规定的其他条件，取得基金销售业务资格并与基金管理人签订了基金销售服务协议，办理基金销售业务的机构。",
                                "24、销售机构：指{IRP_1}以及符合《销售办法》和中国证监会规定的其他条件，取得基金销售业务资格并与基金管理人签订了基金销售服务协议，办理基金销售业务的机构，包括发售代理机构和申购赎回代理机构。",
                            ],
                        ],
                    },
                    [
                        "25、发售代理机构：指符合《销售办法》和中国证监会规定的其他条件，由基金管理人指定的在募集期间代理本基金发售业务的机构；",
                        "25、发售代理机构：指符合《销售办法》和中国证监会规定的其他条件，由基金管理人指定的代理本基金发售业务的机构；",
                    ],
                    "26、申购赎回代理机构：指符合《销售办法》和中国证监会规定的其他条件，由基金管理人指定的、在《基金合同》生效后办理本基金申购、赎回业务的机构；",
                    {
                        "conditions": [TemplateConditional.SPECIAL_TYPE_LOF_NO],
                        "items": [
                            [
                                "27、登记业务：指基金登记、存管、过户、清算和结算业务，具体内容包括投资人基金账户的建立和管理、基金份额登记、基金销售业务的确认、清算和结算、代理发放红利、建立并保管基金份额持有人名册和办理非交易过户等；",
                                "27、登记业务：指基金登记、存管、过户、清算和结算业务，具体内容包括投资人相关账户的建立和管理、基金份额登记、基金销售业务的确认、基金交易的确认、清算和结算、代理发放红利、建立并保管基金份额持有人名册和办理非交易过户等；",
                            ],
                        ],
                    },
                    {
                        "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                        "rules": {"IRP_1": {"func": "get_fund_manage_name"}},
                        "items": [
                            {
                                "single_optional": [
                                    {
                                        "conditions": [TemplateConditional.LISTED_TRANSACTION_NO],
                                        "items": [
                                            "28、登记机构：指办理登记业务的机构。基金的登记机构为{IRP_1}或接受{IRP_1}委托代为办理登记业务的机构；",
                                        ],
                                    },
                                    {
                                        "items": [
                                            "28、登记机构：指办理登记业务的机构。基金的登记机构为中国证券登记结算有限责任公司；",
                                        ],
                                    },
                                ]
                            },
                        ],
                    },
                    {
                        "conditions": [TemplateConditional.SPECIAL_TYPE_LOF_NO],
                        "items": [
                            "29、基金账户：指登记机构为投资人开立的、记录其持有的、基金管理人所管理的基金份额余额及其变动情况的账户；",
                        ],
                    },
                    "30、基金交易账户：指销售机构为投资人开立的、记录投资人通过该销售机构办理认购、申购、赎回、转换及转托管等业务而引起的基金份额变动及结余情况的账户；",
                ],
            },
        ],
    },
    {
        "label": "template_804",
        "rule_type": RuleType.SCHEMA.value,
        "schema_fields": ["其它费用"],
        "related_name": "基金费用与税收",
        "name": "其他费用",
        "from": "",
        "origin": "上述“一、基金费用的种类”中第3－7项费用，根据有关法规及相应协议规定，按费用实际支出金额列入当期费用，由基金托管人从基金财产中支付。",
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "上述“一、基金费用的种类”中第3－7项费用，根据有关法规及相应协议规定，按费用实际支出金额列入当期费用，由基金托管人从基金财产中支付。",
            "【指数型】3、基金的指数许可使用费",
            "（请列明基金费用计提方法、标准和支付方式）",
        ],
        "templates": [
            {
                "name": TemplateName.LAW_NAME,
                "content_title": TemplateName.LAW_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_EXPENSES_STANDARD_METHOD_CALCULATION_MODE_PAYMENT,
                "items": [
                    {
                        "type": TemplateCheckTypeEnum.INNER_REFER.value,
                        "rules": {
                            "IRF_1": {
                                "refer_chapters": ChapterPattern.CHAPTER_FUND_BASIC_EXPENSE_TYPES,
                                "default": "3－7",
                                "multiple": True,
                                "patterns": [
                                    PatternCollection(r"(?<!.{2}管理|.{2}托管|销售服务)费用?.?$"),
                                ],
                            },
                        },
                        "items": [
                            "上述“一、基金费用的种类”中第{IRF_1}项费用，根据有关法规及相应协议规定，按费用实际支出金额列入当期费用，由基金托管人从基金财产中支付。",
                        ],
                    },
                ],
            },
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_EXPENSES_STANDARD_METHOD_CALCULATION_MODE_PAYMENT,
                "items": [
                    {
                        "type": TemplateCheckTypeEnum.INNER_REFER.value,
                        "rules": {
                            "IRF_1": {
                                "refer_chapters": ChapterPattern.CHAPTER_FUND_BASIC_EXPENSE_TYPES,
                                "default": "3－7",
                                "multiple": True,
                                "patterns": [
                                    PatternCollection(r"(?<!.{2}管理|.{2}托管|销售服务)费用?.?$"),
                                ],
                            },
                        },
                        "items": [
                            "上述“一、基金费用的种类”中第{IRF_1}项费用，根据有关法规及相应协议规定，按费用实际支出金额列入或摊入当期费用，由基金托管人从基金财产中支付。",
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_677",
        "related_name": "释义",
        "schema_fields": ["释义"],
        "name": "释义-基金文档和法律法规",
        "from": "",
        "origin": [
            "在本基金合同中，除非文意另有所指，下列词语或简称具有如下含义：",
            "1、基金或本基金：指 证券投资基金；",
            "2、基金管理人：指 ；",
            "3、基金托管人：指 ；",
            "4、基金合同或本基金合同：指《 证券投资基金基金合同》及对本基金合同的任何有效修订和补充；",
            "5、托管协议：指基金管理人与基金托管人就本基金签订之《 证券投资基金托管协议》及对该托管协议的任何有效修订和补充；",
            "6、招募说明书：指《 证券投资基金招募说明书》及其定期的更新；",
            "7、基金份额发售公告：指《 证券投资基金基金份额发售公告》；",
            "8、法律法规：指中国现行有效并公布实施的法律、行政法规、规范性文件、司法解释、行政规章以及其他对基金合同当事人有约束力的决定、决议、通知等；",
            "9、《基金法》：指2003年10月28日经第十届全国人民代表大会常务委员会第五次会议通过，经2012年12月28日第十一届全国人民代表大会常务委员会第三十次会议修订，"
            "自2013年6月1日起实施，并经2015年4月24日第十二届全国人民代表大会常务委员会第十四次会议《全国人民代表大会常务委员会关于修改<中华人民共和国港口法>等七部法律的决定》"
            "修正的《中华人民共和国证券投资基金法》及颁布机关对其不时做出的修订；",
            "10、《销售办法》：指中国证监会2013年3月15日颁布、同年6月1日实施的《证券投资基金销售管理办法》及颁布机关对其不时做出的修订；",
            "11、《信息披露办法》：指中国证监会2004年6月8日颁布、同年7月1日实施的《证券投资基金信息披露管理办法》及颁布机关对其不时做出的修订；",
            "12、《运作办法》：指中国证监会2014年7月7日颁布、同年8月8日实施的《公开募集证券投资基金运作管理办法》及颁布机关对其不时做出的修订；",
            "13、《流动性风险管理规定》：指中国证监会2017年8月31日颁布、同年10月1日实施的《公开募集开放式证券投资基金流动性风险管理规定》及颁布机关对其不时做出的修订；",
        ],
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "在本基金合同中，除非文意另有所指，下列词语或简称具有如下含义：",
            "1、基金或本基金：指 证券投资基金；",
            "2、基金管理人：指 ；",
            "3、基金托管人：指 ；",
            "4、基金合同或本基金合同：指《 证券投资基金基金合同》及对本基金合同的任何有效修订和补充；",
            "5、托管协议：指基金管理人与基金托管人就本基金签订之《 证券投资基金托管协议》及对该托管协议的任何有效修订和补充；",
            "6、招募说明书：指《 证券投资基金招募说明书》及其定期的更新；",
            "7、基金份额发售公告：指《 证券投资基金基金份额发售公告》；",
            "8、法律法规：指中国现行有效并公布实施的法律、行政法规、规范性文件、司法解释、行政规章以及其他对基金合同当事人有约束力的决定、决议、通知等；",
            "9、《基金法》：指2003年10月28日经第十届全国人民代表大会常务委员会第五次会议通过，经2012年12月28日第十一届全国人民代表大会常务委员会第三十次会议修订，自2013年6月1日起实施，并经2015年4月24日第十二届全国人民代表大会常务委员会第十四次会议《全国人民代表大会常务委员会关于修改<中华人民共和国港口法>等七部法律的决定》修正的《中华人民共和国证券投资基金法》及颁布机关对其不时做出的修订；",
            "10、《销售办法》：指中国证监会2013年3月15日颁布、同年6月1日实施的《证券投资基金销售管理办法》及颁布机关对其不时做出的修订；",
            "11、《信息披露办法》：指中国证监会2004年6月8日颁布、同年7月1日实施的《证券投资基金信息披露管理办法》及颁布机关对其不时做出的修订；",
            "12、《运作办法》：指中国证监会2014年7月7日颁布、同年8月8日实施的《公开募集证券投资基金运作管理办法》及颁布机关对其不时做出的修订；",
            "13、《流动性风险管理规定》：指中国证监会2017年8月31日颁布、同年10月1日实施的《公开募集开放式证券投资基金流动性风险管理规定》及颁布机关对其不时做出的修订；",
        ],
        "templates": [
            {
                "name": "范文",
                "content_title": "合同范文",
                "rule_fields": ["基金名称", "基金管理人-名称", "基金托管人-名称"],
                "chapter": ChapterPattern.CHAPTER_FUND_PARAPHRASE,
                "items": [
                    "在本基金合同中，除非文意另有所指，下列词语或简称具有如下含义：",
                    {
                        "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                        "rules": {
                            "IRP_1": {"func": "get_fund_name"},
                            "IRP_2": {"func": "get_fund_manage_name"},
                            "IRP_3": {"func": "get_fund_custodian_name"},
                        },
                        "items": [
                            "1、基金或本基金：指{IRP_1}；",
                            "2、基金管理人：指{IRP_2}；",
                            "3、基金托管人：指{IRP_3}；",
                        ],
                    },
                    {
                        "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                        "rules": {"IRP_1": {"func": "get_fund_name"}},
                        "items": [
                            "4、基金合同或本基金合同：指《{IRP_1}合同》及对本基金合同的任何有效修订和补充；",
                            "5、托管协议：指基金管理人与基金托管人就本基金签订之《{IRP_1}托管协议》及对该托管协议的任何有效修订和补充；",
                            [
                                "6、招募说明书：指《{IRP_1}招募说明书》及其更新；",
                                "6、招募说明书：指《{IRP_1}招募说明书》及其定期的更新；",
                            ],
                            "7、基金产品资料概要：指《{IRP_1}基金产品资料概要》及其更新；",
                            "8、基金份额发售公告：指《{IRP_1}基金份额发售公告》；",
                            {
                                "conditions": [TemplateConditional.LISTED_TRANSACTION_YES],
                                "items": [
                                    "9、上市交易公告书：指《{IRP_1}上市交易公告书》；",
                                ],
                            },
                        ],
                    },
                    [
                        "10、《基金法》：指2003年10月28日经第十届全国人民代表大会常务委员会第五次会议通过，经2012年12月28日第十一届全国人民代表大会常务委员会第三十次会议修订，自2013年6月1日起实施，并经2015年4月24日第十二届全国人民代表大会常务委员会第十四次会议《全国人民代表大会常务委员会关于修改<中华人民共和国港口法>等七部法律的决定》修正的《中华人民共和国证券投资基金法》及颁布机关对其不时做出的修订；",
                        "10、《基金法》：指《中华人民共和国证券投资基金法》及颁布机关对其不时做出的修订；",
                    ],
                    [
                        "11、《销售办法》：指《公开募集证券投资基金销售机构监督管理办法》及颁布机关对其不时做出的修订",
                        "11、《销售办法》：指中国证监会2020年8月28日颁布、同年10月1日实施的《公开募集证券投资基金销售机构监督管理办法》及颁布机关对其不时做出的修订",
                    ],
                    [
                        "12、《信息披露办法》：指中国证监会2019年7月26日颁布、同年9月1日实施的，并经2020年3月20日中国证监会《关于修改部分证券期货规章的决定》修正的《公开募集证券投资基金信息披露管理办法》及颁布机关对其不时做出的修订；",
                        "12、《信息披露办法》：指中国证监会2019年7月26日颁布、同年9月1日实施的《公开募集证券投资基金信息披露管理办法》及颁布机关对其不时做出的修订；",
                        "12、《信息披露办法》：指《公开募集证券投资基金信息披露管理办法》及颁布机关对其不时做出的修订；",
                    ],
                    [
                        "13、《运作办法》：指《公开募集证券投资基金运作管理办法》及颁布机关对其不时做出的修订；",
                        "13、《运作办法》：指中国证监会2014年7月7日颁布、同年8月8日实施的《公开募集证券投资基金运作管理办法》及颁布机关对其不时做出的修订；",
                    ],
                    {
                        "conditions": [TemplateConditional.SIDE_TYPE_MONEY],
                        "items": [
                            [
                                "14、《管理办法》：指中国证监会、中国人民银行2015年12月17日颁布，2016年2月1日实施的《货币市场基金监督管理办法》及颁布机关对其不时做出的修订；",
                                "14、《管理办法》：指《货币市场基金监督管理办法》及颁布机关对其不时做出的修订；",
                            ],
                        ],
                    },
                    [
                        "15、《流动性风险管理规定》：指中国证监会2017年8月31日颁布、同年10月1日实施的《公开募集开放式证券投资基金流动性风险管理规定》及颁布机关对其不时做出的修订；",
                        "15、《流动性风险管理规定》：指《公开募集开放式证券投资基金流动性风险管理规定》及颁布机关对其不时做出的修订；",
                    ],
                    {
                        "conditions": [TemplateConditional.FUND_TYPE_INDEX],
                        "items": [
                            [
                                "16、《指数基金指引》：指中国证监会2021年1月22日颁布、同年2月1日实施的《公开募集证券投资基金运作指引第3号——指数基金指引》及颁布机关对其不时做出的修订；",
                                "16、《指数基金指引》：指《公开募集证券投资基金运作指引第3号——指数基金指引》及颁布机关对其不时做出的修订；",
                            ]
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_683",
        "related_name": "释义",
        "schema_fields": ["释义"],
        "name": "释义-基金的认申赎",
        "from": "",
        "origin": [
            "38、《业务规则》：指《开放式基金业务规则》，是规范基金管理人所管理的开放式证券投资基金登记方面的业务规则，由基金管理人和投资人共同遵守（中国证券登记结算有限责任公司为注册登记机构的可另行约定）",
            "39、认购：指在基金募集期内，投资人申请购买基金份额的行为；",
            "40、申购：指基金合同生效后，投资人根据基金合同和招募说明书的规定申请购买基金份额的行为；",
            "41、赎回：指基金合同生效后，基金份额持有人按基金合同规定的条件要求将基金份额兑换为现金的行为；",
        ],
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "38、《业务规则》：指《 开放式基金业务规则》，是规范基金管理人所管理的开放式证券投资基金登记方面的业务规则，由基金管理人和投资人共同遵守（中国证券登记结算有限责任公司为注册登记机构的可另行约定）",
            "39、认购：指在基金募集期内，投资人申请购买基金份额的行为；",
            "40、申购：指基金合同生效后，投资人根据基金合同和招募说明书的规定申请购买基金份额的行为；",
            "41、赎回：指基金合同生效后，基金份额持有人按基金合同规定的条件要求将基金份额兑换为现金的行为；",
        ],
        "templates": [
            {
                "name": "法规",
                "content_title": "法规条款",
                "chapter": ChapterPattern.CHAPTER_FUND_PARAPHRASE,
                "items": [
                    "39、认购：指在基金募集期内，投资人申请购买基金份额的行为；",
                    "40、申购：指基金合同生效后，投资人根据基金合同和招募说明书的规定申请购买基金份额的行为；",
                    {
                        "conditions": [TemplateConditional.SPECIAL_TYPE_ETF_NO],
                        "items": [
                            "41、赎回：指基金合同生效后，基金份额持有人按基金合同规定的条件要求将基金份额兑换为现金的行为；",
                        ],
                    },
                ],
            },
            {
                "name": "范文",
                "content_title": "合同范文",
                "rule_fields": [("基金管理人-名称", [TemplateConditional.LISTED_TRANSACTION_NO])],
                "chapter": ChapterPattern.CHAPTER_FUND_PARAPHRASE,
                "items": [
                    {
                        "conditions": [TemplateConditional.LISTED_TRANSACTION_NO],
                        "items": [
                            {
                                "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                                "rules": {
                                    "IRP_1": {"func": "get_fund_manage_name"},
                                },
                                "items": [
                                    [
                                        "38、《业务规则》：指《{IRP_1}开放式基金业务规则》，是由基金管理人制定并不时修订，规范基金管理人所管理的开放式证券投资基金登记方面的业务规则，"
                                        "由基金管理人和投资人共同遵守;",
                                        "38、《业务规则》：指《{IRP_1}开放式基金业务规则》，是规范基金管理人所管理的开放式证券投资基金登记方面的业务规则，由基金管理人和投资人共同遵守;",
                                    ]
                                ],
                            },
                        ],
                    },
                    {
                        "conditions": [TemplateConditional.STOCK_BOURSE_SZ],
                        "items": [
                            "38、《业务规则》：指深圳证券交易所发布实施的《深圳证券交易所交易型开放式指数基金业务实施细则》及其不时修订的版本、"
                            "中国证券登记结算有限责任公司发布实施的《中国证券登记结算有限责任公司关于交易所交易型开放式证券投资基金登记结算业务实施细则》及其不时修订的版本，"
                            "以及基金管理人、深圳证券交易所、中国证券登记结算有限责任公司、销售机构发布及其不时修订的其他相关规则和规定；",
                        ],
                    },
                    {
                        "conditions": [TemplateConditional.STOCK_BOURSE_SH],
                        "items": [
                            "38、《业务规则》：指上海证券交易所发布实施的《上海证券交易所交易型开放式指数基金业务实施细则》及其不时修订的版本、"
                            "中国证券登记结算有限责任公司发布实施的《中国证券登记结算有限责任公司关于交易所交易型开放式证券投资基金登记结算业务实施细则》及其不时修订的版本，"
                            "以及基金管理人、上海证券交易所、中国证券登记结算有限责任公司、销售机构发布及其不时修订的其他相关规则和规定；",
                        ],
                    },
                    "39、认购：指在基金募集期内，投资人根据基金合同和招募说明书的规定，申请购买基金份额的行为；",
                    {
                        "conditions": [TemplateConditional.SPECIAL_TYPE_ETF_NO],
                        "items": [
                            "40、申购：指基金合同生效后，投资人根据基金合同和招募说明书的规定，申请购买基金份额的行为；",
                            "41、赎回：指基金合同生效后，基金份额持有人按基金合同和招募说明书规定的条件，要求将基金份额兑换为现金的行为；",
                        ],
                    },
                    {
                        "conditions": [TemplateConditional.SPECIAL_TYPE_ETF],
                        "items": [
                            [
                                "40、申购：指基金合同生效后，投资人根据基金合同和招募说明书的规定，申请购买基金份额的行为；",
                                "40、申购：指基金合同生效后，投资人根据基金合同和招募说明书规定的条件，以基金合同规定的对价向基金管理人购买基金份额的行为;",
                                "40、申购：指基金合同生效后，投资人根据基金合同和招募说明书的规定，以申购赎回清单规定的申购对价向基金管理人申请购买基金份额的行为",
                            ],
                            [
                                "41、赎回：指基金合同生效后，基金份额持有人按基金合同和招募说明书规定的条件，要求将基金份额兑换为基金合同所规定对价的行为；",
                                "41、赎回：指基金合同生效后，基金份额持有人按基金合同和招募说明书规定的条件，要求将基金份额兑换为赎回对价的行为；",
                                "41、赎回：指:基金合同生效后，基金份额持有人按基金合同规定的条件，要求将基金份额兑换为基金合同约定的对价资产的行为；",
                            ],
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_791",
        "schema_fields": ["投资比例", "投资限制"],
        "related_name": "基金的投资",
        "name": "投资组合比例-现金类资产",
        "from": [
            "《公开募集证券投资基金运作管理办法（证监会令第104号 2014年7月7日）》",
            "《公开募集开放式证券投资基金流动性风险管理规定（证监会公告[2017]12号 2017年8月31日）》",
        ],
        "origin": [
            "第二十八条 开放式基金应当保持不低于基金资产净值百分之五的现金或者到期日在一年以内的政府债券，以备支付基金份额持有人的赎回款项，但中国证监会规定的特殊基金品种除外。",
            "第十八条 基金管理人应当严格执行有关开放式基金资金头寸管理的相关规定，不得将结算备付金、存出保证金、应收申购款等计入《公开募集证券投资基金运作管理办法》第二十八条所规定的现金类资产范围。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_INVEST_SCOPE_INVESTMENT_RESTRICTION,
                "items": [
                    {
                        "conditions": [TemplateConditional.SIDE_TYPE_OPEN_REGULAR_OPEN],
                        "items": [
                            {
                                "type": TemplateCheckTypeEnum.INNER_RECOMBINATION.value,
                                "rules": {
                                    "IR_1": {
                                        "para_pattern": PatternCollection(r"扣除(?P<content>.+)交易保证金"),
                                        "default": "股指期货、国债期货、股票期权合约",
                                        "patterns": [
                                            {
                                                "pattern": PatternCollection(r"股指期货"),
                                                "value": "股指期货",
                                                "conditions": [TemplateConditional.SPECIAL_TYPE_STOCK_INDEX_FEATURES],
                                            },
                                            {
                                                "pattern": PatternCollection(r"国债期货"),
                                                "value": "国债期货",
                                                "conditions": [TemplateConditional.SPECIAL_TYPE_DEBT_FEATURES],
                                            },
                                            {
                                                "pattern": PatternCollection(r"股票期权(?:合约)?"),
                                                "value": "股票期权合约",
                                                "conditions": [TemplateConditional.SPECIAL_TYPE_STOCK_FEATURES],
                                            },
                                        ],
                                    },
                                },
                                "items": [
                                    [
                                        "现金或到期日在一年以内的政府债券的比例合计不低于基金资产净值的5%，其中现金不包括结算备付金、存出保证金和应收申购款等。",
                                        "本基金应当保持不低于基金资产净值的5%的现金或到期日在一年以内的政府债券，其中现金不包括结算备付金、存出保证金、应收申购款等。",
                                        "本基金每个交易日日终在扣除{IR_1}需缴纳的交易保证金以后，现金或者到期日在一年以内的政府债券不低于基金资产净值的5%，其中现金不包括结算备付金、存出保证金、应收申购款等。",
                                    ]
                                ],
                            },
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_775",
        "schema_fields": ["基金净值的确认"],
        "related_name": "基金资产估值",
        "name": "估值-净值的确认",
        "from": "",
        "origin": [
            "八、基金净值的确认",
            "用于基金信息披露的基金资产净值和基金份额净值由基金管理人负责计算，基金托管人负责进行复核。基金管理人应于每个开放日交易结"
            "束后计算当日的基金资产净值和基金份额净值并发送给基金托管人。基金托管人对净值计算结果复核确认后发送给基金管理人，由基金管理人对基金净值予以公布。",
        ],
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "八、基金净值的确认",
            "用于基金信息披露的基金资产净值和基金份额净值由基金管理人负责计算，基金托管人负责进行复核。基金管理人应于每个开放日交易结束后计算当日的基金资产净值和基金份额净值并发送给基金托管人。基金托管人对净值计算结果复核确认后发送给基金管理人，由基金管理人对基金净值予以公布。",
        ],
        "templates": [
            {
                "name": TemplateName.LAW_NAME,
                "content_title": TemplateName.LAW_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_ASSET_VALUATION_NET_VALUE,
                "items": [
                    "八、基金净值的确认",
                    "用于基金信息披露的基金资产净值和基金份额净值由基金管理人负责计算，基金托管人负责进行复核。基金管理人应于每个开"
                    "放日交易结束后计算当日的基金资产净值和基金份额净值并发送给基金托管人。基金托管人对净值计算结果复核确认后发送给基金管理人，由基金管理人对基金净值予以公布。",
                ],
            },
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_ASSET_VALUATION_NET_VALUE,
                "items": [
                    {
                        "type": TemplateCheckTypeEnum.SINGLE_SELECT.value,
                        "rules": {
                            "IS_1": {
                                "para_pattern": PatternCollection(
                                    rf"(?P<content>[^{R_NOT_CONJUNCTION_PUNCTUATION}]+)管理人负责计算"
                                ),
                                "default": "基金份额净值（基金净值信息）",
                                "patterns": [
                                    {
                                        "pattern": PatternCollection(r"份额净值"),
                                        "content": "基金份额净值",
                                    },
                                    {
                                        "pattern": PatternCollection(r"净值信息"),
                                        "content": "基金净值信息",
                                    },
                                ],
                            },
                            "IS_2": {
                                "para_pattern": PatternCollection(
                                    rf"(?P<content>[^{R_NOT_CONJUNCTION_PUNCTUATION}]+)公布"
                                ),
                                "default": "基金份额净值（基金净值信息）",
                                "patterns": [
                                    {
                                        "pattern": PatternCollection(r"份额净值"),
                                        "content": "基金份额净值",
                                    },
                                    {
                                        "pattern": PatternCollection(r"净值信息"),
                                        "content": "基金净值信息",
                                    },
                                ],
                            },
                            "IS_3": {
                                "para_pattern": PatternCollection(
                                    rf"(?P<content>[^{R_NOT_CONJUNCTION_PUNCTUATION}]+)计算[^{R_NOT_CONJUNCTION_PUNCTUATION}]+?基金资产净值"
                                ),
                                "default": "工作日（估值日）",
                                "patterns": [
                                    {
                                        "pattern": PatternCollection(r"工作日"),
                                        "content": "工作日",
                                    },
                                    {
                                        "pattern": PatternCollection(r"估值日"),
                                        "content": "估值日",
                                    },
                                ],
                            },
                        },
                        "items": [
                            {
                                "single_optional": [
                                    {
                                        "conditions": [TemplateConditional.SHARE_CLASSIFY_YES],
                                        "items": [
                                            [
                                                (
                                                    "用于基金信息披露的基金资产净值和各类{IS_1}由基金管理人负责计算，基金托管人负责进行复核。"
                                                    "基金管理人应于每个{IS_3}交易结束后计算当日的基金资产净值及各类基金份额净值并发送给基金托管人。"
                                                    "基金托管人对净值计算结果复核确认后发送给基金管理人，由基金管理人对{IS_2}予以公布。"
                                                ),
                                                (
                                                    "用于基金信息披露的基金资产净值和各类{IS_1}由基金管理人负责计算，基金托管人负责进行复核。"
                                                    "基金管理人应于每个{IS_3}交易结束后计算当日的基金资产净值及各类基金份额净值并发送给基金托管人。"
                                                    "基金托管人对净值计算结果复核确认后发送给基金管理人，由基金管理人按规定对{IS_2}予以公布。"
                                                ),
                                            ],
                                        ],
                                    },
                                    {
                                        "items": [
                                            [
                                                (
                                                    "用于基金信息披露的基金资产净值和{IS_1}由基金管理人负责计算，基金托管人负责进行复核。"
                                                    "基金管理人应于每个{IS_3}交易结束后计算当日的基金资产净值及基金份额净值并发送给基金托管人。"
                                                    "基金托管人对净值计算结果复核确认后发送给基金管理人，由基金管理人对{IS_2}予以公布。"
                                                ),
                                                (
                                                    "用于基金信息披露的基金资产净值和{IS_1}由基金管理人负责计算，基金托管人负责进行复核。"
                                                    "基金管理人应于每个{IS_3}交易结束后计算当日的基金资产净值及基金份额净值并发送给基金托管人。"
                                                    "基金托管人对净值计算结果复核确认后发送给基金管理人，由基金管理人按规定对{IS_2}予以公布。"
                                                ),
                                            ],
                                        ],
                                    },
                                ]
                            }
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_731",
        "schema_fields": ["拒绝或暂停申购的情形"],
        "related_name": "基金份额的申购与赎回",
        "name": "拒绝或暂停申购的情形",
        "from": "《公开募集开放式证券投资基金流动性风险管理规定（证监会公告[2017]12号 2017年8月31日）》",
        "origin": [
            "第十四条基金管理人新设基金，拟允许单一投资者持有基金份额超过基金总份额50%的，应当采用封闭或定期开放运作方式且定期开放周期不得低于3个月（货币市场基金除外），"
            "并采用发起式基金形式，在基金合同、招募说明书等文件中进行充分披露及标识，且不得向个人投资者公开发售。",
            "交易型开放式指数基金及其联接基金可不受前款规定的限制。",
            "第十九条基金管理人应当加强对开放式基金申购环节的管理，合理控制基金份额持有人集中度，审慎确认大额申购申请，在基金合同、招募说明书中应当对拒绝或暂停接受投资者申购申请的情形进行约定；"
            "除本规定第十四条、第二十八条约定的基金品种及中国证监会认定的特殊情形外，不得出现接受某一投资者申购申请后导致其份额超过基金总份额50%以上的情形。"
            "当接受申购申请对存量基金份额持有人利益构成潜在重大不利影响时，基金管理人应当采取设定单一投资者申购金额上限或基金单日净申购比例上限、拒绝大额申购、暂停基金申购等措施，"
            "切实保护存量基金份额持有人的合法权益。基金管理人基于投资运作与风险控制的需要，可采取上述措施对基金规模予以控制。",
            "第二十四条基金管理人应当按照最大限度保护基金份额持有人利益的原则处理基金估值业务，加强极端市场条件下的估值业务管理。",
            "当前一估值日基金资产净值50%以上的资产出现无可参考的活跃市场价格且采用估值技术仍导致公允价值存在重大不确定性时，经与基金托管人协商确认后，"
            "基金管理人应当暂停基金估值，并采取延缓支付赎回款项或暂停接受基金申购赎回申请的措施。前述情形及处理方法应当在基金合同中事先约定。",
            "第二十八条 基金管理人新设货币市场基金，拟允许单一投资者持有基金份额比例超过基金总份额50%情形的，除应当符合本规定第十四条要求外，还应当至少符合以下情形之一：",
            "（一）不得采用摊余成本法对基金持有的组合资产进行会计核算；",
            "（二）80%以上的基金资产需投资于现金、国债、中央银行票据、政策性金融债券以及5个交易日内到期的其他金融工具。",
            "第四十条 本规定相关释义如下：",
            "（四）基金管理人使用固有资金、公司高级管理人员及基金经理等人员出资认购的基金份额超过基金总份额50%的，不受本规定第十四条、第十九条的限制。",
        ],
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "七、拒绝或暂停申购的情形",
            "发生下列情况时，基金管理人可拒绝或暂停接受投资人的申购申请：",
            "1、因不可抗力导致基金无法正常运作。",
            "2、发生基金合同规定的暂停基金资产估值情况时，基金管理人可暂停接受投资人的申购申请。",
            "3、证券交易所交易时间非正常停市，导致基金管理人无法计算当日基金资产净值。",
            "4、接受某笔或某些申购申请可能会影响或损害现有基金份额持有人利益时。",
            "5、基金资产规模过大，使基金管理人无法找到合适的投资品种，或其他可能对基金业绩产生负面影响，或发生其他损害现有基金份额持有人利益的情形。",
            "6、当前一估值日基金资产净值50%以上的资产出现无可参考的活跃市场价格且采用估值技术仍导致公允价值存在重大不确定性时，经与基金托管人协商确认后，基金管理人应当暂停接受基金申购申请。",
            "7、基金管理人接受某笔或者某些申购申请有可能导致单一投资者持有基金份额的比例达到或者超过50%，或者变相规避50%集中度的情形。",
            "8、法律法规规定或中国证监会认定的其他情形。",
            "发生上述第1、2、3、5、6、8项暂停申购情形之一且基金管理人决定暂停接受投资人申购申请时，基金管理人应当根据有关规定在指定媒介上刊登暂停申购公告。如果投资人的申购申请被拒绝，被拒绝的申购款项将退还给投资人。在暂停申购的情况消除时，基金管理人应及时恢复申购业务的办理。",
        ],
        "templates": [
            {
                "name": TemplateName.LAW_NAME,
                "content_title": TemplateName.LAW_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_SUBSCRIPTION_REJECT_SUSPEND_SUBSCRIBE,
                "items": [
                    {
                        "conditions": [TemplateConditional.SPECIAL_TYPE_ETF_NO, TemplateConditional.SIDE_TYPE_MONEY_NO],
                        "items": [
                            "七、拒绝或暂停申购的情形",
                            "发生下列情况时，基金管理人可拒绝或暂停接受投资人的申购申请：",
                            "1、因不可抗力导致基金无法正常运作。",
                            "2、发生基金合同规定的暂停基金资产估值情况时，基金管理人可暂停接受投资人的申购申请。",
                            "3、证券交易所交易时间非正常停市，导致基金管理人无法计算当日基金资产净值。",
                            "4、接受某笔或某些申购申请可能会影响或损害现有基金份额持有人利益时。",
                            "5、基金资产规模过大，使基金管理人无法找到合适的投资品种，或其他可能对基金业绩产生负面影响，或发生其他损害现有基金份额持有人利益的情形。",
                            "6、当前一估值日基金资产净值50%以上的资产出现无可参考的活跃市场价格且采用估值技术仍导致公允价值存在重大不确定性时，经与基金托管人协商确认后，"
                            "基金管理人应当暂停接受基金申购申请。",
                            {
                                "single_optional": [
                                    {
                                        "conditions": [
                                            TemplateConditional.SPECIAL_TYPE_INITIATE,
                                            TemplateConditional.SIDE_TYPE_CLOSE_REGULAR_OPEN,
                                        ],
                                        "items": [
                                            [
                                                "7、基金管理人接受某笔或者某些申购申请有可能导致单一投资者持有基金份额的比例达到或者超过50%，或者变相规避50%集中度的情形。",
                                                "",
                                            ],
                                        ],
                                    },
                                    {
                                        "items": [
                                            "7、基金管理人接受某笔或者某些申购申请有可能导致单一投资者持有基金份额的比例达到或者超过50%，或者变相规避50%集中度的情形。",
                                        ]
                                    },
                                ],
                            },
                            "8、法律法规规定或中国证监会认定的其他情形。",
                        ],
                    }
                ],
            },
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_SUBSCRIPTION_REJECT_SUSPEND_SUBSCRIBE,
                "items": [
                    {
                        "conditions": [TemplateConditional.SPECIAL_TYPE_ETF_NO, TemplateConditional.SIDE_TYPE_MONEY_NO],
                        "items": [
                            {
                                "type": TemplateCheckTypeEnum.INNER_REFER.value,
                                "rules": {
                                    "IRF_1": {
                                        "default": "1、2、3、5、6、8",
                                        "patterns": [
                                            PatternCollection(r"不可抗力"),
                                            PatternCollection(r"暂停基金资产估值"),
                                            PatternCollection(r"非正常停市.+无法计算[\u4e00-\u9fa5]*?资产净值"),
                                            PatternCollection(
                                                r"(?:无法找到合适的投资品种|基金业绩产生负面影响|损害[\u4e00-\u9fa5]*?持有人利益)"
                                            ),
                                            PatternCollection(
                                                r"基金资产净值.{1,20}活跃市场价格.{1,20}重大不确定性.{1,30}暂停接受基金申购申请"
                                            ),
                                            PatternCollection(
                                                r"(?:法律法规规定|中国证监会认定)[\u4e00-\u9fa5]*?其他情形"
                                            ),
                                        ],
                                    },
                                },
                                "items": [
                                    "3、证券、期货交易所交易时间非正常停市，导致基金管理人无法计算当日基金资产净值。",
                                    "4、基金管理人认为接受某笔或某些申购申请可能会影响或损害现有基金份额持有人利益时。",
                                    {
                                        "conditions": [TemplateConditional.INVESTMENT_SCOPE_HK_STOCK],
                                        "items": [
                                            "因港股通交易当日额度使用完毕而暂停或停止接受买入申报，或者发生证券交易服务公司等机构认定的交易异常情况并决定暂停提供部分或者全部港股通服务，"
                                            "或者发生其他影响通过内地与香港股票市场交易互联互通机制进行正常交易的情形。",
                                        ],
                                    },
                                    {
                                        "conditions": [TemplateConditional.SPECIAL_TYPE_LINKED_FUND],
                                        "items": [
                                            "8、目标ETF暂停基金资产估值，导致基金管理人无法计算当日基金资产净值时。",
                                            "9、目标ETF暂停申购、暂停上市或目标ETF停牌等基金管理人认为有必要暂停本基金申购的情形。",
                                        ],
                                    },
                                    [
                                        "发生上述第{IRF_1}项暂停申购情形之一且基金管理人决定暂停接受投资人申购申请时，基金管理人应当根据有关规定在规定媒介上刊登暂停申购公告。"
                                        "如果投资人的申购申请被拒绝，被拒绝的申购款项将退还给投资人。在暂停申购的情况消除时，基金管理人应及时恢复申购业务的办理。",
                                        "发生上述第{IRF_1}项暂停申购情形之一且基金管理人决定暂停接受投资人申购申请时，基金管理人应当根据有关规定在规定媒介上刊登暂停申购公告。"
                                        "如果投资人的申购申请被全部或部分拒绝，被拒绝的申购款项将退还给投资人。在暂停申购的情况消除时，基金管理人应及时恢复申购业务的办理。",
                                    ],
                                ],
                            }
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_614",
        "schema_fields": ["申购与赎回的原则"],
        "related_name": "基金份额的申购与赎回",
        "name": "申购与赎回的原则",
        "from": "",
        "origin": [
            "三、申购与赎回的原则",
            "1、“未知价”原则，即申购、赎回价格以申请当日收市后计算的基金份额净值为基准进行计算；",
            "2、“金额申购、份额赎回”原则，即申购以金额申请，赎回以份额申请；",
            "3、当日的申购与赎回申请可以在基金管理人规定的时间以内撤销；",
            "4、赎回遵循“先进先出”原则，即按照投资人认购、申购的先后次序进行顺序赎回；",
            "5、办理申购、赎回业务时，应当遵循基金份额持有人利益优先原则，确保投资者的合法权益不受损害并得到公平对待。",
            "6、其他。",
            "基金管理人可在法律法规允许的情况下，对上述原则进行调整。基金管理人必须在新规则开始实施前依照《信息披露办法》的有关规定在指定媒介上公告。",
        ],
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "三、申购与赎回的原则",
            "1、“未知价”原则，即申购、赎回价格以申请当日收市后计算的基金份额净值为基准进行计算；",
            "2、“金额申购、份额赎回”原则，即申购以金额申请，赎回以份额申请；",
            "3、当日的申购与赎回申请可以在基金管理人规定的时间以内撤销；",
            "4、赎回遵循“先进先出”原则，即按照投资人认购、申购的先后次序进行顺序赎回；（可选）",
            "5、办理申购、赎回业务时，应当遵循基金份额持有人利益优先原则，确保投资者的合法权益不受损害并得到公平对待。",
            "6、其他。",
            "基金管理人可在法律法规允许的情况下，对上述原则进行调整。基金管理人必须在新规则开始实施前依照《信息披露办法》的有关规定在指定媒介上公告。",
        ],
        "templates": [
            {
                "name": "法规",
                "content_title": "法规条款",
                "chapter": ChapterPattern.CHAPTER_FUND_SUBSCRIPTION_PRINCIPLE,
                "items": [
                    {
                        "conditions": [TemplateConditional.SPECIAL_TYPE_ETF_NO],
                        "items": [
                            "三、申购与赎回的原则",
                            {
                                "conditions": [TemplateConditional.SHARE_CLASSIFY_NO],
                                "items": [
                                    "1、“未知价”原则，即申购、赎回价格以申请当日收市后计算的基金份额净值为基准进行计算；",
                                ],
                            },
                            "2、“金额申购、份额赎回”原则，即申购以金额申请，赎回以份额申请；",
                            "3、当日的申购与赎回申请可以在基金管理人规定的时间以内撤销；",
                            [
                                "",
                                "4、赎回遵循“先进先出”原则，即按照投资人认购、申购的先后次序进行顺序赎回；",
                            ],
                            "5、办理申购、赎回业务时，应当遵循基金份额持有人利益优先原则，确保投资者的合法权益不受损害并得到公平对待。",
                            [
                                "",
                                "6、其他。",
                            ],
                        ],
                    },
                ],
            },
            {
                "name": "范文",
                "content_title": "合同范文",
                "rule_fields": [("上市交易所", [TemplateConditional.SPECIAL_TYPE_ETF_LOF])],
                "chapter": ChapterPattern.CHAPTER_FUND_SUBSCRIPTION_PRINCIPLE,
                "items": [
                    {
                        "type": TemplateCheckTypeEnum.INNER_REPLACE.value,
                        "rules": {
                            "IRP_1": {"func": "get_fund_bourse_name"},
                            "IRP_2": {"func": "get_city_by_bourse"},
                        },
                        "items": [
                            {
                                "single_optional": [
                                    {
                                        "conditions": [TemplateConditional.SPECIAL_TYPE_ETF],
                                        "items": [
                                            "三、申购与赎回的原则",
                                            "1、申购、赎回应遵守相关《业务规则》的规定。",
                                            "2、本基金采用份额申购和份额赎回的方式，即申购和赎回均以份额申请。",
                                            "3、本基金的申购对价、赎回对价包括组合证券、现金替代、现金差额及其他对价。",
                                            "4、申购、赎回申请提交后不得撤销。",
                                            "5、基金的申购、赎回对价依据招募说明书约定的代理买卖原则确定，与受理申请当日的基金份额净值或有不同。",
                                            "6、办理申购、赎回业务时，应当遵循基金份额持有人利益优先原则，确保投资者的合法权益不受损害并得到公平对待。",
                                            "基金管理人可在法律法规允许的情况下，对上述原则进行调整，或依据{IRP_1}、登记机构相关规则及其变更调整上述原则。"
                                            "基金管理人必须在新规则开始实施前依照《信息披露办法》的有关规定在规定媒介上公告。",
                                        ],
                                    },
                                    {
                                        "items": [
                                            {
                                                "conditions": [TemplateConditional.SHARE_CLASSIFY_YES],
                                                "items": [
                                                    [
                                                        "1、“未知价”原则，即申购、赎回价格以申请当日收市后计算的该类别基金份额净值为基准进行计算；",
                                                        "1、“未知价”原则，即申购、赎回价格以申请当日收市后计算的各类基金份额净值为基准进行计算；",
                                                    ],
                                                ],
                                            },
                                            (
                                                "基金管理人可在法律法规允许的情况下，对上述原则进行调整。"
                                                "基金管理人必须在新规则开始实施前依照《信息披露办法》的有关规定在规定媒介上公告。"
                                            ),
                                        ]
                                    },
                                ]
                            },
                            {
                                "conditions": [TemplateConditional.SPECIAL_TYPE_LOF],
                                "items": [
                                    "投资者通过场外申购、赎回应使用中国证券登记结算有限责任公司开立的开放式基金账户，通过场内申购、"
                                    "赎回应使用中国证券登记结算有限责任公司{IRP_2}分公司开立的{IRP_1}（人民币普通股票账户和证券投资基金账户）；",
                                    "本基金的场内申购、赎回等业务，按照{IRP_1}、中国证券登记结算有限责任公司的相关业务规则执行。"
                                    "若相关法律法规、中国证监会、{IRP_1}或中国证券登记结算有限责任公司对申购、赎回业务等规则有新的规定，按新规定执行。",
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_782",
        "schema_fields": ["基金费用的种类"],
        "related_name": "基金费用与税收",
        "name": "基金费用的种类",
        "from": "公开募集证券投资基金运作管理办法（证监会令第104号 2014年7月7日）",
        "origin": [
            "第三十六条 下列与基金有关的费用可以从基金财产中列支：",
            "（一）基金管理人的管理费；",
            "（二）基金托管人的托管费；",
            "（三）基金合同生效后的会计师费和律师费；",
            "（四）基金份额持有人大会费用；",
            "（五）基金的证券交易费用；",
            "（六）按照国家有关规定和基金合同约定，可以在基金财产中列支的其他费用。",
            "基金管理人可以根据与基金份额持有人利益一致的原则，结合产品特点和投资者的需求设置基金管理费率的结构和水平。",
        ],
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "一、基金费用的种类",
            "1、基金管理人的管理费；",
            "2、基金托管人的托管费；",
            "3、《基金合同》生效后与基金相关的信息披露费用；",
            "4、《基金合同》生效后与基金相关的会计师费、律师费和诉讼费；",
            "5、基金份额持有人大会费用；",
            "6、基金的证券交易费用；",
            "7、基金的银行汇划费用；",
            "8、其他（可补充）",
            "9、按照国家有关规定和《基金合同》约定，可以在基金财产中列支的其他费用。",
        ],
        "templates": [
            {
                "name": TemplateName.LAW_NAME,
                "content_title": TemplateName.LAW_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_BASIC_EXPENSE_TYPES,
                "items": [
                    "1、基金管理人的管理费；",
                    "2、基金托管人的托管费；",
                    "3、《基金合同》生效后与基金相关的信息披露费用；",
                    "4、《基金合同》生效后与基金相关的会计师费、律师费和诉讼费；",
                    "5、基金份额持有人大会费用；",
                    "6、基金的证券交易费用；",
                    "7、基金的银行汇划费用；",
                    "9、按照国家有关规定和《基金合同》约定，可以在基金财产中列支的其他费用。",
                ],
            },
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_BASIC_EXPENSE_TYPES,
                "items": [
                    {
                        "conditions": [TemplateConditional.SHARE_CLASSIFY_YES],
                        "items": [
                            [
                                "3、C类基金份额的销售服务费；",
                                "3、销售服务费；",
                            ],
                        ],
                    },
                    {
                        "type": TemplateCheckTypeEnum.INNER_RECOMBINATION.value,
                        "rules": {
                            "IRB_1": {
                                "para_pattern": PatternCollection(
                                    r"与基金相关的(?P<content>(?:会计师费|律师费|诉讼费|公证费|仲裁费)[^,，。；;]+)"
                                ),
                                "default": "会计师费、律师费、诉讼费、公证费和仲裁费",
                                "patterns": [
                                    {
                                        "pattern": PatternCollection(r"会计师费"),
                                        "value": "会计师费",
                                    },
                                    {
                                        "pattern": PatternCollection(r"律师费"),
                                        "value": "律师费",
                                    },
                                    {
                                        "pattern": PatternCollection(r"诉讼费"),
                                        "value": "诉讼费",
                                    },
                                    {
                                        "pattern": PatternCollection(r"公证费"),
                                        "value": "公证费",
                                    },
                                    {
                                        "pattern": PatternCollection(r"仲裁费"),
                                        "value": "仲裁费",
                                    },
                                ],
                            },
                        },
                        "items": ["4、基金合同生效后与基金相关的{IRB_1}；"],
                    },
                    {
                        "single_optional": [
                            {
                                "conditions": [TemplateConditional.SPECIAL_TYPE_STOCK_FEATURES],
                                "items": [
                                    "6、基金的证券、期货、股票期权等交易、结算费用；",
                                ],
                            },
                            {
                                "items": [
                                    "6、基金的证券、期货等交易、结算费用；",
                                ],
                            },
                        ]
                    },
                    {
                        "single_optional": [
                            {
                                "conditions": [TemplateConditional.SPECIAL_TYPE_GOLD_ETF],
                                "items": [
                                    "8、基金的黄金现货合约交易、结算、仓储所产生的费用（包括但不限于交易手续费、延期补偿费、结算、过户费、仓储费、运保费）、其他证券交易费用；",
                                ],
                            },
                            {
                                "items": [
                                    "8、基金相关账户开户费用、账户维护费用；",
                                ],
                            },
                        ]
                    },
                    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1917#note_312858
                    {
                        "conditions": [TemplateConditional.LISTED_TRANSACTION_YES],
                        "items": [
                            "9、基金上市费及年费、IOPV计算与发布费用；",
                        ],
                    },
                    {
                        "conditions": [TemplateConditional.INVESTMENT_SCOPE_HK_STOCK],
                        "items": [
                            [
                                "10、因投资港股通标的股票而产生的各项合理费用；",
                                "10、因投资内地与香港股票市场交易互联互通机制允许买卖的香港证券市场股票而产生的各项合理费用；",
                            ],
                        ],
                    },
                    {
                        "conditions": [TemplateConditional.SPECIAL_TYPE_GOLD_ETF],
                        "items": [
                            "11、基金的黄金合约租借业务及质押业务手续费用；",
                        ],
                    },
                    {
                        "conditions": [TemplateConditional.SPECIAL_TYPE_GOLD_ETF],
                        "items": [
                            "12、黄金账户开户费用",
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_635",
        "schema_fields": ["基金备案的条件"],
        "related_name": "基金备案",
        "name": "基金备案的条件",
        "from": [
            "《公开募集证券投资基金运作管理办法（证监会令第104号 2014年7月7日）》",
            "《关于实施<公开募集证券投资基金运作管理办法>有关问题的规定（证监会公告[2014]36号 2014年7月7日）》",
            "《中华人民共和国证券投资基金法（主席令第23号 2015年4月24日修订）》",
        ],
        "origin": [
            "第十二条 基金募集期限届满，募集的基金份额总额符合《证券投资基金法》第五十九条的规定，并具备下列条件的，基金管理人应当按照规定办理验资和基金备案手续："
            "基金募集份额总额不少于两亿份，基金募集金额不少于两亿元人民币；基金份额持有人的人数不少于二百人。",
            "发起式基金不受上述限制。发起式基金是指，基金管理人在募集基金时，使用公司股东资金、公司固有资金、公司高级管理人员或者基金经理等人员资金认购基金的金额不少于一千万元人民币，"
            "且持有期限不少于三年。发起式基金的基金合同生效三年后，若基金资产净值低于两亿元的，基金合同自动终止。"
            "（六、《运作办法》第十二条第二款中，发起资金持有期限自该基金公开发售之日或者合同生效之日孰晚日起计算。）",
            "第五十八条 基金募集期限届满，封闭式基金募集的基金份额总额达到准予注册规模的百分之八十以上，开放式基金募集的基金份额总额超过准予注册的最低募集份额总额，"
            "并且基金份额持有人人数符合国务院证券监督管理机构规定的，基金管理人应当自募集期限届满之日起十日内聘请法定验资机构验资，自收到验资报告之日起十日内，"
            "向国务院证券监督管理机构提交验资报告，办理基金备案手续，并予以公告。",
            "第五十九条 基金募集期间募集的资金应当存入专门账户，在基金募集行为结束前，任何人不得动用。",
            "第六十条 投资人交纳认购的基金份额的款项时，基金合同成立；基金管理人依照本法第五十八条的规定向国务院证券监督管理机构办理基金备案手续，基金合同生效。",
        ],
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "一、基金备案的条件",
            "本基金自基金份额发售之日起3个月内，在基金募集份额总额不少于2亿份，基金募集金额不少于2亿元人民币且基金认购人数不少于200人的条件下，基金募集期届满或基金管理人依据法律法规及招募说明书可以决定停止基金发售，并在10日内聘请法定验资机构验资，自收到验资报告之日起10日内，向中国证监会办理基金备案手续。（发起式基金可另行约定）",
            "基金募集达到基金备案条件的，自基金管理人办理完毕基金备案手续并取得中国证监会书面确认之日起，《基金合同》生效；否则《基金合同》不生效。基金管理人在收到中国证监会确认文件的次日对《基金合同》生效事宜予以公告。基金管理人应将基金募集期间募集的资金存入专门账户，在基金募集行为结束前，任何人不得动用。",
        ],
        "templates": [
            {
                "name": TemplateName.LAW_NAME,
                "content_title": TemplateName.LAW_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_RECORD_CONDITIONS,
                "items": [
                    "一、基金备案的条件",
                    {
                        "conditions": [TemplateConditional.SPECIAL_TYPE_INITIATE_NO],
                        "items": [
                            "本基金自基金份额发售之日起3个月内，在基金募集份额总额不少于2亿份，基金募集金额不少于2亿元人民币且基金认购人数不少于200人的条件下，"
                            "基金募集期届满或基金管理人依据法律法规及招募说明书可以决定停止基金发售，并在10日内聘请法定验资机构验资，自收到验资报告之日起10日内，向中国证监会办理基金备案手续。",
                        ],
                    },
                    "基金募集达到基金备案条件的，自基金管理人办理完毕基金备案手续并取得中国证监会书面确认之日起，《基金合同》生效；否则《基金合同》不生效。"
                    "基金管理人在收到中国证监会确认文件的次日对《基金合同》生效事宜予以公告。基金管理人应将基金募集期间募集的资金存入专门账户，在基金募集行为结束前，任何人不得动用。",
                ],
            },
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_RECORD_CONDITIONS,
                "items": [
                    {
                        "type": TemplateCheckTypeEnum.SINGLE_SELECT.value,
                        "rules": {
                            "IS_1": {
                                "para_pattern": PatternCollection(
                                    rf"(?P<content>[^{R_NOT_CONJUNCTION_PUNCTUATION}]+)停止(?:基金|发售){{2}}[{R_PUNCTUATION}]"
                                ),
                                "default": "基金募集期届满或基金管理人依据法律法规及招募说明书可以决定",
                                "patterns": [
                                    {
                                        "pattern": PatternCollection(
                                            [
                                                rf"届满[^{R_PUNCTUATION}]*?(?:(?:法律法规|招募说明书)[^{R_PUNCTUATION}]*?){{1,2}}",
                                                rf"(?:(?:法律法规|招募说明书)[^{R_PUNCTUATION}]*?){{1,2}}届满",
                                            ]
                                        ),
                                        "content": "基金募集期届满或基金管理人依据法律法规及招募说明书可以决定",
                                    },
                                    {
                                        "pattern": PatternCollection(
                                            rf"(?:(?:法律法规|招募说明书)[^{R_PUNCTUATION}]*?){{2}}"
                                        ),
                                        "content": "基金管理人依据法律法规及招募说明书可以决定",
                                    },
                                    {
                                        "pattern": PatternCollection(r"届满"),
                                        "content": "基金募集期届满",
                                    },
                                ],
                            },
                        },
                        "items": [
                            {
                                "single_optional": [
                                    {
                                        "conditions": [TemplateConditional.SPECIAL_TYPE_INITIATE_NO],
                                        "items": [
                                            {
                                                "single_optional": [
                                                    {
                                                        "conditions": [TemplateConditional.SPECIAL_TYPE_LINKED_FUND],
                                                        "items": [
                                                            (
                                                                "本基金自基金份额发售之日起3个月内，在基金募集份额总额不少于2亿份，基金募集金额不少于2亿元人民币且基金认购人数不少于200人的条件下，"
                                                                "同时本基金目标ETF符合基金备案条件的前提下，{IS_1}停止基金发售，并在10日内聘请法定验资机构验资，"
                                                                "自收到验资报告之日起10日内，向中国证监会办理基金备案手续。"
                                                            ),
                                                        ],
                                                    },
                                                    {
                                                        "items": [
                                                            "本基金自基金份额发售之日起3个月内，在基金募集份额总额不少于2亿份，基金募集金额不少于2亿元人民币且基金认购人数不少于200人的条件下，"
                                                            "{IS_1}停止基金发售，并在10日内聘请法定验资机构验资，自收到验资报告之日起10日内，向中国证监会办理基金备案手续。",
                                                        ],
                                                    },
                                                ]
                                            },
                                        ],
                                    },
                                    {
                                        "type": TemplateCheckTypeEnum.SINGLE_SELECT.value,
                                        "rules": {
                                            "IS_2": {
                                                "para_pattern": PatternCollection(
                                                    rf"认购[\u4e00-\u9fa5]*?金额(?P<content>[^{R_PUNCTUATION}]+(?:(?:承诺|持有|期限)[^{R_PUNCTUATION}]*?){{2}}[\u4e00-\u9fa5]+)[^{R_PUNCTUATION}]"
                                                ),
                                                "default": "",
                                                "patterns": [
                                                    {
                                                        "pattern": PatternCollection(r"认购费用"),
                                                        "content": "（不含认购费用）",
                                                    },
                                                ],
                                            },
                                            "IS_3": {
                                                "para_pattern": PatternCollection(
                                                    rf"认购[\u4e00-\u9fa5]*?金额(?P<content>[^{R_PUNCTUATION}]+(?:(?:承诺|持有|期限)[^{R_PUNCTUATION}]*?){{2}}[\u4e00-\u9fa5]+)[^{R_PUNCTUATION}]"
                                                ),
                                                "default": "",
                                                "patterns": [
                                                    {
                                                        "pattern": PatternCollection(r"合同生效"),
                                                        "content": "（自基金合同生效日起）",
                                                    },
                                                ],
                                            },
                                            "IS_4": {
                                                "para_pattern": PatternCollection(
                                                    rf"(?P<content>[^{R_NOT_CONJUNCTION_PUNCTUATION}]+)验资机构[^,，。;；]"
                                                ),
                                                "default": "",
                                                "patterns": [
                                                    {
                                                        "pattern": PatternCollection(r"募集结束"),
                                                        "content": "（募集结束之日起）",
                                                    },
                                                ],
                                            },
                                        },
                                        "items": [
                                            {
                                                "single_optional": [
                                                    {
                                                        "conditions": [TemplateConditional.SPECIAL_TYPE_LINKED_FUND],
                                                        "items": [
                                                            (
                                                                "本基金自基金份额发售之日起3个月内，在发起资金提供方认购本基金的金额不少于1000万元人民币{IS_2}且承诺持有期限{IS_3}不少于3年的条件下，"
                                                                "同时本基金目标ETF符合基金备案条件的前提下，{IS_1}停止基金发售，并在{IS_4}10日内聘请法定验资机构验资，"
                                                                "验资报告需对发起资金提供方及其持有份额进行专门说明。基金管理人自收到验资报告之日起10日内，向中国证监会办理基金备案手续。"
                                                            ),
                                                        ],
                                                    },
                                                    {
                                                        "items": [
                                                            (
                                                                "本基金自基金份额发售之日起3个月内，在发起资金提供方认购本基金的金额不少于1000万元人民币{IS_2}且承诺持有期限{IS_3}不少于3年的条件下，"
                                                                "{IS_1}停止基金发售，并在{IS_4}10日内聘请法定验资机构验资，验资报告需对发起资金提供方及其持有份额进行专门说明。"
                                                                "基金管理人自收到验资报告之日起10日内，向中国证监会办理基金备案手续。"
                                                            ),
                                                        ],
                                                    },
                                                ]
                                            },
                                        ],
                                    },
                                ]
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_709",
        "related_name": "基金的收益与分配",
        "name": "收益分配-货币基金的收益分配原则",
        "from": "《货币市场基金监督管理办法（证监会令第120号 2015年12月17日）》",
        "origin": [
            "第十条 对于每日按照面值进行报价的货币市场基金，可以在基金合同中将收益分配的方式约定为红利再投资，并应当每日进行收益分配。",
            "第十五条 当日申购的基金份额应当自下一个交易日起享有基金的分配权益；当日赎回的基金份额自下一个交易日起不享有基金的分配权益，但中国证监会认定的特殊货币市场基金品种除外。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_INCOME_ALLOCATION_PRINCIPLE,
                "items": [
                    {
                        "conditions": [TemplateConditional.SIDE_TYPE_MONEY],
                        "items": [
                            "本基金收益分配应遵循下列原则：",
                            {
                                "type": TemplateCheckTypeEnum.RECOMBINATION.value,
                                "patterns": [
                                    PatternCollection(r"基金份额享有同等分配权"),  # 1
                                    PatternCollection(r"收益分配方式为?(红利再投资|现金分红)"),  # 2
                                    PatternCollection(r"当日收益.*去尾原则"),  # 3
                                    PatternCollection(r"收益大于零.*收益小于零.*收益等于零"),  # 4
                                    PatternCollection(r"下一个工作日.*享有.*不享有"),  # 5
                                    PatternCollection(r"法律法规.*基金份额持有人.*基金份额持有人大会"),  # 7
                                    PatternCollection(
                                        rf"(?:(?:法律法规|监管机构)[{R_CONJUNCTION}]?){{2}}另有规定的从其规定"
                                    ),  # 8
                                ],
                                "serial_num_pattern": P_PARA_PREFIX_NUM,
                                "default_prefix_type": "{num}",
                                "items": [
                                    "本基金同一类别内的每份基金份额享有同等分配权；",
                                    [
                                        "本基金收益分配方式为红利再投资，免收再投资的费用；",
                                        "本基金收益分配方式为现金分红；",
                                    ],
                                    "本基金根据每日基金收益情况，以基金净收益为基准，为投资人每日计算当日收益并分配。投资人当日收益分配的计算保留到小数点后2位，小数点后第3位按去尾原则处理；",
                                    "本基金根据每日收益情况，将当日收益全部分配，若当日已实现收益大于零时，为投资人记正收益；若当日已实现收益小于零时，为投资人记负收益；若当日已实现收益等于零时，当日投资人不记收益；",
                                    "当日申购的基金份额自下一个工作日起，享有基金的收益分配权益；当日赎回的基金份额自下一个工作日起，不享有基金的收益分配权益；",
                                    "在不违反法律法规且对基金份额持有人利益无实质不利影响的前提下，基金管理人可调整基金收益的分配原则和支付方式，不需召开基金份额持有人大会审议；",
                                    "法律法规或监管机构另有规定的从其规定。",
                                ],
                            },
                        ],
                    },
                ],
            }
        ],
    },
    {
        "label": "template_710",
        "related_name": "基金费用与税收",
        "name": "【FOF】不可列支的费用",
        "from": "公开募集证券投资基金运作指引第2号——基金中基金指引（证监会公告〔2016〕20号 2016年9月11日）",
        "origin": [
            "第五条 基金管理人不得对基金中基金财产中持有的自身管理的基金部分收取基金中基金的管理费。",
            "基金托管人不得对基金中基金财产中持有的自身托管的基金部分收取基金中基金的托管费。",
            "基金管理人运用基金中基金财产申购自身管理的基金的（ETF除外），应当通过直销渠道申购且不得收取申购费、赎回费（按照相关法规、基金招募说明书约定应当收取，并记入基金财产的赎回费用除外）、销售服务费等销售费用。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_BASIC_COST_REVENUE,
                "items": [
                    {
                        "conditions": [TemplateConditional.SIDE_TYPE_FOF],
                        "items": [
                            {
                                "type": TemplateCheckTypeEnum.RECOMBINATION.value,
                                "patterns": [
                                    PatternCollection(r"管理费"),
                                    PatternCollection(r"托管费"),
                                    PatternCollection(r"申购费|赎回费|销售(?:服务)?费用?"),
                                ],
                                "items": [
                                    "本基金的基金管理人不得对基金中基金财产中持有的自身管理的基金部分收取管理费。",
                                    "本基金的基金托管人不得对基金中基金财产中持有的自身托管的基金部分收取托管费。",
                                    "基金管理人运用本基金财产申购自身管理的其他基金（ETF除外），应当通过直销渠道申购且不得收取申购费、赎回费"
                                    "（按照相关法规、基金招募说明书约定应当收取，并记入基金财产的赎回费用除外）、销售服务费等销售费用。",
                                ],
                            },
                        ],
                    }
                ],
            }
        ],
    },
    {
        "label": "template_629",
        "schema_fields": ["暂停估值的情形"],
        "related_name": "基金资产估值",
        "name": "暂停估值的情形",
        "from": "公开募集开放式证券投资基金流动性风险管理规定（证监会公告[2017]12号 2017年8月31日）",
        "origin": [
            "第二十四条 基金管理人应当按照最大限度保护基金份额持有人利益的原则处理基金估值业务，加强极端市场条件下的估值业务管理。",
            "当前一估值日基金资产净值50%以上的资产出现无可参考的活跃市场价格且采用估值技术仍导致公允价值存在重大不确定性时，经与基金托管人协商确认后，"
            "基金管理人应当暂停基金估值，并采取延缓支付赎回款项或暂停接受基金申购赎回申请的措施。前述情形及处理方法应当在基金合同中事先约定。",
        ],
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "七、暂停估值的情形",
            "1、基金投资所涉及的证券交易市场遇法定节假日或因其他原因暂停营业时；",
            "2、因不可抗力致使基金管理人、基金托管人无法准确评估基金资产价值时；",
            "3、当特定资产占前一估值日基金资产净值50%以上的，经与基金托管人协商确认后，基金管理人应当暂停估值；",
            "4、中国证监会和基金合同认定的其它情形。",
        ],
        "templates": [
            {
                "name": TemplateName.LAW_NAME,
                "content_title": TemplateName.LAW_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_SITUATION_VALUATION_SUSPENDED,
                "items": [
                    "七、暂停估值的情形",
                    {
                        "type": TemplateCheckTypeEnum.RECOMBINATION.value,
                        "patterns": [
                            PatternCollection(r"法定节假日|暂?停止?营业"),
                            PatternCollection(r"不可抗力|评估(?:基金)?资产"),
                            PatternCollection(
                                rf"特定资产占[^{R_PUNCTUATION}]*?基金资产净值|与(?:基金)?托管人协商.*?暂停估值"
                            ),
                            PatternCollection(r"证监会|合同.*?其它情形"),
                        ],
                        "serial_num_pattern": P_PARA_PREFIX_NUM,
                        "default_prefix_type": "{num}",
                        "items": [
                            "基金投资所涉及的证券交易市场遇法定节假日或因其他原因暂停营业时；",
                            "因不可抗力致使基金管理人、基金托管人无法准确评估基金资产价值时；",
                            "当特定资产占前一估值日基金资产净值50%以上的，经与基金托管人协商确认后，基金管理人应当暂停估值；",
                            "中国证监会和基金合同认定的其它情形。",
                        ],
                    },
                ],
            },
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_SITUATION_VALUATION_SUSPENDED,
                "items": [
                    {
                        "type": TemplateCheckTypeEnum.RECOMBINATION.value,
                        "patterns": [
                            PatternCollection(r"法定节假日|暂?停止?营业"),
                            PatternCollection(r"不可抗力|评估(?:基金)?资产"),
                            PatternCollection(r"公允价值|与(?:基金)?托管人协商.*?暂停估值"),
                            PatternCollection(r"证监会|合同.*?其它情形"),
                            PatternCollection(r"投资基金.*?暂停(?:估值|公告)"),
                            PatternCollection(r"ETF.*?暂停(?:估值|公告)"),
                        ],
                        "serial_num_pattern": P_PARA_PREFIX_NUM,
                        "default_prefix_type": "{num}",
                        "items": [
                            [
                                "基金投资所涉及的证券/期货交易市场遇法定节假日或因其他原因暂停营业时；",
                                "基金投资所涉及的证券、期货交易市场遇法定节假日或因其他原因暂停营业时；",
                            ],
                            "因不可抗力或其他情形致使基金管理人、基金托管人无法准确评估基金资产价值时；",
                            "当前一估值日基金资产净值50%以上的资产出现无可参考的活跃市场价格且采用估值技术仍导致公允价值存在重大不确定性时，经与基金托管人协商确认后，基金管理人应当暂停估值；",
                            "法律法规、中国证监会和基金合同认定的其他情形。",
                            {
                                "conditions": [TemplateConditional.SIDE_TYPE_FOF],
                                "items": [
                                    [
                                        "占本基金相当比例的被投资基金发生暂停估值、暂停公告基金份额净值或暂停公告万份（百份）收益的情形；",
                                        "占相当比例的被投资基金发生暂停估值、暂停公告基金份额净值时；",
                                    ]
                                ],
                            },
                            {
                                "conditions": [TemplateConditional.SPECIAL_TYPE_LINKED_FUND],
                                "items": [
                                    [
                                        "所投资的目标ETF暂停估值、暂停公告基金份额净值时；",
                                        "目标ETF发生暂停估值、暂停公告基金份额净值的情形；",
                                    ]
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_609",
        "schema_fields": ["基金管理人代表基金行使股东或债权人权利的处理原则及方法"],
        "related_name": "基金的投资",
        "name": "投资-管理人代表基金行使股东或债权人权利的处理原则及方法",
        "from": "",
        "origin": [
            "七、基金管理人代表基金行使股东或债权人权利的处理原则及方法",
            "1、基金管理人按照国家有关规定代表基金独立行使股东或债权人权利，保护基金份额持有人的利益；",
            "2、不谋求对上市公司的控股；",
            "3、有利于基金财产的安全与增值；",
            "4、不通过关联交易为自身、雇员、授权代理人或任何存在利害关系的第三人牟取任何不当利益。",
        ],
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "七、基金管理人代表基金行使股东或债权人权利的处理原则及方法",
            "1、基金管理人按照国家有关规定代表基金独立行使股东或债权人权利，保护基金份额持有人的利益；",
            "2、不谋求对上市公司的控股； ",
            "3、有利于基金财产的安全与增值； ",
            "4、不通过关联交易为自身、雇员、授权代理人或任何存在利害关系的第三人牟取任何不当利益。",
        ],
        "templates": [
            {
                "name": "法规",
                "content_title": "法规条款",
                "chapter": ChapterPattern.CHAPTER_FUND_INVEST_PRINCIPLE,
                "min_ratio": 0.4,
                "items": [
                    "七、基金管理人代表基金行使股东或债权人权利的处理原则及方法",
                    {
                        "type": TemplateCheckTypeEnum.RECOMBINATION.value,
                        "patterns": [
                            PatternCollection(rf"管理人.*?保护[^{R_PUNCTUATION}]*?利益"),
                            PatternCollection(r"控股"),
                            PatternCollection(rf"财产[^{R_PUNCTUATION}]*?(?:安全|增值)"),
                            PatternCollection(r"关联交易.*?[牟谋获][取求得].*?利益"),
                        ],
                        "serial_num_pattern": P_PARA_PREFIX_NUM,
                        "default_prefix_type": "{num}",
                        "items": [
                            "基金管理人按照国家有关规定代表基金独立行使股东或债权人权利，保护基金份额持有人的利益；",
                            "不谋求对上市公司的控股；",
                            "有利于基金财产的安全与增值；",
                            "不通过关联交易为自身、雇员、授权代理人或任何存在利害关系的第三人牟取任何不当利益。",
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_745",
        "schema_fields": ["投资限制"],
        "related_name": "基金的投资",
        "name": "投资限制-股指期货",
        "from": "证券投资基金参与股指期货交易指引（证监会公告〔2010〕13号 2010年4月21日）",
        "origin": [
            "第五条 基金参与股指期货交易，除中国证监会另有规定或批准的特殊基金品种外，应当遵守下列要求：",
            "（一）基金在任何交易日日终，持有的买入股指期货合约价值，不得超过基金资产净值的10%。",
            "（二）开放式基金在任何交易日日终，持有的买入期货合约价值与有价证券市值之和,不得超过基金资产净值的95%。",
            "封闭式基金、开放式指数基金（不含增强型）、交易型开放式指数基金（ETF）在任何交易日日终，持有的买入期货合约价值与有价证券市值之和,不得超过基金资产净值的100%。",
            "其中，有价证券指股票、债券（不含到期日在一年以内的政府债券）、权证、资产支持证券、买入返售金融资产（不含质押式回购）等。",
            "（三）基金在任何交易日日终，持有的卖出期货合约价值不得超过基金持有的股票总市值的20%。",
            "基金管理公司应当按照中国金融期货交易所要求的内容、格式与时限向交易所报告所交易和持有的卖出期货合约情况、交易目的及对应的证券资产情况等。",
            "（四）基金所持有的股票市值和买入、卖出股指期货合约价值，合计（轧差计算）应当符合基金合同关于股票投资比例的有关约定。",
            "（五）基金在任何交易日内交易（不包括平仓）的股指期货合约的成交金额不得超过上一交易日基金资产净值的20%。",
            "（六）开放式基金（不含ETF）每个交易日日终在扣除股指期货合约需缴纳的交易保证金后，应当保持不低于基金资产净值5%的现金或到期日在一年以内的政府债券。",
            "（七）封闭式基金、ETF每个交易日日终在扣除股指期货合约需缴纳的交易保证金后，应当保持不低于交易保证金一倍的现金。",
            "（八）保本基金参与股指期货交易不受上述第（一）项至第（七）项的限制，但应当符合基金合同约定的保本策略和投资目标，"
            "且每日所持期货合约及有价证券的最大可能损失不得超过基金净资产扣除用于保本部分资产后的余额。担保机构应当充分了解保本基金的股指期货交易策略和可能损失，并在担保协议中作出专门说明。",
            "（九）法律法规、基金合同规定的其他比例限制。",
            "因证券期货市场波动、基金规模变动等基金管理人之外的因素致使基金投资比例不符合上述要求的，基金管理人应当在10个交易日之内调整完毕。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_INVEST_SCOPE_INVESTMENT_RESTRICTION,
                "items": [
                    {
                        "type": TemplateCheckTypeEnum.RECOMBINATION.value,
                        "patterns": [
                            PatternCollection(r"交易日?日终.*?买入.*?股指期货(?:合约)?价值"),
                            PatternCollection(
                                rf"有价证券.?(?:(?:股票|债券|资产支持证券|买入返售金融资产)[{R_CONJUNCTION}]?){{2,}}"
                            ),
                            PatternCollection(r"交易日?日终.*?卖出.*?股指期货(?:合约)?价值"),
                            PatternCollection(
                                rf"(?:(?:买入|卖出)[{R_CONJUNCTION}]?){{2}}股指期货(?:合约)?.*股票投资比例"
                            ),
                            PatternCollection(r"交易.*?股指期货(?:合约)?的?(?:成交)?金额.*?基金资产净值"),
                            PatternCollection(r"交易日日?终.扣除股指期货(?:合约)?.*?[交缴付].{0,2}的交易保证金"),
                        ],
                        "serial_num_pattern": P_PARA_PREFIX_NUM,
                        "default_prefix_type": "{num}）",
                        "conditions": [TemplateConditional.SPECIAL_TYPE_STOCK_INDEX_FEATURES],
                        "items": [
                            "在任何交易日日终，持有的买入股指期货合约价值，不得超过基金资产净值的10%；",
                            {
                                "single_optional": [
                                    {
                                        "conditions": [TemplateConditional.SIDE_TYPE_REGULAR_OPEN],
                                        "items": [
                                            "在任何交易日日终，持有的买入期货合约价值与有价证券市值之和，不得超过基金资产净值的95%，"
                                            "其中，有价证券指股票、债券（不含到期日在一年以内的政府债券）、资产支持证券、买入返售金融资产（不含质押式回购）等；",
                                        ],
                                    },
                                    {
                                        "conditions": [TemplateConditional.SPECIAL_TYPE_ETF_OR_CLOSE],
                                        "items": [
                                            [
                                                "在任何交易日日终，持有的买入期货合约价值与有价证券市值之和，不得超过基金资产净值的100%，"
                                                "其中，有价证券指股票、债券（不含到期日在一年以内的政府债券）、资产支持证券、买入返售金融资产（不含质押式回购）等；",
                                                "在任何交易日日终，持有的买入期货合约价值与有价证券市值之和，不得超过基金资产净值的100%；"
                                                "其中，有价证券指股票、债券（不含到期日在一年以内的政府债券）、资产支持证券、买入返售金融资产（不含质押式回购）等；",
                                            ]
                                        ],
                                    },
                                    {
                                        "conditions": [
                                            TemplateConditional.SIDE_TYPE_OPEN,
                                            TemplateConditional.FUND_TYPE_ENHANCE_INDEX_NO,
                                            TemplateConditional.FUND_TYPE_INDEX,
                                        ],
                                        "items": [
                                            [
                                                "在任何交易日日终，持有的买入期货合约价值与有价证券市值之和，不得超过基金资产净值的100%，"
                                                "其中，有价证券指股票、债券（不含到期日在一年以内的政府债券）、资产支持证券、买入返售金融资产（不含质押式回购）等；",
                                                "在任何交易日日终，持有的买入期货合约价值与有价证券市值之和，不得超过基金资产净值的100%；"
                                                "其中，有价证券指股票、债券（不含到期日在一年以内的政府债券）、资产支持证券、买入返售金融资产（不含质押式回购）等；",
                                            ]
                                        ],
                                    },
                                    {
                                        "conditions": [
                                            TemplateConditional.SIDE_TYPE_OPEN,
                                            TemplateConditional.FUND_TYPE_ENHANCE_INDEX_OR_NO_INDEX,
                                        ],
                                        "items": [
                                            "在任何交易日日终，持有的买入期货合约价值与有价证券市值之和，不得超过基金资产净值的95%，"
                                            "其中，有价证券指股票、债券（不含到期日在一年以内的政府债券）、资产支持证券、买入返售金融资产（不含质押式回购）等；",
                                        ],
                                    },
                                ]
                            },
                            "在任何交易日日终，持有的卖出期货合约价值不得超过基金持有的股票总市值的20%；",
                            "持有的股票市值和买入、卖出股指期货合约价值，合计（轧差计算）应当符合基金合同关于股票投资比例的有关约定；",
                            "在任何交易日内交易（不包括平仓）的股指期货合约的成交金额不得超过上一交易日基金资产净值的20%；",
                            {
                                "single_optional": [
                                    {
                                        "conditions": [TemplateConditional.SIDE_TYPE_REGULAR_OPEN],
                                        "items": [
                                            "每个交易日日终，扣除股指期货合约需缴纳的交易保证金后，保持不低于基金资产净值5%的现金或者到期日在一年以内的政府债券，"
                                            "其中现金不包括结算备付金、存出保证金和应收申购款等；",
                                        ],
                                    },
                                    {
                                        "conditions": [
                                            TemplateConditional.SIDE_TYPE_OPEN,
                                            TemplateConditional.SPECIAL_TYPE_ETF_NO,
                                        ],
                                        "items": [
                                            "每个交易日日终，扣除股指期货合约需缴纳的交易保证金后，保持不低于基金资产净值5%的现金或者到期日在一年以内的政府债券，"
                                            "其中现金不包括结算备付金、存出保证金和应收申购款等；",
                                        ],
                                    },
                                    {
                                        "conditions": [
                                            TemplateConditional.SPECIAL_TYPE_ETF_OR_CLOSE,
                                        ],
                                        "items": [
                                            "每个交易日日终在扣除股指期货合约需缴纳的交易保证金后，应当保持不低于交易保证金一倍的现金。",
                                        ],
                                    },
                                ]
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_776",
        "schema_fields": ["不列入基金费用的项目"],
        "related_name": "基金费用与税收",
        "name": "不列入基金费用的项目",
        "from": "",
        "origin": [
            "三、不列入基金费用的项目",
            "下列费用不列入基金费用：",
            "1、基金管理人和基金托管人因未履行或未完全履行义务导致的费用支出或基金财产的损失；",
            "2、基金管理人和基金托管人处理与基金运作无关的事项发生的费用；",
            "3、《基金合同》生效前的相关费用；",
            "4、其他根据相关法律法规及中国证监会的有关规定不得列入基金费用的项目。",
        ],
        "contract_content": [
            "《证券投资基金基金合同填报指引第1、2、3号》（证监会201104）",
            "三、不列入基金费用的项目",
            "下列费用不列入基金费用：",
            "1、基金管理人和基金托管人因未履行或未完全履行义务导致的费用支出或基金财产的损失；",
            "2、基金管理人和基金托管人处理与基金运作无关的事项发生的费用；",
            "3、《基金合同》生效前的相关费用；",
            "4、其他根据相关法律法规及中国证监会的有关规定不得列入基金费用的项目。",
        ],
        "templates": [
            {
                "name": TemplateName.LAW_NAME,
                "content_title": TemplateName.LAW_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_BASIC_ITEMS_NOT_INCLUDED_FUND_COSTS,
                "items": [
                    {
                        "conditions": [TemplateConditional.FUND_TYPE_INDEX_NO],
                        "items": [
                            "三、不列入基金费用的项目",
                            "下列费用不列入基金费用：",
                            "1、基金管理人和基金托管人因未履行或未完全履行义务导致的费用支出或基金财产的损失；",
                            "2、基金管理人和基金托管人处理与基金运作无关的事项发生的费用；",
                            "3、《基金合同》生效前的相关费用；",
                            "4、其他根据相关法律法规及中国证监会的有关规定不得列入基金费用的项目。",
                        ],
                    },
                ],
            },
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_BASIC_ITEMS_NOT_INCLUDED_FUND_COSTS,
                "items": [
                    {
                        "conditions": [TemplateConditional.FUND_TYPE_INDEX],
                        "items": [
                            "三、不列入基金费用的项目",
                            "下列费用不列入基金费用：",
                            {
                                "type": TemplateCheckTypeEnum.RECOMBINATION.value,
                                "patterns": [
                                    PatternCollection(rf"(?:(?:基金管理人|基金托管人)[{R_CONJUNCTION}]?){{1,2}}因"),
                                    PatternCollection(rf"(?:(?:基金管理人|基金托管人)[{R_CONJUNCTION}]?){{1,2}}处理"),
                                    PatternCollection(r"《?基金合同》?生效前的?相关费用"),
                                    PatternCollection(
                                        rf"规定.?不.?列入基金费用的[{R_NOT_CONJUNCTION_PUNCTUATION}]*?项目"
                                    ),
                                    PatternCollection(r"标的指数许可使用费|指数许可使用费"),
                                ],
                                "serial_num_pattern": P_PARA_PREFIX_NUM,
                                "default_prefix_type": "{num}",
                                "items": [
                                    "基金管理人和基金托管人因未履行或未完全履行义务导致的费用支出或基金财产的损失；",
                                    "基金管理人和基金托管人处理与基金运作无关的事项发生的费用；",
                                    "《基金合同》生效前的相关费用；",
                                    "其他根据相关法律法规及中国证监会的有关规定不得列入基金费用的项目。",
                                    [
                                        "基金的标的指数许可使用费，本基金的标的指数许可使用费由基金管理人承担；",
                                        "基金标的指数许可使用费（由基金管理人承担）；",
                                        "标的指数许可使用费；标的指数许可使用费由基金管理人承担，不得从基金财产中列支；",
                                        "指数许可使用费；",
                                    ],
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_746",
        "schema_fields": ["投资限制"],
        "related_name": "基金的投资",
        "name": "投资限制-国债期货",
        "from": "公开募集证券投资基金参与国债期货交易指引（证监会公告〔2013〕37号 2013年9月3日）",
        "origin": [
            "第五条 基金参与国债期货交易，除中国证监会另有规定或批准的特殊基金品种外，应当遵守下列要求：",
            "（一）基金在任何交易日日终，持有的买入国债期货合约价值，不得超过基金资产净值的15%。",
            "（二）开放式基金在任何交易日日终，持有的买入国债期货和股指期货合约价值与有价证券市值之和,不得超过基金资产净值的95%。",
            "封闭式基金、开放式指数基金（不含增强型）、交易型开放式指数基金（ETF）在任何交易日日终，持有的买入国债期货和股指期货合约价值与有价证券市值之和,"
            "不得超过基金资产净值的100%。其中，有价证券指股票、债券（不含到期日在一年以内的政府债券）、权证、资产支持证券、买入返售金融资产（不含质押式回购）等。",
            "债券基金参与国债期货交易不受本项限制，但应当符合基金合同约定的投资策略和投资目标。",
            "（三）基金在任何交易日日终，持有的卖出国债期货合约价值不得超过基金持有的债券总市值的30%。",
            "基金管理人应当按照中国金融期货交易所要求的内容、格式与时限向交易所报告所交易和持有的卖出期货合约情况、交易目的及对应的证券资产情况等。",
            "（四）基金所持有的债券（不含到期日在一年以内的政府债券）市值和买入、卖出国债期货合约价值，合计（轧差计算）应当符合基金合同关于债券投资比例的有关约定。",
            "（五）基金在任何交易日内交易（不包括平仓）的国债期货合约的成交金额不得超过上一交易日基金资产净值的30%。",
            "（六）开放式基金（不含ETF）每个交易日日终在扣除国债期货和股指期货合约需缴纳的交易保证金后，应当保持不低于基金资产净值5%的现金或到期日在一年以内的政府债券。",
            "（七）封闭式基金、ETF每个交易日日终在扣除国债期货和股指期货合约需缴纳的交易保证金后，应当保持不低于交易保证金一倍的现金。",
            "（八）保本基金参与国债期货交易不受上述第（一）项至第（七）项的限制，但应当符合基金合同约定的保本策略和投资目标，"
            "且每日所持期货合约及有价证券的最大可能损失不得超过基金净资产扣除用于保本部分资产后的余额。担保机构应当充分了解保本基金的国债期货交易策略和可能损失，并在担保协议中作出专门说明。",
            "（九）法律法规、基金合同规定的其他比例限制。",
            "因证券期货市场波动、基金规模变动等基金管理人之外的因素致使基金投资比例不符合上述要求的，基金管理人应当在10个交易日之内调整完毕。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_INVEST_SCOPE_INVESTMENT_RESTRICTION,
                "min_ratio": 0.5,
                "items": [
                    {
                        "conditions": [TemplateConditional.SPECIAL_TYPE_DEBT_FEATURES],
                        "items": [
                            "本基金参与国债期货交易，还应遵循如下投资组合限制：",
                            {
                                "type": TemplateCheckTypeEnum.RECOMBINATION.value,
                                "patterns": [
                                    PatternCollection(r"交易日?日终.*?买入.*?国债期货(?:合约)?价值"),
                                    PatternCollection(
                                        rf"有价证券.?(?:(?:股票|债券|资产支持证券|买入返售金融资产)[{R_CONJUNCTION}]?){{2,}}"
                                    ),
                                    PatternCollection(r"交易日?日终.*?卖出.*?国债期货(?:合约)?价值"),
                                    PatternCollection(
                                        rf"(?:(?:买入|卖出)[{R_CONJUNCTION}]?){{2}}国债期货.*?债券投资比例"
                                    ),
                                    PatternCollection(r"交易.*?国债期货(?:合约)?的?(?:成交)?金额.*?基金资产净值"),
                                    PatternCollection(r"交易日日?终.扣除国债期货(?:合约)?.*?[交缴付].{0,2}交易保证金"),
                                ],
                                "serial_num_pattern": P_PARA_PREFIX_NUM,
                                "default_prefix_type": "{num}）",
                                "items": [
                                    "在任何交易日日终，持有的买入国债期货合约价值不得超过基金资产净值的15%；",
                                    {
                                        "single_optional": [
                                            {"conditions": [TemplateConditional.FUND_TYPE_BOND], "items": [""]},
                                            {
                                                "conditions": [TemplateConditional.SIDE_TYPE_REGULAR_OPEN],
                                                "items": [
                                                    [
                                                        "在任何交易日日终，持有的买入国债期货和股指期货合约价值与有价证券市值之和,不得超过基金资产净值的95%，"
                                                        "其中，有价证券指股票、债券（不含到期日在一年以内的政府债券）、资产支持证券、买入返售金融资产（不含质押式回购）等；",
                                                        "在任何交易日日终，持有的买入国债期货和股指期货合约价值与有价证券市值之和,不得超过基金资产净值的95%；"
                                                        "其中，有价证券指股票、债券（不含到期日在一年以内的政府债券）、资产支持证券、买入返售金融资产（不含质押式回购）等；",
                                                    ]
                                                ],
                                            },
                                            {
                                                "conditions": [TemplateConditional.SPECIAL_TYPE_ETF_OR_CLOSE],
                                                "items": [
                                                    [
                                                        "在任何交易日日终，持有的买入国债期货和股指期货合约价值与有价证券市值之和，不得超过基金资产净值的100%，"
                                                        "其中，有价证券指股票、债券（不含到期日在一年以内的政府债券）、资产支持证券、买入返售金融资产（不含质押式回购）等",
                                                        "在任何交易日日终，持有的买入国债期货和股指期货合约价值与有价证券市值之和，不得超过基金资产净值的100%；"
                                                        "其中，有价证券指股票、债券（不含到期日在一年以内的政府债券）、资产支持证券、买入返售金融资产（不含质押式回购）等",
                                                    ]
                                                ],
                                            },
                                            {
                                                "conditions": [
                                                    TemplateConditional.SIDE_TYPE_OPEN,
                                                    TemplateConditional.FUND_TYPE_ENHANCE_INDEX_NO,
                                                ],
                                                "items": [
                                                    [
                                                        "在任何交易日日终，持有的买入国债期货和股指期货合约价值与有价证券市值之和，不得超过基金资产净值的100%，"
                                                        "其中，有价证券指股票、债券（不含到期日在一年以内的政府债券）、资产支持证券、买入返售金融资产（不含质押式回购）等",
                                                        "在任何交易日日终，持有的买入国债期货和股指期货合约价值与有价证券市值之和，不得超过基金资产净值的100%；"
                                                        "其中，有价证券指股票、债券（不含到期日在一年以内的政府债券）、资产支持证券、买入返售金融资产（不含质押式回购）等",
                                                    ]
                                                ],
                                            },
                                            {
                                                "conditions": [
                                                    TemplateConditional.SIDE_TYPE_OPEN,
                                                    TemplateConditional.FUND_TYPE_ENHANCE_INDEX_OR_NO_INDEX,
                                                ],
                                                "items": [
                                                    [
                                                        "在任何交易日日终，持有的买入国债期货和股指期货合约价值与有价证券市值之和,不得超过基金资产净值的95%，"
                                                        "其中，有价证券指股票、债券（不含到期日在一年以内的政府债券）、资产支持证券、买入返售金融资产（不含质押式回购）等；",
                                                        "在任何交易日日终，持有的买入国债期货和股指期货合约价值与有价证券市值之和,不得超过基金资产净值的95%；"
                                                        "其中，有价证券指股票、债券（不含到期日在一年以内的政府债券）、资产支持证券、买入返售金融资产（不含质押式回购）等；",
                                                    ]
                                                ],
                                            },
                                        ]
                                    },
                                    "在任何交易日日终，持有的卖出国债期货合约价值不得超过基金持有的债券总市值的30%；",
                                    "持有的债券（不含到期日在一年以内的政府债券）市值和买入、卖出国债期货合约价值，合计（轧差计算）应当符合基金合同关于债券投资比例的有关约定；",
                                    "在任何交易日内交易（不包括平仓）的国债期货合约的成交金额不得超过上一交易日基金资产净值的30%；",
                                    {
                                        "single_optional": [
                                            {
                                                "conditions": [TemplateConditional.SIDE_TYPE_REGULAR_OPEN],
                                                "items": [
                                                    "每个交易日日终在扣除国债期货和股指期货合约需缴纳的交易保证金后，应当保持不低于基金资产净值5%的现金或到期日在一年以内的政府债券。",
                                                ],
                                            },
                                            {
                                                "conditions": [
                                                    TemplateConditional.SIDE_TYPE_OPEN,
                                                    TemplateConditional.SPECIAL_TYPE_ETF_NO,
                                                ],
                                                "items": [
                                                    "每个交易日日终在扣除国债期货和股指期货合约需缴纳的交易保证金后，应当保持不低于基金资产净值5%的现金或到期日在一年以内的政府债券。",
                                                ],
                                            },
                                            {
                                                "conditions": [
                                                    TemplateConditional.SPECIAL_TYPE_ETF_OR_CLOSE,
                                                ],
                                                "items": [
                                                    "每个交易日日终在扣除国债期货和股指期货合约需缴纳的交易保证金后，应当保持不低于交易保证金一倍的现金。",
                                                ],
                                            },
                                        ]
                                    },
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_670",
        "schema_fields": ["基金份额的上市", "基金份额的上市交易"],
        "related_name": "基金份额的上市交易",
        "name": "基金份额的上市交易",
        "from": [
            "《深圳证券交易所证券投资基金上市规则（2006年02月13日 深证会[2006]3号）》",
            "《上海证券交易所证券投资基金上市规则（修订稿）（2007年08月29日 债券基金部[2007]62号）》",
        ],
        "origin": [
            "第五条 基金在本所上市，应当符合下列条件：",
            "（一）经中国证券监督管理委员会（以下简称“中国证监会”）核准募集且基金合同生效；",
            "（二）基金合同期限为五年以上；",
            "（三）基金募集金额不低于二亿元人民币；",
            "（四）基金份额持有人不少于一千人；",
            "（五）本所规定的其他条件。",
            "第七条 基金符合上市条件的，本所向基金管理人出具《上市通知书》，并与基金管理人签订上市协议。",
            "第四条 基金在本所上市，应符合下列条件：",
            "（一）经中国证监会核准发售且基金合同生效；",
            "（二）基金合同期限五年以上；",
            "（三）基金募集金额不低于二亿元人民币；",
            "（四）基金份额持有人不少于一千人；",
            "（五）有经核准的基金管理人和基金托管人；",
            "（六）本所要求的其他条件。",
            "第七条 基金上市前，基金管理人应与本所签定上市协议书。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_LISTED_LISTED_TRANSACTION,
                "items": [
                    {
                        "conditions": [TemplateConditional.LISTED_TRANSACTION_YES],
                        "items": [
                            {
                                "type": TemplateCheckTypeEnum.INNER_RECOMBINATION.value,
                                "rules": {
                                    "IRB_1": {
                                        "para_pattern": PatternCollection(
                                            r"基金份额在深圳证券交易所的上市交易.?[应须需]遵照(?P<content>.*)等有关规定"
                                        ),
                                        "default": "《深圳证券交易所交易规则》、《深圳证券交易所证券投资基金上市规则》、《深圳证券交易所证券投资基金交易和申购赎回实施细则》",
                                        "exclude_patterns": PatternCollection(
                                            rf"(?:(?:交易|申购)[{R_CONJUNCTION}]?){{2}}"
                                        ),
                                        "patterns": [
                                            {
                                                "pattern": PatternCollection(r"《深圳证券交易所交易规则》"),
                                                "value": "《深圳证券交易所交易规则》",
                                            },
                                            {
                                                "pattern": PatternCollection(r"《深圳证券交易所证券投资基金上市规则》"),
                                                "value": "《深圳证券交易所证券投资基金上市规则》",
                                            },
                                            {
                                                "pattern": PatternCollection(
                                                    r"《深圳证券交易所证券投资基金交易和申购赎回实施细则》"
                                                ),
                                                "value": "《深圳证券交易所证券投资基金交易和申购赎回实施细则》",
                                            },
                                        ],
                                    },
                                },
                                "conditions": [TemplateConditional.STOCK_BOURSE_SZ],
                                "items": [
                                    "一、基金份额的上市",
                                    "基金合同生效后，具备下列条件的，基金管理人可依据《深圳证券交易所证券投资基金上市规则》，向深圳证券交易所申请基金份额上市：",
                                    [
                                        "1、基金募集金额不低于2亿元；",
                                        "1、基金募集金额（含网下股票认购所募集的股票市值）不低于2亿元人民币；",
                                    ],
                                    "2、基金份额持有人不少于1000人；",
                                    "3、《深圳证券交易所证券投资基金上市规则》规定的其他条件。",
                                    [
                                        "基金份额上市前，基金管理人应与深圳证券交易所签订上市协议书。基金获准在深圳证券交易所上市的，基金管理人应按照相关规定发布基金上市交易公告书",
                                        "基金份额上市前，基金管理人应与深圳证券交易所签订上市协议书。基金获准在深圳证券交易所上市的，基金管理人应在基金份额上市日的3个工作日前发布基金份额上市交易公告书。",
                                    ],
                                    "二、基金份额的上市交易",
                                    "基金份额在深圳证券交易所的上市交易，应遵照{IRB_1}等有关规定。",
                                ],
                            },
                            {
                                "type": TemplateCheckTypeEnum.INNER_RECOMBINATION.value,
                                "rules": {
                                    "IRB_2": {
                                        "para_pattern": PatternCollection(
                                            r"基金份额在上海证券交易所的上市交易.?[应须需]遵照(?P<content>.*)等有关规定"
                                        ),
                                        "default": "《上海证券交易所交易规则》、《上海证券交易所证券投资基金上市规则》、《上海证券交易所交易型开放式指数基金业务实施细则》",
                                        "patterns": [
                                            {
                                                "pattern": PatternCollection(r"《上海证券交易所交易规则》"),
                                                "value": "《上海证券交易所交易规则》",
                                            },
                                            {
                                                "pattern": PatternCollection(r"《上海证券交易所证券投资基金上市规则》"),
                                                "value": "《上海证券交易所证券投资基金上市规则》",
                                            },
                                            {
                                                "pattern": PatternCollection(
                                                    r"《上海证券交易所交易型开放式指数基金业务实施细则》"
                                                ),
                                                "value": "《上海证券交易所交易型开放式指数基金业务实施细则》",
                                            },
                                        ],
                                    },
                                },
                                "conditions": [TemplateConditional.STOCK_BOURSE_SH],
                                "items": [
                                    "一、基金份额的上市",
                                    "基金合同生效后，具备下列条件的，基金管理人可依据《上海证券交易所证券投资基金上市规则》，向上海证券交易所申请基金份额上市：",
                                    "1、基金场内资产净值不少于2亿元；",
                                    "2、基金场内份额持有人不少于1000人；",
                                    "3、符合上海证券交易所规定的其他条件。",
                                    "二、基金份额的上市交易",
                                    "本基金基金份额在上海证券交易所的上市交易需遵照{IRB_2}等有关规定。",
                                    "在确定上市交易的时间后，基金管理人应依据法律法规规定在规定媒介上刊登基金份额上市交易公告书。",
                                ],
                            },
                        ],
                    }
                ],
            },
        ],
    },
]
