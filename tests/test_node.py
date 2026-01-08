import pytest

from remarkable.answer.node import AnswerItem, simple_json_v2


@pytest.mark.parametrize(
    "s,expected",
    [
        (
            {
                "key": '["资产管理合同:0","集合计划的募集:2","测试字段4:0"]',
                "data": [
                    {
                        "boxes": [
                            {
                                "box": {
                                    "box_left": 149.23076923076923,
                                    "box_top": 330.7692307692308,
                                    "box_right": 291.53846153846155,
                                    "box_bottom": 357.6923076923077,
                                },
                                "page": 1,
                                "text": "份额持有人大会及日常机构",
                            }
                        ],
                        "handleType": "wireframe",
                    }
                ],
                "value": "",
                "schema": {
                    "data": {"label": "测试字段4", "required": False, "multi": True, "type": "文本", "words": ""}
                },
                "manual": True,
                "custom": True,
            },
            {
                "text": "份额持有人大会及日常机构",
            },
        ),
        (
            {
                "key": '["资产管理合同:0","集合计划的募集:2","测试字段4:0"]',
                "data": [
                    {
                        "boxes": [
                            {
                                "box": {
                                    "box_left": 149.23076923076923,
                                    "box_top": 330.7692307692308,
                                    "box_right": 291.53846153846155,
                                    "box_bottom": 357.6923076923077,
                                },
                                "page": 1,
                                "text": "份额持有人大会及日常机构",
                            }
                        ],
                        "handleType": "wireframe",
                    }
                ],
                "value": "哈喽Kitty",
                "schema": {
                    "data": {"label": "测试字段4", "required": False, "multi": True, "type": "Hello", "words": ""}
                },
                "manual": True,
                "custom": True,
            },
            {
                "choices": ["哈喽Kitty"],
                "text": "份额持有人大会及日常机构",
            },
        ),
        (
            {
                "key": '["资产管理合同:0","集合计划的募集:2","测试字段4:0"]',
                "data": [],
                "value": ["哈喽", "Kitty"],
                "schema": {
                    "data": {"label": "测试字段4", "required": False, "multi": True, "type": "World", "words": ""}
                },
                "manual": True,
                "custom": True,
            },
            {
                "choices": ["哈喽", "Kitty"],
                "text": None,
            },
        ),
        (
            {
                "key": '["资产管理合同:0","集合计划的募集:2","测试字段4:0"]',
                "data": [],
                "value": "",
                "schema": {
                    "data": {"label": "测试字段4", "required": False, "multi": True, "type": "文本", "words": ""}
                },
                "manual": True,
                "custom": True,
            },
            {
                "text": None,
            },
        ),
    ],
)
def test_simple_json_v2(s, expected):
    assert simple_json_v2({"Hello", "World"}, AnswerItem(**s)) == expected
