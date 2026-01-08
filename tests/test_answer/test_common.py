from remarkable.answer.common import is_empty_answer


def test_is_empty_answer():
    # 测试空字典
    assert is_empty_answer(None)
    assert is_empty_answer({})
    # 测试没有 userAnswer 和 custom_field 的字典
    assert is_empty_answer({"other_key": {}})
    # 测试 userAnswer 为空
    assert is_empty_answer({"userAnswer": {"items": []}})
    # 测试 userAnswer 有空项
    assert is_empty_answer({"userAnswer": {"items": [{}, {}]}})
    # 测试 userAnswer 有有效项
    assert not is_empty_answer({"userAnswer": {"items": [{"data": "value"}, {"value": "value"}]}})
    # 测试 custom_field 有有效项
    assert not is_empty_answer({"custom_field": {"items": [{"data": "value"}]}}, check_key="custom_field")
