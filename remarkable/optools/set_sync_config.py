from remarkable.common.util import loop_wrapper
from remarkable.db import db, peewee_transaction_wrapper
from remarkable.pw_models.model import NewSystemConfig

# schema 配置
schema_id = 7

# 上游配置
upstream_db_driver = "MySQL"
upstream_db_host = "localhost"
upstream_db_port = 3306
upstream_db_user = "root"
upstream_db_password = "123"
upstream_db_name = "scriber"  # 上游数据库名
upstream_table_name = "document"  # 文档记录表名
upstream_table_pk_column = "f001v"  # 文档记录表主键
upstream_table_link_column = "f009v"  # 文档记录表下载链接字段（用于下载文档）
upstream_tree_id = 7  # 上传至 scriber 系统目录 id

# 下游配置
downstream_db_driver = "MySQL"
downstream_db_host = "localhost"
downstream_db_port = 3306
downstream_db_user = "root"
downstream_db_password = "123"
downstream_db_name = "scriber"  # 下游数据库名


@loop_wrapper
@peewee_transaction_wrapper
async def main():
    await db.raw_sql("delete from system_config;")
    await NewSystemConfig.create(
        **{
            "name": "answer_sync_db",
            "data": {
                "db_driver": downstream_db_driver,
                "db_host": downstream_db_host,
                "db_port": downstream_db_port,
                "db_user": downstream_db_user,
                "db_password": downstream_db_password,
                "db_name": downstream_db_name,
                "sync_frequency": "daily",
                "sync_weekday": "",
                "sync_time": "00:00",
                "schema_id": schema_id,
            },
            "index": f"schema:{schema_id}",
            "enable": 1,
        }
    )
    await NewSystemConfig.create(
        **{
            "name": "sync_external_file",
            "data": {
                "db_driver": upstream_db_driver,
                "db_host": upstream_db_host,
                "db_port": upstream_db_port,
                "db_user": upstream_db_user,
                "db_password": upstream_db_password,
                "db_name": upstream_db_name,
                "db_table": upstream_table_name,
                "db_table_pk": upstream_table_pk_column,
                "db_table_link": upstream_table_link_column,
                "tree_id": upstream_tree_id,
                "schema_id": schema_id,
                "sync_frequency": "daily",
                "sync_time": "00:00",
                "sync_weekday": "",
            },
            "index": f"schema:{schema_id}",
            "enable": 1,
        }
    )


if __name__ == "__main__":
    main()
