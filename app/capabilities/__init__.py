"""能力子包：各 capability 实现与注册表。"""

from app.capabilities.registry import CAPABILITY_REGISTRY, run_capability

__all__ = ["CAPABILITY_REGISTRY", "run_capability"]
