# 中信证券循环购买报告信息抽取

> 需求池: https://gitpd.paodingai.com/cheftin/docs_scriber/-/issues/484

## 导入Schema

`inv op.import-schema --name=ecitic_poc`

## 模型部署

   ```shell
   inv op.deploy-model "“小而分散”类资产" --name=ecitic_poc_small_scattered
   inv op.deploy-model "非“小而分散”类资产" --name=ecitic_poc_not_small_scattered
   ```



## 批量任务

1. 初步定位: `inv op.prompt-element --mold=2 --overwrite`
2. 精确提取: `inv op.preset-answer --mold=2 --overwrite`

## 杂项

1. 精确提取(预测)结果评估: `python -m remarkable.optools.stat_scriber_answer --mold=2`
