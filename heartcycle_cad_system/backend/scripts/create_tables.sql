-- MySQL数据库表创建脚本
-- 用于创建heartcycle_cad系统所需的表

USE heartcycle_cad;

-- 创建训练任务表
CREATE TABLE IF NOT EXISTS training_tasks (
    task_id VARCHAR(64) PRIMARY KEY COMMENT '任务ID',
    status VARCHAR(20) NOT NULL DEFAULT 'running' COMMENT '任务状态: running/completed/failed',
    progress FLOAT DEFAULT 0.0 COMMENT '进度 (0.0-1.0)',
    message TEXT COMMENT '状态消息',
    current_file VARCHAR(255) COMMENT '当前处理的文件',
    total_files INT DEFAULT 0 COMMENT '总文件数',
    processed_files INT DEFAULT 0 COMMENT '已处理文件数',
    result TEXT COMMENT '训练结果（JSON格式）',
    error TEXT COMMENT '错误信息',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL COMMENT '更新时间',
    expires_at TIMESTAMP COMMENT '过期时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='训练任务表';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_status ON training_tasks(status);
CREATE INDEX IF NOT EXISTS idx_created_at ON training_tasks(created_at);
CREATE INDEX IF NOT EXISTS idx_expires_at ON training_tasks(expires_at);

-- 查看表结构
SHOW CREATE TABLE training_tasks;

-- 查看表信息
DESCRIBE training_tasks;

