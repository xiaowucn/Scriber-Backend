注:
以下步骤默认服务监听端口号为 8097, 数据库端口号为 35336。如需调整请对应修改。


1. 检出工程

    ```bash
    git clone git@gitpd.appdao.com:cheftin/Remarkable.git
    ```

2. 安装依赖

    ```bash
    pip install -r misc/requirements.txt -U
    ```

3. 修改标注系统使用的nginx配置文件，增加如下路由项:

    ```bash
    location ^~ /lrfapi/ {
        proxy_pass http://127.0.0.1:8097/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Original-Request-URI $scheme://$host$request_uri;
    }
    ```

4. 创建数据库

    ```bash
    ./bin/db_init 35336 pdftable
    ```

5. 创建数据表

    ```bash
    psql -p 35336 pdftable postgres < ./misc/db-schema.sql
    ```

6. 初始化tag表数据

    ```bash
    psql -p 35336 pdftable postgres -c "INSERT INTO tag (name) values ('表格划分问题'), ('不确定是否有表格'), ('其他问题')"
    ```

7. 启动服务，注意设置合适的环境变量

    ```bash
    ENV=pdfprod nohup ./bin/run &
    ```

8. 导入PDF数据
