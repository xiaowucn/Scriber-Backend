#### 模型的开发流程

##### 1.配置文件
    - 当前环境的predictor所在的包:glazer_predictor
    - schema中信-募集书抽取的prophet_config所在文件:citic_issue_announcement_schema.py
```yaml
prophet:
  package_name: "glazer_predictor"
  config_map:
    中信-募集书抽取: "citic_issue_announcement"
```

##### 2.调试命令
```bash
MOLD=<mold>
# 初步定位:

# 准备数据, training_cache/<mold>/<vid>/elements
inv prompter.load-data-v2 $MOLD --clear --update

# 提取特征, training_cache/<mold>/<vid>/feature
inv prompter.extract-feature-v2 $MOLD

# 训练, training_cache/<mold>/<vid>/models
inv prompter.train-v2 $MOLD

# 预测
inv prompter.prompt-element --mold=$MOLD --overwrite

# 初步定位统计
inv prompter.stat -m $MOLD

# 提取:

# 准备数据, training_cache/<mold>/<vid>/answers
inv predictor.prepare-dataset $MOLD

# 训练, training_cache/<mold>/<vid>/predictors
inv predictor.train $MOLD

# 预测
inv predictor.preset-answer --mold=$MOLD --overwrite

# 提取统计
inv predictor.stat -m $MOLD

# 打包初步定位模型, data/model/custom_name_v2.zip 
inv prompter.archive-modelv2-for -s $MOLD -n custom_name

# 打包提取模型, data/model/custom_name_predictor.zip
inv predictor.archive-model-for -s $MOLD -n custom_name

# 部署 初步定位模型&提取模型
inv op.deploy-model mold_name --name=custom_name

```

##### 3.debug提取模型的文件
- 建议放在remarkable/predictor/debug_helpers.py,该路径已添加到git ignore

```python
from remarkable.predictor.helpers import prepare_dataset, train_answer_data, predict_mold_answer, stat
from remarkable.worker.tasks import inspect_rule_task


async def main():
    mid = 1
    fid = 500
    start_id = fid
    stop_id = fid
    debug_schema = ['发行概况-有关机构', '发行人机构信息']
    # debug_schema = None
    
    # await prophet_config_assist(mid)
    await prepare_dataset(mid, start_id, stop_id)  # 准备数据
    await train_answer_data(mid, special_rules=debug_schema)  # 训练数据
    await predict_mold_answer(mid, start_id, stop_id, special_rules=debug_schema)  # 预测
    await stat(mid, start_id, 160)  # 准确率统计
    # await inspect_rule(fid) # 合规


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
```

##### 4.将打包好的模型push到git lfs 仓库

##### 5.其他
- 开始一个新schema的提取时,可用prophet_config_assist()函数生成一份初始化的prophet_config文件
- 参见: test_predict_pipeline.py
- 修改了schema,须更新相应的导出文件: ```inv op.export-schema --name=<client_name> -s $MOLD -e $MOLD --delta```, 会更新data/schema/client_name_schema.json
- 打包模型时,建议将所使用的的训练集记录在prophet_config所在文件,以便于后期回归测试
- 更新模型后,线上环境需要重新部署并启用新版本,可用 GET ~/api/v1/plugins/debug/molds/(?P<mold_id>.*)/deploy?name=<custom_name> 一步完成, custom_name即为打包模型时的custom_name
- 本地开发调试时,可使用 ```inv op.deploy-model mold_name --name=custom_name --dev``` 来部署模型,以便忽略模型版本(model_version)的控制


##### 6.报错备忘录
- "This solver needs samples of at least 2 classes in the data, but the data contains only one class: 1"
  - model.fit(train_data, y_train), 某字段,标了所有文档中的所有元素块时,会报此错; 一般是因为文档元素块极少,比如整个文档就1、2个元素块
  - 解决办法:至少一篇文档,不要所有元素块都标
