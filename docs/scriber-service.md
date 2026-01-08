# scriber 提取服务接口
scriber 可独立为提取服务运行，服务间使用 grpc 进行调用

## proto
```
syntax = "proto3";
package ai;

service AI {
    rpc initialize(Input) returns (Output) {}
    rpc train(Input) returns (Output) {}
    rpc predict(Input) returns (Output) {}
    rpc log(Input) returns (Output) {}
}

message Input {
    bytes kwargs_json = 1;
    string version = 2;
    bytes binary_data = 3;
}

message Output {
    bytes data_json = 1;
}

```

## 预测调用方法
通过 grpc 调用 `predict` 接口，参数如下：
| name | type | intro |
| ---- | ---- | ----- |
| binary_data | bytes | 预处理后的文件 |
| kwargs_json | bytes | 预测kw参数，暂未使用 |
| version | str | 模型版本号（深交所创业板使用版本号 `2`） |


## 预测返回结果
```json
{
    "crude_answer": ..., // 定位结果
    "predict_answer": ..., // 提取结果
}
```

关于定位结果格式：
```json
{
    "深交所信息抽取-创业板-注册制-财务基础数据|合并资产负债表|报告期": [
        {
            "score": 0.9230860353457743,  // 分数
            "text": "1、合并资产负债表",     // 内容
            "page": 254,                  // 页码
            "outlines": [                 // 外框
                [
                    83.8589,
                    87.5043,
                    511.265,
                    756.026502734375
                ]
            ]
        },
        ...
    ]
}
```


关于提取结果格式：
```json
{
    "schema": ...,  // 答案结构定义，省略
    "userAnswer": {
        "version": "2.2",
        "items": [
            {
                "key": "[\"深交所信息抽取-创业板-注册制-财务基础数据:0\", \"合并资产负债表:0\", \"报告期:0\"]",
                "schema": {
                    "data": {
                        "type": "日期",
                        "label": "报告期",
                        "words": "",
                        "multi": false,
                        "required": false,
                        "description": null
                    }
                },
                "score": "0.92",
                "data": [
                    {
                        "boxes": [
                            {
                                "page": 254,
                                "box": {
                                    "box_top": 95.6169,
                                    "box_right": 263.2153,
                                    "box_bottom": 102.8848,
                                    "box_left": 215.2277
                                },
                                "text": "2020-12-31"
                            }
                        ],
                        "handleType": "wireframe"
                    }
                ],
                "value": null,
                "meta": {
                    "cell": [
                        0,
                        1
                    ]
                }
            },
            ...  // 省略其他字段
        ]
    }
}
```
