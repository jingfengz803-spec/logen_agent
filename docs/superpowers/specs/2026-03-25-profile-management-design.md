# 档案管理（Profile Management）设计文档

## 概述

为用户提供档案管理功能，用户创建档案后可选择将档案输出给大模型生成文案（短视频脚本/纯文字文案），支持多版本选择。所有数据按用户严格隔离。

## 需求总结

| 决策项 | 结论 |
|---|---|
| 行业列表 | 系统预设 + 用户自定义，仅当前用户可见 |
| 文案生成触发 | 手动点击按钮触发 |
| 文案类型 | 两者都支持：短视频脚本（含 TTS→视频）和纯文字文案 |
| 脚本生成 | 生成 3 个版本供用户选择，选中后再走后续流程 |
| 行业输入 | 简单文本输入 |
| 模块划分 | 独立模块，新建 profiles.py + profiles 表 |
| 数据隔离 | 严格隔离，复用 Database 自动过滤 |

## 数据模型

### profiles 表

```sql
CREATE TABLE IF NOT EXISTS profiles (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    profile_id VARCHAR(64) UNIQUE NOT NULL,
    user_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL COMMENT '档案名称',
    industry VARCHAR(200) NOT NULL COMMENT '所需行业',
    video_url VARCHAR(500) COMMENT '视频链接',
    homepage_url VARCHAR(500) COMMENT '主页链接',
    target_audience TEXT NOT NULL COMMENT '目标用户群体',
    customer_pain_points TEXT NOT NULL COMMENT '客户痛点',
    solution TEXT NOT NULL COMMENT '解决方案',
    persona_background TEXT NOT NULL COMMENT '人设背景',
    status VARCHAR(20) DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_user_status (user_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户档案表'
```

### user_industries 表

```sql
CREATE TABLE IF NOT EXISTS user_industries (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    name VARCHAR(100) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_industry (user_id, name),
    INDEX idx_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户自定义行业'
```

### 系统预设行业

在代码中维护一个常量列表，启动时不需要插入数据库：

```python
SYSTEM_INDUSTRIES = [
    "美食", "科技", "美妆", "穿搭", "母婴", "教育",
    "健身", "旅行", "汽车", "房产", "家居", "宠物",
    "医疗", "金融", "法律", "娱乐", "电商", "其他"
]
```

## API 端点

### 档案 CRUD

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/profiles` | 创建档案 |
| GET | `/api/v1/profiles` | 获取当前用户档案列表 |
| GET | `/api/v1/profiles/{profile_id}` | 获取档案详情 |
| PUT | `/api/v1/profiles/{profile_id}` | 更新档案 |
| DELETE | `/api/v1/profiles/{profile_id}` | 删除档案 |

### 行业管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/profiles/industries` | 获取行业列表（系统+自定义） |
| POST | `/api/v1/profiles/industries` | 添加自定义行业 |
| DELETE | `/api/v1/profiles/industries/{id}` | 删除自定义行业 |

### 文案生成

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chain/generate-from-profile` | 从档案生成文案 |

请求参数：
```json
{
    "profile_id": "profile_xxx",
    "generate_type": "video_script" | "text_copy",
    "topic": "可选的主题补充",
    "count": 3
}
```

返回：3 个版本的文案列表，每个版本包含完整文案内容。

## 文案生成流程

### 短视频脚本

```
档案信息 → 组装 prompt → 大模型生成 3 版脚本
→ 用户选择版本 → 进入 chain 脚本流程
→ TTS → 视频（复用现有逻辑）
```

### 纯文字文案

```
档案信息 → 组装 prompt → 大模型生成 3 版文案
→ 用户选择版本 → 保存为任务结果（纯文本）
```

### Prompt 模板

```
你是一个专业的短视频内容策划师，请根据以下档案信息生成{类型}：

行业：{industry}
目标用户群体：{target_audience}
客户痛点：{customer_pain_points}
解决方案：{solution}
人设背景：{persona_background}

参考素材（如有）：
- 视频链接：{video_url}
- 主页链接：{homepage_url}

{topic补充}

请生成 {count} 个不同风格的版本供选择。
```

## 文件改动

### 新增

| 文件 | 说明 |
|---|---|
| `python_services/api/v1/profiles.py` | 档案 API 路由 |
| `python_services/dao/profile_dao.py` | 档案数据访问层 |

### 修改

| 文件 | 改动 |
|---|---|
| `python_services/database.py` | `_ISOLATED_TABLES` 添加 `profiles` 和 `user_industries` |
| `python_services/main.py` | 注册 profiles 路由、初始化 profiles 表 |
| `python_services/api/v1/chain.py` | 新增 `generate-from-profile` 端点 |

## 数据隔离

`profiles` 和 `user_industries` 表加入 `Database._ISOLATED_TABLES`，复用现有的自动过滤机制：
- 普通用户只能看到自己的档案和行业
- 管理员可以看到所有
- 无需在每个 DAO 方法中手动传 user_id
