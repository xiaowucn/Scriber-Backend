### 1.开启审核功能时,需要设置的配置项
##### 1.1 feature.inspect_modules
 - 打开以启用前端相关模块
##### 1.2 feature.rule_need_review
 - 根据新建审核规则时是否需要复核,决定是否开启
##### 1.3 inspector.package_name
 - 后端审核模块所在的包
##### 1.4 inspector.audit_molds
 - 允许进行审核的mold,不配置时将允许所有mold
##### 1.5 data_flow.post_pipe_after_preset
 - 打开以在预测完之后执行后处理
##### 1.6 data_flow.gen_file_answer
 - 打开以生成文件级答案供审核用
##### 1.7 feature.additional_permissions
 - 审核需要的相关权限,一般是customer_rule_participate & inspect
##### 1.8 web.plugins.inspector web.plugins.cgs
 - 审核相关的接口

### 2.关键入口函数
 - inspect_rule_pipe()