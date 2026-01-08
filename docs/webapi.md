<!-- TOC -->

- [1. 说明](#1-说明)
    - [1.1. api共同前缀](#11-api共同前缀)
    - [1.2. 状态说明](#12-状态说明)
        - [1.2.1. 题目状态](#121-题目状态)
        - [1.2.2. 答案状态](#122-答案状态)
        - [1.2.3. 状态转换图](#123-状态转换图)
- [2. 通用接口](#2-通用接口)
    - [2.1. Question 相关](#21-question-相关)
        - [2.1.1. 查询题目列表](#211-查询题目列表)
        - [2.1.2. 查询当前用户已做题目](#212-查询当前用户已做题目)
        - [2.1.3. 查询题目列表](#213-查询题目列表)
        - [2.1.4. 获取题目](#214-获取题目)
        - [2.1.5. 查询指定题目](#215-查询指定题目)
        - [2.1.6. 提交题目答案](#216-提交题目答案)
        - [2.1.7. 设置题目为反馈](#217-设置题目为反馈)
    - [2.2. Answer 相关](#22-answer-相关)
        - [2.2.1. 导出所有答案](#221-导出所有答案)
        - [2.2.2. 根据题目ID获取当前用户给出的答案](#222-根据题目id获取当前用户给出的答案)
        - [2.2.3. 管理员标记正确答案](#223-管理员标记正确答案)
        - [2.2.4. 题目重做](#224-题目重做)
    - [2.3. Tag 相关](#23-tag-相关)
        - [2.3.1. 查询所有tag](#231-查询所有tag)
        - [2.3.2. 为题目设置tag](#232-为题目设置tag)
    - [2.4. DBG按ID获取题目数据](#24-dbg按id获取题目数据)
    - [2.5. 答题统计](#25-答题统计)
        - [2.5.1. 答题统计](#251-答题统计)
- [3. 业务定制接口](#3-业务定制接口)
    - [3.1. Causality 因果标注](#31-causality-因果标注)
        - [3.1.1. 根据连词拆分短句](#311-根据连词拆分短句)
    - [3.2. pdftable pdf表格标注](#32-pdftable-pdf表格标注)
        - [3.2.1. 返回特定题目的PDF文件数据](#321-返回特定题目的pdf文件数据)
        - [3.2.2. 返回特定题目对应的PDF单页的URL](#322-返回特定题目对应的pdf单页的url)
        - [3.2.3. 根据外框返回特定题目的推荐内线](#323-根据外框返回特定题目的推荐内线)
        - [3.2.4. 预测外框](#324-预测外框)
        - [3.2.5. 按题目返回答题用户答案差异详情](#325-按题目返回答题用户答案差异详情)
        - [3.2.6. 返回两个用户的答案差异详情](#326-返回两个用户的答案差异详情)
        - [3.2.7. 题目重做](#327-题目重做)
    - [3.3. PDFContext pdf表格上下文标注](#33-pdfcontext-pdf表格上下文标注)
        - [3.3.1. 根据题目ID获取PDF文件下载链接](#331-根据题目id获取pdf文件下载链接)
        - [3.3.2. 根据题目ID获取box在pdf文件中某页上框选出来的文字](#332-根据题目id获取box在pdf文件中某页上框选出来的文字)
    - [3.4. PDFToc pdf目录结构标注](#34-pdftoc-pdf目录结构标注)
        - [3.4.1. 根据题目ID获取PDF文件下载链接](#341-根据题目id获取pdf文件下载链接)
        - [3.4.2. 根据题目ID获取box在pdf文件中某页上框选出来的文字](#342-根据题目id获取box在pdf文件中某页上框选出来的文字)
    - [3.5. PDFEle pdf元素块标注](#35-pdfele-pdf元素块标注)
        - [3.5.1. 根据题目ID获取PDF文件下载链接](#351-根据题目id获取pdf文件下载链接)
    - [3.6. 底稿标注](#36-底稿标注)
    - [3.7. 导出训练数据](#37-导出训练数据)
        - [3.7.1. 新建任务](#371-新建任务)
        - [3.7.2. 任务列表](#372-任务列表)
        - [3.7.3. 删除任务](#373-删除任务)
        - [3.7.4. 导出标注数据](#374-导出标注数据)
- [4. mold 相关](#4-mold-相关)
    - [4.1. 获取所有 mold(目前没有分页)](#41-获取所有-mold目前没有分页)
    - [4.2. 添加 mold](#42-添加-mold)
    - [4.3. 获取指定 id 的 mold](#43-获取指定-id-的-mold)
    - [4.4. 更新指定 id 的 mold](#44-更新指定-id-的-mold)
    - [4.5. 删除指定 id 的 mold](#45-删除指定-id-的-mold)
    - [4.6. 查询指定 id 的 mold 字段注释信息](#46-查询指定-id-的-mold注释)
    - [4.7. 获取所有模型模板](#47-获取所有模型模板)

<!-- /TOC -->

# 1. 说明
## 1.1. api共同前缀
所有api需要添加共同的前缀:
* 对于因果关系标注，这个前缀是`/lrcapi/v1`;
* 对于pdf表格标注，这个前缀是`/lrfapi/v1`。
* 对于pdf上下文标注，这个前缀是`/lrtapi/v1`。
* 对于高管简历标注，这个前缀是`/lrrapi/v1`。
* 对于pdf元素块标注, 这个前缀是`/pdfele/v1`。
* 对于pdf目录标注, 这个前缀是`/pdftoc/v1`。

其中v1为接口版本，根据实际调整，在后面的说明中以`~/`代替

## 1.2. 状态说明

### 1.2.1. 题目状态
* TODO = 1            # 待作
* FINISH = 2          # 答题完毕
* VERIFY = 3          # 已反馈
* DISACCORD = 4       # 答案不一致
* ACCORDANCE = 5      # 答案一致
* VERIFY_CONFIRMED = 6  # 管理员确认了反馈

### 1.2.2. 答案状态
* WAITING = 0              # 等待凑组答题人数后的答案比较
* CORRECT = 1              # 正确
* INCORRECT = 2            # 错误
* TOBE_JUDGED = 3          # 自动比较无法判断, 等待管理员判断

### 1.2.3. 状态转换图

``` mermaid
graph TD;
A[题目:TODO <br/>答案:WAITING] -- 提交答案 --> B{满足答题人数?};
B -- 是 --> C[题目:DONE <br/>答案:WAITING];
B -- 否 --> A;
C -- 答案比较,答案不一致 --> E[题目:DISACCORD <br/>答案:TOBE_JUDGED];
C -- 答案比较,答案一致 --> F[题目:ACCORDANCE <br/>答案:CORRECT];
E -- 管理员处理冲突 --> G[题目:ACCORDANCE <br/>答案:CORRECT/INCORRECT];
A -- 题目反馈 --> H[题目:VERIFY <br/>答案:WAITING];
H -- 管理员处理反馈 --> I[题目:VERIFY_CONFIRMED <br/>答案:WAITING];
```

状态说明:
* 题目处于`TODO`状态的时候, 用户可以修改答案; 其他状态下用户不可以修改答案.
* 题目何时离开`TODO`状态, 取决于是否凑组了答题人数, 对单个用户来说是不可控的. **并不是说**用户自己答题完毕题目就进入`DONE`状态了.
* 题目在`DISACCORD`状态的时候, 需要管理员裁决:
    1. 管理员认为某个用户答案是正确的, 则将该用户的答案标记为标准答案(~/question/:qid/markcorrect/:uid).标记后后端会自动重新比较答案, 跟标准答案一致的定为正确答案；跟标准答案不一致的定为错误答案.
    2. 管理员认为当前几个用户的答案都是错误的, 则管理员自己答题, 提交后作为标准答案. 提交后后端会自动重新比较答案, 跟标准答案一致的定为正确答案；跟标准答案不一致的定为错误答案.
* 题目在`VERIFY`状态的时候, 需要管理员确认:
    1. 管理员认为用户的反馈是正确的, 则确认反馈(~/question/(\d+)/confirm_verify)
    2. 管理员认为题目可以正常答题, 则管理员"去做题"

# 2. 通用接口
## 2.1. Question 相关
### 2.1.1. 查询题目列表
GET: ~/question
* page: int, 页码, 默认1
* size: int, 每页数量, 默认20
* status: int, 题目状态，默认1
    * 1: 待做
    * 2: 已做
    * 3: 反馈（跳过）
    * 4: 冲突

返回示例:
```javascript
{
    "data":{
        "size":20,
        "total":2,
        "page":1,
        "items":[
            {
                "id":9499,
                "updated_utc":1513132796,
                "status":4,     // 题目状态
                "data":{},
                "tags":[],
                "answer":null
            },
        ]
    },
    "status":"ok"
}
```
### 2.1.2. 查询当前用户已做题目

GET ~/question/mine

参数:
* result   1 返回当前用户答对的题目 2 返回当前用户答错的题目. 不填返回所有题目
* page: int, 页码, 默认1
* size: int, 每页数量, 默认20

返回示例

```javascript
{
    "status":"ok",
    "data":{
        "page":1,
        "total":1,
        "items":[
            {
                "updated_utc":1519637622,  // 答题时间
                "answer":[],        // 当前用户给出的答案数据
                "status":1,         // 题目状态
                "data": {},         // 题目数据
                "tags":[            // 题目当前的标签

                ],
                "id":81621          // 题目ID
            }
        ],
        "size":20
    }
}
```

### 2.1.3. 查询题目列表
随机获得一道待做的题目
GET: ~/question/random

### 2.1.4. 获取题目

随机获取一道题目，会记住用户正在做的题目并防止多用户答同一道题目

GET: ~/mark

返回示例:

```javascript
{
    "status": "ok",
    "data": {
        "items": [
            {
                "question": {
                    "id": 8901,             // 题目ID
                    "preset_answer": null,  // 推荐答案
                    "tags": [],             // 题目标签
                    "data": {},             // 题目数据
                    "status": 1             // 题目状态: 1 待作
                },
                "answer": {
                    "data": null            // 当前用户曾经给出的答案
                }
            }
        ],
        "total": 72                         // 题库题目总数
    }
}
```

### 2.1.5. 查询指定题目
使用 id 或 checksum 查询一道题目
GET: ~/question/(id|checksum)/:id

返回示例:

```javascript
{
    "data": {
        "data": {},             // 题目数据
        "tags": [],             // 标签
        "id": 9494,
        "preset_answer": null,  // 推荐答案
        "status": 5,            // 题目状态 1_todo, 2_finish, 3_verify, 4_disaccord, 5_accordance
        "answers": [{           // 该问题的所有答案
            "uid": 8888,        // 用户的 id
            "name": "ldmiao",   // 用户的名字, 为 null 说明没有取到用户的名字
            "result": 1,        // 该答案是正确答案还是错误答案: 0 等待凑足答题人数；1 正确；2 错误；3 等待管理员判断
            "standard": 1,      // 该答案是否被用作标准答案: 0 否 1 是
            "data": null        // 答案, 类型不定
            "updated_utc": 1539823983 // 答案修改时间戳
        }]
    },
    "status": "ok"
}
```

### 2.1.6. 提交题目答案
POST: ~/question/:id/answer

#### URL参数

* save_data_only    是否保存临时答案. 1 答题中保存临时答案; 0(默认) 提交答题完毕提交题目答案.

#### 请求body示例:

```javascript
{
    "data": {}    // json 必填, 答案json数据
}
```

### 2.1.7. 设置题目为反馈
POST: ~/question/:id/verify

### 2.1.8. 锁定题目
PUT: ~/question/:id/lock

返回示例：
* 成功(200)
  ```
    {
        "status": "ok",
        "data": null
    }
  ```

* 失败(400)
  ```
    {
        "status": "error",
        "message": "Question is locked by other user"
    }
  ```

## 2.2. Answer 相关
### 2.2.1. 导出所有答案
GET: ~/answer/dump
ps: 数量少时可以直接用这个接口下载，数量较多时需在服务器上以脚本方式导出答案

### 2.2.2. 根据题目ID获取当前用户给出的答案
GET: ~/question/:qid/answer

返回示例:

```js
{
    "status":"ok",
    "data":{
        "question_data": {},         // 题目数据
        "qid":108618,                // 题目ID
        "uid":8888,                  // 当前用户的ID
        "data":{},                   // 当前用户给出的答案数据
        "id":23201,                  // 当前用户给出的答案的ID
        "preset_answer":null,        // 系统推荐答案
        "created_utc":1521700290,    // 答案创建时间
        "updated_utc":1521700290     // 答案最后修改时间
    }
}
```

### 2.2.3. 管理员标记正确答案

管理员将指定问题qid的正确答案标记为用户uid提供的答案

POST: ~/question/:qid/markcorrect/:uid

### 2.2.4. 题目重做

POST ~/batch_redo?by_checksum=1

请求参数:
* by_checksum 可选 1 表示传入参数为checksum，不填或0表示传入参数为id

#### 请求body示例

```js
{
    // 单个ID的格式: <sid|id>, 其中id是字符串形式的数字, sid格式没有严格限制, 随业务不同
    "id_list": ["6442", "7220"]
}
```

## 2.3. Tag 相关
### 2.3.1. 查询所有tag
GET: ~/tag

### 2.3.2. 为题目设置tag
POST: ~/question/:id/tag
* tags: int[] 必填，题目id的

注：覆盖题目的原有tag，请提交完整的tags数组

## 2.4. DBG按ID获取题目数据
GET ~/dbg/question/:id

返回示例:
```javascript
{
    "data":{
        "answer":[ 						// 答案数据，一个问题可能对应多个人标注的答案
            {
                "standard":0,
                "uid":9002,
                "result":1,
                "id":10282,
                "data":[],
                "status":1
            },
        ],
        "question":[					// 问题数据
            {
                "health":0,
                "preset_answer":null,
                "tags":[],
                "id":9497,
                "data":{},
                "status":5
            }
        ]
    },
    "status":"ok"
}
```

## 2.5. 答题统计

### 2.5.1. 答题统计

GET ~/answer/stat

返回示例:

```javascript

{
　　"data":[
　　　　{
　　　　　　"count":4,          // 已做题目总数
　　　　　　"admin_verify":0,   // 作为管理员审核的反馈题目的数量
　　　　　　"correct":2,        // 作对的题目数量
　　　　　　"waiting":2,        // 当前作答完毕, 等待其他用户作答的题目的数量
　　　　　　"wrong":0,          // 做错的题目的数量
　　　　　　"name":"admin",     // 用户名称
　　　　　　"uid":8888,         // 用户ID
　　　　　　"nonconclusion":0,  // 自动比较后无法判定对错, 等待管理员进一步判定的题目的个数
　　　　　　"admin_judge":1     // 作为管理员处理的冲突题目的数量
　　　　}
　　],
　　"status":"ok"
}
```

# 3. 业务定制接口

各个具体标注的特殊需求, 使用插件的方式实现. URL都以`~/plugins`为前缀.

## 3.1. Causality 因果标注
### 3.1.1. 根据连词拆分短句
POST: ~/plugins/causality/splitedsentence
* sentence: string 必填，题目原句
* links: string[] 必填，连词数组

## 3.2. pdftable pdf表格标注
### 3.2.1. 返回特定题目的PDF文件数据
NOTE: 因PDF存放机制发生变化，该接口已废弃
GET: ~/plugins/pdftable/question/:qid/pdf

### 3.2.2. 返回特定题目对应的PDF单页的URL
GET ~/plugins/pdftable/question/:qid/pdfurl

#### 输出示例

```javascript
{
    "url": "..."
}
```


### 3.2.3. 根据外框返回特定题目的推荐内线

POST ~/plugins/pdftable/question/:qid/candidate

请求参数:
* by_model 可选 1 表示从模型生成推荐内线，不填或0表示从算法生成推荐内线

#### 请求body示例
```js
{
    "outlines":[
        {"tableId":1,"outline":[50,50,500,500]},        // 题目中第一个表格的外框
        {"tableId":2,"outline":[80,90,500,500]},        // 题目中第二个表格的外框
        ...
    ]
}
```

#### 返回body示例

```js
{
    "status": "ok",
    "data": {
        "28": {           #为pdf传入的页码,其余类似表格标注的推荐答案answer内容
            "tables": [
                {
                    "topleft": [ 50, 50 ],
                    "outline": [ 50, 50, 500, 500 ],
                    "height": 450,
                    "width": 450,
                    "tableId": 1,
                    "grid": {
                        "rows": [97, 118, 157, 215, 255, 333, 410 ],
                        "columns": [355]
                    },
                    "merged": []
                },
                {
                    "topleft": [ 90, 80 ],
                    "outline": [ 80, 90, 500, 500 ],
                    "height": 410,
                    "width": 420,
                    "tableId": 2,
                    "grid": {
                        "rows": [ 204 ],
                        "columns": [ 209 ]
                    },
                    "merged": []
                }
            ],
            "size": [
                595,
                841
            ]
        }
    }
}
```

### 3.2.4. 预测外框

POST ~/plugins/pdftable/question/:qid/outline


#### 请求body示例
不需要请求body

#### 返回body示例

```js
{
	"status":"ok",
	"data":{
		"tables":{
			"4793_00116":[
				{
					"topleft":[ 246, 62 ],
					"height":381,
					"grid":{
						"rows":[ ],
						"columns":[ ]
					},
					"outline":[ 62, 246, 534, 627 ],
					"width":472
				},
				{
					"topleft":[ 77, 58 ],
					"height":80,
					"grid":{
						"rows":[ ],
						"columns":[ ]
					},
					"outline":[ 58, 77, 538, 157 ],
					"width":480
				}
			]
		},
		"size":[ 595, 841]}
}
```


### 3.2.5. 按题目返回答题用户答案差异详情

GET ~/plugins/pdftable/question/:qid/diff_detail

#### 返回body示例

```js
{
    "8882": [                          // ID为8882的用户标注的答案的差异数据
        {                               // ID为8882的用户标注的答案的第一个表格的差异
            "conflict": [               // 冲突内容，包含若干个单元格差异
                {
                    "cell": (1, 2),         // 有差异的单元格的行列号
                    "count": 0              // 冲突次数
                },
                ...                         // 其他有差异的单元格
            ]
            "topleft": ["142.3620", "85.6799"]  // 表格左上角坐标，方便排序
        },
        ...                             // ID为8882的用户标注的答案的其他表格的差异
    ]
    "8888": [                          // ID为8888的用户标注的答案的差异数据
    ]
}
```

### 3.2.6. 返回两个用户的答案差异详情

GET ~/plugins/pdftable/question/:qid/diff_detail_by_user?uid1=8882&uid2=8888

请求参数:
* uid1 第一个用户的uid
* uid2 第二个用户的uid

#### 返回body示例

```js
{
    "8882": [                          // ID为8882的用户标注的答案的差异数据
        {                               // ID为8882的用户标注的答案的第一个表格的差异
            "conflict": [               // 冲突内容，包含若干个单元格差异
                {
                    "cell": (1, 2),         // 有差异的单元格的行列号
                    "count": 0              // 冲突次数
                },
                ...                         // 其他有差异的单元格
            ]
            "topleft": ["142.3620", "85.6799"]  // 表格左上角坐标，方便排序
        },
        ...                             // ID为8882的用户标注的答案的其他表格的差异
    ]
    "8888": [                          // ID为8888的用户标注的答案的差异数据
    ]
}
```

### 3.2.7. 题目重做

POST ~/plugins/pdftable/batch_redo

#### 请求body示例

```js
{
    // 单个ID的格式: <id_in_docinfo>-<page_num>[-<tableid>], 其中最后的tableid部分可以省略
    "id_list": ["6442-233-2", "7220-2-3"]
}
```

## 3.3. PDFContext pdf表格上下文标注

### 3.3.1. 根据题目ID获取PDF文件下载链接

GET ~/plugins/pdfcontext/question/\d+/fileurl

返回示例

```javascript
{
    "status": "ok",
    "data": {
        "page": 32,                                                                 // 当前PDF页在整个PDF文件中的页码
        "url": "http://ampere.cheftin.com:8089/api/v1/farm/pdf/4790/page/267/blob"  // pdf下载链接
    }
}
```

### 3.3.2. 根据题目ID获取box在pdf文件中某页上框选出来的文字

POST ~/plugins/pdfcontext/question/int:qid/text_in_box

请求body示例:

```javascript
// 可以传入多个box, 接口返回保持和输入box一样的顺序
[
    {
        "box": [0, 0, 200, 200],        // 四个值表示box的四条边线和pdf页的左边线或上边线的距离, 按照左-上-右-下的顺序
        "page": 0                       // box所在页的编号
    },
    ...
]
```

返回示例

```javascript
{
    "status":"ok",
    "data":[
        {
            "text":"项目营业外支出利润总额净利润营业毛利率营业净利率净资产收益率",
            "box": {        // 原样返回对应的输入box的数据
                "page": 0,
                "box": [0, 0, 200, 200]
            }
        },
        ...
    ]
}
```

## 3.4. PDFToc pdf目录结构标注

### 3.4.1. 根据题目ID获取PDF文件下载链接

GET ~/plugins/pdftoc/question/\d+/fileurl

#### 返回示例

```javascript
{
    "status": "ok",
    "data": {
        "page": 32,                                                                 // 当前PDF页在整个PDF文件中的页码
        "url": "http://ampere.cheftin.com:8089/api/v1/farm/pdf/4790/page/267/blob"  // pdf下载链接
    }
}
```

### 3.4.2. 根据题目ID获取box在pdf文件中某页上框选出来的文字

POST ~/plugins/pdftoc/question/int:qid/text_in_box

#### 请求body示例

```javascript
// 可以传入多个box, 接口返回保持和输入box一样的顺序
[
    {
        "box": [0, 0, 200, 200],        // 四个值表示box的四条边线和pdf页的左边线或上边线的距离, 按照左-上-右-下的顺序
        "page": 0                       // box所在页的编号
    },
    ...
]
```

#### 返回示例

```javascript
{
    "status":"ok",
    "data":[
        {
            "text":"项目营业外支出利润总额净利润营业毛利率营业净利率净资产收益率",
            "box": {        // 原样返回对应的输入box的数据
                "page": 0,
                "box": [0, 0, 200, 200]
            }
        },
        ...
    ]
}
```

## 3.5. PDFEle pdf元素块标注

### 3.5.1. 根据题目ID获取PDF文件下载链接

GET ~/plugins/pdfelement/question/\d+/fileurl

#### 返回示例

```javascript
{
    "status": "ok",
    "data": {
        "page": 32,                                                                 // 当前PDF页在整个PDF文件中的页码
        "url": "http://ampere.cheftin.com:8089/api/v1/farm/pdf/4790/page/267/blob"  // pdf下载链接
    }
}
```

## 3.6. 底稿标注

见 [底稿标注API](./draft-api.md)

## 3.7. 导出训练数据

### 3.7.1. 新建任务

```
POST ~/training_data
```

请求参数:
* schema_id schema的id（int）

#### 返回示例

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

### 3.7.2. 任务列表

```
GET ~/training_data
```

请求参数:
* schema_id schema的id（int）

#### 返回示例

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

### 3.7.3. 删除任务

```
DELETE ~/training_data/(\d+)
```

### 3.7.4. 导出标注数据

```
GET ~/training_data/(\d+)
```



# 4. mold 相关

## 4.1. 获取所有 mold(目前没有分页)
GET ~/mold

RESP
- 200

```javascript
{
    "status":"ok",
    "data":[
        {
            "id":1,
            "name":"name",
            "mold_type": 0,  //0-复杂长文档信息抽取 1-固定版式文档KV抽取
            "data":{
                "age":"age",
                "name":"name"
            },
            "checksum":"37a6259cc0c1dae299a7866489dff0bd",  // data 的 md5sum
            "created_utc":1513664919,
            "updated_utc":1513667033,
        }
    ]
}
```

## 4.2. 添加 mold
POST ~/mold

PARA(json)
- name: str, required. 不能为空字符串; 有唯一性检查
- mold_type, int, optional. 默认为0，0-复杂长文档信息抽取 1-固定版式文档KV抽取
- data: null/json, required. 如果想传入 json, 必须是有效的 json

RESP
- 200

```javascript
{
    "status":"ok",
    "data":{
        "id":1,
        "updated_utc":1513667718,
        "data":"a string",
        "created_utc":1513667718,
        "checksum":"879ec0e295a91dd2224ac2786c44a23a",
        "name":"formala"
    }
}
```

- 400(传输的数据是非法的 json, 此时返回不是一个 json, 而是以一个异常的形式从后台抛出)

```
raise tornado.web.HTTPError(400, u'Invalid JSON in body of request')
```

- 400(请求不包含任何数据或包含的数据不是字典)

```javascript
{
    "message":"Payload is not dict",
    "status":"error"
}
```

- 400(name 不能为空字符串)

```javascript
{
    "status":"error",
    "message":"empty name is not allowed"
}
```

- 400(相同的 name 已经存在)

```javascript
{
    "status":"error",
    "message":"Duplicate schema name detected"
}
```

- 400(data 字段不是有效的 json)

```javascript
{
    "status":"error",
    "message":"data is not valid json"
}
```

## 4.3. 获取指定 id 的 mold
GET ~/mold/`:id`

RESP
- 200

```javascript
{
    "status":"ok",
    "data":{
        "id":1,
        "updated_utc":1513668953,
        "data":"data",
        "mold_type": 0,  //0-复杂长文档信息抽取 1-固定版式文档KV抽取
        "created_utc":1513667718,
        "checksum":"6d9852ec2eae74ecb679cd9b89675fc9",
        "name":"formala",
        "predictors":[
            {
                "path": [
                    "公司简称"
                ],
                "model": "fixed_position",
            },
            {
                "path": [
                    "（二级）"
                ],
                "model": "table_row"
            }
        ]
    }
}
```

- 404(对应 id 的数据不存在)

```javascript
{
    "status":"error",
    "message":"Item Not Found"
}
```


## 4.4. 更新指定 id 的 mold
PUT ~/mold/`:id`

PARA(json)
- name: str, optional. 不能为空字符串; 有唯一性检查
- data: null/json, optional. 如果想传入 json, 必须是有效的 json

RESP
- 200

```javascript
{
    "status":"ok",
    "data":{
        "id":23,
        "updated_utc":1513668953,
        "data":"data",
        "created_utc":1513667718,
        "checksum":"6d9852ec2eae74ecb679cd9b89675fc9",
        "name":"formala",
        "predictors":[
            {
                "path": [
                    "公司简称"
                ],
                "model": "fixed_position",
            },
            {
                "path": [
                    "（二级）"
                ],
                "model": "table_row"
            }
        ]
    }
}
```

- 400(传输的数据是非法的 json, 此时返回不是一个 json, 而是以一个异常的形式从后台抛出)

```
raise tornado.web.HTTPError(400, u'Invalid JSON in body of request')
```

- 400(请求不包含任何数据或包含的数据不是字典)

```javascript
{
    "message":"Payload is not dict",
    "status":"error"
}
```

- 404(对应 id 的数据不存在)

```javascript
{
    "status":"error",
    "message":"Item Not Found"
}
```

- 400(name 不能为空字符串)

```javascript
{
    "status":"error",
    "message":"empty name is not allowed"
}
```

- 400(相同的 name 已经存在)

```javascript
{
    "status":"error",
    "message":"Duplicate schema name detected"
}
```

- 400(data 字段不是有效的 json)

```javascript
{
    "status":"error",
    "message":"data is not valid json"
}
```

- 400(更新的 json 中不包含 `name` 或者 `data`)

```javascript
{
    "status":"error",
    "message":"not a valid update"
}
```

## 4.5. 删除指定 id 的 mold
DELETE ~/mold/`:id`

RESP
- 200

```javascript
{
    "status":"ok",
    "data":{
        "id":23
    }
}
```

- 404(对应 id 的数据不存在)

```javascript
{
    "status":"error",
    "message":"Item Not Found"
}
```

## 4.6. 查询指定 id 的 mold 的字段注释
GET ~/mold/`:id`/intro_words

RESP
- 200

```javascript
{
    "status":"ok",
    "data":{
        "LRs_A1": "Rule 13.35: An...",
        "LRs_A2": "App 16(12B): A listed...",
    }
}
```

- 404(对应 id 的数据不存在)

```javascript
{
    "status":"error",
    "message":"Item Not Found"
}
```

## 4.7. 获取所有模型模板
GET ~/model_class
RESP
- 200

```javascript
{
    "status":"ok",
    "data":{
        "partial_text": {
            "name": "段落",
            "doc": "段落中文本内容提取",
            "template": {
                "path": [
                    "<path>"
                ],
                "model": "partial_text",
            }
        }
    }
}
```

# 5. 系统配置
## 5.1. 获取单条配置
GET ~/config/`:key`
RESP
- 200

```javascript
{
    "status": "ok",
    "data": {
        "created_utc": 1576726744,
    	"data": {
            "db_driver": "postgresql",
            "db_host": "localhost",
            "db_port": "35332",
            "db_user": "postgres",
            "db_password": "",
            "db_name": "test_1",
            "sync_frequency": "daily",
            "sync_time": "2:00"
    	},
    	"enable": 1,
    	"id": 3,
    	"index": "schema:27",
    	"name": "sync_external_file",
    	"updated_utc": 1576726744,
    }
}
```

## 5.2. 写入单条配置
POST ~/config/`:key`
BODY
```javascript
{
    "db_driver": "postgresql",
    "db_host": "localhost",
    "db_port": "35332",
    "db_user": "postgres",
    "db_password": "",
    "db_name": "test_1",
    "sync_frequency": "daily",
    "sync_time": "2:00"
}
```

RESP
- 200

```javascript
{
    "status": "ok",
    "data": null
}
```

## 5.3. 停用/启用单条配置
POST ~/enable_config/`:key`/`:enable`?schema=`\d+`

PARA(json)
- key: str, 必填. config_name
- enable: int, 必填. 1-启用；0-停用
- schema: int，必填. schema_id

RESP
- 200

```javascript
{
    "status": "ok",
    "data": null
}
```
