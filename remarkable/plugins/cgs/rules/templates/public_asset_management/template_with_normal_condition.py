from remarkable.plugins.cgs.common.chapters_patterns import ChapterPattern
from remarkable.plugins.cgs.common.template_condition import AssetTemplateConditional, TemplateName

example = [
    {
        "label": "template_10000",
        "schema_fields": [],
        "related_name": "",
        "name": "",
        "from": "",
        "origin": "",
        "templates": [
            {
                "name": TemplateName.LAW_NAME,
                "content_title": TemplateName.LAW_TITLE,
                # 'chapter': ChapterPattern.CHAPTER_FUND_ASSET_VALUATION_ERROR_HANDLING,
                "items": [],
            },
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                # 'chapter': ChapterPattern.CHAPTER_FUND_CUSTODY_FUND_TRUSTEE,
                "items": [],
            },
        ],
    },
]

TEMPLATE_WITH_MULTI_EXPRESSION = [
    {
        "label": "template_1010",
        "related_name": "释义",
        "name": "释义-7个工作日可变现资产",
        "from": "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）",
        "origin": [
            "第四十七条 本规定下列用语的含义：",
            "……",
            "（四）7个工作日可变现资产，包括可在交易所、银行间市场正常交易的股票、债券、非金融企业债务融资工具、期货及标准化期权合约和同业存单，7个工作日内到期或者可支取的逆回购、银行存款，7个工作日内能够确认收到的各类应收款项等。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_PARAPHRASE,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            [
                                "7个工作日可变现资产：包括可在交易所、银行间市场正常交易的股票、债券、非金融企业债务融资工具、期货及标准化期权合约和同业存单，7个工作日内到期或者可支取的逆回购、银行存款，7个工作日内能够确认收到的各类应收款项等。",
                                "",
                            ]
                        ],
                    },
                ],
            }
        ],
    },
    {
        "label": "template_1007",
        "related_name": "",
        "name": "前言-协会备案要求及其声明",
        "from": "",
        "origin": "",
        "contract_content": [
            "【单一&集合】",
            "第十四条 说明管理人应当对资产管理计划的设立、变更、展期、终止、清算等行为向证券投资基金业协会进行备案，并抄报中国证监会相关派出机构。",
            "说明证券投资基金业协会接受资产管理计划备案不能免除管理人按照规定真实、准确、完整、及时地披露产品信息的法律责任，也不代表证券投资基金业协会对资产管理计划的合规性、投资价值及投资风险做出保证和判断。投资者应当自行识别产品投资风险并承担投资行为可能出现的损失。",
        ],
        "templates": [
            {
                "name": TemplateName.LAW_NAME,
                "content_title": TemplateName.LAW_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_FOREWORD,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            "管理人应当对资产管理计划的设立、变更、展期、终止、清算等行为向证券投资基金业协会进行备案，并抄报中国证监会相关派出机构。",
                            "证券投资基金业协会接受资产管理计划备案不能免除管理人按照规定真实、准确、完整、及时地披露产品信息的法律责任，也不代表证券投资基金业协会对资产管理计划的合规性、投资价值及投资风险做出保证和判断。投资者应当自行识别产品投资风险并承担投资行为可能出现的损失。",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1008",
        "related_name": "释义",
        "name": "释义-家庭金融总资产",
        "from": "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）",
        "origin": [
            "第四十七条 本规定下列用语的含义：",
            "……",
            "（二）家庭金融总资产，是指全体家庭成员共有的全部金融资产，包括银行存款、股票、债券、基金份额、资产管理计划、银行理财产品、信托计划、保险产品、期货和衍生品等。家庭金融净资产是指家庭金融总资产减去全体家庭成员的全部负债。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_PARAPHRASE,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            [
                                "家庭金融总资产：是指全体家庭成员共有的全部金融资产，包括银行存款、股票、债券、基金份额、资产管理计划、银行理财产品、信托计划、保险产品、期货和衍生品等。家庭金融净资产是指家庭金融总资产减去全体家庭成员的全部负债。",
                                "",
                            ]
                        ],
                    }
                ],
            }
        ],
    },
    {
        "label": "template_1009",
        "related_name": "释义",
        "name": "释义-流动性受限资产",
        "from": "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）",
        "origin": [
            "第四十七条 本规定下列用语的含义：",
            "……",
            "（三）流动性受限资产，是指由于法律法规、监管、合同或者操作障碍等原因无法以合理价格予以变现的资产，包括到期日在10个交易日以上的逆回购与银行定期存款（含协议约定有条件提前支取的银行存款）、资产支持证券（票据）、流动受限的新股以及非公开发行股票、停牌股票、因发行人债务违约无法进行转让或交易的债券和非金融企业债务融资工具等资产。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_PARAPHRASE,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            [
                                "流动性受限资产：是指由于法律法规、监管、合同或者操作障碍等原因无法以合理价格予以变现的资产，包括到期日在10个交易日以上的逆回购与银行定期存款（含协议约定有条件提前支取的银行存款）、资产支持证券（票据）、流动受限的新股以及非公开发行股票、停牌股票、因发行人债务违约无法进行转让或交易的债券和非金融企业债务融资工具等资产。",
                                "",
                            ]
                        ],
                    }
                ],
            }
        ],
    },
    {
        "label": "template_1014",
        "related_name": "承诺与声明",
        "name": "合规投资者的条件",
        "from": "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）",
        "origin": [
            "第三条 资产管理计划应当向合格投资者非公开募集。合格投资者是指具备相应风险识别能力和风险承受能力，投资于单只资产管理计划不低于一定金额且符合下列条件的自然人、法人或者其他组织：",
            "（一）具有2年以上投资经历，且满足下列三项条件之一的自然人：家庭金融净资产不低于300万元，家庭金融资产不低于500万元，或者近3年本人年均收入不低于40万元；",
            "（二）最近1年末净资产不低于1000万元的法人单位；",
            "（三）依法设立并接受国务院金融监督管理机构监管的机构，包括证券公司及其子公司、基金管理公司及其子公司、期货公司及其子公司、在中国证券投资基金业协会（以下简称证券投资基金业协会）登记的私募基金管理人、商业银行、商业银行理财子公司、金融资产投资公司、信托公司、保险公司、保险资产管理机构、财务公司及中国证监会认定的其他机构；",
            "（四）接受国务院金融监督管理机构监管的机构发行的资产管理产品；",
            "（五）基本养老金、社会保障基金、年金基金等养老基金，慈善基金等社会公益基金，合格境外机构投资者（QFII）、人民币合格境外机构投资者（RQFII）；",
            "（六）中国证监会视为合格投资者的其他情形。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_COMMITMENTS_STATEMENTS,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            "（一）具有2年以上投资经历，且满足下列三项条件之一的自然人：家庭金融净资产不低于300万元，家庭金融资产不低于500万元，或者近3年本人年均收入不低于40万元；",
                            "（二）最近1年末净资产不低于1000万元的法人单位；",
                            "（三）依法设立并接受国务院金融监督管理机构监管的机构，包括证券公司及其子公司、基金管理公司及其子公司、期货公司及其子公司、在中国证券投资基金业协会（以下简称证券投资基金业协会）登记的私募基金管理人、商业银行、商业银行理财子公司、金融资产投资公司、信托公司、保险公司、保险资产管理机构、财务公司及中国证监会认定的其他机构；",
                            "（四）接受国务院金融监督管理机构监管的机构发行的资产管理产品；",
                            "（五）基本养老金、社会保障基金、年金基金等养老基金，慈善基金等社会公益基金，合格境外机构投资者（QFII）、人民币合格境外机构投资者（RQFII）；",
                            "（六）中国证监会视为合格投资者的其他情形。",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1015",
        "schema_fields": [
            "计划托管人-名称",
            "计划托管人-住所",
            "计划托管人-通讯地址",
            "计划托管人-法定代表人或授权代表",
            "计划托管人-联系电话",
        ],
        "related_name": "当事人及权利义务",
        "name": "托管人的基础信息",
        "from": "",
        "origin": "",
        "contract_content": [
            "【集合】",
            "第十七条 订明投资者、管理人和托管人的基本情况，包括但不限于姓名/名称、住所、联系人、通讯地址、联系电话等信息，投资者基本情况可在资产管理合同签署页列示。",
            "【单一】",
            "第十七条 订明投资者、管理人和托管人（如有）的基本情况，包括但不限于姓名/名称、住所、联系人、通讯地址、联系电话等信息。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            "名称：中国银河证券股份有限公司",
                            "住所：北京市丰台区西营街8号院1号楼7至18层101",
                            "通讯地址：北京市丰台区西营街8号院1号楼青海金融大厦",
                            "法定代表人：陈亮",
                            "联系电话：95551",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1016",
        "related_name": "当事人及权利义务",
        "name": "集合计划份额均等且具有同等权益",
        "from": "",
        "origin": "",
        "contract_content": "第十八条 说明资产管理计划应当设定为均等份额。除资产管理合同另有约定外，每份份额具有同等的合法权益。",
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_DUTY_POWER,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_POOLED],
                        "items": [
                            "资产管理计划应当设定为均等份额。除资产管理合同另有约定外，每份份额具有同等的合法权益。",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1031",
        "related_name": "资产管理计划的成立与备案",
        "name": "资管计划的成立与备案",
        "from": "证券期货经营机构私募资产管理业务管理办法（证监会令第203号修订 2023年1月12日）",
        "origin": [
            "第三十二条 集合资产管理计划在募集金额缴足之日起十个工作日内，由证券期货经营机构公告资产管理计划成立；单一资产管理计划在受托资产入账后，由证券期货经营机构书面通知投资者资产管理计划成立。",
            "第三十三条 证券期货经营机构应当在资产管理计划成立之日起五个工作日内，将资产管理合同、投资者名单与认购金额资产缴付证明等材料报证券投资基金业协会备案。",
            "证券投资基金业协会应当制定资产管理计划备案规则，明确工作程序和期限，并向社会公开。",
        ],
        "contract_content": [
            "【集合】",
            "第三十条 订明资产管理计划的募集金额缴足之日起10个工作日内，管理人应当委托具有证券相关业务资格的会计师事务所进行验资并出具验资报告，并在取得验资报告后公告资产管理计划成立。管理人应在资产管理计划成立起5个工作日内报证券投资基金业协会备案，抄报中国证监会相关派出机构。资产管理计划成立前，任何机构和个人不得动用投资者参与资金。",
            "【单一】",
            "第二十六条 订明资产管理计划在受托资产入账后，管理人书面通知投资者资产管理计划成立。管理人应在资产管理计划成立起5个工作日内报证券投资基金业协会备案，抄报中国证监会相关派出机构。资产管理计划成立前，任何机构和个人不得动用投资者参与资金。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGE_PLAN_ESTABLISHMENT_FILING,
                "items": [
                    {
                        "single_optional": [
                            {
                                "conditions": [AssetTemplateConditional.NAME_SINGLE],
                                "items": [
                                    "【1】资产管理计划在受托资产入账后，由管理人书面通知投资者资产管理计划成立。",
                                ],
                            },
                            {
                                "conditions": [AssetTemplateConditional.NAME_POOLED],
                                "items": [
                                    [
                                        "【1】本计划在募集金额缴足之日起十个工作日内，由管理人公告资产管理计划成立。",
                                        "【1】资产管理人应当自本计划募集金额缴足之日起十个工作日内公告本计划成立。",
                                    ]
                                ],
                            },
                        ]
                    },
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            [
                                "【2】管理人应当在资产管理计划成立之日起五个工作日内，将资产管理合同、投资者名单与认购金额资产缴付证明等材料报证券投资基金业协会备案。",
                                "【2】管理人应在资产管理计划成立后5个工作日内报证券投资基金业协会备案。",
                            ]
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_1032",
        "related_name": "资产管理计划的成立与备案",
        "name": "资管计划备案前投资",
        "from": "",
        "origin": "",
        "contract_content": [
            "【单一&集合】",
            "第三十一条 订明资产管理计划在成立后备案完成前，不得开展投资活动，以现金管理为目的，投资于银行活期存款、国债、中央银行票据、政策性金融债、地方政府债券、货币市场基金等中国证监会认可的投资品种的除外。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGE_PLAN_ESTABLISHMENT_FILING,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            "资产管理计划在成立后备案完成前，不得开展投资活动，以现金管理为目的，投资于银行活期存款、国债、中央银行票据、政策性金融债、地方政府债券、货币市场基金等中国证监会认可的投资品种的除外。",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1034",
        "related_name": "资产管理计划的参与、退出与转让",
        "name": "投资者参与和退出的金额限制",
        "from": "",
        "origin": "",
        "contract_content": [
            "【集合】",
            "第三十三条 订明开放式资产管理计划在运作期间，投资者参与和退出资产管理计划的有关事项，包括但不限于：",
            "（一）参与和退出场所；",
            "（二）参与和退出的开放日和时间，包括但不限于符合《运作规定》的开放频率、开放时限、通知方式等；",
            "（三） 临时开放期的触发条件、程序及披露等相关安排；",
            "（四）参与和退出的方式、价格、程序及确认等；",
            "（五）参与和退出的金额限制。订明投资者在资产管理计划存续期开放日购买资产管理计划份额的，投资者应符合合格投资者标准，且参与金额应满足资产管理计划最低参与金额限制（不含参与费用），已持有资产管理计划份额的投资者在资产管理计划存续期开放日追加购买资产管理计划份额的除外。投资者部分退出资产管理计划的，其退出后持有的资产管理计划份额净值应当不低于规定的合格投资者最低参与金额。投资者持有的资产管理计划份额净值低于规定的最低投资金额时，需要退出资产管理计划的，应当一次性全部退出。",
            "（六）参与和退出的费用；",
            "（七）参与份额的计算方式、退出金额的计算方式；",
            "（八）参与资金的利息处理方式（如有）；",
            "（九） 巨额退出或连续巨额退出的认定标准、退出顺序、退出价格确定、退出款项支付、告知客户方式，以及单个客户大额退出的预约申请等事宜，相关约定应符合公平、合理、公开的原则；",
            "（十）延期支付及延期退出的情形和处理方式；",
            "（十一）拒绝或暂停参与、暂停退出的情形及处理方式；",
            "（十二）其他事项。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGE_PLAN_PARTICIPATION_WITHDRAWAL_TRANSFER,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_POOLED],
                        "items": [
                            "【1】投资者在资产管理计划存续期开放日购买资产管理计划份额的，投资者应符合合格投资者标准，且参与金额应满足资产管理计划最低参与金额限制（不含参与费用），已持有资产管理计划份额的投资者在资产管理计划存续期开放日追加购买资产管理计划份额的除外。",
                            "【2】投资者部分退出资产管理计划的，其退出后持有的资产管理计划份额净值应当不低于规定的合格投资者最低参与金额。投资者持有的资产管理计划份额净值低于规定的最低投资金额时，需要退出资产管理计划的，应当一次性全部退出。",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1036",
        "related_name": "资产管理计划的参与、退出与转让",
        "name": "集合计划的份额转让机制",
        "from": "证券期货经营机构私募资产管理业务管理办法（证监会令第203号修订 2023年1月12日）",
        "origin": [
            "第三十六条 投资者可以通过证券交易所以及中国证监会认可的其他方式，向合格投资者转让其持有的集合资产管理计划份额，并按规定办理份额变更登记手续。转让后，持有资产管理计划份额的合格投资者合计不得超过二百人。",
            "证券期货经营机构应当在集合资产管理计划份额转让前，对受让人的合格投资者身份和资产管理计划的投资者人数进行合规性审查。受让方首次参与集合资产管理计划的，应当先与证券期货经营机构、托管人签订资产管理合同。",
            "证券期货经营机构、交易场所不得通过办理集合资产管理计划的份额转让，公开或变相公开募集资产管理计划。",
        ],
        "contract_content": [
            "【集合】",
            "第三十四条 资产管理合同中可以约定投资者在资产管理计划投资运作期间的份额转让事宜。",
            "投资者可以通过证券交易所以及中国证监会认可的其他方式，向合格投资者转让其持有的资产管理计划份额，份额转让应遵守交易场所相关规定及要求，并按规定办理份额变更登记手续。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGE_PLAN_PARTICIPATION_WITHDRAWAL_TRANSFER,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_POOLED],
                        "items": [
                            "【1】投资者可以通过证券交易所以及中国证监会认可的其他方式，向合格投资者转让其持有的资产管理计划份额，份额转让应遵守交易场所相关规定及要求，并按规定办理份额变更登记手续。",
                            "投资者可以通过证券交易所以及中国证监会认可的其他方式，向合格投资者转让其持有的集合资产管理计划份额，并按规定办理份额变更登记手续。",
                            [
                                "【2】转让后，持有资产管理计划份额的合格投资者合计不得超过二百人。",
                                "",
                            ],
                            [
                                "【3】管理人应当在资产管理计划份额转让前，对受让人的合格投资者身份和资产管理计划的投资者人数进行合规性审查。受让方首次参与资产管理计划的，应当先与管理人、托管人签订资产管理合同。",
                                "",
                            ],
                            [
                                "【4】管理人、交易场所不得通过办理集合资产管理计划的份额转让，公开或变相公开募集资产管理计划。",
                                "",
                            ],
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1038",
        "related_name": "资产管理计划的参与、退出与转让",
        "name": "集合计划管理人自有资金的参与和退出",
        "from": [
            "证券期货经营机构私募资产管理业务管理办法（证监会令第203号修订 2023年1月12日）",
            "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）",
        ],
        "origin": [
            "第三十五条 证券期货经营机构以自有资金参与集合资产管理计划，应当符合法律、行政法规和中国证监会的规定，并按照《中华人民共和国公司法》和公司章程的规定，获得公司股东会、董事会或者其他授权程序的批准。证券期货经营机构自有资金所持的集合资产管理计划份额，应当与投资者所持的同类份额享有同等权益、承担同等风险。",
            "第十条 证券期货经营机构自有资金参与、退出集合资产管理计划的，应当提前5个工作日告知全体投资者和托管人，并取得其同意；证券期货经营机构自有资金参与集合资产管理计划的，持有期限不得少于6个月。",
            "证券期货经营机构及其子公司以自有资金参与其自身或其子公司管理的单个集合资产管理计划的份额合计不得超过该资产管理计划总份额的50%。中国证监会对证券期货经营机构自有资金投资比例另有规定的，从其规定。因集合资产管理计划规模变动等客观因素导致前述比例被动超标的，证券期货经营机构应当依照中国证监会规定及资产管理合同的约定及时调整达标。",
            "为应对集合资产管理计划巨额赎回以解决流动性风险，或者中国证监会认可的其他情形，在不存在利益冲突并遵守合同约定的前提下，证券期货经营机构及其子公司以自有资金参与及其后续退出集合资产管理计划可不受本条第一款、第二款规定的限制，但应当及时告知投资者和托管人，并向中国证监会相关派出机构报告。",
        ],
        "contract_content": [
            "【集合】",
            "第三十六条 订明管理人以自有资金参与资产管理计划的条件、方式、金额、比例以及管理人自有资金退出的条件。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGE_PLAN_PARTICIPATION_WITHDRAWAL_TRANSFER,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_POOLED],
                        "items": [
                            "【1】管理人以自有资金参与本计划，应当符合法律、行政法规和中国证监会的规定，并按照《中华人民共和国公司法》和公司章程的规定，获得公司股东会、董事会或者其他授权程序的批准。",
                            "【2】管理人以自有资金投资所持的本计划份额，与投资者所持的份额享有同等权益、承担同等风险。",
                            "【3】管理人自有资金参与、退出本计划的，应当提前5个工作日告知全体投资者和托管人，并取得其同意；",
                            "【4】管理人自有资金参与本计划的，持有期限不得少于6个月。",
                            "【5】管理人及其子公司以自有资金参与本计划的份额合计不得超过本计划总份额的50%。中国证监会对证券期货经营机构自有资金投资比例另有规定的，从其规定。因本计划规模变动等客观因素导致前述比例被动超标的，管理人应当依照中国证监会规定及资产管理合同的约定及时调整达标。",
                            "【6】为应对本计划巨额赎回以解决流动性风险，或者中国证监会认可的其他情形，在不存在利益冲突并遵守合同约定的前提下，管理人及其子公司以自有资金参与及其后续退出本计划可不受上述限制，但应当及时告知投资者和托管人，并向中国证监会相关派出机构报告。",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1039",
        "related_name": "资产管理计划的参与、退出与转让",
        "name": "集合计划管理人应定期报送投资者变更情况",
        "from": "",
        "origin": "",
        "contract_content": [
            "【集合】",
            "第三十七条 订明管理人应定期将资产管理计划投资者变更情况报送证券投资基金业协会。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGE_PLAN_PARTICIPATION_WITHDRAWAL_TRANSFER,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_POOLED],
                        "items": [
                            "管理人应定期将资产管理计划投资者变更情况报送证券投资基金业协会",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1050",
        "related_name": "资产管理计划的投资",
        "name": "投资-建仓期及其投资安排",
        "from": "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）",
        "origin": [
            "第十三条 资产管理合同应当明确约定资产管理计划的建仓期。集合资产管理计划的建仓期自产品成立之日起不得超过6个月，专门投资于未上市企业股权的集合资产管理计划除外。",
            "建仓期的投资活动，应当符合资产管理合同约定的投向和资产管理计划的风险收益特征。以现金管理为目的，投资于银行活期存款、国债、中央银行票据、政策性金融债、地方政府债券、货币市场基金等中国证监会认可的投资品种的除外。",
            "建仓期结束后，资产管理计划的资产组合应当符合法律、行政法规、中国证监会规定和合同约定的投向和比例。",
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
                            "【1】本计划的建仓期为自本计划成立之日起6个月。",
                            "【2】本计划建仓期的投资活动，应当符合本合同约定的投向和资产管理计划的风险收益特征。以现金管理为目的，投资于银行活期存款、国债、中央银行票据、政策性金融债、地方政府债券、货币市场基金等中国证监会认可的投资品种的除外。",
                            "【3】建仓期结束后，资产管理计划的资产组合应当符合法律、行政法规、中国证监会规定和合同约定的投向和比例。",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1042",
        "related_name": "份额持有人大会及日常机构",
        "name": "集合计划份额持有人大会-特殊事项决议",
        "from": "",
        "origin": "",
        "contract_content": [
            "【集合】",
            "第四十二条 根据《基金法》和其他有关规定订明资产管理计划份额持有人大会及/或日常机构的下列事项：……",
            "（六）更换资产管理计划管理人或者托管人、提前终止资产管理合同等对投资者产生重要影响的特殊决议事项，应当经参加大会的资产管理计划份额持有人所持表决权的三分之二以上通过。",
        ],
        "templates": [
            {
                "name": TemplateName.LAW_NAME,
                "content_title": TemplateName.LAW_TITLE,
                "chapter": ChapterPattern.CHAPTER_GENERAL_ASSEMBLY_DAILY_INSTITUTIONS,
                "items": [
                    {
                        "conditions": [
                            AssetTemplateConditional.NAME_POOLED,
                            AssetTemplateConditional.HOLDER_MEETING_YES,
                        ],
                        "items": [
                            "更换资产管理计划管理人或者托管人、提前终止资产管理合同等对投资者产生重要影响的特殊决议事项，应当经参加大会的资产管理计划份额持有人所持表决权的三分之二以上通过。",
                        ],
                    }
                ],
            },
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_GENERAL_ASSEMBLY_DAILY_INSTITUTIONS,
                "items": [
                    {
                        "conditions": [
                            AssetTemplateConditional.NAME_POOLED,
                            AssetTemplateConditional.HOLDER_MEETING_YES,
                        ],
                        "items": [
                            "如根据相关法律法规存在合理要求需要更换管理人或托管人、提前终止资产管理合同的，应当经出席会议的资产管理计划份额持有人或其代理人所持表决权的2/3以上（含2/3）通过方为有效",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1043",
        "related_name": "份额持有人大会及日常机构",
        "name": "集合计划份额持有人大会-托管人召集要求",
        "from": "证券投资基金托管业务管理办法（证监会令第172号修订 2020年7月10日）",
        "origin": [
            "第二十三条 对于转换基金运作方式、更换基金管理人等需召开基金份额持有人大会审议的事项，基金托管人应当积极配合基金管理人召集基金份额持有人大会；基金管理人未按规定召集或者不能召集的，基金托管人应当按照规定召集基金份额持有人大会，并依法履行对外披露与报告义务。",
        ],
        "contract_content": [
            "【集合】",
            "第四十三条 订明管理人发生异常且无法履行管理职能的，由托管人召集资产管理计划份额持有人大会，份额持有人大会设立日常机构的除外。",
        ],
        "templates": [
            {
                "name": TemplateName.LAW_NAME,
                "content_title": TemplateName.LAW_TITLE,
                "chapter": ChapterPattern.CHAPTER_GENERAL_ASSEMBLY_DAILY_INSTITUTIONS,
                "items": [
                    {
                        "conditions": [
                            AssetTemplateConditional.NAME_POOLED,
                            AssetTemplateConditional.HOLDER_MEETING_YES,
                        ],
                        "items": [
                            "管理人发生异常且无法履行管理职能的，由托管人召集资产管理计划份额持有人大会",
                        ],
                    }
                ],
            },
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_GENERAL_ASSEMBLY_DAILY_INSTITUTIONS,
                "items": [
                    {
                        "conditions": [
                            AssetTemplateConditional.NAME_POOLED,
                            AssetTemplateConditional.HOLDER_MEETING_YES,
                        ],
                        "items": [
                            "管理人发生异常且无法履行管理职能的，由托管人召集份额持有人大会",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1044",
        "related_name": "份额持有人大会及日常机构",
        "name": "集合计划份额持有人大会-不得干涉投资管理活动",
        "from": "",
        "origin": "",
        "contract_content": [
            "【集合】",
            "第四十四条 订明资产管理计划份额持有人大会及其日常机构不得直接参与或者干涉资产管理计划的投资管理活动。",
        ],
        "templates": [
            {
                "name": TemplateName.LAW_NAME,
                "content_title": TemplateName.LAW_TITLE,
                "chapter": ChapterPattern.CHAPTER_GENERAL_ASSEMBLY_DAILY_INSTITUTIONS,
                "items": [
                    {
                        "conditions": [
                            AssetTemplateConditional.NAME_POOLED,
                            AssetTemplateConditional.HOLDER_MEETING_YES,
                        ],
                        "items": [
                            "份额持有人大会及其日常机构不得直接参与或者干涉资产管理计划的投资管理活动",
                        ],
                    }
                ],
            },
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_GENERAL_ASSEMBLY_DAILY_INSTITUTIONS,
                "items": [
                    {
                        "conditions": [
                            AssetTemplateConditional.NAME_POOLED,
                            AssetTemplateConditional.HOLDER_MEETING_YES,
                        ],
                        "items": [
                            "份额持有人大会不得直接参与或者干涉资产管理计划的投资管理活动",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1046",
        "related_name": "资产管理计划份额的登记",
        "name": "集合计划份额登记机构的数据备份和保存要求",
        "from": [
            "中华人民共和国证券投资基金法（主席令第23号 2015年4月24日修订）",
            "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）",
        ],
        "origin": [
            "第一百零二条　基金份额登记机构以电子介质登记的数据，是基金份额持有人权利归属的根据。基金份额持有人以基金份额出质的，质权自基金份额登记机构办理出质登记时设立。",
            "基金份额登记机构应当妥善保存登记数据，并将基金份额持有人名称、身份信息及基金份额明细等数据备份至国务院证券监督管理机构认定的机构。其保存期限自基金账户销户之日起不得少于二十年。",
            "基金份额登记机构应当保证登记数据的真实、准确、完整，不得隐匿、伪造、篡改或者毁损。",
            "第十一条 份额登记机构应当妥善保存登记数据，并将集合资产管理计划投资者名称、身份信息以及集合资产管理计划份额明细等数据备份至中国证监会认定的机构。其保存期限自集合资产管理计划账户销户之日起不得少于20年。",
        ],
        "contract_content": [
            "【集合】",
            "第四十六条 订明全体资产管理计划份额持有人同意管理人、份额登记机构或其他份额登记义务人将集合资产管理计划投资者名称、身份信息以及集合资产管理计划份额明细等数据备份至中国证监会认定的机构。",
        ],
        "templates": [
            {
                "name": TemplateName.LAW_NAME,
                "content_title": TemplateName.LAW_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_REGISTRATION,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_POOLED],
                        "items": [
                            "全体资产管理计划份额持有人同意管理人、份额登记机构或其他份额登记义务人将集合资产管理计划投资者名称、身份信息以及集合资产管理计划份额明细等数据备份至中国证监会认定的机构。",
                        ],
                    },
                ],
            },
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_REGISTRATION,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_POOLED],
                        "items": [
                            [
                                "保存本资产管理计划投资者资料表及相关的参与和退出等业务记录20年以上；",
                                "保存投资者名册及相关的相关业务记录20年以上；",
                            ]
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_1049",
        "related_name": "资产管理计划的投资",
        "name": "投资-集合计划资产组合流动性应与参与、退出安排相匹配",
        "from": "",
        "origin": "",
        "contract_content": [
            "【集合】",
            "第四十七条 说明资产管理计划财产投资的有关事项，包括但不限于：",
            "……",
            "（十二）订明投资的资产组合的流动性与参与、退出安排相匹配。 ",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_INVEST,
                "items": [
                    {
                        "conditions": [
                            AssetTemplateConditional.NAME_POOLED,
                        ],
                        "items": [
                            [
                                "管理人将按照法律法规及本合同约定确保本计划所投资的资产组合流动性与本计划参与、退出安排相匹配，并按照法律法规及本合同约定在开放期保持适当比例的现金或者其他高流动性金额资产，且限制流动性受限资产投资比例。",
                                "管理人应当确保本资产管理计划所投资的资产组合的流动性与本资产管理合同约定的参与、退出安排相匹配，确保在开放期保持适当比例的现金或者其他高流动性金融资产，且限制流动性受限资产投资比例。",
                            ]
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1061",
        "related_name": "投资顾问（如有）",
        "name": "投顾-管理人的职责不应免除",
        "from": "",
        "origin": "",
        "contract_content": [
            "【单一&集合】",
            "第四十九条 说明管理人应切实履行主动管理职责，依法应当承担的责任不因聘请投资顾问而免除。",
        ],
        "templates": [
            {
                "name": TemplateName.LAW_NAME,
                "content_title": TemplateName.LAW_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_INVESTMENT_COUNSELOR,
                "items": [
                    {
                        "conditions": [
                            AssetTemplateConditional.NAME_SINGLE_POOLED,
                            AssetTemplateConditional.INVESTMENT_ADVISER,
                        ],
                        "items": [
                            "管理人应切实履行主动管理职责，依法应当承担的责任不因聘请投资顾问而免除",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1062",
        "related_name": "投资顾问（如有）",
        "name": "投顾-管理人应审查投资建议",
        "from": "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）",
        "origin": [
            "第三十七条 证券期货经营机构应当对投资顾问的投资建议进行审查，不得由投资顾问直接执行投资指令。",
            "证券期货经营机构不得允许投资顾问及其关联方以其自有资金或者募集资金投资于分级资产管理计划的劣后级份额，不得向未提供实质服务的投资顾问支付费用或者支付与其提供的服务不相匹配的费用。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_INVESTMENT_COUNSELOR,
                "items": [
                    {
                        "conditions": [
                            AssetTemplateConditional.NAME_SINGLE_POOLED,
                            AssetTemplateConditional.INVESTMENT_ADVISER,
                        ],
                        "items": [
                            "管理人应当对投资顾问的投资建议进行审查，不得由投资顾问直接执行投资指令。",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1065",
        "related_name": "利益冲突及关联交易",
        "name": "关联交易-管理人关联方参与计划的处理",
        "from": "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）",
        "origin": [
            "第三十一条 证券期货经营机构董事、监事、从业人员及其配偶不得参与本公司管理的单一资产管理计划。",
            "证券期货经营机构董事、监事、从业人员及其配偶、控股股东、实际控制人或者其他关联方参与证券期货经营机构设立的资产管理计划，证券期货经营机构应当向投资者进行披露，对该资产管理计划账户进行监控，并及时向中国证监会相关派出机构报告。",
            "证券期货经营机构管理的分级资产管理计划资产，不得直接或者间接为该分级资产管理计划劣后级投资者及其控股股东、实际控制人或者其他关联方提供或者变相提供融资。",
        ],
        # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2425
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_CONFLICTS_INTEREST_RELATED_PARTY_TRANSACTIONS,
                "items": [
                    "证券期货经营机构董事、监事、从业人员及其配偶、控股股东、实际控制人或者其他关联方",
                ],
            },
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_CONFLICTS_INTEREST_RELATED_PARTY_TRANSACTIONS,
                "items": [
                    "管理人的董事、监事、从业人员及其配偶、控股股东、实际控制人或者其他关联方参与资产管理计划的",
                ],
            },
        ],
    },
    {
        "label": "template_1067",
        "related_name": "资产管理计划的财产",
        "name": "财产-保管与处分",
        "from": "证券期货经营机构私募资产管理业务管理办法（证监会令第203号修订 2023年1月12日）",
        "origin": [
            "第六条 资产管理计划财产为信托财产，其债务由资产管理计划财产本身承担，投资者以其出资为限对资产管理计划财产的债务承担责任。但资产管理合同依照《证券投资基金法》另有约定的，从其约定。",
            "资产管理计划财产独立于证券期货经营机构和托管人的固有财产，并独立于证券期货经营机构管理的和托管人托管的其他财产。证券期货经营机构、托管人不得将资产管理计划财产归入其固有财产。",
            "证券期货经营机构、托管人因资产管理计划财产的管理、运用或者其他情形而取得的财产和收益，归入资产管理计划财产。",
            "证券期货经营机构、托管人因依法解散、被依法撤销或者被依法宣告破产等原因进行清算的，资产管理计划财产不属于其清算财产。",
            "非因资产管理计划本身的债务或者法律规定的其他情形，不得查封、冻结、扣划或者强制执行资产管理计划财产。",
        ],
        "contract_content": [
            "【单一&集合】",
            "第五十八条 订明与资产管理计划财产有关的事项，包括但不限于：",
            "（一）资产管理计划财产的保管与处分",
            "1.说明资产管理计划财产的债务由资产管理计划财产本身承担责任，投资者以其出资为限对资产管理计划财产的债务承担责任。",
            "2.说明资产管理计划财产独立于管理人和托管人的固有财产，并独立于管理人管理的和托管人托管的其他财产。管理人、托管人不得将资产管理计划财产归入其固有财产。",
            "3.说明管理人、托管人因资产管理计划财产的管理、运用或者其他情形而取得的财产和收益，归入资产管理计划财产。",
            "4.说明管理人、托管人可以按照本合同的约定收取管理费、托管费以及本合同约定的其他费用。管理人、托管人以其固有财产承担法律责任，其债权人不得对资产管理计划财产行使请求冻结、扣押和其他权利。管理人、托管人因依法解散、被依法撤销或者被依法宣告破产等原因进行清算的，资产管理计划财产不属于其清算财产。",
            "5.说明资产管理计划财产产生的债权不得与不属于资产管理计划财产本身的债务相互抵销。非因资产管理计划财产本身承担的债务，管理人、托管人不得主张其债权人对资产管理计划财产强制执行。上述债权人对资产管理计划财产主张权利时，管理人、托管人应明确告知资产管理计划财产的独立性，采取合理措施并及时通知投资者。",
        ],
        "templates": [
            {
                "name": TemplateName.LAW_NAME,
                "content_title": TemplateName.LAW_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_PROPERTY,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            "资产管理计划财产的债务由资产管理计划财产本身承担责任，投资者以其出资为限对资产管理计划财产的债务承担责任。",
                            "资产管理计划财产独立于管理人和托管人的固有财产，并独立于管理人管理的和托管人托管的其他财产。管理人、托管人不得将资产管理计划财产归入其固有财产。",
                            "管理人、托管人因资产管理计划财产的管理、运用或者其他情形而取得的财产和收益，归入资产管理计划财产。",
                            "管理人、托管人可以按照本合同的约定收取管理费、托管费以及本合同约定的其他费用。管理人、托管人以其固有财产承担法律责任，其债权人不得对资产管理计划财产行使请求冻结、扣押和其他权利。管理人、托管人因依法解散、被依法撤销或者被依法宣告破产等原因进行清算的，资产管理计划财产不属于其清算财产。",
                            "资产管理计划财产产生的债权不得与不属于资产管理计划财产本身的债务相互抵销。非因资产管理计划财产本身承担的债务，管理人、托管人不得主张其债权人对资产管理计划财产强制执行。上述债权人对资产管理计划财产主张权利时，管理人、托管人应明确告知资产管理计划财产的独立性，采取合理措施并及时通知投资者。",
                        ],
                    }
                ],
            },
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_PROPERTY,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            "资产管理计划财产为信托财产，其债务由资产管理计划财产本身承担责任，投资者以其出资为限对资产管理计划财产的债务承担责任。",
                            "资产管理计划财产独立于管理人和托管人的固有财产，并独立于管理人管理的和托管人托管的其他财产。管理人、托管人不得将资产管理计划财产归入其固有财产。",
                            "管理人、托管人因资产管理计划财产的管理、运用或者其他情形而取得的财产和收益，归入资产管理计划财产。",
                            "管理人、托管人可以按照本合同的约定收取管理费、托管费以及本合同约定的其他费用。管理人、托管人以其固有财产承担法律责任，其债权人不得对资产管理计划财产行使请求冻结、扣押和其他权利。管理人、托管人因依法解散、被依法撤销或者被依法宣告破产等原因进行清算的，资产管理计划财产不属于其清算财产。",
                            "资产管理计划财产产生的债权不得与不属于资产管理计划财产本身的债务相互抵销。非因资产管理计划财产本身承担的债务，管理人、托管人不得主张其债权人对资产管理计划财产强制执行。上述债权人对资产管理计划财产主张权利时，管理人、托管人应明确告知资产管理计划财产的独立性，采取合理措施并及时通知投资者。",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1068",
        "schema_fields": ["委托财产的移交"],
        "related_name": "资产管理计划的财产",
        "name": "财产-单一计划委托财产的移交",
        "from": "",
        "origin": "",
        "contract_content": [
            "【单一】",
            "（三）委托财产的移交",
            "1.订明在委托财产相关账户开立完毕后，委托财产移交的流程及其他事项。如聘请托管人，投资者应及时将初始委托财产足额划拨至托管人为本委托财产开立的托管账户、证券账户或其他专用账户，托管人应于委托财产托管账户收到初始委托财产的当日向投资者及管理人发送《委托财产到账通知书》。",
            "2.列明初始委托财产可以为货币资金，或者投资者合法持有的股票、债券或中国证监会认可的其他金融资产。初始委托财产价值不得低于1000万元人民币。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE],
                        "items": [
                            [
                                "本计划初始委托财产应为货币资金。初始委托财产价值不得低于1000万元人民币。",
                                "初始委托财产为货币资金，初始委托财产价值不低于人民币1000万元",
                            ]
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1069",
        "schema_fields": ["委托财产的追加"],
        "related_name": "资产管理计划的财产",
        "name": "财产-单一计划委托财产的追加",
        "from": "",
        "origin": "",
        "contract_content": [
            "【单一】",
            "（四）委托财产的追加",
            "列明开放式资产管理计划在合同有效期内，投资者有权以书面通知或指令的形式追加委托财产。追加委托财产比照初始委托财产办理移交手续，管理人、托管人（如有）应按照本合同的约定分别管理和托管追加部分的委托财产。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE],
                        "items": [
                            "在本合同有效期内，资产委托人有权以书面通知或指令的形式追加委托财产。",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1070",
        "schema_fields": ["委托财产的提取"],
        "related_name": "资产管理计划的财产",
        "name": "财产-单一计划委托财产的提取",
        "from": "",
        "origin": "",
        "contract_content": [
            "【单一】",
            "（五）委托财产的提取",
            "1.订明开放式资产管理计划在本合同存续期内，投资者提取委托财产的流程和通知方式。如聘请托管人，投资者需提前通知管理人并抄送托管人，投资者要求管理人发送财产划拨指令，通知托管人将相应财产从相关账户划拨至投资者账户，托管人应于划拨财产当日以书面形式或其他各方认可的形式分别通知其他两方。管理人和托管人不承担由于投资者通知不及时造成的资产变现损失。",
            "2.列明投资者在本合同存续期内提取委托财产需提前通知的时间。 ",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE],
                        "items": [
                            [
                                "管理人和托管人不承担由于投资者通知不及时造成的资产变现损失。",
                                "由于投资者通知不及时造成的资产变现损失由投资者承担。",
                            ]
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1073",
        "schema_fields": ["越权交易的界定"],
        "related_name": "越权交易的界定",
        "name": "越权交易-范围界定",
        "from": "",
        "origin": "",
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2451
                            [
                                "【1】违反有关法律法规和本合同规定进行的投资交易行为；",
                                "【1】违反法律、行政法规和其他有关规定以及本合同约定进行的投资交易行为；",
                            ],
                            "【2】法律法规禁止的超买、超卖行为。",
                            [
                                "【3】资产管理人应在本合同规定的权限内运用资产管理计划财产进行投资管理，不得违反本合同的约定，超越权限从事投资。",
                                "【3】资产管理人应在有关法律法规和本合同规定的权限内运用资产管理计划财产进行投资管理，不得违反有关法律法规和本合同的约定，超越权限管理、从事投资。",
                                "【3】管理人应依据法律、行政法规和其他有关规定并在本合同规定的权限内运用资产管理计划财产进行投资管理，不得违反法律、行政法规和其他有关规以及本合同的约定，超越权限管理从事投资活动。",
                            ],
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1074",
        "related_name": "越权交易的界定",
        "name": "越权交易-托管人的监督",
        "from": "证券投资基金托管业务管理办法（证监会令第172号修订 2020年7月10日）",
        "origin": [
            "第二十一条 基金托管人应当根据基金合同及托管协议约定，制定基金投资监督标准与监督流程，对基金合同生效之后所托管基金的投资范围、投资比例、投资风格、投资限制、关联方交易等进行严格监督，及时提示基金管理人违规风险。",
            "当发现基金管理人发出但未执行的投资指令或者已经生效的投资指令违反法律、行政法规和其他有关规定，或者基金合同约定，应当依法履行通知基金管理人等程序，并及时报告中国证监会，持续跟进基金管理人的后续处理，督促基金管理人依法履行披露义务。基金管理人的上述违规失信行为给基金财产或者基金份额持有人造成损害的，基金托管人应当督促基金管理人及时予以赔偿。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_DEFINITION_ULTRA_VIRES_TRANSACTION,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            [
                                "【1】托管人投资监督的准确性、完整性和及时性受限于管理人及其他中介机构提供的数据信息。因管理人及其他中介机构提供的信息的真实性、准确性、完整性和及时性所引起的损失，由信息提供方承担相应的责任。",
                                "【1】托管人判断越权交易的准确性和完整性受限于管理人及其它第三方机构提供的数据和信息。托管人对上述机构的信息的准确性和完整性不作任何担保、暗示或表示，并对上述机构提供的信息的错误、遗漏或延迟所引起的损失不承担任何责任。",
                            ],
                            [
                                "【2】发现管理人发出但未执行的投资指令违反法律、行政法规和其他有关规定以及本合同约定的，应当拒绝执行，立即通知管理人，并有权报告中国证监会相关派出机构",
                                "【2】发现管理人发出但未执行的投资指令违反法律、行政法规和其他有关规定以及本合同约定的，应当拒绝执行，立即通知管理人，并有权依据相关法律法规的要求报告中国证监会或中国基金业协会。",
                            ],
                            [
                                "【3】发现资产管理人依据交易程序已经生效的投资指令违反法律法规和其他规定，或者违反本合同约定的，应当立即通知资产管理人，并有权报告中国证监会相关派出机构。",
                                "【3】发现管理人依据交易程序已经生效的投资指令违反法律、行政法规和其他有关规定以及本合同约定的，应立即通知管理人，并有权依据相关法律法规的要求报告中国证监会或中国基金业协会，因执行该指令造成的损失托管人不承担任何责任。",
                            ],
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1076",
        "related_name": "资产管理计划财产的估值和会计核算",
        "name": "估值-会计核算",
        "from": "",
        "origin": "",
        "contract_content": [
            "【单一&集合】",
            "第六十二条 说明资产管理计划的会计政策比照现行政策或按照资产管理合同约定执行，并订明有关情况：",
            "（一）会计年度、记账本位币、会计核算制度等事项；",
            "（二）资产管理计划应独立建账、独立核算；管理人应保留完整的会计账目、凭证并进行日常的会计核算，编制会计报表；托管人应定期与管理人就资产管理计划的会计核算、报表编制等进行核对。 ",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_VALUATION_ACCOUNTING_SETTLEMENT,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            "【1】资产管理人为本计划的主要会计责任方。",
                            "【2】本计划的会计年度为公历年度的1月1日至12月31日。",
                            "【3】本计划核算以人民币为记账本位币，以人民币元为记账单位。",
                            "【4】本计划独立建账、独立核算。",
                            # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/2465
                            [
                                "【5】资产管理人及资产托管人各自保留完整的会计账目、凭证并进行日常的会计核算，按照本合同约定编制会计报表。",
                                "【5】资产管理人及资产托管人各自保留完整的会计账目、凭证并进行日常的会计核算，编制会计报表。",
                            ],
                            [
                                "【6】资产托管人定期与资产管理人就资产管理计划的会计核算、报表编制等进行核对并以书面方式确认。",
                                "【6】托管人应定期与管理人就资产管理计划的会计核算、报表编制等进行核对。",
                            ],
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1077",
        "related_name": "资产管理计划财产的估值和会计核算",
        "name": "估值-公允价值要求",
        "from": "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）",
        "origin": [
            "第三十八条 资产管理计划应当按照《企业会计准则》、《指导意见》以及中国证监会关于资产管理计划对金融工具进行核算与估值的规定、资产管理计划净值计价及风险控制要求，确认和计量资产管理计划净值。",
            "证券期货经营机构应当定期对资产管理计划估值执行效果进行评估，必要时调整完善，保证公平、合理。",
            "当有充足证据表明资产管理计划相关资产的计量方法已不能真实公允反映其价值时，证券期货经营机构应当与托管人进行协商，及时采用公允价值计量方法对资产管理计划资产净值进行调整。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_VALUATION_ACCOUNTING_SETTLEMENT,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            [
                                "如有确凿证据表明按上述方法进行估值不能客观反映其公允价值的，管理人可根据具体情况与托管人商定后，按最能反映公允价值的价格估值",
                                "当有充足证据表明资产管理计划相关资产的计量方法已不能真实公允反映其价值时，管理人应当与托管人进行协商，及时采用公允价值计量方法对资产管理计划资产净值进行调整。",
                            ]
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1079",
        "schema_fields": ["不列入资产管理业务费用的项目"],
        "related_name": "资产管理计划的费用与税收",
        "name": "费用-不得在计划资产中列支的费用",
        "from": "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）",
        "origin": [
            "第四十条 资产管理计划发生的费用，可以按照资产管理合同的约定，在计划资产中列支。资产管理计划成立前发生的费用，不得在计划资产中列支，专门投资于未上市企业股权的资产管理计划聘请专业服务机构等事项所支出的合理费用除外。存续期间发生的与募集有关的费用，不得在计划资产中列支。",
            "证券期货经营机构应当根据资产管理计划的投资范围、投资策略、产品结构等因素设定合理的管理费率。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            "【1】资产管理计划成立前发生的费用",
                            "【2】存续期间发生的与募集有关的费用",
                            "【3】管理人和托管人因未履行或未完全履行义务导致的费用支出或资产管理计划财产的损失，",
                            "【4】处理与本计划财产运作无关的事项或不合理事项所发生的费用等",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1080",
        "related_name": "资产管理计划的费用与税收",
        "name": "费用-业绩报酬",
        "from": [
            "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）",
            "证券期货经营机构私募资产管理计划备案管理办法（试行） 中基协发[2019]4号	2019年6月3日",
        ],
        "origin": [
            "第四十一条 证券期货经营机构可以与投资者在资产管理合同中约定提取业绩报酬，业绩报酬应当计入管理费。",
            "证券期货经营机构应当坚持公平对待投资者、长期业绩导向和适当激励原则，合理设定业绩报酬的提取频率、比例，以及包括业绩报酬在内的管理费的收取比例上限，确保业绩报酬提取与资产管理计划的存续期限、收益分配和投资运作特征相匹配。",
            "业绩报酬应当从分红资金、退出资金或清算资金中提取，从分红资金中提取业绩报酬的频率不得超过每6个月一次。业绩报酬的提取比例不得超过计提基准以上投资收益的60%。",
            "第二十七条针对业绩比较基准、业绩报酬计提基准，重点核查以下内容：",
            "（一）业绩比较基准、业绩报酬计提基准条款是否与其合理内涵相一致，是否混同使用；",
            "（二）设置业绩比较基准的，是否说明业绩比较基准的确定依据；",
            "（三）业绩比较基准是否为固定数值，是否存在利用业绩比较基准、业绩报酬计提基准变相挂钩宣传预期收益率，明示或暗示产品预期收益的违规情形。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_FEES_TAXES,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            [
                                "本计划不计提业绩报酬。",
                                "本计划不计提管理人业绩报酬。",
                                "业绩报酬提取应当与资产管理计划的存续期限、收益分配和投资运作特征相匹配，提取频率不得超过每6个月一次，提取比例不得超过业绩报酬计提基准以上投资收益的60%。因委托人退出资产管理计划，管理人按照资产管理合同的约定提取业绩报酬的，不受前述提取频率的限制。",
                            ]
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1081",
        "related_name": "资产管理计划的费用与税收",
        "name": "费用-投资者的税收",
        "from": "中华人民共和国证券投资基金法（主席令第23号 2015年4月24日修订）",
        "origin": "第八条　基金财产投资的相关税收，由基金份额持有人承担，基金管理人或者其他扣缴义务人按照国家有关税收征收的规定代扣代缴。",
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_FEES_TAXES,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            [
                                "资产委托人应缴纳的税收，由资产委托人负责，资产管理人不承担代扣代缴或纳税的义务。",
                                "投资者必须自行缴纳的税收由投资者负责，管理人不承担代扣代缴或纳税的义务。",
                            ]
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1083",
        "related_name": "信息披露与报告",
        "name": "信息披露-管理人向投资者提供的信披文件",
        "from": "证券期货经营机构私募资产管理业务管理办法（证监会令第203号修订 2023年1月12日）",
        "origin": [
            "第四十九条 资产管理计划应向投资者提供下列信息披露文件：",
            "（一）资产管理合同、计划说明书和风险揭示书；",
            "（二）资产管理计划净值，资产管理计划参与、退出价格；",
            "（三）资产管理计划定期报告，至少包括季度报告和年度报告；",
            "（四）重大事项的临时报告；",
            "（五）资产管理计划清算报告；",
            "（六）中国证监会规定的其他事项。",
            "前款第（四）项、第（六）项信息披露文件，应当及时报送中国证监会相关派出机构。",
            "信息披露文件的内容与格式指引由中国证监会或者授权证券投资基金业协会另行制定。",
        ],
        "contract_content": [
            "【单一&集合】",
            "第六十六条 订明管理人向投资者披露信息的种类、内容、频率和方式等有关事项，并确保投资者能够按照资产管理合同约定的时间和方式查阅或者复制所披露的信息资料。",
            "【集合】",
            "第六十七条 根据《管理办法》及其他相关规定要求订明管理人披露经托管人复核的资产管理计划份额净值的频率和方式。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_DISCLOSURE_REPORTING,
                "required": False,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            "管理人应向投资者提供下列信息披露文件：",
                            "（1）资产管理合同、计划说明书和风险揭示书；",
                            "（2）资产管理计划净值，资产管理计划参与、退出价格；",
                            "（3）资产管理计划定期报告，至少包括季度报告和年度报告；",
                            "（4）重大事项的临时报告；",
                            "（5）资产管理计划清算报告；",
                            "（6）中国证监会规定的其他事项。",
                            "前款第（4）项、第（6）项信息披露文件，应当及时报送中国证监会相关派出机构。",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1090",
        "related_name": "资产管理合同的变更、终止与财产清算",
        "name": "合同变更-变更方式及备案要求",
        "from": "证券期货经营机构私募资产管理业务管理办法（证监会令第203号修订 2023年1月12日）",
        "origin": [
            "第五十四条 资产管理合同需要变更的，证券期货经营机构应当按照资产管理合同约定的方式取得投资者和托管人的同意，保障投资者选择退出资产管理计划的权利，对相关后续事项作出公平、合理安排。",
            "证券期货经营机构应当自资产管理合同变更之日起五个工作日内报证券投资基金业协会备案。",
        ],
        "contract_content": [
            "【单一&集合】",
            "第七十四条 订明资产管理合同变更的条件、程序等。",
            "（一）因法律法规或中国证监会、证券投资基金业协会的相关规定、要求发生变化必须变更资产管理合同的，管理人可以与托管人协商后修改资产管理合同，并由管理人按照合同约定及时向投资者披露变更的具体内容。",
            "（二）因其他原因需要变更资产管理合同的，【集合】经全体投资者/【单一】经投资者、管理人和托管人协商一致后，可对资产管理合同内容进行变更，资产管理合同另有约定的除外。资产管理计划改变投向和比例的，应当事先取得投资者同意。",
            "（三）管理人应当合理保障合同变更后投资者选择退出资产管理计划的权利。",
            "第七十五条 说明资产管理合同发生变更的，管理人应按照证券投资基金业协会要求及时向证券投资基金业协会备案，并抄报中国证监会相关派出机构。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            "【1】因法律法规或中国证监会、证券投资基金业协会的相关规定、要求发生变化必须变更资产管理合同的，管理人可以与托管人协商后修改资产管理合同，并由管理人按照合同约定及时向投资者披露变更的具体内容。",
                            {
                                "conditions": [AssetTemplateConditional.NAME_SINGLE],
                                "items": [
                                    "【2】因其他原因需要变更资产管理合同的，经投资者、管理人和托管人协商一致后，可对资产管理合同内容进行变更，资产管理合同另有约定的除外。",
                                ],
                            },
                            {
                                "conditions": [AssetTemplateConditional.NAME_POOLED],
                                "items": [
                                    "【2】因其他原因需要变更资产管理合同的，经全体投资者、管理人和托管人协商一致后，可对资产管理合同内容进行变更，资产管理合同另有约定的除外。",
                                ],
                            },
                            "【3】资产管理计划改变投向和比例的，应当事先取得投资者同意。",
                            [
                                "【4】管理人应当自资产管理合同变更之日起五个工作日内报证券投资基金业协会备案。",
                                "【4】管理人应当自资产管理合同变更之日起五个工作日内按监管要求报告相关机构。",
                            ],
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1087",
        "related_name": "信息披露与报告",
        "name": "信息披露-向监管机构报告",
        "from": "证券期货经营机构私募资产管理业务管理办法（证监会令第203号修订 2023年1月12日）",
        "origin": [
            "第七十三条 证券期货经营机构应当于每月十日前向证券投资基金业协会报送资产管理计划的持续募集情况、投资运作情况、资产最终投向等信息。",
            "证券期货经营机构应当在每季度结束之日起一个月内，编制私募资产管理业务管理季度报告，并报送中国证监会相关派出机构。",
            "证券期货经营机构、托管人应当在每年度结束之日起四个月内，分别编制私募资产管理业务管理年度报告和托管年度报告，并报送中国证监会相关派出机构。",
            "证券期货经营机构应当在私募资产管理业务管理季度报告和管理年度报告中，就本办法所规定的风险管理与内部控制制度在报告期内的执行情况等进行分析，并由合规负责人、风控负责人、总经理分别签署。",
        ],
        "contract_content": [
            "【单一&集合】",
            "第七十一条 列明管理人、托管人向监管机构报告的种类、内容、时间和途径等有关事项。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_DISCLOSURE_REPORTING,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            [
                                "管理人、托管人应当根据法律法规、中国证监会和基金业协会的要求履行报告义务。",
                                "管理人、托管人应当根据法律法规和监管机构的要求履行报告义务。",
                                "资产管理人、资产托管人应当根据法律法规和监管机构及自律组织的要求履行报告义务。",
                            ]
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1088",
        "related_name": "信息披露与报告",
        "name": "信息披露-集合计划年度财务会计报告的审计要求",
        "from": "证券期货经营机构私募资产管理业务管理办法（证监会令第203号修订 2023年1月12日）",
        "origin": "第五十三条 集合资产管理计划年度财务会计报告应当经符合《证券法》规定的会计师事务所审计，审计机构应当对资产管理计划会计核算及净值计算等出具意见。",
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_DISCLOSURE_REPORTING,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_POOLED],
                        "items": [
                            "资产管理计划年度财务会计报告应当经符合《证券法》规定的会计师事务所审计，审计机构应当对资产管理计划会计核算及净值计算等出具意见。",
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1029",
        "related_name": "资产管理计划的募集",
        "name": "集合计划初始认购资金的管理及利息处理方式",
        "from": "证券期货经营机构私募资产管理业务管理办法（证监会令第203号修订 2023年1月12日）",
        "origin": [
            "第三十条 集合资产管理计划募集期间，证券期货经营机构、销售机构应当在规定期限内，将投资者参与资金存入集合资产管理计划份额登记机构指定的专门账户。集合资产管理计划成立前，任何机构和个人不得动用投资者参与资金。",
            "按照前款规定存入专门账户的投资者参与资金，独立于证券期货经营机构、销售机构的固有财产。非因投资者本身的债务或者法律规定的其他情形，不得查封、冻结、扣划或者强制执行存入专门账户的投资者参与资金。",
        ],
        "contract_content": [
            "【集合】",
            "第二十八条 说明投资者的认购参与款项（不含认购费用）加计其在初始销售期形成的利息将折算为资产管理计划份额归投资者所有。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_RAISE,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_POOLED],
                        "items": [
                            [
                                "投资者的认购参与款项（不含认购费用）加计其在初始销售期形成的利息将折算为资产管理计划份额归投资者所有。",
                                "投资者的认购参与资金（含认购费用）在初始募集期间发生的利息收入按银行活期存款利率（税后）计算，并在初始募集期结束后折合成计划份额，归资产委托人所有。",
                            ],
                            [
                                "资产管理人应当将资产管理计划初始募集期间客户的认购资金存入资产管理计划募集结算专用账户。",
                                "资产管理人应当将资产管理计划初始募集期间将投资者参与资金存入份额登记机构指定的专门账户。",
                            ],
                            [
                                "资产管理计划成立前，任何机构和个人不得动用。",
                                "资产管理计划成立前，任何机构和个人不得动用投资者参与资金。",
                                "资产管理计划成立前，任何机构和个人不得动用投资者交付的委托资金。",
                            ],
                        ],
                    }
                ],
            },
        ],
    },
    {
        "label": "template_1093",
        "related_name": "前言",
        "name": "前言-订明订立资产管理合同的依据、目的和原则",
        "from": "",
        "origin": "",
        "contract_content": [
            "【单一&集合】",
            "第十三条 订明订立资产管理合同的依据、目的和原则。订立资产管理合同的依据应包括《基金法》、《管理办法》、《运作规定》以及本指引。",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_FUND_FOREWORD,
                "items": [
                    {
                        "conditions": [AssetTemplateConditional.NAME_SINGLE_POOLED],
                        "items": [
                            {
                                "conditions": [AssetTemplateConditional.NAME_SINGLE],
                                "items": [
                                    "订立本合同的依据是《中华人民共和国民法典》、《中华人民共和国证券投资基金法》（以下简称《基金法》）、【管理人为期货公司】《期货公司监督管理办法》、《关于规范金融机构资产管理业务的指导意见》、《证券期货经营机构私募资产管理业务管理办法》（以下简称《管理办法》）、《证券期货经营机构私募资产管理计划运作管理规定》（以下简称《运作规定》）、《单一资产管理计划资产管理合同内容与格式指引（试行）》及其他法律法规的有关规定。",
                                ],
                            },
                            {
                                "conditions": [AssetTemplateConditional.NAME_POOLED],
                                "items": [
                                    "订立本合同的依据是《中华人民共和国民法典》、《中华人民共和国证券投资基金法》（以下简称《基金法》）、【管理人为期货公司】《期货公司监督管理办法》、《关于规范金融机构资产管理业务的指导意见》、《证券期货经营机构私募资产管理业务管理办法》（以下简称《管理办法》）、《证券期货经营机构私募资产管理计划运作管理规定》（以下简称《运作规定》）、《集合资产管理计划资产管理合同内容与格式指引（试行）》及其他法律法规的有关规定。",
                                ],
                            },
                        ],
                    }
                ],
            },
        ],
    },
]
