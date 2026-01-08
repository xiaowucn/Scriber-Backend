# iframe 安全配置指南

## 当前配置问题

当前的 Content-Security-Policy 配置对 iframe 使用有以下限制：

```nginx
Content-Security-Policy "... frame-ancestors 'self'; child-src 'self'; ..."
```

- `frame-ancestors 'self'`: 只允许同源页面嵌入本服务
- `child-src 'self'`: 本服务只能嵌入同源内容

## 配置方案

### 方案 1: 允许特定域名嵌入本服务

如果需要允许特定的合作伙伴网站嵌入本服务：

```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; media-src 'self'; object-src 'none'; child-src 'self'; frame-ancestors 'self' https://partner1.com https://partner2.com; base-uri 'self'; form-action 'self';" always;
```

**适用场景**: 
- B2B 集成
- 合作伙伴嵌入
- 白名单模式

### 方案 2: 允许本服务嵌入第三方内容

如果本服务需要嵌入第三方 iframe（如地图、视频等）：

```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; media-src 'self'; object-src 'none'; child-src 'self' https://maps.google.com https://www.youtube.com https://player.vimeo.com; frame-ancestors 'self'; base-uri 'self'; form-action 'self';" always;
```

**适用场景**:
- 嵌入地图服务
- 嵌入视频播放器
- 嵌入第三方组件

### 方案 3: 双向 iframe 支持

如果既需要被嵌入，又需要嵌入第三方内容：

```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; media-src 'self'; object-src 'none'; child-src 'self' https://maps.google.com https://www.youtube.com; frame-ancestors 'self' https://partner1.com https://partner2.com; base-uri 'self'; form-action 'self';" always;
```

### 方案 4: 开发/测试环境配置

对于开发或测试环境，可以使用更宽松的配置：

```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; media-src 'self'; object-src 'none'; child-src 'self' *; frame-ancestors 'self' *; base-uri 'self'; form-action 'self';" always;
```

**⚠️ 警告**: 此配置安全性较低，仅适用于开发环境。

### 方案 5: 完全移除 frame 限制（不推荐）

```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; media-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self';" always;
```

**⚠️ 高风险**: 移除 `frame-ancestors` 和 `child-src` 限制，容易受到点击劫持攻击。

## 安全考虑

### 点击劫持风险
- 移除 `frame-ancestors` 限制会增加点击劫持攻击风险
- 建议只允许信任的域名嵌入

### 内容注入风险
- 允许嵌入第三方 iframe 可能引入恶意内容
- 建议只允许知名、可信的第三方服务

### 最佳实践
1. **最小权限原则**: 只允许必要的域名
2. **定期审查**: 定期检查允许的域名列表
3. **监控日志**: 监控 CSP 违规报告
4. **分环境配置**: 生产环境使用严格配置

## 实施建议

### 1. 确定需求
- 明确哪些域名需要嵌入本服务
- 明确本服务需要嵌入哪些第三方内容

### 2. 渐进式部署
- 先在测试环境验证配置
- 使用 `Content-Security-Policy-Report-Only` 头进行测试
- 监控违规报告，调整配置

### 3. 配置示例

对于常见的第三方服务：

```nginx
# 地图服务
child-src 'self' https://maps.google.com https://maps.googleapis.com

# 视频服务  
child-src 'self' https://www.youtube.com https://player.vimeo.com

# 社交媒体
child-src 'self' https://www.facebook.com https://platform.twitter.com

# 支付服务
child-src 'self' https://js.stripe.com https://checkout.paypal.com
```

## 测试方法

### 浏览器测试
1. 打开浏览器开发者工具
2. 查看 Console 中的 CSP 错误
3. 检查 Network 面板中被阻止的请求

### 在线工具
- [CSP Evaluator](https://csp-evaluator.withgoogle.com/)
- [CSP Validator](https://cspvalidator.org/)

### 命令行测试
```bash
curl -I https://your-domain.com | grep -i content-security-policy
```
