# 深交所填报系统相关接口

## 用户登录
POST ~/api/v1/login
```json
{
    "name": "admin",  // 用户名
    "password": "abc"  // 用户密码
}
```
RETURN:
若登录成功：302 跳转

若登录失败：
```json
{
    "status": "error",
    "message": "用户名或密码错误",
    "errors": {}
}
```

## 填报系统使用的项目和目录id
（用于任务创建时上传文档）
GET ~/api/v1/plugins/fileapi/tree/default
RETURN:
```json
{
    "status": "ok",
    "data": {
        "file_tree_id": 413,  // 目录id
        "file_project": 23    // 项目id
    }
}
```

## 任务列表
GET ~/szse/question/search
PARAMS:
| name | type | intro |
| ---- | ---- | ----- |
| page | int | 分页页码 |
| size | int | 分页大小 |
| name | str | 任务名称筛选 |
| id | str | 任务编号 |
| fill_in_status | enum | 0: 待填报；2: 已提交 |
RETURN:
```json
{
    "status": "ok",
    "data": {
        "page": 1,
        "size": 20,
        "total": 1,  // 文件数量
        "items": [
            {
                "name": "ZLF_260.docx",  // 文件名
                "fid": 404,              // 文件id
                "qid": 9291,             // 提取任务id
                "user_name": "admin",    // 上传用户
                "question_name": "ZLF",  // 任务名称
                "question_num": "260",   // 任务编号
                "question_ai_status": 3, // 提取状态
                "fill_in_status": 2,     // 填报状态
                "fill_in_user": "admin", // 填报用户
                "data_updated_utc": 1611278532  // 填报时间
            }
        ]
    }
}
```

## 创建任务
POST ~/api/v1/plugins/fileapi/tree/<tree_id>/file
FORM:
| name | type | intro |
| ---- | ---- | ----- |
| name | str | 必填，任务名称 |
| file | file | 必填，文档 |
RETURN:
```json
{
    "status": "ok",
    "data": {
        "id": 782,  // 文件id
        "tree_id": 141,  // 目录id
        "uid": 17,  // 上传用户id
        "pid": 5,  // 所属项目id
        "name": "ZLF_260.docx",
    }
}
```

注：url 中的 <tree_id> 应取值为 `/default` 接口中获取的 file_tree_id

## 页面信息
GET ~/api/v1/plugins/fileapi/file/<file_id>/chapter-info
RETURN:
```json
{
    "status": "ok",
    "data": [
        {
            "page": 0,  // 页码
            "width": 595,  // 宽度
            "height": 841,  // 高度
            "rotate": 0  // 旋转角度
        },
        {
            "page": 1,
            "width": 595,
            "height": 841,
            "rotate": 0
        },
        ...
    ]
}
```

## 提取结果
GET ~/api/v1/plugins/szse/json_answer/<qid>
RETURN:
```json
{
    "status": "ok",
    "data": {
        "json_answer": {  // 答案内容
            "联系方式": [
                {
                    "发行人": [
                        {
                            "公司网址": {
                                "data": [
                                    {
                                        "boxes": [
                                            {
                                                "box": {  // 外框
                                                    "box_top": 360.9665,
                                                    "box_left": 222.9534,
                                                    "box_right": 306.2482,
                                                    "box_bottom": 368.4243
                                                },
                                                "page": 28,  // 页码
                                                "text": "www.incubecn.com"  //内容
                                            }
                                        ]
                                    }
                                ],
                                "text": "www.incubecn.com",
                                "value": null,
                                "manual": false,
                                "schema_path": "深交所信息抽取-创业板-注册制-财务基础数据|五-发行人基本情况|公司网址"
                            },
                            "注册地址": null
                        }
                    ],
                    ...
                }
            ],
            "财务基础数据": [
                ...
            ],
            ...
        },
        "json_schema": {  // 答案结构
            "schemas": [
                {
                    "name": "创业板招股说明书信息抽取",
                    "orders": [
                        "财务基础数据",
                        "项目基本情况表",
                        "联系方式",
                        "发行人相关人员情况",
                        "产品及其他情况表"
                    ],
                    "schema": {
                        "联系方式": {
                            "type": "联系方式",
                            "is_leaf": false
                        },
                        "财务基础数据": {
                            "type": "财务基础数据",
                            "is_leaf": false
                        },
                        "项目基本情况表": {
                            "type": "项目基本情况表",
                            "is_leaf": false
                        },
                        "产品及其他情况表": {
                            "type": "产品及其他情况表",
                            "is_leaf": false
                        },
                        "发行人相关人员情况": {
                            "type": "发行人相关人员情况",
                            "is_leaf": false
                        }
                    }
                },
                {
                    "name": "财务基础数据",
                    "orders": [
                        "合并资产负债表主要数据（万元）",
                        "合并利润表主要数据（万元）",
                        "合并现金流量表主要数据（万元）",
                        "最近三年一期主要财务指标表",
                        "其他指标"
                    ],
                    "schema": {
                        "其他指标": {
                            "type": "其他指标",
                            "is_leaf": false
                        },
                        "合并利润表主要数据（万元）": {
                            "type": "合并利润表主要数据（万元）",
                            "is_leaf": false
                        },
                        "最近三年一期主要财务指标表": {
                            "type": "最近三年一期主要财务指标表",
                            "is_leaf": false
                        },
                        "合并现金流量表主要数据（万元）": {
                            "type": "合并现金流量表主要数据（万元）",
                            "is_leaf": false
                        },
                        "合并资产负债表主要数据（万元）": {
                            "type": "合并资产负债表主要数据（万元）",
                            "is_leaf": false
                        }
                    }
                },
                ...
            ]
        },
        "answer_status": {  //填报状态
            "联系方式": {
                "发行人": 0,
                "保荐机构": 0,
                "律师事务所": 0,
                "会计师事务所": 0,
                "资产评估机构": 0
            },
            "财务基础数据": {
                "其他指标": 0,
                "合并利润表主要数据（万元）": 0,
                "最近三年一期主要财务指标表": 0,
                "合并现金流量表主要数据（万元）": 0,
                "合并资产负债表主要数据（万元）": 0
            },
            "项目基本情况表": {
                "发行人信息": 0,
                "发行前股本结构（万股）": 0,
                "持股5%以上（含5%）股东信息": 0
            },
            "产品及其他情况表": {},
            "发行人相关人员情况": {
                "发行人相关人员情况": 0
            }
        }
    }
}
```

注：url 中的 qid 为任务列表接口中的 `qid 提取任务id`


## 文档页面
GET: ~/api/v1/plugins/fileapi/file/<file_id>/page/<page_index>
RETURN:
SVG data


## 页面画框取字
POST: ~/api/v1/plugins/fileapi/file/<file_id>/text_in_box
```json
[
    {
        "box": [  // 外框坐标，左上右下
            250,
            74.61538461538461,
            348.46153846153845,
            107.6923076923077
        ],
        "page": 1 // 页码
    }
]
```
RETURN:
```json
{
    "status": "ok",
    "data": [
        {
            "box": {
                "box": [
                    250,
                    74.61538461538461,
                    348.46153846153845,
                    107.6923076923077
                ],
                "page": 1
            },
            "text": "声明及承诺"
        }
    ]
}
```

## 确认保存
POST: ~/api/v1/plugins/szse/json_answer/status/<qid>
```json
{
    "field": "重大科技专场",  // 字段
    "field_data": [         // 内容
        {
            "项目名称": {
                "data": [
                    {
                        "boxes": []
                    }
                ],
                "text": "111",
                "manual": true
            }
        }
    ],
    "status": 1
}
```


## 提交填报
POST: ~/api/v1/plugins/szse/json_answer/<qid>
```json
{
    "data": {
        "json_answer": ...,  // 同 提取结果 中的 json_answer 结构
        "json_schema": ...,  // 同 提取结果 中的 json_schema 结构
    }
}
```

RETURN:
```json
{"status": "ok", "data": {}}
```
