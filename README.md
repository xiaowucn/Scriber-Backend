# Remarkable：通用标注工具

## Develop Environment (manual)

1. 参考`docker/runtime/Dockerfile`装好系统依赖（以Ubuntu为例, 推荐 22.04）
2. 安装项目依赖（python3.12）

```bash
> uv python install 3.12
uv venv --python 3.12
uv sync --group=dev
source .venv/bin/activate
```

3. Setup git hooks([pre-commit document](https://pre-commit.com/))

    > _注意: hook 类型较多_
```bash
> for t in pre-commit commit-msg pre-push; do pre-commit install --hook-type $t; done
```

4. 拷贝 `config/config-dev.yml`到同级目录下，重命名为 `config-usr.yml`并修改为自己的配置

   > 具体实现见`remarkable/config.py`代码

5. Create a postgresql database(the default args from get_config function in config file)

> 提前配置好 PostgreSQL 环境变量

```bash
> bin/db_init
```

6. run db migrations

```bash
> inv db.upgrade
```

7. update and create translation file(optional)

```bash
> inv i18n.update
> inv i18n.compile2po
```

8. run the web server

```bash
> bin/run
```

9. try to access the test api `http://localhost:8000/api/v1/config`
10. 关于提取模型的开发说明，请参考 `remarkable/predictor/readme.md`
11. 建议的插件:

    1. Git Commit Template
    2. GitHub Copilot
    3. [tabnine](https://www.tabnine.com)
    4. Translation

12. 推荐的Python虚拟环境管理方案 `uv`

13. .NET docx批注工具(web.revision_tools)

```bash
> sudo pacman -Syu dotnet-runtime-6.0
```

## Location Prompter Model Training

### Mode v1

```bash
# 为 schema 5 训练模型
# --start, --end 为训练集范围
# --clear 清空之前的训练数据缓存和 ngram 词汇表
# --update 读取新的训练文档
inv prompter.build-model 5 --start=200 --end=300 --clear --update
```

### Mode v2

```bash
# 读取文档数据和答案
inv prompter.load-data-v2 5 --start=200 --end=300 --clear --update

# 生成训练数据
inv prompter.extract-feature-v2 5 --start=200 --end=300

# 训练
inv prompter.train-v2 5

# 打包模型
inv prompter.archive-modelv2-for 5 --name=hkex


```

config:

```yaml
prompter:
  mode: "v2"
  use_syllabuses: True # 是否使用目录信息
  tokenization: "jieba" # 分词方法，为 null 则按空白分词（英文）
  context_length: 1 # 上下文范围
  post_process: # 针对港交所的后处理，每页只取一个答案
    - "A12-Biography"
    - "A12-List of directors"
    - "A14"
    - "A20"
    - "A21-A21.1"
    - "A22"
    - "A23"
    - "A24-Table for related party transaction"
    - "A26"
    - "A29-A29.3"
    - "A8"
```

### Evaluation

```bash
# 预测
inv op.prompt-element --start=200 --end=300 --mold=5 --overwrite

# 统计
python -m remarkable.optools.stat_scriber_answer -c -f 200 -t 300 -m 5
```

## Answer Extract Model Training

```bash
# 读取标注数据集
inv predictor.prepare-dataset <schema_id> --start=<start_file_id> --end=<end_file_id>

# 训练
inv predictor.train <schema_id>

# 打包模型
inv predictor.archive-model-for <schema_id> --name=<model_package_name>


## 部署模型
inv op.deploy-model <schema_id> --name=<model_package_name>
```

### Evaluation

```bash
# 预测
inv op.preset-answer --start=<start_file_id> --end=<end_file_id> --mold=<schema_id> --overwrite

# 统计
python -m remarkable.optools.stat_scriber_answer -f <start_file_id> -t <end_file_id> -m <schema_id>
```

### Fintable

三大报表提取服务

部署步骤：

```
# 部署模型，注: id 1 是固定的，不用改
inv op.deploy-model 1 --name=fintable

# 运行服务，可通过 AIPOD_LISTEN_PORT 指定端口
./bin/fintable_service.sh
```

### FAQ

> 任何本地奇怪的运行问题，首先自行参考 `docker/runtime/Dockerfile`装好系统依赖（以Ubuntu为例，macOS自行brew之）

1. `libraries mkl_rt not found in xxx`

   `sudo apt install gfortran libatlas-base-dev`

2. 如何同步线上数据

   1. 修改配置文件 `web.apis.sync_host`，如 `http://hkex.test.paodingai.com`
   2. `inv -h sync.file`支持传入SQL语句查询

3. 新版 `pdfparser`需要 `jsoncpp`依赖

   1. macOS: `brew install jsoncpp`
   2. Ubuntu: `sudo apt install libjsoncpp1`
4. 运行`partial_text`模型会用到Java 的运行环境，需要安装
    1. arch `yay -S jre`

> Mac M1问题汇总

1、如果运行时抛出异常如下

```
ImportError: dlopen(/opt/miniconda3/envs/Scriber-Backend/lib/python3.12/site-packages/palladium.cpython-310-darwin.so, 0x0002): Library not loaded: /usr/local/opt/libpng/lib/libpng16.16.dylib
```

首先排查Conda等虚拟环境是否为M1架构，如果不是，请先更换Conda等虚拟环境为M1架构之后再次进行编译运行。

2、中间可能还需要的包

```
brew install cairo pango gdk-pixbuf libxml2 libxslt libffi qpdf-10.6.3 glib ffmpeg libjpeg spatialindex
```

上述包的安装需要根据具体抛出的异常进行判断安装，安装完成之后，如果提示依旧找不到该包，则可能需要进行软链接，处理如下：
```
sudo ln -s /opt/homebrew/opt/glib/lib/libgobject-2.0.0.dylib /usr/local/lib/gobject-2.0
sudo ln -s /opt/homebrew/opt/pango/lib/libpango-1.0.dylib /usr/local/lib/pango-1.0
sudo ln -s /opt/homebrew/opt/harfbuzz/lib/libharfbuzz.dylib /usr/local/lib/harfbuzz
sudo ln -s /opt/homebrew/opt/fontconfig/lib/libfontconfig.1.dylib /usr/local/lib/fontconfig-1
sudo ln -s /opt/homebrew/opt/pango/lib/libpangoft2-1.0.dylib /usr/local/lib/pangoft2-1.0
sudo ln -s /opt/homebrew/opt/pango/lib/libpangocairo-1.0.dylib /usr/local/lib/pangocairo-1.0
```

其中，上述通过homebrew安装的包的位置可能根据实际情况不一样，需要具体进行查看，查看命令示例：
```
brew list pango
```

## gmssl Sm4
### config
- `web.hex_binary_key` 值必须32为hex (对应16bytes)
  - 之前`web.binary_key` 不是hex格式, 长度为15, 所以新增了配置
  - X-BINARY-KEY 值为加密后的密钥
  - X-BINARY-ALG 值`HexSm4`表明使用sm4算法
- trident `unify_auth.auth_config.auth_{sys}.obs_login_hex`
  - 用来加密login的所有query
  - 值必须32为hex, 加密算法Sm4 且和 scriber`web.hex_binary_key`相同
  - 注意: Sm4依赖差异, scriber使用utensils版本, 使用gmssl-python(系统lib, 效率高); trident使用gmssl纯python版, 无系统依赖, 但效率较差.
