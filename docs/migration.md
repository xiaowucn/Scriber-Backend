# 如何编写兼容MySQL和PostgreSQL的alembic迁移脚本

### 1. 字段类型

#### 字符串类型:

mysql和postgresql中都有varchar和text类型, 不同的是mysql中text类型不支持设置默认值和加索引,postgresql中text可以覆盖varchar的使用场景

- 统一使用varchar+length, 且建立索引时需要索引上的所有字段总长度小于3072字节

#### 表示时间戳的INT类型:
  
mysql8.0.13之后支持函数作为INT默认值, 之前的情况暂时不支持

- 统一使用migrate_util.create_timestamp_field来生成时间戳字段, 最大支持到2038年

#### ARRAY类型:
mysql没有array类型, 使用json类型代替, 不支持默认值和索引, 需要在orm中处理

- 统一使用migrate_util.create_array_field来生成array字段

#### JSON类型:
mysql中的json类型不支持默认值, 需要在orm中处理

#### JSONB类型
mysql没有jsonb类型, 使用json类型代替, 同样不支持默认值, 需要在orm中处理

- 统一使用migrate_util.create_jsonb_field来生成jsonb字段

### 2. 索引

- 创建索引时, 显示指定名称, 不要使用默认名称
- 创建唯一约束时, 使用op.create_unique_index, 而不是op.create_unique_constraint
- 需要手动创建创建唯一索引, 而不是在sa.Column中指定unique=True
- 不支持带条件的索引, 应当尽量避免使用

### 3. 修改表结构

- 修改字段时需要统一显式指定existing_type

### 4. 约束

- mysql中不同的约束drop时语法不同, 谨慎使用, 同时支持的约束类型和postgresql不同

### 5. 执行sql

- 避免使用复杂的语法, mysql可能不支持