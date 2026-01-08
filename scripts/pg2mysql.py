import decimal
import json
import logging
import sys
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Any

import mysql.connector
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)


@dataclass
class PGConfig:
    dbname: str
    user: str
    password: str
    host: str
    port: str | int = "5432"


@dataclass
class MySQLConfig:
    host: str
    user: str
    password: str
    database: str
    port: str | int = "3306"


@dataclass
class TableMigrationEntry:
    pg_table: str
    mysql_table: str | None = None
    columns: list[str] | None = None

    def __post_init__(self):
        if self.mysql_table is None:
            self.mysql_table = self.pg_table


class DatabaseMigrationError(Exception):
    pass


@dataclass
class DatabaseMigrator:
    pg_config: PGConfig
    mysql_config: MySQLConfig
    batch_size: int
    tables_to_migrate_config: list[TableMigrationEntry]

    pg_conn: psycopg2.extensions.connection | None = field(init=False, default=None)
    mysql_conn: mysql.connector.MySQLConnection | None = field(init=False, default=None)
    mysql_db_name: str = field(init=False)

    def __post_init__(self):
        self.mysql_db_name = self.mysql_config.database
        if not self.mysql_db_name:
            logger.error("MySQL配置中缺少 'database' 名称。")
            raise ValueError("MySQL configuration missing 'database' name.")

    def _connect(self) -> None:
        """建立到PostgreSQL和MySQL的连接"""
        try:
            logger.info(
                f"正在连接到 PostgreSQL ({self.pg_config.host}:{self.pg_config.port}, 数据库: {self.pg_config.dbname})..."
            )
            self.pg_conn = psycopg2.connect(
                dbname=self.pg_config.dbname,
                user=self.pg_config.user,
                password=self.pg_config.password,
                host=self.pg_config.host,
                port=str(self.pg_config.port),
            )
            logger.info("成功连接到 PostgreSQL!")

            logger.info(
                f"正在连接到 MySQL ({self.mysql_config.host}:{self.mysql_config.port}, 数据库: {self.mysql_db_name})..."
            )
            self.mysql_conn = mysql.connector.connect(
                host=self.mysql_config.host,
                user=self.mysql_config.user,
                password=self.mysql_config.password,
                database=self.mysql_config.database,
                port=int(self.mysql_config.port),
            )
            logger.info("成功连接到 MySQL!")
        except (psycopg2.Error, mysql.connector.Error) as e:
            raise DatabaseMigrationError(f"数据库连接失败: {e}")

    def _disconnect(self) -> None:
        """关闭数据库连接"""
        if self.pg_conn:
            try:
                self.pg_conn.close()
                logger.info("PostgreSQL 连接已关闭。")
            except psycopg2.Error as e:
                logger.warning(f"关闭 PostgreSQL 连接时出错: {e}")
            finally:
                self.pg_conn = None
        if self.mysql_conn:
            try:
                if self.mysql_conn.is_connected():
                    self.mysql_conn.close()
                    logger.info("MySQL 连接已关闭。")
            except mysql.connector.Error as e:
                logger.warning(f"关闭 MySQL 连接时出错: {e}")
            finally:
                self.mysql_conn = None

    def _enable_mysql_checks(self, enable: bool = True) -> None:
        """启用或禁用MySQL的约束检查 (SESSION级别)"""
        if self.mysql_conn and self.mysql_conn.is_connected():
            try:
                with self.mysql_conn.cursor() as cursor:
                    status = "启用" if enable else "禁用"
                    val = 1 if enable else 0
                    logger.info(f"在MySQL中 {status} 外键和唯一检查 (SESSION)...")
                    cursor.execute(f"SET @@SESSION.foreign_key_checks = {val};")
                    cursor.execute(f"SET @@SESSION.unique_checks = {val};")
                    cursor.execute("SET sql_mode='NO_AUTO_VALUE_ON_ZERO'")
            except mysql.connector.Error as e:
                logger.warning(f"设置MySQL约束检查时出错: {e}")

    @staticmethod
    def _transform_value(value: Any, pg_column_udt_type: str, mysql_column_type_full: str) -> Any:
        """
        根据需要转换从PostgreSQL读取的值，以便插入MySQL。
        pg_column_udt_type: PostgreSQL UDT name (e.g., 'int4', 'varchar', 'jsonb', '_text' for text array)
        mysql_column_type_full: MySQL column type (e.g., 'int(11)', 'varchar(255)', 'json', 'text')
        """
        if value is None:
            return None
        mysql_base_type = mysql_column_type_full.lower().split("(")[0]

        if isinstance(value, bool) and (mysql_base_type == "tinyint" or mysql_base_type == "boolean"):
            return 1 if value else 0
        if isinstance(value, uuid.UUID) and mysql_base_type == "char":
            return str(value)

        if pg_column_udt_type in ("json", "jsonb") and mysql_base_type == "json":
            if isinstance(value, (dict, list)):
                try:
                    return json.dumps(value)
                except TypeError as e:
                    logger.warning(
                        f"无法将Python对象 {type(value)} 序列化为JSON字符串: {e}. 值: {str(value)[:100]}... 将尝试作为普通字符串插入。"
                    )
                    return str(value)
            elif isinstance(value, str):  # Value is already a string
                # MySQL's JSON column will validate if it's a valid JSON string upon insertion.
                # If psycopg2 already converted JSON to a string (less common for json/jsonb), pass it as is.
                return value
            else:  # For other unexpected types, attempt to serialize
                try:
                    return json.dumps(value)
                except TypeError:
                    logger.warning(
                        f"无法将类型 {type(value)} 的值序列化为JSON: {str(value)[:100]}... 将尝试作为普通字符串插入。"
                    )
                    return str(value)

        if pg_column_udt_type and pg_column_udt_type.startswith("_"):  # Handling array types
            if isinstance(value, list):  # psycopg2 converts PG arrays to Python lists
                if mysql_base_type == "json":  # Target is MySQL JSON column
                    try:
                        return json.dumps(value)  # Serialize Python list to JSON array string
                    except TypeError as e:
                        logger.warning(f"无法将数组 {value} 序列化为JSON字符串: {e}. 将存储为普通字符串。")
                        return str(value)
                elif mysql_base_type in ("text", "longtext", "mediumtext", "varchar"):  # Target is a text-based column
                    try:
                        return json.dumps(value)  # Serialize to JSON string for storage in TEXT
                    except TypeError as e:
                        logger.warning(f"无法将数组 {value} 序列化为JSON字符串: {e}. 将存储为普通字符串。")
                        return str(value)
                else:
                    logger.warning(
                        f"PG数组({pg_column_udt_type})到MySQL列({mysql_column_type_full})的策略未定义。将按原样传递。"
                    )
            else:  # Expected a list from PG array, but got something else
                logger.warning(
                    f"期望列表(来自PG数组 {pg_column_udt_type})但收到 {type(value)}。值: {str(value)[:100]}..."
                )

        if pg_column_udt_type == "bytea" and "blob" in mysql_base_type:
            if isinstance(value, (bytes, memoryview)):
                return value
            else:
                logger.warning(f"期望bytes/memoryview(来自PG bytea)但收到 {type(value)}. 值: {str(value)[:100]}...")

        if isinstance(value, decimal.Decimal) and mysql_base_type == "decimal":
            return value

        return value  # Default: pass as is, relies on DB driver compatibility

    def _get_column_details_from_pg(self, table_name: str) -> dict[str, dict[str, str]]:
        """从PostgreSQL的information_schema获取列名、PG数据类型和UDT类型"""
        if not self.pg_conn:
            raise DatabaseMigrationError("PostgreSQL connection not established.")
        details: dict[str, dict[str, str]] = {}
        with self.pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as col_cursor:
            query = """
            SELECT column_name, data_type, udt_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position;
            """
            try:
                col_cursor.execute(query, (table_name,))
                for row in col_cursor.fetchall():
                    details[row["column_name"]] = {"data_type": row["data_type"], "udt_name": row["udt_name"]}
            except psycopg2.Error as e:
                logger.error(f"在表 '{table_name}' 获取PG列详情时发生错误: {e}")
                raise
        return details

    def _get_column_types_from_mysql(self, table_name: str) -> dict[str, str]:
        """从MySQL的information_schema获取列名和完整列类型"""
        if not self.mysql_conn:
            raise DatabaseMigrationError("MySQL connection not established.")
        types_map: dict[str, str] = {}
        with self.mysql_conn.cursor() as mysql_col_cursor:
            query = """
            SELECT column_name, column_type 
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position;
            """
            try:
                mysql_col_cursor.execute(query, (self.mysql_db_name, table_name))
                for row in mysql_col_cursor.fetchall():  # mysql.connector returns tuples
                    types_map[row[0]] = row[1]  # column_name, column_type
            except mysql.connector.Error as e:
                logger.error(f"在MySQL表 '{table_name}' 获取列类型时发生错误: {e}")
                raise
        return types_map

    def _get_all_user_tables_from_pg(self) -> list[TableMigrationEntry]:
        """从PostgreSQL的public schema获取所有用户表名"""
        if not self.pg_conn:
            raise DatabaseMigrationError("PostgreSQL connection not established.")
        tables: list[TableMigrationEntry] = []
        with self.pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            try:
                cursor.execute("""
                    SELECT tablename
                    FROM pg_catalog.pg_tables
                    WHERE schemaname = 'public';
                """)
                for row in cursor.fetchall():
                    tables.append(TableMigrationEntry(pg_table=row["tablename"]))
                logger.info(f"从PostgreSQL 'public' schema 自动发现 {len(tables)} 个表。")
            except psycopg2.Error as e:
                logger.error(f"从PostgreSQL获取表列表时出错: {e}")
                raise
        return tables

    def _migrate_single_table(
        self, pg_table_name: str, mysql_table_name: str, column_config: list[str] | None = None
    ) -> None:
        """迁移单个表的数据"""
        pg_data_cursor: psycopg2.extensions.cursor | None = None
        mysql_data_cursor: mysql.connector.cursor.MySQLCursorPrepared | None = None
        try:
            if not self.pg_conn or not self.mysql_conn:
                raise DatabaseMigrationError("Database connections are not established for table migration.")

            pg_data_cursor = self.pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
            mysql_data_cursor = self.mysql_conn.cursor(prepared=True)

            logger.info(f"--- 开始处理表: {pg_table_name} (PG) -> {mysql_table_name} (MySQL) ---")
            logger.debug(f"PG数据游标类型: {type(pg_data_cursor)}")

            pg_column_details = self._get_column_details_from_pg(pg_table_name)
            mysql_column_types_map = self._get_column_types_from_mysql(mysql_table_name)

            if not pg_column_details:
                raise DatabaseMigrationError(f"无法获取源表 '{pg_table_name}' 的列信息。")
            if not mysql_column_types_map:
                raise DatabaseMigrationError(
                    f"无法获取目标表 '{mysql_table_name}' (数据库 '{self.mysql_db_name}') 的列信息。"
                )

            select_columns_source_order = column_config if column_config else list(pg_column_details.keys())
            pg_select_columns_str = ", ".join([f'"{col}"' for col in select_columns_source_order])

            final_insert_map: dict[str, str] = {}
            insert_columns_for_sql: list[str] = []
            for pg_col_name in select_columns_source_order:
                found_match = False
                # 表名大小写一致，但列名可能不一致，所以保留此逻辑
                if pg_col_name in mysql_column_types_map:  # Exact match (case-sensitive for keys in dict)
                    final_insert_map[pg_col_name] = pg_col_name
                    insert_columns_for_sql.append(pg_col_name)
                    found_match = True
                else:  # Try case-insensitive match by iterating through MySQL column names
                    for mysql_col_name_actual in mysql_column_types_map.keys():
                        if mysql_col_name_actual.lower() == pg_col_name.lower():
                            final_insert_map[pg_col_name] = mysql_col_name_actual
                            insert_columns_for_sql.append(mysql_col_name_actual)
                            found_match = True
                            logger.info(
                                f"源列 '{pg_col_name}' 通过大小写不敏感匹配到目标列 '{mysql_col_name_actual}'。"
                            )
                            break
                if not found_match:
                    logger.warning(f"源表列 '{pg_col_name}' 在目标表 '{mysql_table_name}' 中未找到匹配。将跳过此列。")

            if not insert_columns_for_sql:
                raise DatabaseMigrationError(f"表 '{mysql_table_name}' 没有与源表 '{pg_table_name}' 匹配的列可供迁移。")

            pg_select_query = f'SELECT {pg_select_columns_str} FROM public."{pg_table_name}";'
            mysql_insert_columns_str = ", ".join([f"`{col}`" for col in insert_columns_for_sql])
            placeholders = ", ".join(["%s"] * len(insert_columns_for_sql))
            mysql_insert_query = (
                f"INSERT IGNORE INTO `{mysql_table_name}` ({mysql_insert_columns_str}) VALUES ({placeholders});"
            )

            logger.info(f"将从PostgreSQL读取列 (顺序): {select_columns_source_order}")
            logger.info(f"将向MySQL插入列 (顺序): {insert_columns_for_sql}")
            logger.debug(f"PG SELECT Query: {pg_select_query}")
            logger.debug(f"MySQL INSERT Query: {mysql_insert_query}")

            pg_data_cursor.execute(pg_select_query)
            rows_processed_total: int = 0
            first_batch_row_type_logged: bool = False

            while True:
                pg_rows: list[psycopg2.extras.DictRow] = pg_data_cursor.fetchmany(self.batch_size)
                if not pg_rows:
                    break

                if pg_rows and not first_batch_row_type_logged:
                    logger.debug(f"第一个获取到的PG数据行类型: {type(pg_rows[0])}")
                    if isinstance(pg_rows[0], tuple):  # Should not happen with DictCursor
                        logger.warning("PG数据行是元组(tuple)。DictCursor可能未生效。列将无法通过名称访问。")
                    elif hasattr(pg_rows[0], "keys"):  # Check if it's dict-like
                        logger.debug(f"PG数据行是 DictRow 或类似字典的对象。键示例: {list(pg_rows[0].keys())[:5]}...")
                    first_batch_row_type_logged = True

                data_to_insert: list[tuple[Any, ...]] = []
                for pg_row_dict in pg_rows:
                    row_values_ordered_for_insert: list[Any] = []
                    valid_row: bool = True
                    for pg_col_name in select_columns_source_order:
                        if pg_col_name not in final_insert_map:
                            continue

                        mysql_actual_col_name = final_insert_map[pg_col_name]
                        pg_col_detail = pg_column_details.get(pg_col_name, {})
                        pg_col_udt = pg_col_detail.get("udt_name", "unknown_pg_udt")
                        mysql_col_type_full = mysql_column_types_map.get(mysql_actual_col_name, "unknown_mysql_type")

                        try:
                            original_value = pg_row_dict[pg_col_name]
                            transformed_value = self._transform_value(original_value, pg_col_udt, mysql_col_type_full)
                            row_values_ordered_for_insert.append(transformed_value)
                        except TypeError as te:
                            if "indices must be integers or slices, not str" in str(te):
                                logger.error(
                                    f"严重错误: 发生TypeError (tuple indices...)！DictCursor 未按预期工作。表='{pg_table_name}', PG列尝试访问='{pg_col_name}'"
                                )
                                raise DatabaseMigrationError(f"DictCursor error in table {pg_table_name}: {te}")
                            logger.error(f"值转换时发生TypeError: 表='{pg_table_name}', 列='{pg_col_name}', 错误: {te}")
                            raise  # Re-raise other TypeErrors to stop the process
                        except Exception as e:  # Catch other transformation errors
                            logger.error(
                                f"值转换失败! 表='{pg_table_name}', PG列='{pg_col_name}', MySQL列='{mysql_actual_col_name}', PG UDT='{pg_col_udt}', MySQL类型='{mysql_col_type_full}', 原始值='{str(original_value)[:100]}...', 错误: {e}"
                            )
                            valid_row = False
                            break  # Stop processing this row, and potentially this batch

                    if valid_row:
                        data_to_insert.append(tuple(row_values_ordered_for_insert))
                    else:
                        logger.warning(f"由于转换错误，跳过一行数据。源数据: {str(pg_row_dict)[:200]}...")

                if data_to_insert:
                    try:
                        if not self.mysql_conn or not mysql_data_cursor:
                            raise DatabaseMigrationError("MySQL connection or cursor not available for insert.")
                        print(mysql_insert_query)
                        mysql_data_cursor.executemany(mysql_insert_query, data_to_insert)
                        self.mysql_conn.commit()
                        rows_processed_total += len(data_to_insert)
                        logger.info(
                            f"表 {mysql_table_name}: 已提交 {len(data_to_insert)} 行, 总计 {rows_processed_total} 行..."
                        )
                    except mysql.connector.errors.IntegrityError as err:
                        logger.error(f"MySQL唯一键冲突错误 (表 {mysql_table_name}): {err}")
                        continue
                    except mysql.connector.Error as err:
                        logger.error(f"MySQL插入错误 (表 {mysql_table_name}): {err}")
                        if self.mysql_conn:
                            self.mysql_conn.rollback()
                        raise DatabaseMigrationError(f"MySQL insert error in table {mysql_table_name}: {err}")

            logger.info(
                f"--- 表 {pg_table_name} -> {mysql_table_name} 迁移完成。总共处理 {rows_processed_total} 行。 ---"
            )

        finally:
            if pg_data_cursor:
                try:
                    pg_data_cursor.close()
                except Exception as e_pg_close:
                    logger.warning(f"关闭PG数据游标时出错: {e_pg_close}")
            if mysql_data_cursor:
                try:
                    mysql_data_cursor.close()
                except Exception as e_mysql_close:
                    logger.warning(f"关闭MySQL数据游标时出错: {e_mysql_close}")

    def run_migration(self) -> None:
        """执行整个数据库迁移过程"""
        try:
            self._connect()
            self._enable_mysql_checks(False)

            tables_to_process = self.tables_to_migrate_config
            if not tables_to_process:
                logger.info("`TABLES_TO_MIGRATE` 列表为空，尝试从PostgreSQL 'public' schema 自动发现所有表...")
                tables_to_process = self._get_all_user_tables_from_pg()
                if not tables_to_process:
                    logger.warning("未能自动发现任何表。迁移中止。")
                    return
                logger.info(f"将尝试迁移以下自动发现的表: {[t.pg_table for t in tables_to_process]}")

            for table_entry in tables_to_process:
                if not table_entry.mysql_table:
                    logger.error(
                        f"TableMigrationEntry for pg_table '{table_entry.pg_table}' is missing mysql_table name. Skipping."
                    )
                    continue
                if table_entry.pg_table == "alembic_version":
                    logger.info(f"跳过 alembic_version 表迁移。")
                    continue
                self._migrate_single_table(table_entry.pg_table, table_entry.mysql_table, table_entry.columns)

            logger.info("\n所有指定表的迁移尝试已完成。")

        except (DatabaseMigrationError, psycopg2.Error, mysql.connector.Error) as e:
            logger.error(f"\n发生迁移错误，程序将终止: {e}")
            logger.error(traceback.format_exc())
            raise
        except Exception as e:
            logger.error(f"\n发生未知严重错误，程序将终止: {e}")
            logger.error(traceback.format_exc())
            raise DatabaseMigrationError(f"未知严重错误: {e}")
        finally:
            logger.info("\n开始执行清理操作...")
            if self.mysql_conn and self.mysql_conn.is_connected():
                self._enable_mysql_checks(True)
            self._disconnect()
            logger.info("清理操作完成。迁移过程结束。")


if __name__ == "__main__":
    logger.info("Python PostgreSQL 到 MySQL 数据迁移脚本")
    logger.info("=" * 70)

    # --- 配置 ---
    PG_CONFIG_USER = PGConfig(dbname="nafmii", user="postgres", password="", host="localhost", port="5432")
    MYSQL_CONFIG_USER = MySQLConfig(host="localhost", user="root", password="1", database="scriber", port=3306)
    BATCH_SIZE_USER: int = 1000
    TABLES_TO_MIGRATE_USER: list[TableMigrationEntry] = [
        # TableMigrationEntry(pg_table='file'), # mysql_table will default to 'file'
        # Add more tables as needed:
        # TableMigrationEntry(pg_table='nafmii_system', mysql_table='nafmii_system'),
        # TableMigrationEntry(pg_table='specific_cols_table', columns=['id', 'name', 'description']),
    ]
    # --- 配置结束 ---

    logger.warning("这是一个迁移脚本框架。在生产环境中使用前，请务必:")
    logger.warning("  1. 仔细检查并正确填写 PG_CONFIG_USER 和 MYSQL_CONFIG_USER。")
    logger.warning(
        "  2. 如果不使用自动发现表功能，请详细配置 TABLES_TO_MIGRATE_USER 列表，特别是表迁移顺序以处理外键。"
    )
    logger.warning("  3. 彻底审查和测试 _transform_value 方法，确保所有用到的数据类型都能正确转换。")
    logger.warning("  4. 确保目标MySQL数据库中已存在对应的表结构 (Schema已迁移)。此脚本主要负责数据迁移。")
    logger.warning("  5. 在与生产环境相似的测试环境中，使用数据子集或完整备份进行充分测试。")
    logger.warning("  6. **在执行任何操作前，务必完整备份您的源PostgreSQL和目标MySQL数据库！**")
    logger.info("=" * 70)

    migrator: DatabaseMigrator | None = None
    exit_code: int = 0
    try:
        migrator = DatabaseMigrator(
            pg_config=PG_CONFIG_USER,
            mysql_config=MYSQL_CONFIG_USER,
            batch_size=BATCH_SIZE_USER,
            tables_to_migrate_config=TABLES_TO_MIGRATE_USER,
        )
        migrator.run_migration()
        logger.info("\n迁移脚本成功执行完毕 (所有指定任务完成或按预期停止)。")
    except DatabaseMigrationError as dme:
        logger.error(f"\n迁移过程中发生已知错误，程序已终止: {dme}")
        exit_code = 1
    except Exception as ex:
        logger.error(f"\n迁移过程中发生未处理的意外错误，程序已终止: {ex}")
        logger.error(traceback.format_exc())
        exit_code = 1

    sys.exit(exit_code)
