# 🚀 启动服务指南

## 快速启动

### 方式1: 使用启动脚本（推荐）

#### Windows
```bash
# 双击运行或命令行执行
scripts\start_backend.bat
```

#### Linux/Mac
```bash
python scripts/start_backend.py
```

### 方式2: 直接启动
```bash
cd heartcycle_cad_system/backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## ✨ 新功能：自动端口检测

启动脚本现在会自动检测端口占用情况：

1. **优先使用端口 8000**
2. **如果8000被占用，自动尝试 8001-8009**
3. **显示实际使用的端口**

### 示例输出

```
============================================================
HeartCycle 后端服务启动
============================================================

正在检查可用端口...
警告: 端口 8000 被占用，使用端口 8001 启动服务
启动后端服务在端口 8001...
API文档: http://localhost:8001/docs
健康检查: http://localhost:8001/health

INFO:     Will watch for changes in these directories: ['D:\\Graduate Work\\heartcycle_cad_system\\backend']
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

---

## 📋 启动后的访问地址

根据实际使用的端口，访问以下地址：

| 服务 | 地址 | 说明 |
|------|------|------|
| **API文档** | http://localhost:{port}/docs | Swagger交互式文档 |
| **ReDoc文档** | http://localhost:{port}/redoc | ReDoc风格文档 |
| **健康检查** | http://localhost:{port}/health | 系统健康状态 |
| **性能指标** | http://localhost:{port}/metrics | 性能监控数据 |
| **根路径** | http://localhost:{port}/ | API信息 |

**注意**: `{port}` 是实际使用的端口号（通常是8000，如果被占用则是8001-8009）

---

## 🔧 端口占用问题

### 如果所有端口都被占用

脚本会显示错误：
```
错误: 无法找到可用端口 (尝试了 8000-8009)
请手动停止占用端口的进程或使用其他端口范围
```

### 解决方法

#### 方法1: 查看并停止占用进程
```bash
# Windows
netstat -ano | findstr :8000
taskkill /F /PID <进程ID>

# Linux/Mac
lsof -i :8000
kill -9 <进程ID>
```

#### 方法2: 手动指定端口
```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload
```

---

## 🎯 验证服务启动

### 1. 检查健康状态
```bash
curl http://localhost:8000/health
```

**预期响应**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2026-02-04T10:00:00",
  "database": "connected",
  "disk": {...},
  "memory": {...}
}
```

### 2. 访问API文档
在浏览器打开: http://localhost:8000/docs

### 3. 测试API
```bash
# 获取模型列表
curl http://localhost:8000/api/v1/models

# 查看性能指标
curl http://localhost:8000/metrics
```

---

## 🛠️ 开发模式

启动脚本默认启用热重载（`--reload`），代码修改后会自动重启服务。

### 禁用热重载
如果需要禁用热重载，修改 `scripts/start_backend.py`:

```python
uvicorn.run(
    "app.main:app",
    host="0.0.0.0",
    port=port,
    reload=False,  # 改为 False
    log_level="info"
)
```

---

## 📝 常见问题

### Q1: 如何停止服务？
- 在终端按 `Ctrl+C`
- 或关闭命令行窗口

### Q2: 如何查看日志？
日志会输出到终端，同时保存在 `backend/logs/app.log`

### Q3: 如何修改默认端口范围？
编辑 `scripts/start_backend.py`:
```python
# 修改这一行
port = find_available_port(8000)  # 改为其他起始端口

# 或修改尝试范围
def find_available_port(start_port=8000, max_attempts=10):
    # max_attempts 控制尝试的端口数量
```

### Q4: 前端如何连接到不同端口？
修改前端配置文件 `frontend/.env`:
```
VUE_APP_API_BASE_URL=http://localhost:8001/api/v1
```

---

## 🔄 生产环境部署

生产环境建议使用固定端口和进程管理工具：

### 使用 Gunicorn (Linux)
```bash
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000
```

### 使用 Supervisor
```ini
[program:heartcycle]
command=/path/to/venv/bin/gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
directory=/path/to/heartcycle_cad_system/backend
autostart=true
autorestart=true
```

### 使用 systemd
```ini
[Unit]
Description=HeartCycle Backend Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/heartcycle_cad_system/backend
ExecStart=/path/to/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 📚 相关文档

- **部署指南**: [docs/DEPLOYMENT_GUIDE.md](../docs/DEPLOYMENT_GUIDE.md)
- **API文档**: [docs/API_DOCUMENTATION.md](../docs/API_DOCUMENTATION.md)
- **端口冲突解决**: [docs/PORT_CONFLICT_SOLUTION.md](../docs/PORT_CONFLICT_SOLUTION.md)

---

**更新日期**: 2026-02-04
**版本**: v2.0 (支持自动端口检测)
