"""
MemoMind SDK 公共 API 入口

提供命名空间隔离的导入路径，避免 api/core 等通用包名污染。
用法: from memomind import MemoMind
"""

from api.client import MemoMind  # noqa: F401
