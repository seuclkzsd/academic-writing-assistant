"""LLM 智能路由：在本地端 (Ollama) 与云端 (OpenAI 兼容) 之间自动选择并降级。

设计目标（对应赛道附加分的"云端 + 本地端混合架构"）：
- 隐私敏感 / 轻量任务 -> 优先本地端；
- 高质量 / 重任务     -> 优先云端；
- 任一端不可用时自动降级，最终降到离线模板，保证演示不中断。
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Literal, Optional

import httpx
import requests

from .config import Settings, get_settings

Prefer = Literal["local", "cloud"]


def _http_proxy_from_env() -> Optional[str]:
    """仅返回 http(s) 代理，忽略 SOCKS 代理（避免依赖 socksio）。

    不修改任何系统环境变量，只读取后由 httpx 显式使用。
    """
    for var in (
        "LLM_HTTP_PROXY",
        "HTTPS_PROXY",
        "https_proxy",
        "HTTP_PROXY",
        "http_proxy",
        "ALL_PROXY",
        "all_proxy",
    ):
        value = os.getenv(var)
        if value and value.lower().startswith("http"):
            return value
    return None


def _build_http_client(use_proxy: bool) -> httpx.Client:
    """构造 httpx 客户端：trust_env=False 屏蔽系统(含 SOCKS)代理自动注入；
    云端按需显式走 HTTP 代理，本地端直连 localhost。"""
    # 部分云端 endpoint（尤其推理型模型）首字延迟较高，读超时给足，避免长文本生成被误判超时降级。
    read_timeout = float(os.getenv("LLM_READ_TIMEOUT", "300"))
    timeout = httpx.Timeout(read_timeout, connect=15.0)
    proxy = _http_proxy_from_env() if use_proxy else None
    if proxy:
        return httpx.Client(proxy=proxy, trust_env=False, timeout=timeout)
    return httpx.Client(trust_env=False, timeout=timeout)


@dataclass
class LLMResult:
    text: str
    provider: str  # 人类可读的执行端标签，用于 UI 展示
    ok: bool       # 是否真正由模型生成（False 表示需要调用方走离线模板）


class LLMRouter:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    # ---------- 可用性检测 ----------
    def cloud_available(self) -> bool:
        if self.settings.mode in ("local", "mock"):
            return False
        return self.settings.cloud_configured

    def local_available(self) -> bool:
        if self.settings.mode in ("cloud", "mock"):
            return False
        base = self.settings.local_base_url.rstrip("/")
        if base.endswith("/v1"):
            base = base[: -len("/v1")]
        try:
            resp = requests.get(f"{base}/api/tags", timeout=0.8)
            return resp.status_code == 200
        except Exception:
            return False

    def status(self) -> dict:
        """供 UI 展示当前架构状态。"""
        return {
            "mode": self.settings.mode,
            "cloud": self.cloud_available(),
            "cloud_model": self.settings.cloud_model,
            "local": self.local_available(),
            "local_model": self.settings.local_model,
        }

    # ---------- 实际调用 ----------
    def _call(self, endpoint: Prefer, system: str, user: str, temperature: float) -> str:
        from openai import OpenAI  # 延迟导入，避免无依赖时影响规则化功能

        if endpoint == "cloud":
            client = OpenAI(
                api_key=self.settings.cloud_api_key,
                base_url=self.settings.cloud_base_url,
                http_client=_build_http_client(use_proxy=True),
            )
            model = self.settings.cloud_model
        else:
            client = OpenAI(
                api_key=self.settings.local_api_key or "ollama",
                base_url=self.settings.local_base_url,
                http_client=_build_http_client(use_proxy=False),
            )
            model = self.settings.local_model

        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        return (resp.choices[0].message.content or "").strip()

    def chat(
        self,
        system: str,
        user: str,
        prefer: Prefer = "cloud",
        temperature: float = 0.4,
    ) -> LLMResult:
        """按偏好选择执行端并自动降级。

        prefer="local"：本地 -> 云端；prefer="cloud"：云端 -> 本地。
        """
        order: List[Prefer] = ["local", "cloud"] if prefer == "local" else ["cloud", "local"]

        labels = {
            "cloud": f"云端 ({self.settings.cloud_model})",
            "local": f"本地端 ({self.settings.local_model})",
        }

        for endpoint in order:
            available = self.cloud_available() if endpoint == "cloud" else self.local_available()
            if not available:
                continue
            try:
                text = self._call(endpoint, system, user, temperature)
                if text:
                    return LLMResult(text=text, provider=labels[endpoint], ok=True)
            except Exception:  # 调用失败则尝试下一个端
                continue

        return LLMResult(text="", provider="离线模板", ok=False)
