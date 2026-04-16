# HeartCycle API 文档

本文档详细说明HeartCycle系统的所有API接口。

## 基本信息

- **Base URL**: `http://localhost:8000/api/v1`
- **认证方式**: JWT Bearer Token
- **内容类型**: `application/json`
- **字符编码**: UTF-8

## 认证

### 获取Token

所有需要认证的接口都需要在请求头中携带JWT Token：

```http
Authorization: Bearer <your_token_here>
```

## API端点总览

### 认证与用户（基础 + 扩展）

**基础（登录态前/后）：**
- `POST /auth/register` - 用户注册
- `POST /auth/login` - 用户登录
- `POST /auth/logout` - 用户登出
- `POST /auth/refresh` - 刷新 Token
- `GET /auth/me` - 获取当前用户信息

**当前用户资料与密码：**
- `PUT /auth/me` - 更新当前用户资料
- `POST /auth/change-password` - 修改密码

**管理员（需 admin）：**
- `GET /auth/users` - 用户列表
- `PUT /auth/users/{user_id}/deactivate` - 禁用用户
- `PUT /auth/users/{user_id}/activate` - 启用用户
- `POST /auth/users/{user_id}/reset-password` - 重置用户密码
- `GET /auth/audit-logs` - 审计日志

> 与前端 **个人中心 `/profile`**、**用户管理 `/admin/users`**、**审计 `/admin/audit-logs`** 对应；完整请求体见 Swagger `/docs`。

### 患者管理 (9个接口)
- `POST /patients` - 创建患者
- `GET /patients` - 获取患者列表
- `GET /patients/{id}` - 获取患者详情
- `PUT /patients/{id}` - 更新患者信息
- `DELETE /patients/{id}` - 删除患者
- `GET /patients/{id}/predictions` - 获取患者预测记录
- `GET /patients/{id}/statistics` - 获取患者统计信息
- `GET /patients/follow-up/list` - 获取随访列表
- `PUT /patients/predictions/{id}/notes` - 更新预测备注

### 报告生成 (5个接口)
- `POST /reports/prediction` - 生成预测报告
- `POST /reports/batch` - 生成批量报告
- `GET /reports/download/{filename}` - 下载报告
- `GET /reports/list` - 列出所有报告
- `DELETE /reports/{filename}` - 删除报告

### 模型版本管理 (11个接口)
- `POST /model-versions` - 创建模型版本
- `GET /model-versions` - 列出模型版本
- `GET /model-versions/{version_id}` - 获取版本详情
- `PUT /model-versions/{version_id}` - 更新版本
- `DELETE /model-versions/{version_id}` - 删除版本
- `POST /model-versions/compare` - 对比版本
- `GET /model-versions/{model_name}/active` - 获取激活版本
- `GET /model-versions/{model_name}/production` - 获取生产版本
- `POST /model-versions/{model_name}/rollback` - 回滚版本
- `GET /model-versions/{model_name}/history` - 获取版本历史
- `GET /model-versions/{model_name}/statistics` - 获取模型统计

### 系统监控 (9个接口)
- `GET /monitor/status` - 获取系统状态
- `GET /monitor/cpu` - 获取CPU信息
- `GET /monitor/memory` - 获取内存信息
- `GET /monitor/disk` - 获取磁盘信息
- `GET /monitor/network` - 获取网络信息
- `GET /monitor/process` - 获取进程信息
- `GET /monitor/history` - 获取历史监控数据
- `GET /monitor/alerts` - 获取系统告警
- `GET /monitor/uptime` - 获取运行时间

### 限流管理 (5个接口)
- `POST /rate-limit/blacklist/add` - 添加黑名单
- `POST /rate-limit/blacklist/remove` - 移除黑名单
- `GET /rate-limit/blacklist` - 获取黑名单
- `POST /rate-limit/stats` - 获取限流统计
- `POST /rate-limit/clear` - 清除限流统计

### 缓存管理 (4个接口)
- `GET /cache/stats` - 获取缓存统计
- `POST /cache/clear` - 清空缓存
- `POST /cache/delete` - 删除指定缓存
- `POST /cache/cleanup` - 清理过期缓存

### 任务队列 (5个接口)
- `GET /tasks/list` - 列出任务
- `GET /tasks/stats` - 获取队列统计
- `GET /tasks/{task_id}` - 获取任务状态
- `POST /tasks/{task_id}/cancel` - 取消任务
- `POST /tasks/cleanup` - 清理已完成任务

### 特征 / 特征选择 / 数据分析（概要）

后端在 `/api/v1` 下还注册有 **`features`**、**`selection`**、**`analysis`** 等路由（用于特征提取、筛选与统计分析）。路径与字段以 **Swagger `/docs`** 为准；本文档未逐条展开时可从 OpenAPI 导出或在线调试。

### WebSocket

- `WS /ws?token=<access_token>` — 与 REST **不同前缀**，用于任务进度订阅等（见 `backend/app/api/v1/websocket.py`）。

---

## 详细接口说明

## 1. 认证相关

### 1.1 用户注册

**接口**: `POST /api/v1/auth/register`

**请求体**:
```json
{
  "username": "string",
  "password": "string",
  "email": "string",
  "full_name": "string",
  "role": "doctor"
}
```

**响应**:
```json
{
  "success": true,
  "message": "用户注册成功",
  "data": {
    "id": 1,
    "username": "doctor1",
    "email": "doctor1@example.com",
    "full_name": "张医生",
    "role": "doctor"
  }
}
```

### 1.2 用户登录

**接口**: `POST /api/v1/auth/login`

**请求体**:
```json
{
  "username": "doctor1",
  "password": "password123"
}
```

**响应**:
```json
{
  "success": true,
  "message": "登录成功",
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "username": "doctor1",
      "role": "doctor"
    }
  }
}
```

---

## 2. 患者管理

### 2.1 创建患者

**接口**: `POST /api/v1/patients`

**权限**: 医生、管理员

**请求体**:
```json
{
  "name": "张三",
  "gender": "male",
  "age": 55,
  "phone": "13800138000",
  "id_card": "110101196501010001",
  "address": "北京市朝阳区",
  "medical_history": "高血压10年",
  "allergies": "青霉素过敏"
}
```

**响应**:
```json
{
  "success": true,
  "message": "患者创建成功",
  "data": {
    "id": 1,
    "patient_no": "P202602100001",
    "name": "张三",
    "gender": "male",
    "age": 55,
    "phone": "13800138000",
    "doctor_id": 1,
    "created_at": "2026-02-10T10:00:00"
  }
}
```

### 2.2 获取患者列表

**接口**: `GET /api/v1/patients`

**权限**: 登录用户

**查询参数**:
- `search` (string, optional): 搜索关键词（姓名、患者编号、手机号）
- `skip` (integer, optional): 跳过数量，默认0
- `limit` (integer, optional): 返回数量，默认20

**响应**:
```json
{
  "success": true,
  "message": "找到 2 个患者",
  "data": {
    "patients": [
      {
        "id": 1,
        "patient_no": "P202602100001",
        "name": "张三",
        "gender": "male",
        "age": 55,
        "phone": "13800138000",
        "doctor_id": 1,
        "doctor_name": "李医生",
        "created_at": "2026-02-10T10:00:00"
      }
    ],
    "total": 2,
    "skip": 0,
    "limit": 20
  }
}
```

### 2.3 获取患者统计信息

**接口**: `GET /api/v1/patients/{id}/statistics`

**权限**: 登录用户

**响应**:
```json
{
  "success": true,
  "message": "获取成功",
  "data": {
    "patient_info": {
      "patient_no": "P202602100001",
      "name": "张三",
      "age": 55,
      "gender": "male"
    },
    "prediction_statistics": {
      "total_predictions": 15,
      "high_risk_count": 3,
      "medium_risk_count": 7,
      "low_risk_count": 5
    },
    "latest_prediction": {
      "id": 45,
      "prediction": 1,
      "probability": "0.75",
      "risk_level": "high",
      "created_at": "2026-02-10T10:30:00"
    },
    "risk_trend": [
      {
        "date": "2026-02-01",
        "risk_level": "medium",
        "probability": "0.55"
      }
    ]
  }
}
```

---

## 3. 报告生成

### 3.1 生成预测报告

**接口**: `POST /api/v1/reports/prediction`

**权限**: 登录用户

**请求体**:
```json
{
  "patient_id": 1,
  "prediction_id": 45,
  "include_statistics": true
}
```

**响应**:
```json
{
  "success": true,
  "message": "报告生成成功",
  "data": {
    "filename": "report_P202602100001_20260210_103000.pdf",
    "download_url": "/api/v1/reports/download/report_P202602100001_20260210_103000.pdf"
  }
}
```

### 3.2 下载报告

**接口**: `GET /api/v1/reports/download/{filename}`

**权限**: 登录用户

**响应**: PDF文件流

---

## 4. 模型版本管理

### 4.1 创建模型版本

**接口**: `POST /api/v1/model-versions`

**权限**: 研究员、管理员

**请求**: multipart/form-data

**参数**:
- `file` (file): 模型文件（.pkl, .h5, .joblib）
- `model_name` (string): 模型名称
- `version` (string): 版本号
- `model_type` (string): 模型类型（lr, rf, xgb, cnn, lstm）
- `description` (string, optional): 描述
- `accuracy` (float, optional): 准确率
- `precision` (float, optional): 精确率
- `recall` (float, optional): 召回率
- `f1_score` (float, optional): F1分数
- `auc` (float, optional): AUC

**响应**:
```json
{
  "success": true,
  "message": "模型版本创建成功",
  "data": {
    "id": 1,
    "model_name": "cad_predictor",
    "version": "1.0.0",
    "model_type": "xgb"
  }
}
```

### 4.2 列出模型版本

**接口**: `GET /api/v1/model-versions`

**权限**: 登录用户

**查询参数**:
- `model_name` (string, optional): 模型名称筛选
- `model_type` (string, optional): 模型类型筛选
- `is_active` (boolean, optional): 是否激活筛选
- `is_production` (boolean, optional): 是否生产版本筛选
- `skip` (integer, optional): 跳过数量
- `limit` (integer, optional): 返回数量

**响应**:
```json
{
  "success": true,
  "message": "找到 5 个模型版本",
  "data": {
    "versions": [
      {
        "id": 1,
        "model_name": "cad_predictor",
        "version": "1.0.0",
        "model_type": "xgb",
        "accuracy": 0.92,
        "auc": 0.95,
        "is_active": true,
        "is_production": false,
        "created_at": "2026-02-10T10:00:00"
      }
    ],
    "total": 5
  }
}
```

### 4.3 对比模型版本

**接口**: `POST /api/v1/model-versions/compare`

**权限**: 登录用户

**请求体**:
```json
{
  "version_ids": [1, 2, 3]
}
```

**响应**:
```json
{
  "success": true,
  "message": "对比了 3 个版本",
  "data": {
    "versions": [
      {
        "id": 1,
        "model_name": "cad_predictor",
        "version": "1.0.0",
        "accuracy": 0.92,
        "auc": 0.95
      }
    ],
    "metrics_comparison": {
      "accuracy": {
        "max": 0.92,
        "min": 0.88,
        "avg": 0.90
      },
      "auc": {
        "max": 0.95,
        "min": 0.91,
        "avg": 0.93
      }
    },
    "best_version": {
      "id": 1,
      "model_name": "cad_predictor",
      "version": "1.0.0",
      "auc": 0.95
    }
  }
}
```

---

## 5. 系统监控

### 5.1 获取系统状态

**接口**: `GET /api/v1/monitor/status`

**权限**: 管理员

**响应**:
```json
{
  "success": true,
  "message": "获取成功",
  "data": {
    "status": "healthy",
    "warnings": [],
    "cpu": {
      "percent": 45.2,
      "count": 4,
      "frequency": {
        "current": 2400.0,
        "min": 800.0,
        "max": 3600.0
      }
    },
    "memory": {
      "total_gb": 16.0,
      "used_gb": 8.5,
      "available_gb": 7.5,
      "percent": 53.1
    },
    "disk": {
      "total_gb": 500.0,
      "used_gb": 250.0,
      "free_gb": 250.0,
      "percent": 50.0
    },
    "network": {
      "bytes_sent_mb": 1024.5,
      "bytes_recv_mb": 2048.3,
      "packets_sent": 50000,
      "packets_recv": 60000
    },
    "process": {
      "pid": 12345,
      "cpu_percent": 5.2,
      "memory_mb": 512.0,
      "num_threads": 10,
      "status": "running"
    },
    "uptime": {
      "seconds": 86400,
      "formatted": "1天 0小时 0分钟 0秒",
      "start_time": "2026-02-09T10:00:00"
    },
    "timestamp": "2026-02-10T10:00:00"
  }
}
```

### 5.2 获取系统告警

**接口**: `GET /api/v1/monitor/alerts`

**权限**: 管理员

**响应**:
```json
{
  "success": true,
  "message": "找到 2 个告警",
  "data": {
    "alerts": [
      {
        "level": "warning",
        "type": "memory",
        "message": "内存使用率较高: 85.5%",
        "value": 85.5,
        "threshold": 85,
        "timestamp": "2026-02-10T10:00:00"
      }
    ],
    "count": 2
  }
}
```

---

## 6. 错误响应

所有API在发生错误时返回统一格式：

```json
{
  "success": false,
  "error_code": "ErrorCode",
  "detail": "错误详细信息",
  "timestamp": "2026-02-10T10:00:00"
}
```

### 常见错误码

| 状态码 | 错误码 | 说明 |
|--------|--------|------|
| 400 | ValidationError | 请求参数验证失败 |
| 401 | Unauthorized | 未认证或Token无效 |
| 403 | PermissionDenied | 权限不足 |
| 404 | NotFound | 资源不存在 |
| 429 | RateLimitExceeded | 请求频率超限 |
| 500 | InternalServerError | 服务器内部错误 |

---

## 7. 限流说明

系统实施了API限流机制：

- **IP限流**: 每分钟200个请求
- **用户限流**: 每小时1000个请求

超限时返回429状态码，响应头包含：
- `X-RateLimit-Limit-IP`: IP限流上限
- `X-RateLimit-Remaining-IP`: IP剩余请求数
- `X-RateLimit-Limit-User`: 用户限流上限
- `X-RateLimit-Remaining-User`: 用户剩余请求数
- `Retry-After`: 建议重试时间（秒）

---

## 8. 分页说明

支持分页的接口使用统一的查询参数：

- `skip`: 跳过的记录数（默认0）
- `limit`: 返回的记录数（默认20，最大100）

响应包含分页信息：
```json
{
  "data": {
    "items": [...],
    "total": 100,
    "skip": 0,
    "limit": 20
  }
}
```

---

## 9. 在线API文档

启动后端服务后，可以访问交互式API文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

**最后更新**: 2026-02-10
