"""
检查 douyin_fetch_tasks 表的数据
"""
import pymysql

# 连接配置
config = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",  # 请填写你的密码
    "database": "logen_agent",
    "charset": "utf8mb4"
}

try:
    conn = pymysql.connect(**config)
    cursor = conn.cursor(pymysql.cursors.DictCursor)

    # 查询表是否存在
    cursor.execute("SHOW TABLES LIKE 'douyin%'")
    tables = cursor.fetchall()
    print("=== douyin 开头的表 ===")
    for t in tables:
        print(list(t.values())[0])

    # 查询数据
    print("\n=== douyin_fetch_tasks 数据 ===")
    cursor.execute("SELECT * FROM douyin_fetch_tasks ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()
    print(f"共 {len(rows)} 条记录")
    for row in rows:
        print(row)

    cursor.close()
    conn.close()

except Exception as e:
    print(f"错误: {e}")
