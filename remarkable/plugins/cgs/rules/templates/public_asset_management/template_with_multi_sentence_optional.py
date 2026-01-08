from remarkable.common.pattern import PatternCollection
from remarkable.plugins.cgs.common.chapters_patterns import ChapterPattern
from remarkable.plugins.cgs.common.enum_utils import TemplateCheckTypeEnum
from remarkable.plugins.cgs.common.patterns_util import P_PARA_PREFIX_NUM, R_CONJUNCTION
from remarkable.plugins.cgs.common.template_condition import AssetTemplateConditional, TemplateName

TEMPLATE_WITH_MULTI_SENTENCE_OPTIONALS = [
    {
        "label": "template_1060",
        "related_name": "投资顾问（如有）",
        "name": "投顾-资质条件",
        "from": "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）",
        "origin": [
            "第三十六条 资产管理计划的投资顾问应当为依法可以从事资产管理业务的证券期货经营机构、商业银行资产管理机构、保险资产管理机构以及中国证监会认可的其他金融机构，或者同时符合以下条件的私募证券投资基金管理人：",
            "（一）在证券投资基金业协会登记满1年、无重大违法违规记录的会员；",
            "（二）具备3年以上连续可追溯证券、期货投资管理业绩且无不良从业记录的投资管理人员不少于3人；",
            "（三）中国证监会规定的其他条件。",
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
                            "依法可以从事资产管理业务的证券期货经营机构、商业银行资产管理机构、保险资产管理机构以及中国证监会认可的其他金融机构",
                        ],
                    },
                    {
                        "conditions": [
                            AssetTemplateConditional.NAME_SINGLE_POOLED,
                            AssetTemplateConditional.INVESTMENT_ADVISER,
                        ],
                        "items": [
                            "符合以下条件的私募证券投资基金管理人",
                            {
                                "type": TemplateCheckTypeEnum.RECOMBINATION.value,
                                "patterns": [
                                    PatternCollection(r"(登记满1年|无重大违法违规记录)的?会员"),
                                    PatternCollection(r"(证券|期货)投资管理业绩且无不良从业记录"),
                                    PatternCollection(r"证监会规定的?其他条件"),
                                ],
                                "serial_num_pattern": P_PARA_PREFIX_NUM,
                                "default_prefix_type": "（{num}）",
                                "items": [
                                    "在证券投资基金业协会登记满1年、无重大违法违规记录的会员；",
                                    "具备3年以上连续可追溯证券、期货投资管理业绩且无不良从业记录的投资管理人员不少于3人；",
                                    "中国证监会规定的其他条件。",
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
    },
    {
        "label": "template_1048",
        "related_name": "资产管理计划的投资",
        "name": "投资-投资比例特定安排",
        "from": "证券期货经营机构私募资产管理计划运作管理规定（证监会令第203号修订 2023年1月12日）",
        "origin": "第三十二条 固定收益类、权益类、期货和衍生品类资产管理计划存续期间，为规避特定风险并经全体投资者同意的，投资于对应类别资产的比例可以低于计划总资产80%，但不得持续6个月低于计划总资产80%。",
        "contract_content": [
            "【单一&集合】",
            "第四十七条 说明资产管理计划财产投资的有关事项，包括但不限于：",
            "……",
            "（十）说明固定收益类、权益类、商品及金融衍生品类资产管理计划存续期间，为规避特定风险，【集合】经全体投资者同意后/【单一】经投资者同意后，投资于对应类别资产的比例可以低于计划总资产80%，但不得持续6个月低于计划总资产80%。管理人应详细列明上述相关特定风险；",
            "……",
        ],
        "templates": [
            {
                "name": TemplateName.EDITING_NAME,
                "content_title": TemplateName.EDITING_TITLE,
                "chapter": ChapterPattern.CHAPTER_ASSET_MANAGEMENT_PLAN_INVEST,
                "items": [
                    {
                        "conditions": [
                            AssetTemplateConditional.NAME_SINGLE_POOLED,
                            AssetTemplateConditional.EQUITIES_FIXED_INCOME_CATEGORY_FUTURES_DERIVATIVES,
                        ],
                        "items": [
                            {
                                "single_optional": [
                                    {
                                        "conditions": [AssetTemplateConditional.NAME_SINGLE],
                                        "items": [
                                            "资产管理计划存续期间，为规避特定风险，经投资者同意后，投资于对应类别资产的比例可以低于计划总资产80%，但不得持续6个月低于计划总资产80%。"
                                        ],
                                    },
                                    {
                                        "conditions": [AssetTemplateConditional.NAME_POOLED],
                                        "items": [
                                            "资产管理计划存续期间，为规避特定风险，经全体投资者同意后，投资于对应类别资产的比例可以低于计划总资产80%，但不得持续6个月低于计划总资产80%。"
                                        ],
                                    },
                                ]
                            }
                        ],
                    },
                    {
                        "conditions": [
                            AssetTemplateConditional.NAME_SINGLE_POOLED,
                            AssetTemplateConditional.EQUITIES_FIXED_INCOME_CATEGORY_FUTURES_DERIVATIVES,
                        ],
                        "items": [
                            {
                                "type": "inner_recombination",
                                "rules": {
                                    "IR_1": {
                                        "para_pattern": PatternCollection(
                                            r"规避特定风险.*投资于?(?P<content>.*?)的?比例"
                                        ),
                                        "default": "权益类/固定收益类/期货和衍生品类",
                                        "exclude_patterns": PatternCollection(
                                            rf"(?:(?:期货|衍生品类)[{R_CONJUNCTION}]?){{2}}"
                                        ),
                                        "patterns": [
                                            {
                                                "pattern": PatternCollection(r"权益类"),
                                                "value": "权益类",
                                                "conditions": [AssetTemplateConditional.EQUITIES],
                                            },
                                            {
                                                "pattern": PatternCollection(r"固定收益类"),
                                                "value": "固定收益类",
                                                "conditions": [AssetTemplateConditional.FIXED_INCOME_CATEGORY],
                                            },
                                            {
                                                "pattern": PatternCollection(r"期货|衍生品类"),
                                                "value": "期货和衍生品类",
                                                "conditions": [AssetTemplateConditional.FUTURES_AND_DERIVATIVES],
                                            },
                                        ],
                                    },
                                },
                                "items": [
                                    "存续期间，为规避特定风险并经全体投资者同意的，投资于{IR_1}的比例可以低于计划总资产80%，但不得持续6个月低于计划总资产80%。",
                                ],
                            },
                        ],
                    },
                ],
            },
        ],
    },
]
