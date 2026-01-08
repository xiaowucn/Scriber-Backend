import pytest
from unittest.mock import Mock

from remarkable.predictor.ecitic_predictor.models.investment_restrictions import RestrictionsSplitter
from remarkable.predictor.ecitic_predictor.models.scope_investment import ScopeSplitter


@pytest.mark.parametrize(
    "s,expected",
    [
        (
            [
                {
                    "text": "（1）测试。",
                    "chars": [
                        {"text": "（", "box": [116.9341, 537.164, 119.9843, 545.55]},
                    ],
                },
                {
                    "text": "（14）开始：",
                    "chars": [
                        {"text": "（", "box": [116.9341, 537.164, 119.9843, 545.55]},
                        {"text": "1", "box": [116.9341, 537.164, 119.9843, 545.55]},
                        {"text": "4", "box": [116.9341, 537.164, 119.9843, 545.55]},
                        {"text": "）", "box": [116.9341, 537.164, 119.9843, 545.55]},
                        {"text": "开", "box": [116.9341, 537.164, 119.9843, 545.55]},
                        {"text": "始", "box": [116.9341, 537.164, 119.9843, 545.55]},
                        {"text": "：", "box": [116.9341, 537.164, 119.9843, 545.55]},
                    ],
                },
                {
                    "text": "①利用资产管理计划从事内幕交易、操纵市场或者其他不当、违法的证券期货业务活动；",
                    "chars": [
                        {"text": "①", "box": [111.3297, 559.7895, 121.1875, 569.7894]},
                    ],
                },
                {
                    "text": "②泄露因职务便利获取的未公开信息、利用该信息从事或者明示、暗示他人从事相关交易活动；",
                    "chars": [
                        {"text": "②", "box": [111.2875, 583.1639, 121.1452, 593.1639]},
                    ],
                },
                {
                    "text": "（15）相关法律、行政法规及中国证监会禁止的其他行为。",
                    "chars": [
                        {"text": "（", "box": [116.9341, 116.3743, 119.9843, 124.7604]},
                    ],
                },
            ],
            [
                (
                    {
                        "text": "（1）测试。",
                        "chars": [
                            {"text": "（", "box": [116.9341, 537.164, 119.9843, 545.55]},
                        ],
                    },
                    [
                        {"text": "（", "box": [116.9341, 537.164, 119.9843, 545.55]},
                    ],
                ),
                (
                    {
                        "text": "①利用资产管理计划从事内幕交易、操纵市场或者其他不当、违法的证券期货业务活动；",
                        "chars": [
                            {"text": "①", "box": [111.3297, 559.7895, 121.1875, 569.7894]},
                        ],
                    },
                    [
                        {"text": "（", "box": [116.9341, 537.164, 119.9843, 545.55]},
                        {"text": "1", "box": [116.9341, 537.164, 119.9843, 545.55]},
                        {"text": "4", "box": [116.9341, 537.164, 119.9843, 545.55]},
                        {"text": "）", "box": [116.9341, 537.164, 119.9843, 545.55]},
                        {"text": "开", "box": [116.9341, 537.164, 119.9843, 545.55]},
                        {"text": "始", "box": [116.9341, 537.164, 119.9843, 545.55]},
                        {"text": "：", "box": [116.9341, 537.164, 119.9843, 545.55]},
                        {"text": "①", "box": [111.3297, 559.7895, 121.1875, 569.7894]},
                    ],
                ),
                (
                    {
                        "text": "②泄露因职务便利获取的未公开信息、利用该信息从事或者明示、暗示他人从事相关交易活动；",
                        "chars": [
                            {"text": "②", "box": [111.2875, 583.1639, 121.1452, 593.1639]},
                        ],
                    },
                    [
                        {"text": "（", "box": [116.9341, 537.164, 119.9843, 545.55]},
                        {"text": "1", "box": [116.9341, 537.164, 119.9843, 545.55]},
                        {"text": "4", "box": [116.9341, 537.164, 119.9843, 545.55]},
                        {"text": "）", "box": [116.9341, 537.164, 119.9843, 545.55]},
                        {"text": "开", "box": [116.9341, 537.164, 119.9843, 545.55]},
                        {"text": "始", "box": [116.9341, 537.164, 119.9843, 545.55]},
                        {"text": "：", "box": [116.9341, 537.164, 119.9843, 545.55]},
                        {"text": "②", "box": [111.2875, 583.1639, 121.1452, 593.1639]},
                    ],
                ),
                (
                    {
                        "text": "（15）相关法律、行政法规及中国证监会禁止的其他行为。",
                        "chars": [
                            {"text": "（", "box": [116.9341, 116.3743, 119.9843, 124.7604]},
                        ],
                    },
                    [
                        {"text": "（", "box": [116.9341, 116.3743, 119.9843, 124.7604]},
                    ],
                ),
            ],
        ),
    ],
)
def test_split_restrictions(s, expected):
    assert RestrictionsSplitter().run(s) == expected


@pytest.mark.parametrize(
    "s, expected",
    [
        (
            [
                {
                    "text": "（4）其他：夏洛(主要为:鸡毛装)、好烦恼、马什么梅(简称：马冬梅)。",
                    "chars": [{"char": s} for s in "（4）其他：夏洛(主要为:鸡毛装)、好烦恼、马什么梅(简称：马冬梅)。"],
                    "index": 10,
                }
            ],
            [
                [
                    {"char": "夏"},
                    {"char": "洛"},
                ],
                [
                    {"char": "鸡"},
                    {"char": "毛"},
                    {"char": "装"},
                ],
                [
                    {"char": "好"},
                    {"char": "烦"},
                    {"char": "恼"},
                ],
                [
                    {"char": "马"},
                    {"char": "什"},
                    {"char": "么"},
                    {"char": "梅"},
                ],
                [
                    {"char": "马"},
                    {"char": "冬"},
                    {"char": "梅"},
                ],
            ],
        ),
        (
            [
                {
                    "text": "（1）资产管理产品：夏洛(主要为:鸡毛装)、马什么梅(简称：马冬梅)，参与麻花团队",
                    "chars": [
                        {"char": s}
                        for s in "（1）资产管理产品：夏洛(主要为:鸡毛装)、马什么梅(简称：马冬梅)，参与麻花团队"
                    ],
                    "index": 20,
                }
            ],
            [
                [
                    {"char": "夏"},
                    {"char": "洛"},
                ],
                [
                    {"char": "鸡"},
                    {"char": "毛"},
                    {"char": "装"},
                ],
                [
                    {"char": "马"},
                    {"char": "什"},
                    {"char": "么"},
                    {"char": "梅"},
                ],
                [
                    {"char": "马"},
                    {"char": "冬"},
                    {"char": "梅"},
                ],
                [
                    {"char": "麻"},
                    {"char": "花"},
                    {"char": "团"},
                    {"char": "队"},
                ],
            ],
        ),
    ],
)
def test_split_inverstment(s, expected):
    # 创建模拟的 pdfinsight 
    mock_pdfinsight = Mock()
    
    # 创建 ScopeSplitter 实例并设置必要属性
    splitter = ScopeSplitter()
    splitter.pdfinsight = mock_pdfinsight
    
    # 为 find_element_by_index 提供模拟实现
    def mock_find_element_by_index(index):
        if index < 0:
            return None, None
        # 返回一个简单的模拟元素，包含必要的字段
        return "PARAGRAPH", {
            "text": "模拟段落", 
            "chars": [{"char": c} for c in "模拟段落"],
            "index": index
        }
    
    mock_pdfinsight.find_element_by_index = Mock(side_effect=mock_find_element_by_index)
    
    # 更新测试调用：run 方法现在需要 start_index 参数
    start_index = s[0]["index"]
    assert splitter.run(s[0], start_index) == expected


def test_split_inverstment_split_method():
    """测试 ScopeSplitter 的 split 方法"""
    # 创建模拟的 pdfinsight
    mock_pdfinsight = Mock()
    
    # 创建 ScopeSplitter 实例并设置必要属性
    splitter = ScopeSplitter()
    splitter.pdfinsight = mock_pdfinsight
    
    # 为 find_element_by_index 提供模拟实现
    def mock_find_element_by_index(index):
        if index < 0:
            return None, None
        # 返回一个简单的模拟元素，包含必要的字段
        return "PARAGRAPH", {
            "text": "模拟段落", 
            "chars": [{"char": c} for c in "模拟段落"],
            "index": index
        }
    
    mock_pdfinsight.find_element_by_index = Mock(side_effect=mock_find_element_by_index)
    
    # 测试数据
    test_elements = [
        {
            "text": "（1）资产管理产品：夏洛(主要为:鸡毛装)、马什么梅(简称：马冬梅)，参与麻花团队",
            "chars": [{"char": s} for s in "（1）资产管理产品：夏洛(主要为:鸡毛装)、马什么梅(简称：马冬梅)，参与麻花团队"],
            "index": 20,
        }
    ]
    
    # 调用 split 方法
    results = splitter.split(test_elements)
    
    # 验证结果
    assert len(results) > 0
    assert all(hasattr(result, 'chars') for result in results)
    assert all(hasattr(result, 'element') for result in results)
