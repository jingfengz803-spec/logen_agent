"""
数据库表模型定义
包含用户、音色、任务、操作日志等表
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from database import db


# ==================== SQL 建表语句 ====================

CREATE_TABLES_SQL = """
-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '用户ID',
    user_id VARCHAR(64) UNIQUE NOT NULL COMMENT '用户唯一标识',
    username VARCHAR(50) UNIQUE NOT NULL COMMENT '用户名',
    password_hash VARCHAR(255) COMMENT '密码哈希（bcrypt）',
    api_key VARCHAR(128) UNIQUE NOT NULL COMMENT 'API密钥',
    role VARCHAR(20) DEFAULT 'user' COMMENT '角色 user/admin',
    status TINYINT DEFAULT 1 COMMENT '状态 1=正常 0=禁用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    INDEX idx_user_id (user_id),
    INDEX idx_username (username),
    INDEX idx_api_key (api_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 音色表
CREATE TABLE IF NOT EXISTS voices (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '音色ID',
    voice_id VARCHAR(128) UNIQUE NOT NULL COMMENT 'Dashscope音色ID',
    user_id BIGINT NOT NULL COMMENT '所属用户ID',
    prefix VARCHAR(50) NOT NULL COMMENT '音色前缀',
    model VARCHAR(50) NOT NULL COMMENT '模型名称',
    status VARCHAR(20) DEFAULT 'DEPLOYING' COMMENT '状态 DEPLOYING=审核中 OK=可用 UNDEPLOYED=审核不通过',
    target_model VARCHAR(50) COMMENT '目标模型',
    gmt_create DATETIME COMMENT 'Dashscope创建时间',
    gmt_modified DATETIME COMMENT 'Dashscope修改时间',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '本地记录创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '本地记录更新时间',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_voice_id (voice_id),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='音色表';

-- 任务表
CREATE TABLE IF NOT EXISTS tasks (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '任务ID',
    task_id VARCHAR(64) UNIQUE NOT NULL COMMENT '任务唯一标识',
    user_id BIGINT COMMENT '用户ID（可选，未登录用户为NULL）',
    task_type VARCHAR(50) NOT NULL COMMENT '任务类型 tts_speech/video_generate等',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态 pending/running/success/failed',
    progress INT DEFAULT 0 COMMENT '进度 0-100',
    result JSON COMMENT '任务结果',
    error TEXT COMMENT '错误信息',
    input_params JSON COMMENT '输入参数',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    started_at DATETIME COMMENT '开始时间',
    completed_at DATETIME COMMENT '完成时间',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_task_id (task_id),
    INDEX idx_user_id (user_id),
    INDEX idx_status (status),
    INDEX idx_task_type (task_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务表';

-- 操作日志表（数据溯源）
CREATE TABLE IF NOT EXISTS operation_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '日志ID',
    user_id BIGINT COMMENT '用户ID',
    operation VARCHAR(50) NOT NULL COMMENT '操作类型',
    resource_type VARCHAR(50) COMMENT '资源类型 user/voice/task等',
    resource_id VARCHAR(64) COMMENT '资源ID',
    details JSON COMMENT '操作详情',
    ip_address VARCHAR(50) COMMENT 'IP地址',
    user_agent VARCHAR(500) COMMENT '用户代理',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '操作时间',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_operation (operation),
    INDEX idx_resource (resource_type, resource_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='操作日志表';

-- 生成的资源表（用于后端审核和用户资源管理）
CREATE TABLE IF NOT EXISTS generated_resources (
    id BIGINT PRIMARY KEY AUTO_INCREMENT COMMENT '资源ID',
    user_id BIGINT NOT NULL COMMENT '用户ID',
    resource_type VARCHAR(20) NOT NULL COMMENT '资源类型 audio/video/image',
    resource_url VARCHAR(500) NOT NULL COMMENT 'OSS公网URL',
    file_name VARCHAR(255) COMMENT '文件名',
    file_size BIGINT COMMENT '文件大小(字节)',
    duration INT COMMENT '时长(秒)用于音视频',
    task_id VARCHAR(64) COMMENT '关联的任务ID',
    source_task_type VARCHAR(50) COMMENT '来源任务类型 chain_tts/video_generate等',
    status VARCHAR(20) DEFAULT 'active' COMMENT '状态 active/deleted/blocked',
    metadata JSON COMMENT '额外元数据如分辨率、格式等',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_user_type (user_id, resource_type),
    INDEX idx_user_status (user_id, status),
    INDEX idx_task_id (task_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='生成的资源表';
"""


# ==================== 数据模型 ====================

class User(BaseModel):
    """用户模型"""
    id: Optional[int] = None
    user_id: str
    username: str
    password_hash: Optional[str] = None
    api_key: str
    role: str = "user"
    status: int = 1
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Voice(BaseModel):
    """音色模型"""
    id: Optional[int] = None
    voice_id: str
    user_id: int
    prefix: str
    model: str
    status: str = "DEPLOYING"
    target_model: Optional[str] = None
    gmt_create: Optional[str] = None
    gmt_modified: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Task(BaseModel):
    """任务模型"""
    id: Optional[int] = None
    task_id: str
    user_id: Optional[int] = None
    task_type: str
    status: str = "pending"
    progress: int = 0
    result: Optional[dict] = None
    error: Optional[str] = None
    input_params: Optional[dict] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class OperationLog(BaseModel):
    """操作日志模型"""
    id: Optional[int] = None
    user_id: Optional[int] = None
    operation: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: Optional[datetime] = None


class GeneratedResource(BaseModel):
    """生成的资源模型"""
    id: Optional[int] = None
    user_id: int
    resource_type: str  # audio/video/image
    resource_url: str
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[int] = None  # 时长(秒)
    task_id: Optional[str] = None
    source_task_type: Optional[str] = None
    status: str = "active"  # active/deleted/blocked
    metadata: Optional[dict] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ==================== 数据访问函数 ====================

def init_tables():
    """初始化数据库表"""
    if not db.is_connected():
        return False

    try:
        # 分割并执行多个建表语句
        statements = [s.strip() for s in CREATE_TABLES_SQL.split(';') if s.strip()]
        
        for statement in statements:
            db.execute(statement)
        
        from core.logger import get_logger
        logger = get_logger("database")
        logger.info("✅ 数据库表初始化完成")
        return True
    except Exception as e:
        from core.logger import get_logger
        logger = get_logger("database")
        logger.error(f"❌ 数据库表初始化失败: {e}")
        return False
