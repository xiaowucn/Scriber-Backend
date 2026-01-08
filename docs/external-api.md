# 外部系统 api
## 接口授权验证
外部系统调用接口需经过 token 授权验证，目前支持 `简化版` 和 `普通版` 两种方式
以下接口默认使用 `简化版`，如有安全需要可注明使用 `普通版`

1. 简化版：
- 在 config.yml 中配置 `app.simple_token` 配置校验使用的字符串
- 请求时需在请求头部加入 `access-token: xxxxx`，即可
- 注：建议使用 https 以保证安全

2. 普通版：
- 在 config.yml 中配置 `app.secret`
- 将 secret 告知调用方，并按照 `remarkable.security.authtoken.encode_url` 的方法生成 token 和 时间戳 到 url 中，即可调用



## 上传文档

POST /external_api/v1/upload
```
multipart/form-data
file: 文档
interdoc: pdfinsight 解析结果，非必填，有条件的系统可从 pdfinsight 解析后开始对接，避免重复解析
text: 文本，会根据文本创建 word 文档（注：file/text 二者选一）
filename: 文件名，如以 text 方式上传则必填
tree_id: 上传目录 id
schema_id: 分析使用的 schema id，缺省使用目录对应的默认 schema
meta: json, 文件额外信息
```

返回示例
```json
{
    "data": {
        "id": 1,                // 文件 id
        "filename": "976.pdf",  // 文件名
    },
    "status": "ok"
}
```


## 获取文档分析结果
GET /external_api/v1/file/:file_id/result/:format

format 支持 json/csv

json 返回示例
```json
{
    "data": {
        "id": 1,                // 文件 id
        "filename": "976.pdf",  // 文件名
        "answer": {
            "schema": {},
            "userAnswer": {},
        }
    },
    "status": "ok"
}
```

其他格式返回导出文件

## 深交所定制（scriber与自然语言处理平台融合）

### schema统计

GET /external_api/v1/schema

返回示例:

```
data = {
    'status': "ok",
    'data': {
        'projects': 2,  # 项目数量(schema数量)
        'tasks': 12,  # 文档数
        'task_done': 0,  # 已标注
        'models': 2,  # 模型数量
        'data': [
            {
                'mold_id': 86,
                'mold_name': "0809 业绩预告更正",  # 项目名称(schema名称)
                'tasks': 6,  # 文档数
                'task_done': 0,  # 已标注
                'models': 1,  # 模型数量
                'precision': {
                    'detection': 0.87,  # 定位
                    'extract': null  # 提取
                },  # 最佳评估效果
                'fields': "公司全称、公司简称、公司代码、公告日期、公告编号、业绩预告区..."  # 分类标签（对应schema的字段）
            },
            {
                'mold_id': 87,
                'mold_name': "0530 关联交易的完成",
                'tasks': 6,
                'task_done': 0,
                'models': 1,
                'precision': {
                    'detection': null,  # 定位
                    'extract': null  # 提取
                },  # 最佳评估效果
                'fields': "公司全称、公司简称、公司代码、公告日期、公告编号、业绩预告区..."  # 分类标签（对应schema的字段）
            }
        ]
    }
}

```



### 标注任务页面

GET /api/v1/szse_file

参数:
* page: int, 页码, 默认1
* size: int, 每页数量, 默认20
* mold: int, 筛选条件：schema_id, 默认0
* filename: str, 筛选条件：文件名称, 默认为空

返回示例:

```
{
    'status': "ok",
    'data': {
        'page': 1,
        'size': 20,
        'total': 1,
        'items': [
            {
                'id': 1347,  # 文件id
                'file_name': "粤泰股份 .pdf",  # 文件名称
                'mold_name': "0809 业绩预告更正",  # 所属任务
                'created_utc': "2020.02.27 14:55:21",  # 上传时间
                'mark_users': [
                    "张三"
                ],  # 标注人员
                'updated_utc': "2020.07.15 12:36:49",  # 标注更新时间
                'status': "正在答题",  # 标注状态
                'progress': "-"  # 标注进度
                'qid': 19468,
                'mold_id': 73,
                'tree_id': 219
            },
        ]
    }
}
```



### 模型信息页面

GET /api/v1/szse_model

参数:
* page: int, 页码, 默认1
* size: int, 每页数量, 默认20
* moldname: str, 筛选条件：schema名称, 默认为空

返回示例：

```
{
    "status": "ok",
    "data": {
        "page": 1,
        "size": 20,
        "total": 2,
        "items": [
            {
                "id": 12,  # 模型版本id
                "mold_id": 125,
                "name": '科创板招股书',  # 项目名称(schema名称)
                "enable": 1,  # 启用状态
                "created_utc": "2020.06.01 16:33:10",  # 训练时间
                "files": 5,  # 训练文件基数
                "precision": 0.2903225806451613  # 最新准确率
                "model_type": "精确提取",  # 模型类型
                "model_status": "训练完毕",  # 训练状态
            },
        ]
    }
}

```



### 项目组schema统计

GET /external_api/v1/group_schema/:group_id

参数:

* group_id: int, 项目组id

返回示例：

```
{
    'status': "ok",
    'data': [
        {
            "mold_id': 86,
            "mold_name': "0809 业绩预告更正",  # schema名称
            "comment': null,  # schema 备注
            "tasks': 6,  # 文档总数
            "task_done": 6,  # 已标注文档
            "created_utc": "2020.02.27 14:40:18",  # schema创建时间
            "precision": {
                "detection": null,  # 定位
                "extract": null  # 提取
            },  # 最佳评估效果
            "creator": "mxt",  # 创建者
        }
    ]
}

```

## 交银施罗德接口
### 会议信息结果获取

GET /external_api/v1/meeting/:date

参数:

- date: 8位日期，如 20210401

返回示例：
```json
{
    "会议信息": [
        {
            "会议题目": "会议标题1",
            "会议时间": "4月1日（周一）晚上 20:30",
            "会议号": null,
            "会议电话": "4008 111 111\n+852-1111 111",
            "会议密码": null
        },
        {
            "会议题目": "会议题目2",
            "会议时间": "4月1日（周一）晚上 20:30",
            "会议号": null,
            "会议电话": null,
            "会议密码": null
        }
    ]
}
```
