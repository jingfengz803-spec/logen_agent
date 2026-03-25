"""
导出 OpenAPI 规范文件
用于导入 Apifox 等 API 管理工具
"""
import json
import sys
import re
from pathlib import Path
from typing import List, Dict, Any

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from main import app


def export_openapi_from_app(
    output_path: str = "openapi.json",
    server_url: str = "http://localhost:8088"
):
    """从 FastAPI 应用导出 OpenAPI 规范"""
    # 获取 OpenAPI schema
    openapi_schema = app.openapi()

    # 更新服务器 URL
    openapi_schema["servers"] = [
        {
            "url": server_url,
            "description": "本地开发环境"
        }
    ]

    # 添加 Apifox 扩展字段
    openapi_schema["info"]["x-apifox-name"] = "短视频创作自动化API"

    # 写入文件
    output_file = Path(__file__).parent / output_path
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, ensure_ascii=False, indent=2)

    print(f"[OK] OpenAPI spec exported to: {output_file}")
    print(f"[INFO] Server URL: {server_url}")
    print(f"[INFO] Total endpoints: {len(openapi_schema.get('paths', {}))}")

    # 统计各标签接口数
    tag_count = {}
    for path, methods in openapi_schema['paths'].items():
        for method, details in methods.items():
            tags = details.get('tags', [])
            if tags:
                tag = tags[0]
                tag_count[tag] = tag_count.get(tag, 0) + 1

    print("\n[INFO] Endpoints by tag:")
    for tag, count in sorted(tag_count.items()):
        print(f"   - {tag}: {count}")

    return openapi_schema


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="导出 FastAPI OpenAPI 规范")
    parser.add_argument("-o", "--output", default="openapi.json", help="输出文件路径")
    parser.add_argument("-s", "--server", default="http://localhost:8088", help="服务器 URL")

    args = parser.parse_args()
    export_openapi_from_app(args.output, args.server)


def parse_route_file(file_path: Path) -> List[Dict[str, Any]]:
    """解析路由文件，提取 API 信息"""
    content = file_path.read_text(encoding="utf-8")
    routes = []

    # 匹配 @router.post/get/decorator 和下面的函数
    pattern = r'@router\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']([^)]*)\)'
    doc_pattern = r'""".*?"""'

    for match in re.finditer(pattern, content, re.MULTILINE):
        method = match.group(1).upper()
        path = match.group(2)
        decorator_end = match.end()

        # 查找函数名和文档字符串
        func_pattern = r'async\s+(\w+)\s*\([^)]*\):\s*\n\s+"""([\s\S]*?)"""'
        func_match = re.search(func_pattern, content[decorator_end:decorator_end + 500])

        description = ""
        if func_match:
            description = func_match.group(2).strip()
            # 清理描述中的参数标记
            description = re.sub(r'\*\*[^*]+\*\*\s*[-:—]?\s*', '', description)
            description = re.sub(r'-\s+\*\*', '', description)
            description = description.strip()

        routes.append({
            "method": method,
            "path": path,
            "description": description
        })

    return routes


def generate_openapi() -> Dict[str, Any]:
    """生成 OpenAPI 规范"""
    base_dir = Path(__file__).parent
    api_dir = base_dir / "api" / "v1"

    # 收集所有路由
    all_routes = []
    for py_file in api_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue
        routes = parse_route_file(py_file)
        for route in routes:
            # 添加前缀 /api/v1
            tag = py_file.stem.replace("_", " ").title()
            if tag == "Ai":
                tag = "AI分析"
            elif tag == "Tts":
                tag = "TTS语音"
            elif tag == "Douyin":
                tag = "抖音抓取"
            elif tag == "Profiles":
                tag = "档案管理"
            elif tag == "Chain":
                tag = "任务串联"
            elif tag == "Resources":
                tag = "资源管理"
            elif tag == "Users":
                tag = "用户管理"
            elif tag == "Storage":
                tag = "存储服务"
            elif tag == "Video":
                tag = "视频生成"

            route["tag"] = tag
            all_routes.append(route)

    # 添加根路径和健康检查
    all_routes.insert(0, {
        "method": "GET",
        "path": "/",
        "description": "根路径，返回服务基本信息",
        "tag": "系统"
    })
    all_routes.insert(1, {
        "method": "GET",
        "path": "/health",
        "description": "健康检查接口",
        "tag": "系统"
    })

    # 构建 OpenAPI 规范
    paths = {}
    for route in all_routes:
        full_path = f"/api/v1{route['path']}" if not route['path'].startswith('/') else route['path']
        if route['tag'] == "系统":
            full_path = route['path']

        if full_path not in paths:
            paths[full_path] = {}

        paths[full_path][route['method'].lower()] = {
            "summary": route['description'] or f"{route['method']} {route['path']}",
            "tags": [route['tag']],
            "responses": {
                "200": {
                    "description": "成功",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object"
                            }
                        }
                    }
                }
            }
        }

    openapi_spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "短视频创作自动化API",
            "version": "1.0.0",
            "description": "提供抖音数据抓取、AI分析、TTS语音合成、视频生成等功能的API服务",
            "x-apifox-name": "短视频创作自动化API"
        },
        "servers": [
            {
                "url": "http://localhost:8000",
                "description": "本地开发环境"
            },
            {
                "url": "http://your-server:8000",
                "description": "生产环境"
            }
        ],
        "tags": [
            {"name": "系统", "description": "系统接口"},
            {"name": "用户管理", "description": "用户注册、登录、管理"},
            {"name": "抖音抓取", "description": "抖音数据抓取"},
            {"name": "AI分析", "description": "AI分析与脚本生成"},
            {"name": "TTS语音", "description": "TTS语音合成"},
            {"name": "视频生成", "description": "VideoRetalk视频生成"},
            {"name": "任务串联", "description": "基于task_id的任务串联"},
            {"name": "档案管理", "description": "用户档案与行业管理"},
            {"name": "资源管理", "description": "生成的资源管理"},
            {"name": "存储服务", "description": "文件存储与OSS"}
        ],
        "paths": paths
    }

    return openapi_spec


def export_openapi(output_path: str = "openapi.json", pretty: bool = True):
    """导出 OpenAPI 规范"""
    openapi_schema = generate_openapi()

    output_file = Path(__file__).parent / output_path
    with open(output_file, "w", encoding="utf-8") as f:
        if pretty:
            json.dump(openapi_schema, f, ensure_ascii=False, indent=2)
        else:
            json.dump(openapi_schema, f, ensure_ascii=False)

    print(f"[OK] OpenAPI spec exported to: {output_file}")
    print(f"[INFO] Total {len(openapi_schema.get('paths', {}))} endpoints")

    # 统计各模块接口数
    tag_count = {}
    for path, methods in openapi_schema['paths'].items():
        for method, details in methods.items():
            tag = details['tags'][0] if details.get('tags') else 'Other'
            tag_count[tag] = tag_count.get(tag, 0) + 1

    for tag, count in sorted(tag_count.items()):
        print(f"   - {tag}: {count}")
