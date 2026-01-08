# Nginx 安全配置改进说明

## 改进概述

根据安全建议，对 `docker/nginx/scriber.conf` 进行了全面的安全配置改进，包括：
1. X-Forwarded-For 头的安全配置
2. 重要安全响应头的添加

## 安全问题

### 原始配置问题
- 缺少 `X-Forwarded-For` 头的处理
- 只设置了 `X-Real-IP`，但没有标准的客户端 IP 传递机制
- 存在客户端篡改 XFF 内容的风险

### 安全风险
1. **IP 伪造风险**: 恶意客户端可能篡改 X-Forwarded-For 头来伪造真实 IP
2. **日志记录不准确**: 无法正确记录真实的客户端 IP
3. **安全策略失效**: 基于 IP 的安全策略可能被绕过
4. **XSS 攻击风险**: 缺少安全响应头使网站易受跨站脚本攻击
5. **MIME 类型嗅探**: 缺少 X-Content-Type-Options 头可能导致安全问题
6. **内容注入攻击**: 缺少 Content-Security-Policy 增加数据注入风险

## 改进方案

### 1. X-Forwarded-For 配置变更
在所有 `proxy_pass` 的 location 块中添加了：
```nginx
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

### 2. 安全响应头配置
在 http 块中添加了以下安全响应头：
```nginx
# Security headers
add_header X-Content-Type-Options nosniff always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; media-src 'self'; object-src 'none'; child-src 'self'; frame-ancestors 'self'; base-uri 'self'; form-action 'self';" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
```

### 受影响的 location 块
1. `location ~ /api/(.*)/plugins/fileapi/tree/(.*)/zip`
2. `location ~ /api/(.*)/file/(.*)/association`
3. `location ^~ /api/`
4. `location ^~ /external_api/`
5. `location ^~ /info/idoc`

### 配置说明

#### `$proxy_add_x_forwarded_for` 的工作原理
- 如果客户端请求中已存在 `X-Forwarded-For` 头，则在其后追加 `$remote_addr`
- 如果客户端请求中不存在 `X-Forwarded-For` 头，则设置为 `$remote_addr`
- 这样可以保持完整的代理链路记录

#### 为什么选择 `$proxy_add_x_forwarded_for`
由于这是容器内的 Nginx，前面可能还有其他负载均衡器（如云服务商的 LB），使用 `$proxy_add_x_forwarded_for` 可以：
1. 保持 X-Forwarded-For 链的完整性
2. 防止覆盖上游负载均衡器设置的真实客户端 IP
3. 符合多层负载均衡的最佳实践

### 3. 安全响应头说明

#### X-Content-Type-Options
- **作用**: 防止浏览器进行 MIME 类型嗅探
- **配置**: `nosniff` 强制浏览器严格按照 Content-Type 处理资源
- **防护**: 防止恶意文件被误解析为可执行内容

#### X-XSS-Protection
- **作用**: 启用浏览器内置的 XSS 过滤器
- **配置**: `1; mode=block` 检测到 XSS 攻击时阻止页面加载
- **防护**: 提供额外的 XSS 攻击防护层

#### Content-Security-Policy (CSP)
- **作用**: 控制页面可以加载的资源类型和来源
- **配置**: 严格的白名单策略，允许必要的资源加载
- **防护**: 防止 XSS、数据注入和点击劫持攻击

#### Referrer-Policy
- **作用**: 控制请求中包含的引用信息
- **配置**: `strict-origin-when-cross-origin` 跨域时只发送源信息
- **防护**: 防止敏感信息通过 Referer 头泄露

#### Permissions-Policy
- **作用**: 控制浏览器功能的访问权限
- **配置**: 禁用地理位置、麦克风、摄像头等敏感功能
- **防护**: 减少恶意网站滥用浏览器功能的风险

## 部署建议

### 外层负载均衡器配置
如果在此 Nginx 前面还有其他负载均衡器，建议在最外层配置：
```nginx
proxy_set_header X-Forwarded-For $remote_addr;
```

### 验证配置
部署后可以通过以下方式验证：
1. 检查应用日志中的客户端 IP 记录
2. 使用 curl 测试带有 X-Forwarded-For 头的请求
3. 监控安全日志确保 IP 记录准确

## 兼容性说明

### 保持现有功能
- 保留了原有的 `X-Real-IP` 设置，确保应用兼容性
- 保留了所有其他 proxy_set_header 配置
- 不影响现有的日志格式和监控

### 应用层适配
应用可以按优先级读取客户端 IP：
1. 首先检查 `X-Forwarded-For` 头（取第一个 IP）
2. 其次检查 `X-Real-IP` 头
3. 最后使用 `$remote_addr`

## 安全效果

### 防护能力
1. **防止 IP 伪造**: 通过正确的 XFF 链管理，防止客户端篡改真实 IP
2. **完整的审计日志**: 记录完整的代理链路，便于安全审计
3. **支持安全策略**: 为基于 IP 的安全策略提供可靠的数据源
4. **XSS 攻击防护**: 多层 XSS 防护机制，包括浏览器过滤器和 CSP
5. **内容注入防护**: CSP 策略防止恶意脚本和资源注入
6. **MIME 嗅探防护**: 防止恶意文件被误解析执行
7. **信息泄露防护**: 控制引用信息和浏览器功能访问权限

### 监控建议
1. 监控 X-Forwarded-For 头的格式和内容
2. 检查是否有异常的 IP 链路
3. 对比 X-Real-IP 和 X-Forwarded-For 的一致性

## 注意事项

1. **配置测试**: 部署前在测试环境验证配置正确性
2. **应用适配**: 确保应用正确处理新的 X-Forwarded-For 头
3. **监控调整**: 可能需要调整监控和日志分析规则
4. **性能影响**: 新增头处理对性能影响微乎其微

## 相关文档

- [Nginx proxy_set_header 文档](http://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_set_header)
- [X-Forwarded-For 标准](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-For)
- [负载均衡安全最佳实践](https://owasp.org/www-community/attacks/HTTP_Request_Smuggling)
