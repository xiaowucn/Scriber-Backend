from remarkable.converter import SimpleJSONConverter, flatten_dict

user_answer = {
    "schema": {
        "schemas": [
            {
                "name": "资产管理合同",
                "orders": ["类别", "集合计划的基本情况", "集合计划的募集"],
                "schema": {
                    "类别": {
                        "type": "文本",
                        "required": False,
                        "multi": False,
                        "name": "类别",
                        "_index": 3,
                        "is_leaf": True,
                    },
                    "集合计划的基本情况": {
                        "type": "集合计划的基本情况",
                        "required": False,
                        "multi": True,
                        "name": "集合计划的基本情况",
                        "_index": 4,
                        "is_leaf": False,
                    },
                    "集合计划的募集": {
                        "type": "集合计划的募集",
                        "required": False,
                        "multi": True,
                        "name": "集合计划的募集",
                        "_index": 5,
                        "is_leaf": False,
                    },
                },
            },
            {
                "name": "集合计划的基本情况",
                "orders": ["运作方式", "投资范围", "存续期限"],
                "schema": {
                    "运作方式": {
                        "type": "文本",
                        "required": False,
                        "multi": True,
                        "name": "运作方式",
                        "_index": 7,
                        "is_leaf": True,
                    },
                    "投资范围": {
                        "type": "文本",
                        "required": False,
                        "multi": True,
                        "name": "投资范围",
                        "_index": 8,
                        "is_leaf": True,
                    },
                    "存续期限": {
                        "type": "文本",
                        "required": False,
                        "multi": True,
                        "name": "存续期限",
                        "_index": 9,
                        "is_leaf": True,
                    },
                },
            },
            {
                "name": "集合计划的募集",
                "orders": ["募集机构", "最低认购金额", "数量"],
                "schema": {
                    "募集机构": {
                        "type": "文本",
                        "required": False,
                        "multi": True,
                        "name": "募集机构",
                        "_index": 11,
                        "is_leaf": True,
                    },
                    "最低认购金额": {
                        "type": "文本",
                        "required": False,
                        "multi": True,
                        "name": "最低认购金额",
                        "_index": 12,
                        "is_leaf": True,
                    },
                    "数量": {
                        "type": "最低认购金额",
                        "required": False,
                        "multi": True,
                        "name": "数量",
                        "_index": 13,
                        "is_leaf": False,
                    },
                },
            },
            {
                "name": "募集机构",
                "orders": ["呵呵"],
                "schema": {
                    "呵呵": {
                        "type": "文本",
                        "required": False,
                        "multi": True,
                        "name": "呵呵",
                        "_index": 15,
                        "is_leaf": True,
                    }
                },
            },
            {
                "name": "最低认购金额",
                "orders": ["未知"],
                "schema": {
                    "未知": {
                        "type": "文本",
                        "required": False,
                        "multi": True,
                        "name": "未知",
                        "_index": 17,
                        "is_leaf": True,
                    }
                },
            },
        ],
        "schema_types": [],
        "version": "60d3a7c5958fd2b9c3be372d4e7c9dad",
        "mold_type": 0,
    },
    "userAnswer": {
        "version": "2.2",
        "items": [
            {
                "key": '["资产管理合同:0","集合计划的基本情况:0","投资范围:0"]',
                "data": [
                    {
                        "boxes": [
                            {
                                "box": {
                                    "box_left": 431.53846153846155,
                                    "box_top": 59.230769230769226,
                                    "box_right": 526.1538461538462,
                                    "box_bottom": 88.46153846153845,
                                },
                                "page": 1,
                                "text": "集合资产管理合同",
                            }
                        ],
                        "handleType": "wireframe",
                    }
                ],
                "value": "",
                "schema": {
                    "data": {"label": "投资范围", "required": False, "multi": True, "type": "文本", "words": ""},
                    "meta": {
                        "_index": 211,
                        "_path": ["资产管理合同", "集合计划的基本情况", "文本"],
                        "_partType": "normal.schema",
                        "_type": {"label": "文本", "type": "basic"},
                        "_isHide": False,
                        "_nodeIndex": 1005,
                        "_deepLabels": ["资产管理合同", "集合计划的基本情况", "投资范围"],
                        "_deepIndex": [0, 0],
                        "_parent": ["资产管理合同", "集合计划的基本情况"],
                    },
                    "children": [],
                },
                "manual": True,
                "marker": {"id": 1, "name": "admin", "others": []},
            },
            {
                "key": '["资产管理合同:0","集合计划的募集:2","募集机构:0"]',
                "data": [
                    {
                        "boxes": [
                            {
                                "box": {
                                    "box_left": 266.15384615384613,
                                    "box_top": 534.6153846153846,
                                    "box_right": 463.07692307692304,
                                    "box_bottom": 569.2307692307692,
                                },
                                "page": 0,
                                "text": "上海光大证券资产管理有限公司",
                            }
                        ],
                        "handleType": "wireframe",
                    }
                ],
                "value": "",
                "schema": {
                    "data": {"label": "募集机构", "required": False, "multi": True, "type": "文本", "words": ""},
                    "meta": {
                        "_index": 214,
                        "_path": ["资产管理合同", "集合计划的募集", "文本"],
                        "_partType": "normal.schema",
                        "_type": {"label": "文本", "type": "basic"},
                        "_isHide": False,
                        "_nodeIndex": 1008,
                        "_deepLabels": ["资产管理合同", "集合计划的募集", "募集机构"],
                        "_deepIndex": [0, 0],
                        "_parent": ["资产管理合同", "集合计划的募集"],
                    },
                    "children": [],
                },
                "manual": True,
                "marker": {"id": 1, "name": "admin", "others": []},
            },
            {
                "key": '["资产管理合同:0","集合计划的募集:0","数量:0","未知:0"]',
                "data": [
                    {
                        "boxes": [
                            {
                                "box": {
                                    "box_left": 507.6923076923077,
                                    "box_top": 596.9230769230769,
                                    "box_right": 540.7692307692307,
                                    "box_bottom": 627.6923076923076,
                                },
                                "page": 1,
                                "text": ".. 45",
                            }
                        ],
                        "handleType": "wireframe",
                        "text": "45",
                    }
                ],
                "value": "",
                "schema": {
                    "data": {
                        "label": "未知",
                        "required": False,
                        "multi": True,
                        "type": "文本",
                        "words": "",
                        "description": None,
                    }
                },
                "manual": True,
                "text": "45",
                "marker": {"id": 1, "name": "admin", "others": []},
            },
        ],
    },
    "custom_field": {
        "version": "2.2",
        "items": [
            {
                "key": '["资产管理合同:0","集合计划的基本情况:0","测试字段:0"]',
                "data": [
                    {
                        "boxes": [
                            {
                                "box": {
                                    "box_left": 161.53846153846152,
                                    "box_top": 226.15384615384613,
                                    "box_right": 446.9230769230769,
                                    "box_bottom": 273.0769230769231,
                                },
                                "page": 0,
                                "text": "光证资管XXX集合资产管理计划",
                            }
                        ],
                        "handleType": "wireframe",
                    }
                ],
                "value": "",
                "schema": {
                    "data": {"label": "测试字段", "required": False, "multi": True, "type": "文本", "words": ""}
                },
                "manual": True,
                "custom": True,
            },
            {
                "key": '["资产管理合同:0","集合计划的募集:0","测试字段2:0"]',
                "data": [
                    {
                        "boxes": [
                            {
                                "box": {
                                    "box_left": 190,
                                    "box_top": 533.0769230769231,
                                    "box_right": 467.6923076923077,
                                    "box_bottom": 572.3076923076923,
                                },
                                "page": 0,
                                "text": "管理人：上海光大证券资产管理有限公司",
                            }
                        ],
                        "handleType": "wireframe",
                    }
                ],
                "value": "",
                "schema": {
                    "data": {"label": "测试字段2", "required": False, "multi": True, "type": "文本", "words": ""}
                },
                "manual": True,
                "custom": True,
            },
            {
                "key": '["资产管理合同:0","一级字段:0"]',
                "data": [
                    {
                        "boxes": [
                            {
                                "box": {
                                    "box_left": 237.69230769230768,
                                    "box_top": 275.38461538461536,
                                    "box_right": 389.2307692307692,
                                    "box_bottom": 316.9230769230769,
                                },
                                "page": 0,
                                "text": "资产管理合同",
                            }
                        ],
                        "handleType": "wireframe",
                    }
                ],
                "value": "",
                "schema": {
                    "data": {
                        "label": "一级字段",
                        "type": "集合计划的募集",
                        "required": False,
                        "multi": True,
                        "words": "",
                    }
                },
                "manual": True,
                "custom": True,
            },
            {
                "key": '["资产管理合同:0","集合计划的募集:1","测试字段3:0"]',
                "data": [
                    {
                        "boxes": [
                            {
                                "box": {
                                    "box_left": 150,
                                    "box_top": 304.6153846153846,
                                    "box_right": 306.15384615384613,
                                    "box_bottom": 331.53846153846155,
                                },
                                "page": 1,
                                "text": "集合计划的参与、退出与转让",
                            }
                        ],
                        "handleType": "wireframe",
                    }
                ],
                "value": "",
                "schema": {
                    "data": {"label": "测试字段3", "required": False, "multi": True, "type": "文本", "words": ""}
                },
                "manual": True,
                "custom": True,
            },
            {
                "key": '["资产管理合同:0","集合计划的募集:2","测试字段3:0"]',
                "data": [
                    {
                        "boxes": [
                            {
                                "box": {
                                    "box_left": 143.84615384615384,
                                    "box_top": 360.7692307692308,
                                    "box_right": 285.38461538461536,
                                    "box_bottom": 386.9230769230769,
                                },
                                "page": 1,
                                "text": "资产管理计划份额的登记",
                            }
                        ],
                        "handleType": "wireframe",
                    }
                ],
                "value": "",
                "schema": {
                    "data": {"label": "测试字段3", "required": False, "multi": True, "type": "文本", "words": ""}
                },
                "manual": True,
                "custom": True,
            },
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
                "key": '["资产管理合同:0","集合计划的募集:0","数量:0","不可:0"]',
                "data": [
                    {
                        "boxes": [
                            {
                                "box": {
                                    "box_left": 233.07692307692307,
                                    "box_top": 276.9230769230769,
                                    "box_right": 376.9230769230769,
                                    "box_bottom": 316.9230769230769,
                                },
                                "page": 0,
                                "text": "资产管理合同",
                            }
                        ],
                        "handleType": "wireframe",
                    }
                ],
                "value": "",
                "schema": {"data": {"label": "不可", "required": False, "multi": True, "type": "文本", "words": ""}},
                "manual": True,
                "custom": True,
            },
        ],
    },
}

expected_result = {
    "类别": None,
    "集合计划的基本情况": [
        {
            "运作方式": None,
            "投资范围": "集合资产管理合同",
            "存续期限": None,
            "测试字段_自定义": "光证资管XXX集合资产管理计划",
        }
    ],
    "集合计划的募集": [
        {
            "募集机构": None,
            "最低认购金额": None,
            "数量": [{"未知": "45", "不可_自定义": "资产管理合同"}],
            "测试字段2_自定义": "管理人：上海光大证券资产管理有限公司",
        },
        {
            "募集机构": "上海光大证券资产管理有限公司",
            "最低认购金额": None,
            "数量": [],
            "测试字段3_自定义": "资产管理计划份额的登记",
            "测试字段4_自定义": "份额持有人大会及日常机构",
        },
        {"测试字段3_自定义": "集合计划的参与、退出与转让"},
    ],
    "一级字段_自定义": "资产管理合同",
}

flattened_answer_with_index = [
    ("类别:0", None),
    ("集合计划的基本情况:0-运作方式:0", None),
    ("集合计划的基本情况:0-投资范围:0", "集合资产管理合同"),
    ("集合计划的基本情况:0-存续期限:0", None),
    ("集合计划的基本情况:0-测试字段_自定义:0", "光证资管XXX集合资产管理计划"),
    ("集合计划的募集:0-募集机构:0", None),
    ("集合计划的募集:0-最低认购金额:0", None),
    ("集合计划的募集:0-数量:0-未知:0", "45"),
    ("集合计划的募集:0-数量:0-不可_自定义:0", "资产管理合同"),
    ("集合计划的募集:0-测试字段2_自定义:0", "管理人：上海光大证券资产管理有限公司"),
    ("集合计划的募集:1-募集机构:0", "上海光大证券资产管理有限公司"),
    ("集合计划的募集:1-最低认购金额:0", None),
    ("集合计划的募集:1-数量", ""),
    ("集合计划的募集:1-测试字段3_自定义:0", "资产管理计划份额的登记"),
    ("集合计划的募集:1-测试字段4_自定义:0", "份额持有人大会及日常机构"),
    ("集合计划的募集:2-测试字段3_自定义:0", "集合计划的参与、退出与转让"),
    ("一级字段_自定义:0", "资产管理合同"),
]

flattened_answer = [
    ("类别", None),
    ("集合计划的基本情况-运作方式", None),
    ("集合计划的基本情况-投资范围", "集合资产管理合同"),
    ("集合计划的基本情况-存续期限", None),
    ("集合计划的基本情况-测试字段_自定义", "光证资管XXX集合资产管理计划"),
    ("集合计划的募集-募集机构", None),
    ("集合计划的募集-最低认购金额", None),
    ("集合计划的募集-数量-未知", "45"),
    ("集合计划的募集-数量-不可_自定义", "资产管理合同"),
    ("集合计划的募集-测试字段2_自定义", "管理人：上海光大证券资产管理有限公司"),
    ("集合计划的募集-募集机构", "上海光大证券资产管理有限公司"),
    ("集合计划的募集-最低认购金额", None),
    ("集合计划的募集-数量", ""),
    ("集合计划的募集-测试字段3_自定义", "资产管理计划份额的登记"),
    ("集合计划的募集-测试字段4_自定义", "份额持有人大会及日常机构"),
    ("集合计划的募集-测试字段3_自定义", "集合计划的参与、退出与转让"),
    ("一级字段_自定义", "资产管理合同"),
]


def test_simple_json_convert():
    converter = SimpleJSONConverter(user_answer)
    converted_answer = converter.convert()
    assert converted_answer == expected_result
    assert list(flatten_dict(converted_answer)) == flattened_answer
    assert list(flatten_dict(converted_answer, keep_index=True)) == flattened_answer_with_index
