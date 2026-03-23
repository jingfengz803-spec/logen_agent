"""
导出 OpenAPI 规范文件
用于导入 Apifox 等 API 管理工具
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Any


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
            {"name": "抖音抓取", "description": "抖音数据抓取"},
            {"name": "AI分析", "description": "AI分析与脚本生成"},
            {"name": "TTS语音", "description": "TTS语音合成"},
            {"name": "视频生成", "description": "VideoRetalk视频生成"},
            {"name": "完整工作流", "description": "完整工作流"},
            {"name": "存储", "description": "文件存储"}
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


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="导出 FastAPI OpenAPI 规范")
    parser.add_argument("-o", "--output", default="openapi.json", help="输出文件路径")
    parser.add_argument("-c", "--compact", action="store_true", help="紧凑格式输出")

    args = parser.parse_args()
    export_openapi(args.output, pretty=not args.compact)
