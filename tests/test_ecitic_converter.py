import decimal
from unittest.mock import Mock

import pytest

from remarkable.answer.node import AnswerItem
from remarkable.common.schema import Schema
from remarkable.converter.ecitic.util import convert_date, revise_amount
from remarkable.plugins.ecitic.common import EciticExternalAnswerConverter


def test_convert_func():
    test_data = {
        'data': [
            {
                'boxes': [
                    {
                        'page': 5,
                        'box': {
                            'box_top': 157.2794,
                            'box_right': 154.8759,
                            'box_bottom': 166.8468,
                            'box_left': 109.714,
                        },
                        'text': '(0.00,3.00]',
                    }
                ],
                'handleType': 'wireframe',
            }
        ],
        'value': None,
        'text': None,
        'score': '0.29',
        'key': '["“小而分散”类资产:0","新增基础资产剩余期限分布:0","基础资产剩余期限分布（月）:0"]',
        'manual': None,
        'schema': {
            'data': {
                'type': '文本',
                'label': '基础资产剩余期限分布（月）',
                'words': '',
                'multi': False,
                'required': False,
                'description': None,
            }
        },
        'marker': {'id': 1, 'name': 'admin', 'others': []},
        '_migrated': False,
        'meta': None,
        'custom': False,
        'md5': None,
    }
    test_data = AnswerItem(item=test_data)
    test_data.plain_text = '月份: (0.00,3.00]|单位: '
    assert convert_date(test_data) == '(0.00,3.00]'

    test_data.plain_text = '月份: 100天以内|单位: 天'
    assert convert_date(test_data) == '3.33月以内'

    test_data.plain_text = '月份: 100.0天以内|单位: 天'
    assert convert_date(test_data) == '3.33月以内'

    test_data.plain_text = '月份: 30-90天|单位: 天'
    assert convert_date(test_data) == '1.00-3.00月'

    test_data.plain_text = '月份: 30-90|单位: '
    assert convert_date(test_data) == '1.00-3.00'

    test_data = AnswerItem(
        item={
            'data': [
                {
                    'boxes': [
                        {
                            'page': 4,
                            'box': {
                                'box_top': 189.2488,
                                'box_right': 503.9326,
                                'box_bottom': 198.2361,
                                'box_left': 470.3488,
                            },
                            'text': '200,000',
                        }
                    ],
                    'handleType': 'wireframe',
                }
            ],
            'value': None,
            'text': None,
            'score': '0.86',
            'key': '["“小而分散”类资产:0","资产池基本情况:0","单笔基础资产最高加权平均期限（月）:0","数值:0"]',
            'manual': None,
            'schema': {
                'data': {
                    'type': '数字',
                    'label': '数值',
                    'words': '',
                    'multi': False,
                    'required': False,
                    'description': None,
                }
            },
            'marker': {'id': 1, 'name': 'admin', 'others': []},
            '_migrated': False,
            'meta': None,
            'custom': False,
            'md5': None,
        }
    )
    assert convert_date(test_data) == '6667'

    test_data.key = '["“小而分散”类资产:0","资产池基本情况:0","单个债务人平均未偿基础资产余额（万元）:0","数值:0"]'
    test_data.plain_text = '数值: 123|单位: 元'
    assert revise_amount(test_data) == ('万元', decimal.Decimal('0.0123'))


@pytest.fixture(scope="function")
def schema():
    schema = Mock(Schema)
    schema.contains_path.return_value = (True, '')

    return schema


def test_ecitic_external_answer_converter(schema):
    test_data = [
        {  # leaf_node 简化格式
            "产品名称": ["凌顶望岳十五号私募证券投资基金"],
            "投资范围(其它-投资监督)": [
                {
                    "原文": ["主板、科创板、创业板"],
                    "拆分": ["主板", "科创板", "创业板"]
                }
            ]
        },
        {  # 完整格式
            "产品名称": [["凌顶望岳十五号私募证券投资基金"]],
            "投资范围(其它-投资监督)": [
                {
                    "原文": [["主板、科创板、创业板"]],
                    "拆分": [["主板", "科创板", "创业板"]]
                }
            ]
        }
    ]

    except_key_values = {
        '["schema测试:0","产品名称:0"]': ["凌顶望岳十五号私募证券投资基金"],
        '["schema测试:0","投资范围(其它-投资监督):0","原文:0"]': ["主板、科创板、创业板"],
        '["schema测试:0","投资范围(其它-投资监督):0","拆分:0"]': ["主板", "科创板", "创业板"],

    }

    for data in test_data:
        answer_items = EciticExternalAnswerConverter.build_answer(schema, ["schema测试:0"], data)
        for item in answer_items:
            assert [x["text"] for x in item["data"]] == except_key_values[item["key"]]
