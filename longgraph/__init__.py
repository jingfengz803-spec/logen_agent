"""
LongGraph 模块初始化
统一处理编码问题
"""

import sys
import io

# 修复 Windows 控制台编码 - 只执行一次
if sys.platform == "win32" and not isinstance(sys.stdout, io.TextIOWrapper):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
