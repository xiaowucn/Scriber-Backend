
from remarkable.predictor.ecitic_predictor.models.investment_ratio import remove_unpaired_paren


def test_remove_unpaired_paren_empty():
    """测试空列表"""
    result = remove_unpaired_paren([])
    assert result == []


def test_remove_unpaired_paren_no_brackets():
    """测试没有括号的情况"""
    chars = [{"text": "你好"}, {"text": "世界"}, {"text": "测试"}]
    result = remove_unpaired_paren(chars)
    assert result == chars


def test_remove_unpaired_paren_paired_brackets():
    """测试配对的括号"""
    chars = [{"text": "（"}, {"text": "测试"}, {"text": "）"}]
    result = remove_unpaired_paren(chars)
    assert result == chars


def test_remove_unpaired_paren_multiple_paired():
    """测试多对配对括号"""
    chars = [
        {"text": "（"}, {"text": "第一对"}, {"text": "）"}, 
        {"text": "【"}, {"text": "第二对"}, {"text": "】"}
    ]
    result = remove_unpaired_paren(chars)
    assert result == chars


def test_remove_unpaired_paren_left_bracket_only():
    """测试只有左括号"""
    chars = [{"text": "（"}, {"text": "测试"}, {"text": "内容"}]
    result = remove_unpaired_paren(chars)
    # 左括号应该被移除
    expected = [{"text": "测试"}, {"text": "内容"}]
    assert result == expected


def test_remove_unpaired_paren_right_bracket_only():
    """测试只有右括号"""
    chars = [{"text": "测试"}, {"text": "内容"}, {"text": "）"}]
    result = remove_unpaired_paren(chars)
    # 右括号应该被移除
    expected = [{"text": "测试"}, {"text": "内容"}]
    assert result == expected


def test_remove_unpaired_paren_mixed_unpaired():
    """测试混合的不匹配括号"""
    chars = [
        {"text": "）"},  # 多余右括号 - 应被移除
        {"text": "测试"},
        {"text": "（"},
        {"text": "配对"},
        {"text": "）"},
        {"text": "【"},  # 多余左括号 - 应被移除
        {"text": "内容"},
        {"text": "）"}   # 多余右括号 - 应被移除
    ]
    result = remove_unpaired_paren(chars)
    # 只保留配对的括号（（配对））和内容
    expected = [
        {"text": "测试"},
        {"text": "（"},
        {"text": "配对"},
        {"text": "）"},
        {"text": "内容"}
    ]
    assert result == expected


def test_remove_unpaired_paren_nested_brackets():
    """测试嵌套括号"""
    chars = [
        {"text": "（"}, {"text": "外层"}, {"text": "【"}, 
        {"text": "内层"}, {"text": "】"}, {"text": "）"}
    ]
    result = remove_unpaired_paren(chars)
    assert result == chars


def test_remove_unpaired_paren_complex_case():
    """测试复杂情况"""
    chars = [
        {"text": "）"},  # 移除 - 无配对左括号
        {"text": "投资比例"},
        {"text": "（"}, {"text": "股票"}, {"text": "）"},
        {"text": "【"},  # 移除 - 无配对右括号
        {"text": "债券"},
        {"text": "）"},  # 移除 - 无配对左括号
        {"text": "基金"}
    ]
    result = remove_unpaired_paren(chars)
    expected = [
        {"text": "投资比例"},
        {"text": "（"}, {"text": "股票"}, {"text": "）"},
        {"text": "债券"},
        {"text": "基金"}
    ]
    assert result == expected


def test_remove_unpaired_paren_all_bracket_types():
    """测试所有类型的括号"""
    chars = [
        {"text": "{"}, {"text": "大括号"}, {"text": "}"},
        {"text": "〔"}, {"text": "方头括号"}, {"text": "〕"},
        {"text": "【"}, {"text": "方括号"}, {"text": "】"},
        {"text": "（"}, {"text": "圆括号"}, {"text": "）"},
        {"text": "("}, {"text": "英文括号"}, {"text": ")"}
    ]
    result = remove_unpaired_paren(chars)
    assert result == chars


def test_remove_unpaired_paren_mixed_chars():
    """测试括号与其他字符混合"""
    chars = [
        {"text": "投资"},
        {"text": "（"}, {"text": "股票"}, {"text": "）"},
        {"text": "占比"},
        {"text": "50"},
        {"text": "%"}
    ]
    result = remove_unpaired_paren(chars)
    assert result == chars


def test_remove_unpaired_paren_mixed_english_chinese_brackets():
    """测试中英文圆括号混合匹配"""
    chars = [
        {"text": "("}, {"text": "英文左括号"}, {"text": "）"},  # 英文左+中文右
        {"text": "（"}, {"text": "中文左括号"}, {"text": ")"},  # 中文左+英文右
        {"text": "("}, {"text": "英文配对"}, {"text": ")"},    # 英文配对
        {"text": "（"}, {"text": "中文配对"}, {"text": "）"}   # 中文配对
    ]
    result = remove_unpaired_paren(chars)
    # 所有括号都应该保留，因为都能配对
    assert result == chars