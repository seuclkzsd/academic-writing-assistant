"""集中管理配置与环境变量。"""
from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # python-dotenv 缺失时不致命
    pass


@dataclass
class Settings:
    """运行配置。所有字段均可通过环境变量覆盖。"""

    # 实验阶段默认走云端；本地接口代码保留，设 LLM_MODE=auto 可启用混合架构。
    mode: str = os.getenv("LLM_MODE", "cloud").strip().lower()

    cloud_api_key: str = os.getenv("CLOUD_API_KEY", "").strip()
    cloud_base_url: str = os.getenv(
        "CLOUD_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ).strip()
    cloud_model: str = os.getenv("CLOUD_MODEL", "qwen-plus").strip()

    local_base_url: str = os.getenv("LOCAL_BASE_URL", "http://localhost:11434/v1").strip()
    local_model: str = os.getenv("LOCAL_MODEL", "qwen2.5:7b").strip()
    local_api_key: str = os.getenv("LOCAL_API_KEY", "ollama").strip()

    @property
    def cloud_configured(self) -> bool:
        return bool(self.cloud_api_key)


def get_settings() -> Settings:
    """每次读取，便于在 UI 中即时修改环境后刷新。"""
    return Settings()
