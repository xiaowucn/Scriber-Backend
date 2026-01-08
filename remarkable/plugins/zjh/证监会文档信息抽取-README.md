### 0 证监会文档信息抽取
- 标注人员在文档上按照schema标注好答案后,系统读取标注答案并按照`导出schema`调整数据结构及格式,生成json格式的结果
- 甲方通过调scriber的接口来将数据下载到本地并入库
- 与其他环境的区别在于,证监会环境没有训练模型及预测的过程,是全量人工标注的
- 标注等通用流程与其他环境是共用的一套代码

### 1 主要工作内容
- 证监会网站上有新披露的招股说明书时，人工上传到`Scriber(金融文本处理系统)`的对应项目下
- 上传成功后系统自动调用pdfinsight的web服务跑文档解析，Scriber收到解析完成的回调后将收到的pdfinsight入库并更新status为`解析完成`
- 文档状态更新为解析完成时，标注人员可以开始标注
- 系统支持多人标注，多份标注结果会进行合并(取标注时间最晚的)，并展示在`合并的答案`
- 标注完成后，会生成一份`导出的答案`(耗时10~20s)，此为输出格式
- `导出的答案`支持在页面上修改，为防止修改后的条目在重新生成导出的答案时被覆盖，会在该答案上加一个`manual-tag`，此时该答案所属的一级科目将不会被覆盖
- 也可以在页面上主动点击`采用答案`按钮，以保护某块答案，或者点击`不采用答案`来取消保护
- `inv op.clear-manual-tag`命令可以批量`查看`or`清除`上述`manual-tag`

### 2 代码
- Scriber-Backend:zjh
- 部署服务器:c4
- 配置文件: config-docker-zjh.yml
- 项目地址: http://bj.cheftin.com:44014
- 在c4:/data/zjh_scriber/Scriber-Backend同步了一份项目代码,方便执行一些命令,默认使用config-test.yml

### 3 关键入口函数
- IpoAnswerFormatter.formatter(): 从标注结果中读取答案,生成`标注schema的答案`
    - schema中每个一级字段会有一个对应的handler函数来处理(部分格式较简单的是通用的handler)
    - 对读取到的answer会有一些格式化处理, 针对`日期` `金额` `单位` `百分数`等有专门的处理
- IPOProExPredictor.predict_answer(): 将`标注schema的答案`转换为`导出schema的答案`(即`导出的答案`)
    - 依据配置文件中的web.answer_convert,
- set_convert_answer: 重置`导出的答案`
    - 在question.set_answer()中被调用
    - 如果当前文档已有`导出的答案`,则会将新旧答案进行合并,参照上面有关`manual-tag`的说明
- dump_zjh_json_answer: 将`导出的答案`写入json文件
    - 会调用gen_json_data()对答案的格式&顺序做出一些调整,并去掉提取不完整的条目
    - 会调用ipo_data_json_style()对答案内容做出一些调整,主要是一些与我们schema不一致的地方

### 4 触发
- 以下两种情况会触发question.set_answer(),会重新生成`导出的答案`
    - 修改并保存了标注:POST @route(r'/question/(?P<question_id>\d+)/answer')
    - pdfinsight回调: POST @plugin.route(r'/file/(\d+)/pdfinsight')

### 5 常见错误
#### 5.1 无导出答案
- pdfinsight没有回调
- 标注有误
- 代码有bug
- pdfinsight解析有错误导致代码报错

#### 5.2 一般排查步骤:
- pdfinsight还没有回调时,页面上预处理会显示为`未完成`,一般在文档上传后15min左右pdfinsight能跑完,时间太久时可找文攀确认有无报错或手动重跑
- 如果预处理已`完成`,那应该是在提取答案时有报错,可inv sync.file <fid> 将文档同步到本地, debug入口 set_convert_answer()

#### 5.3 某块数据未导出或导出答案与文档不符
- 使用`inv sync.file`命令同步文档到本地, debug查看相关提取过程, 可能生成`导出的答案`时报错
- 定位了报错所属的一级节点后,debug时可将其他节点跳过以加快速度
- 修复代码后,重跑数据后生成的导出答案如果没有更新,可能是由于该一级字段下某个答案上有`manual-tag`标记,该标记是保证在页面上做的修改不因重跑被覆盖
- 如果确实需要覆盖有manual标记保护的答案,可以使用`inv op.clear-manual-tag`查看并去除标记

#### 5.4 更新线上数据
- 本地解决完问题后,可用set_answers.sh脚本 or `inv op.set-convert-answer`重新生成答案[会生成日志]
- 用法 `./set_answers.sh <fid> 0 重跑fid`
- 用法 `./set_answers.sh 0 <file_path> 重跑文件中的多个fid`

#### 5.5 字段超长
- 更新 mysql_schema.sql 和 enlarge_column.sql,
- 将enlarge_column.sql发给`证通`,通知他们更新数据库结构


### 6 结果检查及推送
#### 6.1 检查
- field_checker.py 中的check_fields()定义了针对各字段的检查方法,可帮助排查错误
#### 6.2 推送流程
- 将复核后的答案导出json-->将数据插入mysql-->通知`证通`同步数据
- `证通`会使用sync_output.py脚本文件将数据同步到他们本地
#### 6.3 推送步骤
- 1.将需要导出的file_id写在文件里[例如 /data/zjh_scriber/Scriber-Backend/in_phase_6_20200120]
    - `inv op.dump-file-ids -s <start_id> -e <end_id> --export-file=<export_file_name>`
- 2.用脚本json_dump.sh or `inv op.dump-zjh-json-answer`来导出json文件[会生成日志] 导出的json文件在/data/zjh_scriber/outputs
    - bash /data/zjh_scriber/Scriber-Backend/json_dump.sh /data/zjh_scriber/Scriber-Backend/in_phase_9_20200306
    - inv op.dump-zjh-json-answer  -s <start_id> -e <end_id>  /data/zjh_scriber/outputs/outputs_in_phase_9_20200306
- 3.将数据导入客户测试环境mysql
    - 确认当前ENV为`test`  `export ENV=test`
    - 修改config-test.yml文件中的ipo.ipo_results_dir
    - 执行`inv op.insert-ipo-tables`
- 4.通知`证通`，到确认信息和更新生产环境的请求后,再导入生产环境
    - 确认当前ENV为`prod`  `export ENV=prod`
    - 修改config-prod.yml文件中的ipo.ipo_results_dir
    - 执行`inv op.insert-ipo-tables`

PS:

- 用mysql_schema.sql创建database,字符集用utf8mb4。还需要执行`additional_table.sql`
- 在服务器上操作前,可将json文件先同步到本地,先在本地导入mysql,并检测其是否有错误
- 导入脚本`inv op.insert-ipo-tables`,导入完成后会输出统计信息,包括文档及各字段的数量;需要覆盖旧数据时加`--overwrite`
- mysql数据库配置信息如下：

|环境|ENV|mysql port|
|---- |---- |---- |
|测试环境|test|43307|
|生产环境|prod|43306|


### 7 三大主表科目名处理
- 三大主表的科目名需要转成用户指定的名称,详见output_fields_info.py
- 在提取主表的答案时会用customer_attribute()会尝试对科目名进行处理,无法处理的会打一条log: ```{value} does not exist in knowledge```
- 可将日志同步到本地, 使用analyze_log.py里的check_knowledge来生成一个excel文件,再逐条核对
- 如果做了相关修改,需要跑一下pre_precess.py里的check_main_table_output_fields,必须要能通过该检查
- pass_subjects:根据历史数据总结的一些不需要提取的科目,或者由于名称不完整无法提取的科目
- 但随着clean_field_name函数的修改,可能会修复一些不完整的科目名使之能够被提取,此时可能需要更正pass_subjects,常见于check_main_table_output_fields未通过并打出包含```should be convert to```的log.
