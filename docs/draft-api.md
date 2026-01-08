<!-- TOC depthTo:4 -->

- [底稿标注相关API](#底稿标注相关api)
    - [历史查询相关API的ACTION定义](#历史查询相关api的action定义)
    - [文件管理插件](#文件管理插件)
        - [项目管理](#项目管理)
            - [创建项目](#创建项目)
            - [项目列表](#项目列表)
            - [删除项目](#删除项目)
            - [配置项目（名称、默认标签）](#配置项目名称默认标签)
            - [查看项目统计数据](#查看项目统计数据)
        - [目录管理](#目录管理)
            - [查询目录内容](#查询目录内容)
            - [删除目录](#删除目录)
            - [修改目录](#修改目录)
            - [上传文件到目录](#上传文件到目录)
            - [创建子目录](#创建子目录)
            - [查询目录下是否有重名对象（文件或目录）](#查询目录下是否有重名对象文件或目录)
            - [打包上传](#打包上传)
        - [文件管理](#文件管理)
            - [下载文件](#下载文件)
            - [修改文件（名称、标签）](#修改文件名称标签)
            - [删除文件](#删除文件)
            - [下载pdf文档](#下载pdf文档)
            - [文件列表](#文件列表)
            - [文件操作历史查询](#文件操作历史查询)
        - [文件标签](#文件标签)
            - [创建标签](#创建标签)
            - [标签列表](#标签列表)
            - [修改标签](#修改标签)
            - [删除标签](#删除标签)
        - [用户管理](#用户管理)
            - [新建](#新建)
            - [列表](#列表)
            - [按ID查询](#按id查询)
            - [修改](#修改)
            - [删除](#删除)
            - [登录系统](#登录系统)
            - [当前用户操作历史查询](#当前用户操作历史查询)
            - [所有用户操作历史查询(需要用户管理权限)](#所有用户操作历史查询需要用户管理权限)
            - [特定用户操作历史查询(需要用户管理权限)](#特定用户操作历史查询需要用户管理权限)
        - [导出标注数据](#导出标注数据)
            - [新建任务](#新建任务)
            - [任务列表](#任务列表)
            - [删除任务](#删除任务)
            - [导出标注数据](#导出标注数据)
        - [统计模型准确率](#统计模型准确率)
            - [查看模型准确率](#查看准确率)
            - [训练模型](#训练模型)

<!-- /TOC -->

# 底稿标注相关API

## 历史查询相关API的ACTION定义

    LOGIN = 1
    OPEN_PDF = 2
    SUBMIT_ANSWER = 3
    ADMIN_VERIFY = 4
    ADMIN_JUDGE = 5
    CREATE_USER = 6
    MODIFY_USER = 7
    DELETE_USER = 8
    CREATE_MOLD = 9
    MODIFY_MOLD = 10
    DELETE_MOLD = 11
    CREATE_PROJECT = 12
    MODIFY_PROJECT = 13
    DELETE_PROJECT = 14
    CREATE_TREE = 15
    MODIFY_TREE = 16
    DELETE_TREE = 17
    CREATE_FILE = 18
    MODIFY_FILE = 19
    DELETE_FILE = 20
    CREATE_TAG = 21
    MODIFY_TAG = 22
    DELETE_TAG = 23
    UPLOAD_ZIP = 24

## 文件管理插件

### 项目管理

#### 创建项目
POST ~/plugins/fileapi/project
```json
{
  "name": "ipo",
  "default_tags": [1, 2, 3],
  "default_mold": 1,
  "preset_answer_model": "none"
}
```

返回示例：
```json
{
    "data": {
        "name": "aaa",
        "id": 1,
        "rtree_id": 1,
        "default_tags": [1, 2, 3],
        "default_mold": 1,
        "preset_answer_model": "none"
    },
    "status": "ok"
}
```
#### 项目列表
GET ~/plugins/fileapi/project

返回示例：
```json
{
    "data": [{
        "name": "ipo",
        "id": 1,
        "rtree_id": 1,
        "default_tags": [1, 2, 3],
        "default_mold": 1,
        "preset_answer_model": "none"
    },
    {
        "name": "gf",
        "id": 2,
        "rtree_id": 2,
        "default_tags": [1, 2, 3],
        "default_mold": 1,
        "preset_answer_model": "none"
    }],
    "status": "ok"
```

#### 删除项目
DELETE ~/plugins/fileapi/project/:project_id

返回示例：
```json
{
    "data": {},
    "status": "ok"
}
```

#### 配置项目（名称、默认标签）
PUT ~/plugins/fileapi/project/:project_id
```json
{
  "name": "ipo",
  "default_tags": [1, 2, 3],
  "default_mold": 1,
}
```

返回示例：
```json
{
    "data": {
        "name": "ipo",
        "id": 1,
        "rtree_id": 1,
        "default_tags": [1, 2, 3],
        "default_mold": 1,
        "preset_answer_model": "none"
    },
    "status": "ok"
}
```

#### 查看项目统计数据

GET ~/plugins/fileapi/project/:project_id/summary

##### 返回示例

```js
{
    "data": {
        "finished": 5,
        "total_page": 1530,
        "total_question": 11,
        "users": [
            {
                "uid": 13,
                "name": "admin",
                "markcount": 1,
                "login_count": 7
            },
            {
                "uid": 8888,
                "name": "super",
                "markcount": 4,
                "login_count": 0
            }
        ],
        "total_file": 11
    },
    "status": "ok"
}
```

#### 查看可用的答案生成模型
GET ~/plugins/fileapi/preset_answer_models

##### 返回示例
```json
{
    "status": "ok",
    "data": [
        {
            "name": "none",
            "label": "无",
            "model": null
        },
        {
            "name": "rule",
            "label": "规则1",
            "model": null
        }
    ]
}
```

### 目录管理
#### 查询目录内容
GET ~/plugins/fileapi/tree/:tree_id

返回示例
```js
{
    "data": {
        "name": "ipo",
        "id": 2,
        "pid": 2,
        "files": [
            {
                "name": "982.pdf",
                "id": 1,
                "pid": 2,
                "tags": [1, 2, 3],
                "tree_id": 2,
                "mark_users":["jack", "tom", "admin"],
                "mark_uids": [8292, 9982, 8888],
                "last_mark_utc":1529029885,
                "hash": "7ecef04a768ca2fdb24c004bf6c63e13",
                "pdf": "7ecef04a768ca2fdb24c004bf6c63e13",
                "pdf_flag": null,
                "pdf_parse_status": 1,  // 1 排队中 2 解析中 3 取消 4 完成 5 失败
                "qid": 8889,
                "mold": 1,
                "question_status": 1,   // 1 待做, 2 答题完毕, 3 已反馈, 4 答案不一致, 5 答案一致， 6 反馈已确认
                "question_health": 1,   // 剩余要标注次数
                "working_by": 1,     // 正在标注的用户
                "my_answer": 8888
            },
            ...
        ],
        "ptree_id": 0,
        "trees": [
            {
                "name": "2017",
                "id": 3,
                "ptree_id": 2,
                "pid": 2,
                "default_mold": 1,
            }
        ],
        "crumbs": [
            {
                "name": "ipo",
                "id": 2
            },
            {
                "name": "2017",
                "id": 3
            }
        ],
    },
    "status": "ok"
}
```
#### 删除目录
DELETE ~/plugins/fileapi/tree/:tree_id

返回示例：
```json
{
    "data": {},
    "status": "ok"
}
```
#### 修改目录
PUT ~/plugins/fileapi/tree/:tree_id
```json
{
    "name": "2017",
    "default_mold": 1,
}
```

返回示例
```json
{
    "data": {
        "name": "2017",
        "id": 3,
        "ptree_id": 2,
        "pid": 2,
        "default_mold": 1,
    },
    "status": "ok"
}
```

#### 上传文件到目录
POST ~/plugins/fileapi/tree/:tree_id/file
```
multipart/form-data
file: 982.pdf
```

返回示例
```json
{
    "data": {
        "name": "982.pdf",
        "id": 1,
        "pid": 2,
        "tags": [],
        "tree_id": 2,
        "hash": "7ecef04a768ca2fdb24c004bf6c63e13",
        "pdf": "7ecef04a768ca2fdb24c004bf6c63e13",
        "pdf_flag": null,
        "pdf_parse_status": 1,  // 1 排队中 2 解析中 3 取消 4 完成 5 失败
        "qid": 8889,    //注：可能为 null
        "mold": 1,
    },
    "status": "ok"
}
```

#### 创建子目录
POST ~/plugins/fileapi/tree/:tree_id/tree
```json
{
    "name": "2017",
    "mold": 1,
}
```

返回示例:
```json
{
    "data": {
        "name": "2017",
        "id": 3,
        "ptree_id": 2,
        "pid": 2
    },
    "status": "ok"
}
```

#### 查询目录下是否有重名对象（文件或目录）
GET ~/plugins/fileapi/tree/:tree_id/name/:name

返回示例
```json
{
    "data": {
        "exists": false
    },
    "status": "ok"
}
```

#### 打包上传
WS ~/plugins/fileapi/tree/:tree_id/zip
```
c => s: zip 二进制数据
s => c: {"stage": "RECEIVE"}
s => c: {"stage": "UNPACK"}
s => c: {"progress": 1, "stage": "IMPORT", "total": 6, "filename": "1.pdf"}
...
s => c: {"progress": 6, "stage": "IMPORT", "total": 6, "filename": "6.pdf"}
```

### 文件管理
#### 下载文件
GET ~/plugins/fileapi/file/:file_id

#### 修改文件（名称、标签）
PUT ~/plugins/fileapi/file/:file_id
```json
{
    "name": "2017",
    "tags": [1, 2, 3],
    "mold": 1
}
```

返回示例：
```json
{
    "data": {
        "name": "982.pdf",
        "id": 1,
        "pid": 2,
        "tags": [1, 2, 3],
        "tree_id": 2,
        "hash": "7ecef04a768ca2fdb24c004bf6c63e13",
        "pdf": 0,
        "mold": 1,
    },
    "status": "ok"
}
```
#### 删除文件
DELETE ~/plugins/fileapi/file/:file_id

返回示例：
```json
{
    "data": {},
    "status": "ok"
}
```

#### 下载pdf文档
GET ~/plugins/fileapi/file/:file_id/pdf


#### 文件列表
GET ~/plugins/fileapi/project/:project_id/file?page=1&size=2&answered=1&mold_id=1

##### 参数

- **page**: 页码
- **size**: 每页记录数. 当size=0的时候, 返回不分页结果.
- **answered**:  1_已标注的文件; 缺省_全部文件
- **mold_id**: 使用mold id过滤

```js
{
    "status": "ok",
    "data": {
        "files": [
            {
                "name": "中国铝业股份有限公司_2014年审计报告.pdf",
                "tags": [1],
                "mark_users":["jack", "tom", "admin"],
                "mark_uids": [8292, 9982, 8888],
                "last_mark_utc":1529029885,
                "mold": 1,
                "pid": 19,
                "pdf": "529a834d7abcda1a362844a79989b305",
                "qid": 9114,
                "hash": "529a834d7abcda1a362844a79989b305",
                "pdf_flag": null,
                "pdf_parse_status": 1,  // 1 排队中 2 解析中 3 取消 4 完成 5 失败
                "id": 278,
                "size": 972897,
                "tree_id": 47,
                "page": 163,
                "question_status": 1,   // 1 待做, 2 答题完毕, 3 已反馈, 4 答案不一致, 5 答案一致， 6 反馈已确认
                "question_health": 1,   // 剩余要标注次数
                "working_by": 1,      // 正在标注的用户
                "my_answer": 8888
            },
            ...
        ],
        "count": 215
    }
}
```

#### 文件操作历史查询

GET ~/plugins/fileapi/file/:fileId/history

##### 返回示例

```js
{
    "status": "ok",
    "data": {
        "page": 1,
        "total": 3,
        "items": [
            {
                "action_time": 1527235194,
                "action": 2,
                "uid": 13,
                "name": "admin"
            },
            ...
        ],
        "size": 20
    }
}
```

### 文件标签
#### 创建标签
POST ~/plugins/fileapi/tag
```json
{
  "name": "年报",
  "columns": ["year", "money"]
}
```

返回示例:
```json
{
    "data": {
        "name": "年报",
        "id": 3,
        "columns": ["year", "money"]
    },
    "status": "ok"
}
```
#### 标签列表
GET ~/plugins/fileapi/tag

返回示例:
```json
{
    "data": [{
        "name": "年报",
        "id": 3,
        "columns": ["year", "money"]
    },
    ... ...
    ],
    "status": "ok"
}
```
#### 修改标签
PUT ~/plugins/fileapi/tag/:tag_id
```json
{
  "name": "年报",
  "columns": ["year", "money"]
}
```

返回示例:
```json
{
    "data": {
        "name": "年报",
        "id": 3,
        "columns": ["year", "money"]
    },
    "status": "ok"
}
```
#### 删除标签
DELETE ~/plugins/fileapi/tag/:tag_id

返回示例：
```json
{
    "data": {},
    "status": "ok"
}
```

### 用户管理

目前系统中有四种权限:

- **remark** 标注
- **manage_prj** 管理项目
- **browse** 浏览
- **manage_user** 管理用户
- **manage_mold** 管理mold(前端叫schema)

#### 新建

POST ~/user

##### 请求示例

```js
{
  "name": "tom",
  "password": "112233",
  "permission": [
      {
          "perm": "remark"         // 适用于所有项目的权限
      },
      {
          "perm": "manage_prj",     // 只在特定的项目上有对应权限
          "prj_filter": []          // 具有该权限的项目的(ID)列表
      }
    ]
}
```

##### 返回示例

```json
{
    "data": {
        "name": "tom",
        "id": 3,
    },
    "status": "ok"
}
```

#### 列表

GET ~/user

##### 返回示例

```json
{
    "data": {
        "size":20,
        "page":1,
        "total":1,
        "items": [{
            "name": "tom",
            "id": 3,
            "permission": [],
            "login_utc": 1482983292,
            "login_count": 20
        },
        ...]
    },
    "status": "ok"
}
```

#### 按ID查询

GET ~/user/(\d+)

##### 返回示例

```json
{
    "data": {
        "name": "tom",
        "id": 3,
        "permission": [],
        "login_utc": 1482983292,
        "login_count": 20
    },
    "status": "ok"
}
```

#### 修改

PUT ~/user/(\d+)

##### 请求示例

```json
{
    "name": "tom",
    "password": "112233",
    "permission": [
        "remark",         // 适用于所有项目的权限
        {
            "perm": "manage_prj",     // 只在特定的项目上有对应权限
            "prj_filter": []          // 具有该权限的项目的(ID)列表
        }
    ]
}
```

#### 删除

DELETE ~/user/(\d+)

#### 登录系统

POST ~/login

##### 请求示例

```json
{
  "name": "tom",
  "password": "112233"
}
```

#### 当前用户操作历史查询

GET ~/user/history

##### 返回示例

```js
{
    "data":{
        "items":[
            {
                "uid":8888,
                "action":1,  // action定义见"历史查询相关API的ACTION定义"
                "user_name": "admin",
                "action_time":1529030760
            },
            ...
        ],
        "total":3268,
        "page":1,
        "size":20
    },
    "status":"ok"
}
```

#### 所有用户操作历史查询(需要用户管理权限)

GET ~/user/all/history

##### 返回示例

```js
{
    "data":{
        "items":[
            {
                "uid":8888,
                "action":1,  // action定义见"历史查询相关API的ACTION定义"
                "user_name": "admin",
                "action_time":1529030760
            },
            ...
        ],
        "total":3268,
        "page":1,
        "size":20
    },
    "status":"ok"
}
```

#### 特定用户操作历史查询(需要用户管理权限)

GET ~/user/:uid/history

##### 返回示例

```js
{
    "data":{
        "items":[
            {
                "uid":8888,
                "action":1,  // action定义见"历史查询相关API的ACTION定义"
                "user_name": "admin",
                "action_time":1529030760
            },
            ...
        ],
        "total":3268,
        "page":1,
        "size":20
    },
    "status":"ok"
}
```

### 根据file_id获取box在pdf文件中某页上框选出来的文字

POST ~/file/:file_id/text_in_box

请求的`url参数`
- parse_pdf: 可选参数, 有效的值是false或true, 不传默认为false;
- with_box: 可选参数, 有效的值是false或true, 不传默认为false;
请求body示例(json格式):

```javascript
// 可以传入多个box, 接口返回保持和输入box一样的顺序
[
    {
        "box": [0, 0, 200, 200],  // 四个值表示box的四条边线和pdf页的左边线或上边线的距离, 按照左-上-右-下的顺序
        "page": 0                 // box所在页的编号
    },
    ...
]
```

### 导出标注数据

#### 新建任务

```
POST ~/training_data
```

##### 请求参数:
* schema_id (int）

##### 返回示例

```javascript
{
    "status": "ok",
    "data": {
        "from_id": 4,
        "task_done": 0,
        "mold": 3,
        "id": 1,
        "created_utc": 1544691606,
        "to_id": 2666,
        "task_total": 2
    }
}
```

#### 任务列表

```
GET ~/training_data
```

##### 请求参数:
* schema_id（int）

##### 返回示例

```javascript
{
    "status": "ok",
    "data": {
        "total": 1,
        "page": 1,
        "size": 20,
        "items": [
            {
                "from_id": 4,
                "task_done": 2,
                "mold": 3,
                "id": 1,
                "zip_path": "/Users/mxt/Desktop/Scriber-Backend/data/export_answer_data/task_1.zip",
                "created_utc": 1544691606,
                "to_id": 2666,
                "task_total": 2
            }
        ]
    }
}
```

#### 删除任务

```
DELETE ~/training_data/(\d+)
```

#### 导出标注数据

```
GET ~/training_data/(\d+)
```

### 统计模型准确率

#### 查看模型准确率

```
GET ~/accuracy_record
```

##### 请求参数:
* schema_id（int）

##### 返回示例

```javascript
{
    "data": [
        {
            "data": {
                "to_id": -1,
                "mold": 4,
                "result": [
                    {
                        "rate": 1,
                        "name": "公司名称",
                        "tagged": 0,
                        "match": 1,
                        "total": 1
                    }
                ],
                "total": 1,
                "top_n_result": [],
                "from_id": 0,
                "total_fit": 1,
                "total_percent": 1
            },
            "mold": 4,
            "last_training_utc": 1545043242,
            "id": 59,
            "created_utc": 1545043245,
            "b_training": 0
        }
    ],
    "status": "ok"
}
```

#### 训练模型

```
POST ~/accuracy_record
```

##### 请求参数:
* schema_id (int）


## 标注工具

### 表格答案联想

```
POST ~/file/<file_id>/association
```

##### 请求参数:
```json
{
    "年度": {
        "box":{
            "page": 236,
            "box": [178.66120481927712, 567.9339759036145, 236.04144578313256, 581.6269879518073]
        },
        "text": "2018",
        "common": true  // 为true表示该字段是共用的,不进行联想
    },
    "项目": {
        "box": {
            "page": 236,
            "box": [69.11710843373494, 608.3609638554218, 134.97397590361447, 624.0101204819277]
        },
        "text": "主营业务成本"
    },
    "成本金额": {
        "box": {
            "page": 236,
            "box": [155.83951807228917, 611.6212048192772, 203.43903614457832, 622.0539759036145]
        },
        "text": "4,616,70"
    },
    "占营业成本比": {
        "box": {
            "page": 236,
            "box": [224.30457831325305, 610.9691566265061, 266.6877108433735, 622.7060240963856]
        },
        "text": "99.95%"
    }
}
```

##### 返回示例

```json
{
    "status": "ok",
    "data": [
        {
            "年度": {
                "box": {
                    "box": [
                        142.7432,
                        565.2517,
                        270.3846,
                        586.2287
                    ],
                    "page": 236
                },
                "text": "2018 年度"
            },
            "项目": {
                "box": {
                    "box": [
                        65.8686,
                        606.7262499999999,
                        142.7432,
                        627.37365
                    ],
                    "page": 236
                },
                "text": "主营业务成本"
            },
            "成本金额": {
                "box": {
                    "box": [
                        142.7432,
                        606.7262499999999,
                        206.6988,
                        627.37365
                    ],
                    "page": 236
                },
                "text": "4,616.70"
            },
            "占营业成本比": {
                "box": {
                    "box": [
                        206.6988,
                        606.7262499999999,
                        270.3846,
                        627.37365
                    ],
                    "page": 236
                },
                "text": "99.95%"
            },
            "测试": null
        },
        {
            "年度": {
                "box": {
                    "box": [
                        142.7432,
                        565.2517,
                        270.3846,
                        586.2287
                    ],
                    "page": 236
                },
                "text": "2018 年度"
            },
            "项目": {
                "box": {
                    "box": [
                        65.8686,
                        627.37365,
                        142.7432,
                        647.9911500000001
                    ],
                    "page": 236
                },
                "text": "其他业务成本"
            },
            "成本金额": {
                "box": {
                    "box": [
                        142.7432,
                        627.37365,
                        206.6988,
                        647.9911500000001
                    ],
                    "page": 236
                },
                "text": "2.12"
            },
            "占营业成本比": {
                "box": {
                    "box": [
                        206.6988,
                        627.37365,
                        270.3846,
                        647.9911500000001
                    ],
                    "page": 236
                },
                "text": "0.05%"
            },
            "测试": null
        }
    ]
}
```


### 答案辅助处理
```markdown
将标注答案按现有格式整体放到"answer"字段
在"key"字段中指定要处理的一级字段
```
```
POST ~/file/<file_id>/answer_assist
```

##### 请求参数
```json
        {
            "answer": {
                "schema":...
                "userAnswer":{
                    "items": [...],
                    "version":"2.2"
                }
            }
            "key":"董监高核心人员基本情况"

        }
```

##### 返回示例
```json
{
    "status": "ok",
    "data": {
        "schema":...
        "userAnswer":{
            "items": [...],
            "version":"2.2"
            }
    }
}
```
