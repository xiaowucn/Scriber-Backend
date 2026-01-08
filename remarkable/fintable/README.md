# 三大报表通用提取模型

基于 scriber predictor 实现，使用 table_tuple 提取模式
训练输入：pdfinsight + 标注答案 （数据由多个环境汇总而来，用一个 scriber 作为训练服务器，数据保存在其上，训练完成后的模型可以脱离数据库运行）
预测输入：pdfinsight + 指定三大报表的 element index （内部转换为 crude answer，输入给 scriber predictor）
预测输出：特定的 schema answer

## 实现
训练过程：
- [ ] 通用三大报表 schema 定义
- [ ] 外部 scriber 标注输入导入
- [ ] 转换各环境答案到通用 schema （保存到 special answer）
- [ ] 使用 special answer 进行训练、评估

预测过程：
- [ ] 按照 aipod 服务对接
  - [ ] 指定三大报表 index，转换为 crude answer
  - [ ] 使用 scriber predictor 进行预测


## 相关命令
### 训练
```bash
# 收集训练数据
inv predictor.prepare-dataset 1 --start=<start> --end=<end>
# 训练
inv predictor.train 1
# 打包模型
inv predictor.archive-model-for 1 -n fintable
# 部署模型
inv op.deploy-model 1 -n fintable
```

### 验证/调试
debug 配置为True时，scriber会把每次外部调用的输入参数保存到`data/requests`目录下

scriber在重新训练之后验证时，可以从`data/requests`目录下获取到`request_log_id`

调用下面示例代码查看结果
```python
@loop_wrapper
async def debug_fintable(reqid):
    from aipod.rpc.client import AIClient
    from remarkable.fintable.model import FintableModel

    request_dir = Path(project_root, "data/requests/", str(reqid))
    pdfinsight_data = (request_dir / "data.bin").read_bytes()
    kwargs = json.loads((request_dir / "kwargs.json").read_text())
    model = AIClient(address="localhost:50051")
    # model = FintableModel()
    res = model.predict(binary_data=pdfinsight_data, **kwargs)
    (request_dir / "debug.json").write_text(json.dumps(res))
    print(res)
```
