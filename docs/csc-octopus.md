# 八爪鱼接口文档

### 更新记录
|Date| Desc|
| ----|----|
|2021-11-05 |1. 文件上传接口增加schema, host, port 三个可选参数 2. 文件上传接口返回URL会附带schema, host, post 信息|
|2021-12-17 |1. 文件上传接口增加projectId, bondId, bondType, add_path, scrier_domain|
|2023-03-28 |1.修改文件上传接口参数增加参数 csc_duration_id 2.删除参数host port add_path schema |

### 1、文件上传 & 链接上传

POST ~/api/v1/plugins/csc_octopus/upload

#### Request Header


|Field | Value Example  |Desc|
| ----|-----|-----|
|Content-Type |multipart/form-data| |
|access-token | 9fpHf8pofUH3njF |String，约定的访问令牌，接口鉴权使用|

#### Request Body

|Field | Value Example  |Desc|
| ----|-----|-----|
|url| https://www.chinabond.com.cn/Info/158980449|String, 公告详情⻚URL,可选参数|
|file|PDF文件| 上传的公共的PDF文件，可选参数|
|confirm_url|http://10.101.252.35:9222/aiProject |解析完成后的推送地址  可选参数|
|scriber_domain|http://100.64.0.3:22109|scriber地址 用来生成标注页面地址 可选参数|
|projecId| project_id |String, 必填参数, 八爪⻥传入|
|bondId| bond_id| String, 必填参数, 八爪⻥传入|
|bondType| bond_type| String, 必填参数, 八爪⻥传入|
|durationId| durationId| String, 必填参数, 八爪⻥传入|


#### 接口说明
- 本接口支持上传公告PDF文档和公告发布链接两种方式
- 请求体的参数 url 和 file 任意使用一个即可，分别表示解析公告链接和公告PDF文档
- 若请求参数同时上传了url 和 file 则优先使用PDF文档

#### Response Body
##### Success

```json
{
    "status": "ok",
    "data": {
        "isSuccess": 1 ,
        "paitechId": 61 ,
        "paitechURL": "http://100.64.0.3:22109/#/csc-octopus/project/remark/10468?treeId=80&fileId=1532&schemaId=24&projectId=46&task_type=extract&fileName=%5B1-12%5D20%E4%BA%9A%E8%BF%AA01%E5%80%BA%E5%88%B8%E6%8C%81%E6%9C%89%E4%BA%BA%E5%90%8D%E5%86%8C20230320_part1%281%29.pdf",
        "confirmURL": ""
        }
    }
}
```

#####Error

```json
{
    "status": "error",
    "data": {
        "message": "fid= 1532, ai result is not finished in 20 seconds"
        }
    }
}
```
