# scriber 预测答案结构说明

## 初步定位结果格式
```json
[
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
```


## 精确提取结果格式：
```json
{
    "preset_answer": {
        "schema": { // 答案结构定义
            "schema_types": [],
            "schemas": [
                {
                    "name": "XX基金V1",
                    "orders": [
                        "名称"
                    ],
                    "schema": {
                        "名称": {
                            "type": "文本",
                            "required": false,
                            "multi": true
                        }
                    }
                }
            ],
            "version": "b1b4b5537568ec4a52c9e56f920cd378"
        },
        "userAnswer": {
            "version": "2.2",
            "items": [
                {
                    "key": "[\"XX基金V1:0\", \"名称:0\"]",
                    "schema": { // 答案结构定义
                        "data": {
                            "type": "文本",
                            "label": "名称",
                            "words": "",
                            "multi": true,
                            "required": false,
                            "description": null
                        }
                    },
                    "score": "0.07",
                    "data": [
                        {
                            "boxes": [
                                {
                                    "page": 3, // 答案所在的页码
                                    "box": {  // 答案外框
                                        "box_top": 221.0196,
                                        "box_right": 106.5114,
                                        "box_bottom": 230.8721,
                                        "box_left": 74.999
                                    },
                                    "text": "xxx基金"  // 答案文本
                                }
                            ],
                            "handleType": "wireframe"
                        }
                    ],
                    "value": null,
                    "meta": null
                }
            ]
        }
    }
}
```
