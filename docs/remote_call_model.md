# 外部模型对接方法

Scriber 系统支持在预测过程中以 http 方式调用外部模型

每次调用时传入 `文档结构化解析结果` `预测目标 Schema` `预测目标字段`

要求外部模型输出指定格式的解析结果



## 一、外部模型 API 定义

#### 输入：

在预测指定字段时，Scriber 会 `POST` 请求外部模型 API 接口，携带参数

| 参数名     | 类型 | 说明                                                         |
| ---------- | ---- | ------------------------------------------------------------ |
| pdfinsight | file | 文档结构化解析结果，是一个 zip 报，解压后第一个文件为 json 格式数据 |
| schema     | json | 预测目标完整 schema                                          |
| path       | json | 本次请求预测的字段 path，如 `["子公司基本信息", "联系电话"]` |

##### 关于 Schema

schema 为 Scriber 系统定义的目标文档输出内容结构，这里需要根据 schema + path 取的目标字段的定义，然后进行预测，输出需要符合此定义

基本结构如下：

```json
{
        "schema_types": [],
        "version": "b9006de7e092edb2eba0f0d4016c330e",
        "schemas": [
            {
                "name": "重组报告业务",  // schema 名称
                "schema": {             // 在此定义 schema 包含的属性
                    "公司名称": {               // "公司名称" 属性
                        "multi": true,         // 是否可多选
                        "_index": 340,
                        "required": false,     // 是否必填
                        "name": "公司名称",     // 属性名称
                        "type": "文本"         // 属性类型，基本类型包括：文本、数字、日期
                    },
                    "收购标的情况": {
                        "multi": true,
                        "_index": 351,
                        "required": false,
                        "name": "收购标的情况",
                        "type": "收购标的情况"   // 属性类型，这里是一个自定义类型，对应另外一个子 schema（见下方）
                    }
                },
                "orders": [             // 显示顺序
                    "公司名称",
                    "收购标的情况"
                ]
            },
            {
                "name": "收购标的情况",           // 子 schema "收购标的情况"
                "schema": {
                    "注册地": {
                        "multi": true,
                        "_index": 363,
                        "required": false,
                        "name": "注册地",
                        "type": "文本"
                    },
                    "收购标的": {
                        "multi": true,
                        "_index": 362,
                        "required": false,
                        "name": "收购标的",
                        "type": "文本"
                    }
                },
                "orders": [
                    "收购标的",
                    "注册地"
                ],
            }
        ]
    }
```



#### 输出：

根据字段定义，输出一段 json 解析结果，这里分两种情况：

若目标字段为 schema 中的叶子节点，应输出 `AnswerItem` 数组：

```json
[answer_item1, answer_item2]
```

若目标字段为非叶子节点，并输出包含其子节点的 dict 数组，支持多级嵌套：

```python
[
    {
        "公司名称": [answer_item1, ]
        "收购标的情况": [
            {
                "收购标的": [answer_item2, ],
                "注册地": [answer_item3, ],
            },
            {
                "收购标的": [answer_item4, ],
                "注册地": [answer_item5, ],
            },
        ]
    },
    ...
]
```



其中，`AnswerItem` 结构如下：

```json
{
    "boxes": [
        {
            "text": "",                             # 内容
            "page": page,                           # 页码
            "outline": (top, left, bottom, right),  # 位置外框，top / left 为左上角坐标, bottom / right 为右下角坐标
        }
    ],
    "enum": "",                                     # 枚举值，用于枚举字段，不适用则置空
}
```





## 二、文档结构化解析结果

文档解析结果是 Scriber 系统对输入文档的预处理，包含结构化的 目录、段落、表格 等信息

主要结构如下：

```json
{
  "syllabuses": [],  # 目录结构
  "paragraphs": [],  # 段落内容
  "tables": [],      # 表格内容
  ...   # 省略不常用字段
}
```



关于 `目录结构`：

```json
[
    {
        "level": 1,
        "index": 0,  # 目录索引
        "children": [],
        "dest": null,
        "parent": -1,  # 上级索引，-1 为无上级
        "range": [     # 内容元素块范围（元素块指段落、表格等）
            26,
            28
        ],
        "title": "一、发行人声明"
    },
    {
        "level": 1,
        "index": 1,
        "children": [],
        "dest": null,
        "parent": -1,
        "range": [
            28,
            30
        ],
        "title": "二、发行人相关负责人声明"
    }
]
```

```python
[{'children': [1, 9, 28, 31],
  'dest': {'box': [208, 86, 387, 103], 'page_id': None, 'page_index': 42},
  'index': 0,    # 目录索引
  'level': 1,
  'parent': -1,  # 上级索引，-1 为无上级
  'range': [386, 522],  # 内容元素块范围（元素块指段落、表格等）
  'title': '第一章 本次交易概述'},
 {'children': [2, 5, 8],
  'dest': {'box': [121, 134, 359, 149], 'page_id': None, 'page_index': 42},
  'index': 1,
  'level': 2,
  'parent': 0,   # 上级索引，这里指 index 为 0 的目录
  'range': [387, 422],
  'title': '一、本次交易的背景、目的及必要性'}]
```



关于 `段落`：

```python
{'class': 'PARAGRAPH',
 'index': 2,  # 元素块索引
 'outline': [136, 275, 458, 292],  # 元素块外框
 'page': 0,  # 页码
 'syllabus': -1,  # 所属目录
 'text': '发行股份及支付现金购买资产暨关联交易',
'chars': [{'bold': True,  # 每一个字符的信息
   'box': [135.6730194091797,  # 字符外框
    275.58648681640625,
    151.55848693847656,
    292.074462890625],
   'char_box': [135.6730194091797,
    275.58648681640625,
    151.55848693847656,
    292.074462890625],
   'familyname': 'SimHei',
   'flag': 0,
   'font_box': [134.82748413085938,
    274.68756103515625,
    152.81781005859375,
    292.6678466796875],
   'fontcolor': 0,
   'fontflags': 524320,
   'fontname': 'SimHei',
   'fontsize': 18,
   'fontweight': 0,
   'has_font': True,
   'italic': False,
   'italic_angle': 0,
   'light': False,
   'nc': [0.0, 0.0, 0.0],
   'nc_alpha': 1.0,
   'page': 0,
   'sc': [0.0, 0.0, 0.0],
   'sc_alpha': 1.0,
   'size': 0,
   'stroking_color': 0,
   'text': '发',
   'text_mode': 2},
   # 省略...
   ],
}
```



关于`表格`：

```json
{
    "index": 4,  // 表格元素块索引
    "page": 0,   // 页码
    "syllabus": -1,  // 所属章节
    "class": "TABLE",
    "outline": [    // 表格位置外框
        83.85890197753906,
        390.22315979003906,
        510.5454406738281,
        466.6995086669922
    ],
    "cells": {    // 每一个单元格信息
        "0_1": {  // 单元格索引，这里指 0行1列 的单元格
            "chars": [],  // 每一个字符信息，与段落相同，省略
            "styles": {   // 单元格样式
                "align_prob": 1,
                "align": "center",
                "fontcolor": "#000000",
                "fontname": "SimSun",
                "italic": false,
                "fontweight": "bold",
                "bg_color": "#FFFFFF"
            },
            "text": "名称",  // 单元内容
            "styles_diff": {},
            "page": 0
        },
        "0_0": {
            "chars": [],  // 省略...
            "styles": {
                "align_prob": 1,
                "align": "center",
                "fontcolor": "#000000",
                "fontname": "SimSun",
                "italic": false,
                "fontweight": "bold",
                "bg_color": "#FFFFFF"
            },
            "text": "交易对方 ",
            "styles_diff": {},
            "page": 0
        }
    },
}
```
