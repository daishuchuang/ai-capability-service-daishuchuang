"""pytest 公共 fixture。"""

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def _zero_simulated_latency():
    """全会话关闭 ``text_summary`` mock 模式的模拟延迟，加快测试。"""
    os.environ["AI_CAPABILITY_SIMULATED_LATENCY_MS"] = "0"
    yield

