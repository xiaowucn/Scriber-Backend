# Scriber 作为独立的预测服务
Scriber 可作为独立的预测服务启动(aipod)
此模式不依赖数据库，需要部署相关的预训练模型或外部模型

以下操作以 `深交所创业板` 环境为例

## 服务配置
aipod 服务端配置：
```yaml
prophet:  # 预测类相关配置
  package_name: "szse_poc_predictor"
  config_map:
    深交所信息抽取-创业板-注册制-财务基础数据: "financial_data"

aipod:
  mold_id: 2                                             # schema id（由于不依赖数据库，可随意指定，和部署的模型 id 匹配即可）
  schema_path: "data/schema/szse_financial_schema.json"  # schema 归档文件路径
  schema_name: "深交所信息抽取-创业板-注册制-财务基础数据"     # schema 名称

```

客户端配置（深交所填报系统）:
```yaml
ai:
  scriber:
    address: "localhost:2999"
    mode: "distributed"  # "allinone" or "distributed"
```

## 模型部署
```bash
# 部署 初步定位模型&提取模型
inv op.deploy-model 2 --name=szse_financial
```
注：仅初次或模型更新时执行

## 服务启动
```bash
AIPOD_LISTEN_PORT=2999 ./bin/scriber_service.sh
```
