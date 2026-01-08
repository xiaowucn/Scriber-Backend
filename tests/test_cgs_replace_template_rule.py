from unittest import TestCase

from remarkable.checker.cgs_checker.answers import CGSAnswerManager
from remarkable.checker.cgs_checker.template_checker import PublicReplaceTemplateChecker
from remarkable.common.pattern import PatternCollection
from remarkable.plugins.cgs.common.enum_utils import TemplateCheckTypeEnum
from remarkable.plugins.cgs.common.patterns_util import P_PARA_PREFIX_NUM


class TestDiff(TestCase):
    def assert_replace_template(self, checker_type, paragraphs, templates):
        checker = PublicReplaceTemplateChecker(
            reader=None,
            manager=CGSAnswerManager({}),
            file=None,
            schema_id=None,
            labels=[''],
        )
        match_templates = checker.split_templates_by_conditions(checker_type, paragraphs=paragraphs)
        match_templates = checker.recombined_template(match_templates)

        self.assertSequenceEqual(templates, match_templates)

    def test_inner_replace(self):
        inner_replace = [
            {
                'type': TemplateCheckTypeEnum.INNER_REPLACE.value,
                'rules': {'IRP_1': {'func': 'get_fund_bourse_name_with_test'}},
                'items': ['{IRP_1}证券投资基金（基金名称）由基金管理人依照《基金法》'],
            },
        ]
        self.assert_replace_template(inner_replace, [], [['上海证券投资基金（基金名称）由基金管理人依照《基金法》']])

    def test_inner_recombination(self):
        inner_recombination = [
            {
                'type': TemplateCheckTypeEnum.INNER_RECOMBINATION.value,
                'rules': {
                    'IR_1': {
                        'para_pattern': PatternCollection(r'工作日[:：](?P<content>.*)的正常交易日'),
                        'default': '上海证券交易所、深圳证券交易所、北京证券交易所',
                        'patterns': [
                            {
                                'pattern': PatternCollection(r'上海证券交易所|上交所'),
                                'value': '上海证券交易所',
                            },
                            {
                                'pattern': PatternCollection(r'北京证券交易所|北交所'),
                                'value': '北京证券交易所',
                                'conditions': [],
                            },
                            {
                                'pattern': PatternCollection(r'深圳证券交易所|深交所'),
                                'value': '深圳证券交易所',
                            },
                        ],
                    },
                },
                'items': ['工作日：{IR_1}的正常交易日'],
            },
        ]

        paragraphs = [
            {'text': '工作日：指上海证券交易所、北交所和深圳证券交易所的正常交易日', 'class': 'PARAGRAPH'},
        ]

        self.assert_replace_template(inner_recombination, paragraphs, [['工作日：上海证券交易所、北京证券交易所和深圳证券交易所的正常交易日']])

    def test_recombination(self):
        inner_recombination = [
            '测试头部',
            {
                'type': TemplateCheckTypeEnum.RECOMBINATION.value,
                'patterns': [
                    PatternCollection(r'不可抗力导致基金无法正常运作'),
                    PatternCollection(r'交易时间非正常停市.?导致基金管理人无法'),
                    PatternCollection(r'为基金提供服务的外部机构'),
                ],
                # 头部添加自增序号1、2、
                'serial_num_pattern': P_PARA_PREFIX_NUM,
                'items': [
                    '因不可抗力导致基金无法正常运作或无法接受赎回；',
                    {
                        'type': 'inner_recombination',
                        'rules': {
                            'IRB_1': {
                                'para_pattern': PatternCollection(r'导致基金管理人(?P<content>.*)'),
                                'default': '无法计算当日基金资产净值或无法进行证券交易',
                                'patterns': [
                                    {
                                        'pattern': PatternCollection(r'无法计算当日基金资产净值'),
                                        'value': '无法计算当日基金资产净值',
                                    },
                                    {
                                        'pattern': PatternCollection(r'无法进行证券交易'),
                                        'value': '无法进行证券交易',
                                    },
                                ],
                            },
                        },
                        'items': [
                            [
                                '证券/期货交易所交易时间非正常停市，导致基金管理人{IRB_1}；',
                                '期货/证券交易所交易时间非正常停市，导致基金管理人{IRB_1}；',
                            ],
                        ],
                    },
                    {
                        'type': 'inner_recombination',
                        'rules': {
                            'IR_1': {
                                'para_pattern': PatternCollection(r'(?P<content>.*)为基金提供服务的外部机构'),
                                'default': '选择、更换',
                                'patterns': [
                                    {
                                        'pattern': PatternCollection(r'选择'),
                                        'value': '选择',
                                    },
                                    {
                                        'pattern': PatternCollection(r'更换'),
                                        'value': '更换',
                                    },
                                ],
                            },
                            'IR_2': {
                                'para_pattern': PatternCollection(r'(选择|更换)(?P<content>.*)为基金提供服务的外部机构'),
                                'default': '律师事务所、会计师事务所、证券/期货经纪商或其他',
                                'patterns': [
                                    {
                                        'pattern': PatternCollection(r'律师事务所'),
                                        'value': '律师事务所',
                                    },
                                    {
                                        'pattern': PatternCollection(r'会计师事务所'),
                                        'value': '会计师事务所',
                                    },
                                    {
                                        'pattern': PatternCollection(r'其他'),
                                        'value': '其他',
                                    },
                                    {
                                        'pattern': PatternCollection(r'(?:(?:证券|期货)(?:经纪商)?[、/或]?){1,2}经纪商'),
                                        'value': '证券/期货经纪商',
                                        'condition': [],
                                    },
                                ],
                            },
                        },
                        'items': [
                            '{IR_1}{IR_2}为基金提供服务的外部机构；',
                        ],
                    },
                ],
            },
            '测试尾部',
        ]

        paragraphs = [
            {'index': 1, 'text': '发生下列情形时，基金管理人可暂停接受投资人的赎回申请或延缓支付赎回对价：', 'class': 'PARAGRAPH'},
            {'index': 2, 'text': '1、因不可抗力导致基金无法正常运作或无法接受赎回；', 'class': 'PARAGRAPH'},
            {'index': 3, 'text': '2、选择、更换律师事务所、会计师事务所、证券/期货经纪商或其他为基金提供服务的外部机构；', 'class': 'PARAGRAPH'},
            {'index': 4, 'text': '3、证券/期货交易所交易时间非正常停市，导致基金管理人无法计算当日基金资产净值或无法进行证券交易；', 'class': 'PARAGRAPH'},
        ]

        result = [
            ['测试头部'],
            ['1、因不可抗力导致基金无法正常运作或无法接受赎回；'],
            ['2、选择、更换律师事务所、会计师事务所、证券/期货经纪商或其他为基金提供服务的外部机构；'],
            [
                '3、证券/期货交易所交易时间非正常停市，导致基金管理人无法计算当日基金资产净值或无法进行证券交易；',
                '3、期货/证券交易所交易时间非正常停市，导致基金管理人无法计算当日基金资产净值或无法进行证券交易；',
            ],
            ['测试尾部'],
        ]

        result = PublicReplaceTemplateChecker.recombined_template(result)

        self.assert_replace_template(inner_recombination, paragraphs, result)

    def test_inner_refer(self):
        inner_replace = [
            {
                'type': TemplateCheckTypeEnum.INNER_REFER.value,
                'rules': {
                    'IRF_1': {
                        'default': '7',
                        'patterns': [
                            PatternCollection(r'无法计算当日基金资产净值或无法进行证券交易'),
                        ],
                    },
                    'IRF_2': {
                        'default': '2、4、5、6',
                        'patterns': [
                            PatternCollection(r'不可抗力导致基金无法正常运作'),
                            PatternCollection(r'管理人无法按时公布基金份额净值'),
                            PatternCollection(r'发生基金合同规定的暂停基金资产估值情况时'),
                            PatternCollection(r'基金所投资的投资品种的估值出现重大转变时'),
                        ],
                    },
                    'IRF_3': {
                        'default': '1-3',
                        'patterns': [
                            PatternCollection(r'不可抗力导致基金无法正常运作或无法接受赎回'),
                            PatternCollection(r'为基金提供服务的外部机构'),
                            PatternCollection(r'无法计算当日基金资产净值或无法进行证券交易'),
                        ],
                    },
                },
                'items': [
                    '发生除上述第{IRF_1}项以外的情形',
                    '除上述{IRF_2}情形之外',
                    '上述“一、基金费用的种类”中第{IRF_3}项费用',
                ],
            },
            {
                'type': TemplateCheckTypeEnum.INNER_REFER.value,
                'rules': {
                    'IRF_1': {
                        'default': '7',
                        'patterns': [
                            PatternCollection(r'因不可抗力导致基金无法正常运作或无法接受赎回'),
                        ],
                    },
                },
                'items': [
                    {
                        'type': TemplateCheckTypeEnum.RECOMBINATION.value,
                        'patterns': [
                            PatternCollection(r'不可抗力导致基金无法正常运作'),
                            PatternCollection(r'交易时间非正常停市.?导致基金管理人无法'),
                            PatternCollection(r'为基金提供服务的外部机构'),
                        ],
                        # 头部添加自增序号1、2、
                        'serial_num_pattern': P_PARA_PREFIX_NUM,
                        'items': [
                            '因不可抗力导致基金无法正常运作或无法接受赎回；',
                            {
                                'type': TemplateCheckTypeEnum.INNER_RECOMBINATION.value,
                                'rules': {
                                    'IRB_1': {
                                        'para_pattern': PatternCollection(r'导致基金管理人(?P<content>.*)'),
                                        'default': '无法计算当日基金资产净值或无法进行证券交易',
                                        'patterns': [
                                            {
                                                'pattern': PatternCollection(r'无法计算当日基金资产净值'),
                                                'value': '无法计算当日基金资产净值',
                                            },
                                            {
                                                'pattern': PatternCollection(r'无法进行证券交易'),
                                                'value': '无法进行证券交易',
                                            },
                                        ],
                                    },
                                },
                                'items': [
                                    [
                                        '证券/期货交易所交易时间非正常停市，导致基金管理人{IRB_1}；',
                                        '期货/证券交易所交易时间非正常停市，导致基金管理人{IRB_1}；',
                                    ],
                                ],
                            },
                            {
                                'type': TemplateCheckTypeEnum.INNER_RECOMBINATION.value,
                                'rules': {
                                    'IR_1': {
                                        'para_pattern': PatternCollection(r'(?P<content>.*)为基金提供服务的外部机构'),
                                        'default': '选择、更换',
                                        'patterns': [
                                            {
                                                'pattern': PatternCollection(r'选择'),
                                                'value': '选择',
                                            },
                                            {
                                                'pattern': PatternCollection(r'更换'),
                                                'value': '更换',
                                            },
                                        ],
                                    },
                                    'IR_2': {
                                        'para_pattern': PatternCollection(r'(选择|更换)(?P<content>.*)为基金提供服务的外部机构'),
                                        'default': '律师事务所、会计师事务所、证券/期货经纪商或其他',
                                        'patterns': [
                                            {
                                                'pattern': PatternCollection(r'律师事务所'),
                                                'value': '律师事务所',
                                            },
                                            {
                                                'pattern': PatternCollection(r'会计师事务所'),
                                                'value': '会计师事务所',
                                            },
                                            {
                                                'pattern': PatternCollection(r'其他'),
                                                'value': '其他',
                                            },
                                            {
                                                'pattern': PatternCollection(r'(?:(?:证券|期货)(?:经纪商)?[、/或]?){1,2}经纪商'),
                                                'value': '证券/期货经纪商',
                                                'condition': [],
                                            },
                                        ],
                                    },
                                },
                                'items': [
                                    '引用第{IRF_1}项{IR_1}{IR_2}为基金提供服务的外部机构；',
                                ],
                            },
                        ],
                    },
                ],
            },
        ]

        paragraphs = [
            {'index': 1, 'text': '发生下列情形时，基金管理人可暂停接受投资人的赎回申请或延缓支付赎回对价：', 'class': 'PARAGRAPH'},
            {'index': 2, 'text': '1、因不可抗力导致基金无法正常运作或无法接受赎回；', 'class': 'PARAGRAPH'},
            {'index': 3, 'text': '2、选择、更换律师事务所、会计师事务所、证券/期货经纪商或其他为基金提供服务的外部机构；', 'class': 'PARAGRAPH'},
            {'index': 4, 'text': '3、导致基金管理人无法计算当日基金资产净值或无法进行证券交易；', 'class': 'PARAGRAPH'},
            {'index': 5, 'text': '(4)、基金管理人无法按时公布基金份额净值。', 'class': 'PARAGRAPH'},
            {'index': 6, 'text': '5、发生基金合同规定的暂停基金资产估值情况时。', 'class': 'PARAGRAPH'},
            {'index': 7, 'text': '(6)、基金所投资的投资品种的估值出现重大转变时。', 'class': 'PARAGRAPH'},
        ]

        results = [
            ['发生除上述第3项以外的情形'],
            ['除上述1、4、5、6情形之外'],
            [
                '上述“一、基金费用的种类”中第1-3项费用',
                '上述“一、基金费用的种类”中第1、2、3项费用',
            ],
            ['1、因不可抗力导致基金无法正常运作或无法接受赎回；'],
            ['2、引用第1项选择、更换律师事务所、会计师事务所、证券/期货经纪商或其他为基金提供服务的外部机构；'],
            [
                '证券/期货交易所交易时间非正常停市，导致基金管理人无法计算当日基金资产净值或无法进行证券交易；',
                '期货/证券交易所交易时间非正常停市，导致基金管理人无法计算当日基金资产净值或无法进行证券交易；',
            ],
        ]

        result = PublicReplaceTemplateChecker.recombined_template(results)

        self.assert_replace_template(inner_replace, paragraphs, result)

    def test_chapter_recombination(self):
        inner_recombination = [
            '测试头部',
            {
                'type': TemplateCheckTypeEnum.CHAPTER_COMBINATION.value,
                'patterns': [
                    PatternCollection(r'不可抗力导致基金无法正常运作'),
                    PatternCollection(r'交易时间非正常停市.?导致基金管理人无法'),
                    PatternCollection(r'为基金提供服务的外部机构'),
                ],
                # 头部添加自增序号1、2、
                'serial_num_pattern': P_PARA_PREFIX_NUM,
                'default_prefix_type': '{num}、',
                'items': [
                    '因不可抗力导致基金无法正常运作或无法接受赎回；',
                    '证券/期货交易所交易时间非正常停市，导致基金管理人无法计算当日基金资产净值或无法进行证券交易；',
                    '选择、更换律师事务所、会计师事务所、证券/期货经纪商或其他为基金提供服务的外部机构；',
                ],
                'child_items': [
                    {'items': ['1）无法赎回标题的内容；']},
                    {'items': ['1）非正常停市；']},
                    {'items': ['1）更换律师事务所；', '2）更换会计师事务所；']},
                ],
            },
            '测试尾部',
        ]

        paragraphs = [
            {'index': 1, 'text': '发生下列情形时，基金管理人可暂停接受投资人的赎回申请或延缓支付赎回对价：', 'class': 'PARAGRAPH'},
            {'index': 2, 'text': '1、因不可抗力导致基金无法正常运作或无法接受赎回；', 'class': 'PARAGRAPH'},
            {'index': 3, 'text': '1）无法赎回标题的内容；', 'class': 'PARAGRAPH'},
            {'index': 4, 'text': '2、选择、更换律师事务所、会计师事务所、证券/期货经纪商或其他为基金提供服务的外部机构；', 'class': 'PARAGRAPH'},
            {'index': 5, 'text': '1）更换律师事务所；', 'class': 'PARAGRAPH'},
            {'index': 6, 'text': '2）更换会计师事务所；', 'class': 'PARAGRAPH'},
            {'index': 7, 'text': '3、证券/期货交易所交易时间非正常停市，导致基金管理人无法计算当日基金资产净值或无法进行证券交易；', 'class': 'PARAGRAPH'},
            {'index': 8, 'text': '1）非正常停市；', 'class': 'PARAGRAPH'},
        ]

        result = [
            ['测试头部'],
            ['1、因不可抗力导致基金无法正常运作或无法接受赎回；'],
            ['1）无法赎回标题的内容；'],
            ['2、选择、更换律师事务所、会计师事务所、证券/期货经纪商或其他为基金提供服务的外部机构；'],
            ['1）更换律师事务所；'],
            ['2）更换会计师事务所；'],
            ['3、证券/期货交易所交易时间非正常停市，导致基金管理人无法计算当日基金资产净值或无法进行证券交易；'],
            ['1）非正常停市；'],
            ['测试尾部'],
        ]

        result = PublicReplaceTemplateChecker.recombined_template(result)

        self.assert_replace_template(inner_recombination, paragraphs, result)
