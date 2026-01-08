"""股东股份变更明细(Details of shareholder share changes)"""

from remarkable.predictor.eltype import ElementType

R_ANY_SPACE = r"\s*"

predictor_options = [
    {
        "path": ["清单"],
        "models": [
            {
                "name": "details_of_ssc",
                "target_element": ElementType.TABLE.value,
                "use_all_elements": True,
                "multi_elements": True,
                "sub_primary_key": ["股东名称"],
                "special_title_pattern": ["股东名称"],
                "split_table_pattern": (R_ANY_SPACE.join("变更日期"),),
                "股东名称": {
                    "from_title": (
                        r"股东名称[:：\s]*?(?P<dst>\w+)证[件券]\w+",
                        r"\d+(?P<dst>[^:：\d]+)证[件券]\w+",
                    ),
                    "feature_white_list": [
                        rf"__regex__{R_ANY_SPACE.join('股东名称')}",
                    ],
                },
                "变更日期": {
                    "feature_white_list": [
                        rf"__regex__{R_ANY_SPACE.join('变更日期')}",
                    ],
                },
                "证券代码": {
                    "feature_white_list": [
                        rf"__regex__{R_ANY_SPACE.join('证券代码')}",
                    ],
                },
                "证券简称": {
                    "feature_white_list": [
                        rf"__regex__{R_ANY_SPACE.join('证券简称')}",
                    ],
                },
                "托管单元代码": {
                    "feature_white_list": [
                        rf"__regex__{R_ANY_SPACE.join('托管单元代码')}",
                    ],
                },
                "托管单元名称": {
                    "feature_white_list": [
                        rf"__regex__{R_ANY_SPACE.join('托管单元名称')}",
                    ],
                },
                "证券类别": {
                    "feature_white_list": [
                        rf"__regex__{R_ANY_SPACE.join('证券类别')}",
                    ],
                },
                "流通类型": {
                    "feature_white_list": [
                        rf"__regex__{R_ANY_SPACE.join('流通类型')}",
                    ],
                },
                "权益类别": {
                    "feature_white_list": [
                        rf"__regex__{R_ANY_SPACE.join('权益类别')}",
                    ],
                },
                "挂牌年份": {
                    "feature_white_list": [
                        rf"__regex__{R_ANY_SPACE.join('挂牌年份')}",
                    ],
                },
                "变更股数": {
                    "feature_white_list": [
                        rf"__regex__{R_ANY_SPACE.join('变更股数')}",
                    ],
                },
                "结余股数": {
                    "feature_white_list": [
                        rf"__regex__{R_ANY_SPACE.join('结余股数')}",
                    ],
                },
                "变更摘要": {
                    "feature_white_list": [
                        rf"__regex__{R_ANY_SPACE.join('变更摘要')}",
                    ],
                },
            },
        ],
    },
]

prophet_config = {"depends": {}, "predictor_options": predictor_options}
