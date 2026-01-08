from collections import defaultdict

from remarkable.answer.common import get_first_level_field
from remarkable.common.constants import FileAnswerMergeStrategy
from remarkable.pw_models.answer_data import NewAnswerData
from remarkable.schema.answer import AnswerGroup


def get_key_value_map(items):
    ret = {}
    for item in items:
        ret[get_first_level_field(item["key"])] = item["value"]
    return ret


def test_merge_groups():
    new_items = [
        {"key": '["私募基金合同:0","产品名称:0"]', "record": None, "value": "产品名称-new"},
        {"key": '["私募基金合同:0","平仓线:0"]', "record": None, "value": "平仓线-new"},
        {"key": '["私募基金合同:0","预警线:0"]', "record": None, "value": "预警线"},
        {"key": '["私募基金合同:0","投资范围:0"]', "record": None, "value": "投资范围"},
    ]
    old_items = [
        {"key": '["私募基金合同:0","产品名称:0"]', "record": [1], "value": "产品名称-edited"},
        {"key": '["私募基金合同:0","平仓线:0"]', "record": None, "value": "平仓线"},
        {"key": '["私募基金合同:0","预警线:0"]', "record": None, "value": "预警线"},
        {"key": '["私募基金合同:0","投资策略:0"]', "record": None, "value": "投资策略"},
    ]
    only_latest_map = {
        "产品名称": "产品名称-new",
        "平仓线": "平仓线-new",
        "预警线": "预警线",
        "投资范围": "投资范围",
    }
    edited_first_map = {
        "产品名称": "产品名称-edited",
        "平仓线": "平仓线-new",
        "预警线": "预警线",
        "投资范围": "投资范围",
        "投资策略": "投资策略",
    }
    old_first_map = {
        "产品名称": "产品名称-edited",
        "平仓线": "平仓线",
        "预警线": "预警线",
        "投资策略": "投资策略",
        "投资范围": "投资范围",
    }

    old_data_groups = defaultdict(AnswerGroup)
    for item in old_items:
        first_level_field = get_first_level_field(item["key"])
        group = old_data_groups[first_level_field]
        group.items.append(item)
        group.manual = group.manual or bool(item["record"])

    new_data_groups = defaultdict(AnswerGroup)
    for item in new_items:
        first_level_field = get_first_level_field(item["key"])
        group = new_data_groups[first_level_field]
        group.items.append(item)

    expected_options = [
        (
            FileAnswerMergeStrategy.ONLY_LATEST,
            only_latest_map,
        ),
        (
            FileAnswerMergeStrategy.OLD_FIRST,
            old_first_map,
        ),
        (
            FileAnswerMergeStrategy.EDITED_FIRST,
            edited_first_map,
        ),
    ]
    for merge_strategy, expected_map in expected_options:
        answer_datas = NewAnswerData.merge_groups(old_data_groups, new_data_groups, merge_strategy)
        assert len(answer_datas) == len(expected_map)
        answer_datas_map = get_key_value_map(answer_datas)
        for key, value in expected_map.items():
            assert answer_datas_map[key] == value
