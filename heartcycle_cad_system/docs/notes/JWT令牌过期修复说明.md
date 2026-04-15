# JWT令牌过期问题修复说明

## 问题描述

用户在使用系统时遇到 `401: 无效的令牌: Signature has expired` 错误，无法访问需要认证的页面（如用户管理）。

## 原因分析

1. **令牌有效期太短**：原来的access_token有效期只有30分钟
2. **缺少自动刷新机制**：前端没有处理令牌过期的自动刷新逻辑

## 修复内容

### 1. 后端修改 - 延长令牌有效期

**文件：** `backend/app/services/auth_service.py`

```python
# 修改前
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # 30分钟
REFRESH_TOKEN_EXPIRE_DAYS = 7     # 7天

# 修改后
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8小时
REFRESH_TOKEN_EXPIRE_DAYS = 30     # 30天
```

**改进：**
- access_token有效期从30分钟延长到8小时
- refresh_token有效期从7天延长到30天
- 用户在正常工作时间内不会频繁遇到令牌过期

### 2. 前端修改 - 自动刷新令牌

**文件：** `frontend/src/services/api.js`

**新增功能：**
- 检测401错误和令牌过期消息
- 自动使用refresh_token刷新access_token
- 刷新成功后重试原请求
- 刷新失败则清除令牌并跳转到登录页

**流程：**
```
请求 → 401错误 → 检测令牌过期 → 使用refresh_token刷新
  ↓
刷新成功 → 保存新令牌 → 重试原请求 → 返回结果
  ↓
刷新失败 → 清除令牌 → 跳转登录页
```

## 使用说明

### 重启服务

**必须重启后端和前端才能生效！**

#### 1. 重启后端
```bash
# 停止后端（Ctrl+C）
cd "D:\Graduate Work\heartcycle_cad_system"
python scripts/start_backend.py
```

#### 2. 重启前端
```bash
# 停止前端（Ctrl+C）
cd frontend
npm run dev
```

### 重新登录

由于令牌配置已更改，需要重新登录：

1. 访问 http://localhost:5173
2. 如果自动跳转到登录页，输入账号密码登录
3. 登录后会获得新的8小时有效期令牌

### 测试验证

1. **登录系统**
2. **访问用户管理页面** (`/admin/users`)
3. **应该能正常访问**，不再出现401错误
4. **8小时内无需重新登录**

## 技术细节

### 令牌刷新逻辑

```javascript
// 检测到401令牌过期
if (error.response.status === 401 && errorMessage.includes('expired')) {
  // 使用refresh_token刷新
  const response = await axios.post('/auth/refresh', {
    refresh_token: refreshToken
  })

  // 保存新令牌
  localStorage.setItem('access_token', response.data.access_token)

  // 重试原请求
  return api(originalRequest)
}
```

### 安全考虑

- refresh_token存储在localStorage中
- 刷新失败会立即清除所有令牌
- 自动跳转到登录页，防止未授权访问
- 每次刷新都会生成新的refresh_token（滚动刷新）

## 常见问题

### Q1: 为什么还是提示令牌过期？
**A:** 需要重启后端和前端服务，并重新登录获取新令牌。

### Q2: 8小时后会怎样？
**A:** 8小时后access_token过期，系统会自动使用refresh_token刷新（30天有效期）。如果refresh_token也过期，则需要重新登录。

### Q3: 多个标签页会有问题吗？
**A:** 不会。所有标签页共享localStorage中的令牌，一个标签页刷新令牌后，其他标签页也会使用新令牌。

### Q4: 如何手动刷新令牌？
**A:** 系统会自动刷新，无需手动操作。如果需要手动刷新，可以重新登录。

## 相关文件

- `backend/app/services/auth_service.py` - JWT配置
- `frontend/src/services/api.js` - 令牌刷新逻辑
- `backend/app/api/v1/auth.py` - 认证API端点

## 更新日志

**日期：** 2026-03-06

**修改：**
1. ✅ 延长access_token有效期至8小时
2. ✅ 延长refresh_token有效期至30天
3. ✅ 添加��端自动令牌刷新机制
4. ✅ 改进401错误处理逻辑

---

**维护者：** Claude Sonnet 4.6
**项目：** HeartCycle 冠心病风险预测系统
