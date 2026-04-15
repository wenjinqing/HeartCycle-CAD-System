# HeartCycle 部署指南

本文档详细说明如何在不同环境下部署HeartCycle冠心病风险预测系统。

## 目录

- [系统要求](#系统要求)
- [Docker部署（推荐）](#docker部署推荐)
- [手动部署](#手动部署)
- [生产环境配置](#生产环境配置)
- [性能优化](#性能优化)
- [安全加固](#安全加固)
- [监控和维护](#监控和维护)
- [故障排查](#故障排查)

## 系统要求

### 最低配置
- CPU: 2核
- 内存: 4GB
- 磁盘: 20GB
- 操作系统: Ubuntu 20.04+ / CentOS 7+ / Windows 10+

### 推荐配置
- CPU: 4核+
- 内存: 8GB+
- 磁盘: 50GB+ SSD
- 操作系统: Ubuntu 22.04 LTS

### 软件依赖
- Python 3.8+
- Node.js 14+
- MySQL 8.0+
- Docker 20.10+ (可选)
- Docker Compose 2.0+ (可选)
- Nginx 1.18+ (生产环境)

## Docker部署（推荐）

### 1. 安装Docker和Docker Compose

#### Ubuntu/Debian
```bash
# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker --version
docker-compose --version
```

#### Windows
下载并安装 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)

### 2. 克隆项目

```bash
git clone https://github.com/yourusername/heartcycle-cad-system.git
cd heartcycle-cad-system
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
nano .env
```

关键配置项：
```env
# 数据库配置
MYSQL_ROOT_PASSWORD=your_secure_password
MYSQL_DATABASE=heartcycle
MYSQL_USER=heartcycle
MYSQL_PASSWORD=your_db_password

# 后端配置
SECRET_KEY=your_secret_key_here
DATABASE_URL=mysql+pymysql://heartcycle:your_db_password@db:3306/heartcycle

# 前端配置
VUE_APP_API_URL=http://localhost:8000
```

### 4. 启动服务

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 5. 初始化数据库

```bash
# 进入后端容器
docker-compose exec backend bash

# 运行数据库迁移
alembic upgrade head

# 创建初始管理员账号（可选）
python scripts/create_admin.py

# 退出容器
exit
```

### 6. 访问系统

- 前端: http://localhost:8080
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

### 7. 停止服务

```bash
# 停止服务
docker-compose stop

# 停止并删除容器
docker-compose down

# 停止并删除容器和数据卷
docker-compose down -v
```

## 手动部署

### 1. 安装MySQL

#### Ubuntu/Debian
```bash
sudo apt update
sudo apt install mysql-server
sudo mysql_secure_installation
```

#### 创建数据库
```bash
sudo mysql -u root -p

CREATE DATABASE heartcycle CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'heartcycle'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON heartcycle.* TO 'heartcycle'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 2. 部署后端

```bash
# 进入后端目录
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
nano .env

# 运行数据库迁移
alembic upgrade head

# 启动后端服务（开发模式）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 或使用gunicorn（生产模式）
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 3. 部署前端

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 配置API地址
# 编辑 .env.production
echo "VUE_APP_API_URL=http://your-domain.com/api" > .env.production

# 构建生产版本
npm run build

# 构建产物在 dist/ 目录
```

### 4. 配置Nginx

```bash
# 安装Nginx
sudo apt install nginx

# 创建配置文件
sudo nano /etc/nginx/sites-available/heartcycle
```

Nginx配置示例：
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端
    location / {
        root /var/www/heartcycle/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 静态文件
    location /static {
        alias /var/www/heartcycle/backend/static;
    }
}
```

启用配置：
```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/heartcycle /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启Nginx
sudo systemctl restart nginx
```

### 5. 配置Systemd服务

创建后端服务：
```bash
sudo nano /etc/systemd/system/heartcycle-backend.service
```

服务配置：
```ini
[Unit]
Description=HeartCycle Backend Service
After=network.target mysql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/heartcycle/backend
Environment="PATH=/var/www/heartcycle/backend/venv/bin"
ExecStart=/var/www/heartcycle/backend/venv/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
# 重载systemd
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start heartcycle-backend

# 设置开机自启
sudo systemctl enable heartcycle-backend

# 查看状态
sudo systemctl status heartcycle-backend
```

## 生产环境配置

### 1. 环境变量配置

```env
# 应用配置
APP_NAME=HeartCycle
APP_VERSION=1.0.0
DEBUG=False
SECRET_KEY=your_very_long_and_random_secret_key

# 数据库配置
DATABASE_URL=mysql+pymysql://user:password@localhost:3306/heartcycle

# CORS配置
CORS_ORIGINS=["https://your-domain.com"]

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=/var/log/heartcycle/app.log

# 限流配置
RATE_LIMIT_ENABLED=True
IP_MAX_REQUESTS=200
USER_MAX_REQUESTS=1000

# 缓存配置
CACHE_ENABLED=True
CACHE_TTL=300
```

### 2. 数据库优化

```sql
-- 创建索引
CREATE INDEX idx_patient_no ON patients(patient_no);
CREATE INDEX idx_patient_doctor ON patients(doctor_id);
CREATE INDEX idx_prediction_patient ON predictions(patient_id);
CREATE INDEX idx_prediction_created ON predictions(created_at);

-- 配置连接池
SET GLOBAL max_connections = 200;
SET GLOBAL wait_timeout = 28800;
```

### 3. 配置SSL证书（HTTPS）

使用Let's Encrypt免费证书：
```bash
# 安装certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo certbot renew --dry-run
```

Nginx HTTPS配置：
```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # ... 其他配置
}

# HTTP重定向到HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

## 性能优化

### 1. 后端优化

#### 启用缓存
```python
# 在需要缓存的函数上添加装饰器
from app.services.cache_service import cached

@cached(prefix="patient", ttl=300)
async def get_patient(patient_id: int):
    return await patient_service.get_patient(patient_id)
```

#### 数据库连接池
```python
# app/core/config.py
SQLALCHEMY_POOL_SIZE = 20
SQLALCHEMY_MAX_OVERFLOW = 40
SQLALCHEMY_POOL_TIMEOUT = 30
```

#### 异步任务队列
```python
# 使用任务队列处理耗时操作
from app.services.task_queue import task_queue

task_id = task_queue.submit(
    func=generate_batch_report,
    args=(predictions,),
    description="生成批量报告"
)
```

### 2. 前端优化

#### 启用Gzip压缩
```nginx
# Nginx配置
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css text/xml text/javascript application/javascript application/json;
```

#### 配置CDN
```javascript
// vue.config.js
module.exports = {
  publicPath: process.env.NODE_ENV === 'production'
    ? 'https://cdn.your-domain.com/'
    : '/'
}
```

### 3. 数据库优化

```sql
-- 定期优化表
OPTIMIZE TABLE patients;
OPTIMIZE TABLE predictions;

-- 分析表
ANALYZE TABLE patients;
ANALYZE TABLE predictions;

-- 清理日志
PURGE BINARY LOGS BEFORE DATE_SUB(NOW(), INTERVAL 7 DAY);
```

## 安全加固

### 1. 防火墙配置

```bash
# 安装ufw
sudo apt install ufw

# 允许SSH
sudo ufw allow 22/tcp

# 允许HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 启用防火墙
sudo ufw enable

# 查看状态
sudo ufw status
```

### 2. 限制数据库访问

```sql
-- 只允许本地访问
REVOKE ALL PRIVILEGES ON *.* FROM 'heartcycle'@'%';
GRANT ALL PRIVILEGES ON heartcycle.* TO 'heartcycle'@'localhost';
FLUSH PRIVILEGES;
```

### 3. 定期更新

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 更新Python依赖
pip install --upgrade -r requirements.txt

# 更新Node依赖
npm update
```

### 4. 备份策略

```bash
# 创建备份脚本
sudo nano /usr/local/bin/backup-heartcycle.sh
```

备份脚本：
```bash
#!/bin/bash
BACKUP_DIR="/backup/heartcycle"
DATE=$(date +%Y%m%d_%H%M%S)

# 备份数据库
mysqldump -u heartcycle -p heartcycle > $BACKUP_DIR/db_$DATE.sql

# 备份上传的文件
tar -czf $BACKUP_DIR/files_$DATE.tar.gz /var/www/heartcycle/backend/uploads

# 删除7天前的备份
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

设置定时任务：
```bash
# 编辑crontab
crontab -e

# 每天凌晨2点备份
0 2 * * * /usr/local/bin/backup-heartcycle.sh
```

## 监控和维护

### 1. 日志管理

```bash
# 查看后端日志
tail -f /var/log/heartcycle/app.log

# 查看Nginx日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# 查看系统日志
journalctl -u heartcycle-backend -f
```

### 2. 性能监控

访问系统监控页面：
- http://your-domain.com/system-monitor

或使用API：
```bash
# 获取系统状态
curl http://localhost:8000/api/v1/monitor/status

# 获取告警信息
curl http://localhost:8000/api/v1/monitor/alerts
```

### 3. 健康检查

```bash
# 检查后端健康状态
curl http://localhost:8000/health

# 检查数据库连接
mysql -u heartcycle -p -e "SELECT 1"

# 检查Nginx状态
sudo systemctl status nginx
```

## 故障排查

### 1. 后端无法启动

**问题**: 后端服务启动失败

**排查步骤**:
```bash
# 查看日志
journalctl -u heartcycle-backend -n 50

# 检查端口占用
sudo lsof -i :8000

# 检查数据库连接
mysql -u heartcycle -p -e "SELECT 1"

# 检查Python环境
source venv/bin/activate
python -c "import app.main"
```

### 2. 数据库连接失败

**问题**: 无法连接到MySQL数据库

**排查步骤**:
```bash
# 检查MySQL服务
sudo systemctl status mysql

# 检查连接
mysql -u heartcycle -p

# 检查权限
mysql -u root -p -e "SHOW GRANTS FOR 'heartcycle'@'localhost'"

# 检查防火墙
sudo ufw status
```

### 3. 前端无法访问后端

**问题**: 前端请求后端API失败

**排查步骤**:
```bash
# 检查Nginx配置
sudo nginx -t

# 检查Nginx日志
tail -f /var/log/nginx/error.log

# 检查CORS配置
# 编辑 backend/.env
CORS_ORIGINS=["http://your-domain.com"]

# 测试API
curl http://localhost:8000/api/v1/health
```

### 4. 内存不足

**问题**: 系统内存使用率过高

**解决方案**:
```bash
# 查看内存使用
free -h

# 查看进程内存
ps aux --sort=-%mem | head

# 重启服务
sudo systemctl restart heartcycle-backend

# 清理缓存
curl -X POST http://localhost:8000/api/v1/cache/clear
```

### 5. 磁盘空间不足

**问题**: 磁盘空间不足

**解决方案**:
```bash
# 查看磁盘使用
df -h

# 清理日志
sudo journalctl --vacuum-time=7d

# 清理旧备份
find /backup -mtime +30 -delete

# 清理Docker
docker system prune -a
```

## 更新升级

### 1. 更新代码

```bash
# 拉取最新代码
git pull origin main

# 更新后端依赖
cd backend
pip install -r requirements.txt

# 运行数据库迁移
alembic upgrade head

# 更新前端依赖
cd ../frontend
npm install

# 重新构建
npm run build

# 重启服务
sudo systemctl restart heartcycle-backend
sudo systemctl reload nginx
```

### 2. 回滚版本

```bash
# 查看提交历史
git log --oneline

# 回滚到指定版本
git checkout <commit-hash>

# 回滚数据库
alembic downgrade -1

# 重启服务
sudo systemctl restart heartcycle-backend
```

## 联系支持

如遇到问题，请：
1. 查看日志文件
2. 参考本文档的故障排查部分
3. 提交Issue: https://github.com/yourusername/heartcycle-cad-system/issues
4. 发送邮件: support@your-domain.com

---

**最后更新**: 2026-02-10
