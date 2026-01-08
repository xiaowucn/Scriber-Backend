注:
以下步骤默认服务监听端口号为 8098, 数据库端口号为 35337。如需调整请对应修改。


1. 检出工程

    ```bash
    git clone git@gitpd.appdao.com:cheftin/Remarkable.git
    ```

2. 安装依赖

    ```bash
    pip install -r misc/requirements.txt -U
    ```

3. 创建数据库

    ```bash
    ./bin/db_init 35337 mold
    ```

4. 创建数据表

    ```bash
    psql -p 35337 mold postgres < ./misc/db-schema.sql
    psql -p 35337 mold postgres < ./misc/db-tools.sql
    ```

5. 启动服务，注意设置合适的环境变量

    ```bash
    ENV=moldprod nohup ./bin/run &
    ```
