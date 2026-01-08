# fmt: off
# 替换模板中单选或多选项
import itertools

from remarkable.common.pattern import PatternCollection
from remarkable.plugins.cgs.common.chapters_patterns import CustodyChapterPattern
from remarkable.plugins.cgs.common.enum_utils import TemplateCheckTypeEnum
from remarkable.plugins.cgs.common.patterns_util import P_PARA_PREFIX_NUM
from remarkable.plugins.cgs.common.template_condition import (
    ContentConditional,
    TemplateConditional,
    TemplateName,
)

CALCULATION_WITHDRAWAL = ['计算计提', '计算', '计提']
SABBATICAL_LEAVE = ['公休假（公休日）', '公休假', '公休日']


TEMPLATE_WITH_REPLACE_CONDITIONS = [
    {
        'label': 'template_950',
        'related_name': '基金费用',
        'name': '基金费用',
        'schema_fields': [
            '托管费率',
            '托管费计提及支付方式',
            '基金费用的其他规则',
        ],
        'from': '证券投资基金托管业务管理办法（证监会令第172号修订 2020年7月10日）',
        'origin': [
            '第二十五条 基金托管人应当按照市场化原则，综合考虑基金托管规模、产品类别、服务内容、业务处理难易程度等因素，与基金管理人协商确定基金托管费用的计算方式和方法。',
            '基金托管费用的计提方式和计算方法应当在基金合同、托管协议、基金招募说明书中明确列示。',
        ],
        "contract_content": [
            "《证券投资基金信息披露内容与格式准则第7号<托管协议的内容与格式>》（证监基金字[2005]203号）",
            '第三十一条 订明基金托管人对从基金财产中列支的各类费用进行复核及支付的原则和程序，以及该类费用列支违反《基金法》、基金合同、《运作办法》及其他有关规定时的处理方式。',
        ],
        'templates': [
            {
                'name': TemplateName.EDITING_NAME,
                'content_title': TemplateName.EDITING_TITLE,
                'chapter': CustodyChapterPattern.CHAPTER_FUND_EXPENSES,
                'content_condition': ContentConditional.TRUSTEE_FEE,
                'min_ratio': 0.3,
                'items': [
                    '（一）基金托管人的托管费',
                    '本基金的托管费按前一日基金资产净值的{X}的年费率计提。托管费的计算方法如下：',
                    'H=E×{X1}÷当年天数',
                    'H为每日应计提的基金托管费',
                    'E为前一日的基金资产净值',
                    # https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/1598#note_329337
                    [
                        ('基金托管费每日计提，按月支付。由基金托管人根据与基金管理人核对一致的估值数据，自动在次月初5个工作日内按照指定的账户路径进行支付。'
                         '若遇法定节假日、休息日或不可抗力等，支付日期顺延。费用自动扣划后，基金管理人应进行核对，如发现数据不符，应及时联系基金托管人协商解决。'),
                        *[
                            f"基金托管费每日{v1}，逐日累计至每个月月末，按月支付。经基金管理人与基金托管人核对一致后，基金管理人向基金托管人发送基金托管费划款指令，"
                            f"由基金托管人于次月首日起{{X2}}个工作日内从基金财产中一次性支取。若遇法定节假日、{v2}等，支付日期顺延。"
                            for v1, v2 in
                            itertools.product(CALCULATION_WITHDRAWAL, SABBATICAL_LEAVE)
                        ],
                        *[
                            f"基金托管费每日{v1}，逐日累计至每个月月末，按月支付。基金托管人自基金成立日的次月起，于每月前10个工作日内将托管费直接从基金财产中支付给基金托管人。"
                            f"但支付前基金管理人应与基金托管人核对一致，且基金管理人需保证划款日在基金托管资金账户中有足够的资金余额。若遇法定节假日、{v2}，支付日期顺延，"
                            f"若遇不可抗力或委托财产无法变现致使无法按时支付的，顺延至最近可支付日支付。"
                            for v1, v2 in
                            itertools.product(CALCULATION_WITHDRAWAL, SABBATICAL_LEAVE)
                        ],
                    ],
                    '收取托管费的收款账户信息如下：',
                    '账户名称：中国银河证券股份有限公司',
                    '开户行：兴业银行股份有限公司北京世纪坛支行',
                    '账号：321200100100059631',
                    '大额支付系统号：309100001209',
                    {
                        'conditions': [TemplateConditional.SPECIAL_TYPE_LINKED_FUND],
                        'items': [
                            '基金托管人对本基金投资组合中投资于目标ETF部分的基金资产净值不计提基金托管费。',
                            '前一日的基金资产净值为已扣除本基金投资于目标ETF部分基金资产净值后的净额，金额为负时以零计。',
                        ]
                    },
                    '基金的其他费用按照《基金合同》的约定计提和支付。',
                ],
            },
        ],
    },
    {
        'label': 'template_941',
        'related_name': '基金资产净值计算和会计核算',
        'name': '估值方法-证券投资基金的估值',
        'schema_fields': ['估值方法'],
        'from': [
            '《公开募集证券投资基金运作指引第2号——基金中基金指引（证监会公告〔2016〕20号 2016年9月11日）》',
            '《基金中基金（FOF）审核指引（证监会机构部2017年4月24日）》',
        ],
        'origin': [
            '第八条 基金中基金应当采用公允的估值方法，及时、准确地反映基金资产的价值变动。基金管理人应当在基金中基金所投资基金披露净值的次日，及时披露基金中基金份额净值和份额累计净值。',
            '七、估值方法及时效',
            '（一）FOF的估值按照《基金中基金估值业务指引》执行。',
            '（二）若FOF投资范围中明确不投资QDII，则T日的基金份额净值应不迟于T+2日公告；若投资范围包括QDII，则T日的基金份额净值应不迟于T+3日公告。',
            '（三）若占相当比例的被投资基金暂停估值，FOF也可相应暂停。',
        ],
        'templates': [
            {
                'name': TemplateName.EDITING_NAME,
                'content_title': TemplateName.EDITING_TITLE,
                'chapter': CustodyChapterPattern.CHAPTER_FUND_NET_ASSET_VALUE_CALCULATION_ACCOUNTING,
                'items': [
                    {
                        'conditions': [TemplateConditional.SIDE_TYPE_FOF],
                        'items': [
                            [
                                '证券投资基金的估值',
                                '基金份额的估值',
                            ],
                            {
                                'type': TemplateCheckTypeEnum.CHAPTER_COMBINATION.value,
                                'patterns': [
                                    PatternCollection(r'非上市基金的估值'),
                                    PatternCollection(r'(?<!非)上市基金的估值'),
                                    PatternCollection(r'特殊情况.*?根据以下原则进行估值'),
                                ],
                                'serial_num_pattern': P_PARA_PREFIX_NUM,
                                'default_prefix_type': '（{num}）',
                                'items': [
                                    '非上市基金的估值',
                                    '上市基金的估值',
                                    '如遇所投资基金不公布基金份额净值、进行折算或拆分、估值日无交易等特殊情况，基金管理人根据以下原则进行估值：',
                                ],
                                'child_items': [
                                    {
                                        'type': TemplateCheckTypeEnum.RECOMBINATION.value,
                                        'patterns': [
                                            PatternCollection(r'非货币市场'),
                                            PatternCollection(r'(?<!非)货币市场'),
                                        ],
                                        # 头部添加自增序号1、2、
                                        'serial_num_pattern': P_PARA_PREFIX_NUM,
                                        'default_prefix_type': '{num}）',
                                        'items': [
                                            '境内非货币市场基金按其估值日的份额净值估值；',
                                            '境内货币市场基金，如其披露份额净值，则按其估值日的份额净值估值；如其披露万份（百份）收益，按其前一估值日后至估值日期间（含节假日）的万份（百份）收益计提估值日基金收益。',
                                        ],
                                    },
                                    {
                                        'type': TemplateCheckTypeEnum.RECOMBINATION.value,
                                        'patterns': [
                                            PatternCollection(r'ETF基金'),
                                            PatternCollection(r'(?<!定期)开放式基金'),
                                            PatternCollection(r'定期开放式基金'),
                                            PatternCollection(r'交易型货币市场基金'),
                                        ],
                                        'serial_num_pattern': P_PARA_PREFIX_NUM,
                                        'default_prefix_type': '{num}）',
                                        'items': [
                                            'ETF基金按其估值日的收盘价估值；',
                                            '境内上市开放式基金（LOF）按其估值日的份额净值估值；',
                                            '境内上市定期开放式基金、封闭式基金按其估值日的收盘价估值；',
                                            '对于境内上市交易型货币市场基金，如其披露份额净值，则按其估值日的份额净值估值；如其披露万份（百份）收益，则按其前一估值日后至估值日期间（含节假日）的万份（百份）收益计提估值日基金收益。',
                                        ],
                                    },
                                    {
                                        'type': TemplateCheckTypeEnum.RECOMBINATION.value,
                                        'patterns': [
                                            PatternCollection(r'未公布估值日基金份额净值'),
                                            PatternCollection(r'交易日的收盘价估值.*?调整最近交易市价'),
                                            PatternCollection(r'(?:基金份额净值或收盘价|单位基金份额分红金额|折算拆分比例|持仓份额)等因素合理确定公允价值'),
                                        ],
                                        'serial_num_pattern': P_PARA_PREFIX_NUM,
                                        'default_prefix_type': '{num}）',
                                        'items': [
                                            '以所投资基金的基金份额净值估值的，若所投资基金与本基金估值频率一致但未公布估值日基金份额净值，按其最近公布的基金份额净值为基础估值；',
                                            '以所投资基金的收盘价估值的，若估值日无交易，且最近交易日后市场环境未发生重大变化，按最近交易日的收盘价估值；'
                                            '如最近交易日后市场环境发生了重大变化的，可使用最新的基金份额净值为基础或参考类似投资品种的现行市价及重大变化因素调整最近交易市价，确定公允价值；',
                                            '如果所投资基金前一估值日至估值日期间发生分红除权、折算或拆分，基金管理人应根据基金份额净值或收盘价、单位基金份额分红金额、折算拆分比例、持仓份额等因素合理确定公允价值。',
                                        ],
                                    },
                                ]
                            },
                            '（4）当基金管理人认为所投资基金按上述第（1）至第（3）项进行估值存在不公允时，应与基金托管人协商一致采用合理的估值技术或估值标准确定其公允价值。',
                        ],
                    }
                ],
            },
        ],
    },
]
