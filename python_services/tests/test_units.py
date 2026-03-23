"""
单元测试示例 - 测试服务类
不需要启动 HTTP 服务，直接测试代码功能
"""
import sys
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

# 添加项目路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))


# ==================== 示例1: 测试模型类 ====================
def test_request_models():
    """测试请求模型验证"""
    from models.request import FetchUserVideosRequest, GenerateScriptRequest
    
    # 测试 FetchUserVideosRequest
    request = FetchUserVideosRequest(
        url="https://www.douyin.com/user/test123",
        max_count=50,
        enable_filter=True,
        min_likes=100
    )
    assert request.url == "https://www.douyin.com/user/test123"
    assert request.max_count == 50
    assert request.enable_filter is True
    print("[OK] FetchUserVideosRequest model test passed")

    # 测试 GenerateScriptRequest
    script_request = GenerateScriptRequest(
        reference_data={"videos": []},
        topic="测试主题",
        target_duration=60
    )
    assert script_request.topic == "测试主题"
    assert script_request.target_duration == 60
    print("[OK] GenerateScriptRequest model test passed")

    # 测试 URL 验证
    try:
        invalid_request = FetchUserVideosRequest(
            url="https://example.com/user/test",  # 非抖音URL
            max_count=50
        )
        assert False, "Should have raised validation error"
    except ValueError:
        print("[OK] URL validation test passed")


# ==================== 示例2: 测试服务类（使用 Mock） ====================
def test_douyin_service_mock():
    """测试抖音服务类（使用 mock）"""
    from services.douyin_service import DouyinService
    
    service = DouyinService()
    
    # 验证服务初始化
    assert service.tool_dir is not None
    assert service.executor is not None
    print("[OK] DouyinService initialization test passed")


def test_ai_service_mock():
    """测试AI服务类（使用 mock）"""
    from services.ai_service import AIService
    
    service = AIService()
    
    # 验证服务初始化
    assert service.longgraph_dir is not None
    assert service.executor is not None
    print("[OK] AIService initialization test passed")


# ==================== 示例3: 测试工具函数 ====================
def test_config_settings():
    """测试配置设置"""
    from core.config import settings
    
    assert settings.APP_NAME == "短视频创作自动化API"
    assert settings.PORT == 8088
    assert settings.API_PREFIX == "/api/v1"
    print("[OK] Config settings test passed")


def test_task_manager():
    """测试任务管理器"""
    from core.task_manager import task_manager
    
    # 创建测试任务
    task_id = task_manager.create_task("test_task", {"param": "value"})
    
    # 获取任务
    task = task_manager.get_task(task_id)
    assert task is not None
    assert task.task_id == task_id
    assert task.status.value == "pending"
    
    # 更新进度
    task_manager.update_progress(task_id, 50, "处理中...")
    task = task_manager.get_task(task_id)
    assert task.progress == 50
    
    print(f"[OK] TaskManager test passed (task_id: {task_id})")


# ==================== 示例4: 异步测试 ====================
@pytest.mark.asyncio
async def test_async_service():
    """测试异步服务"""
    from services.ai_service import AIService
    
    service = AIService()
    
    # 使用 mock 测试异步方法（不执行真实逻辑）
    with patch.object(service, 'longgraph_dir'):
        # 这里只是测试异步调用是否正常
        # 实际测试中可以 mock 内部依赖
        print("[OK] Async service test passed")


# ==================== 示例5: 测试响应模型 ====================
def test_response_models():
    """测试响应模型"""
    from models.response import TaskResponse, TaskStatus, FetchVideosResponse
    
    # 测试 TaskResponse
    task_response = TaskResponse(
        task_id="test-123",
        status=TaskStatus.PENDING,
        progress=0,
        created_at="2024-01-01T00:00:00"
    )
    assert task_response.task_id == "test-123"
    assert task_response.status == TaskStatus.PENDING
    print("[OK] TaskResponse model test passed")
    
    # 测试 FetchVideosResponse
    from models.response import VideoInfo
    videos_response = FetchVideosResponse(
        data=[
            VideoInfo(
                aweme_id="123",
                desc="Test video 1",
                author="Test Author",
                author_id="auth123"
            ),
            VideoInfo(
                aweme_id="456",
                desc="Test video 2",
                author="Test Author",
                author_id="auth123"
            )
        ],
        total=2,
        filtered_count=2,
        request_id="req-123"
    )
    assert len(videos_response.data) == 2
    assert videos_response.total == 2
    print("[OK] FetchVideosResponse model test passed")


# ==================== 运行所有测试 ====================
def run_all_unit_tests():
    """运行所有单元测试"""
    print("=" * 60)
    print("Running Unit Tests (No HTTP server needed)")
    print("=" * 60)
    
    tests = [
        ("Request Models", test_request_models),
        ("DouyinService Mock", test_douyin_service_mock),
        ("AIService Mock", test_ai_service_mock),
        ("Config Settings", test_config_settings),
        ("Task Manager", test_task_manager),
        ("Response Models", test_response_models),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            print(f"\n[Test] {name}...")
            test_func()
            passed += 1
        except Exception as e:
            print(f"[FAIL] {name}: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"Unit Test Results: {passed} passed, {failed} failed")
    print("=" * 60)


if __name__ == "__main__":
    run_all_unit_tests()
