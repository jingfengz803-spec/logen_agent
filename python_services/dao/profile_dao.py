"""
档案数据访问层
管理用户档案和自定义行业
"""

from typing import Optional, List, Dict
from database import db
from core.logger import get_logger

logger = get_logger("dao:profile")

# 系统预设行业
SYSTEM_INDUSTRIES = [
    "美食", "科技", "美妆", "穿搭", "母婴", "教育",
    "健身", "旅行", "汽车", "房产", "家居", "宠物",
    "医疗", "金融", "法律", "娱乐", "电商", "其他"
]


class ProfileDAO:
    """档案数据访问对象"""

    @staticmethod
    def init_tables():
        """初始化档案表和用户行业表"""
        profiles_sql = """
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
        """
        industries_sql = """
        CREATE TABLE IF NOT EXISTS user_industries (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            user_id BIGINT NOT NULL,
            name VARCHAR(100) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY uk_user_industry (user_id, name),
            INDEX idx_user_id (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户自定义行业'
        """
        try:
            db.execute(profiles_sql)
            db.execute(industries_sql)
            logger.info("✅ 档案表初始化完成")
        except Exception as e:
            logger.warning(f"档案表初始化失败（可能已存在）: {e}")

    # ── 档案 CRUD ──────────────────────────────────────

    @staticmethod
    def create_profile(
        user_db_id: int,
        profile_id: str,
        name: str,
        industry: str,
        target_audience: str,
        customer_pain_points: str,
        solution: str,
        persona_background: str,
        video_url: Optional[str] = None,
        homepage_url: Optional[str] = None,
    ) -> int:
        """创建档案"""
        sql = """
            INSERT INTO profiles
            (profile_id, user_id, name, industry, video_url, homepage_url,
             target_audience, customer_pain_points, solution, persona_background)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        return db.insert_return_id(sql, (
            profile_id, user_db_id, name, industry, video_url, homepage_url,
            target_audience, customer_pain_points, solution, persona_background
        ))

    @staticmethod
    def _resolve_id(raw_id: str):
        """根据输入判断使用 id（数字）还是 profile_id（字符串）"""
        if raw_id.isdigit():
            return "id", int(raw_id)
        return "profile_id", raw_id

    @staticmethod
    def get_profile(profile_id: str) -> Optional[Dict]:
        """根据 id 或 profile_id 获取档案（自动按 user_id 过滤）"""
        col, val = ProfileDAO._resolve_id(profile_id)
        sql = f"SELECT * FROM profiles WHERE {col} = %s AND status = 'active'"
        return db.fetch_one(sql, (val,))

    @staticmethod
    def list_profiles(limit: int = 50, offset: int = 0) -> List[Dict]:
        """获取当前用户的档案列表（自动按 user_id 过滤）"""
        sql = """
            SELECT * FROM profiles
            WHERE status = 'active'
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        return db.fetch_all(sql, (limit, offset))

    @staticmethod
    def update_profile(
        profile_id: str,
        name: Optional[str] = None,
        industry: Optional[str] = None,
        video_url: Optional[str] = None,
        homepage_url: Optional[str] = None,
        target_audience: Optional[str] = None,
        customer_pain_points: Optional[str] = None,
        solution: Optional[str] = None,
        persona_background: Optional[str] = None,
    ) -> bool:
        """更新档案"""
        fields = []
        params = []
        for field, value in [
            ("name", name), ("industry", industry),
            ("video_url", video_url), ("homepage_url", homepage_url),
            ("target_audience", target_audience),
            ("customer_pain_points", customer_pain_points),
            ("solution", solution), ("persona_background", persona_background),
        ]:
            if value is not None:
                fields.append(f"{field} = %s")
                params.append(value)

        if not fields:
            return False

        col, val = ProfileDAO._resolve_id(profile_id)
        params.append(val)
        sql = f"UPDATE profiles SET {', '.join(fields)} WHERE {col} = %s AND status = 'active'"
        affected = db.execute(sql, tuple(params))
        return affected > 0

    @staticmethod
    def delete_profile(profile_id: str) -> bool:
        """软删除档案（设置 status = deleted），支持 id 或 profile_id"""
        col, val = ProfileDAO._resolve_id(profile_id)
        sql = f"UPDATE profiles SET status = 'deleted' WHERE {col} = %s AND status = 'active'"
        affected = db.execute(sql, (val,))
        return affected > 0

    # ── 行业管理 ──────────────────────────────────────

    @staticmethod
    def get_custom_industries() -> List[Dict]:
        """获取当前用户的自定义行业列表（自动按 user_id 过滤）"""
        sql = "SELECT * FROM user_industries ORDER BY created_at DESC"
        return db.fetch_all(sql)

    @staticmethod
    def add_custom_industry(user_db_id: int, name: str) -> int:
        """添加自定义行业"""
        sql = "INSERT INTO user_industries (user_id, name) VALUES (%s, %s)"
        return db.insert_return_id(sql, (user_db_id, name))

    @staticmethod
    def delete_custom_industry(industry_id: int) -> bool:
        """删除自定义行业"""
        sql = "DELETE FROM user_industries WHERE id = %s"
        affected = db.execute(sql, (industry_id,))
        return affected > 0
