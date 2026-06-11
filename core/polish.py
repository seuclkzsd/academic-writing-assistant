"""学术表达润色（短文本、隐私敏感，优先本地端）。"""
from __future__ import annotations

from .llm import LLMResult, LLMRouter

STYLES = {
    "严谨": "严谨、客观，符合学术规范，措辞精确，避免口语化与主观夸张。",
    "简洁": "精炼凝练，删除冗余，保持信息密度，句式简洁有力。",
    "流畅": "逻辑连贯、过渡自然，提升可读性，同时保持学术语体。",
    "降AI味": "更像人类研究者的自然书写，减少模板化、套话与重复结构，避免机械的排比与空洞措辞。",
}

_SYSTEM = (
    "你是一名学术论文语言润色专家。请在不改变原意、不编造内容的前提下润色文本，"
    "保持专业术语准确。"
)

_USER_TMPL = """请润色以下{lang}学术文本。

润色风格：{style_desc}

原文：
\"\"\"
{text}
\"\"\"

输出要求：
1. 先给出【润色结果】（仅正文，不要解释）。
2. 再用【修改说明】用 3-5 条列出主要改动及原因。
"""


def polish_text(
    text: str,
    style: str = "严谨",
    lang: str = "中文",
    router: LLMRouter | None = None,
) -> LLMResult:
    router = router or LLMRouter()
    style_desc = STYLES.get(style, STYLES["严谨"])
    user = _USER_TMPL.format(
        lang=lang.strip() or "中文",
        style_desc=style_desc,
        text=text.strip(),
    )
    # 润色偏轻量且涉及未发表文稿隐私 -> 优先本地端
    result = router.chat(_SYSTEM, user, prefer="local", temperature=0.5)
    if not result.ok:
        result.text = (
            "【润色结果】\n（离线示例：未连接模型，此处原样返回原文）\n\n"
            + text.strip()
            + "\n\n【修改说明】\n- 配置本地或云端模型后，将按所选风格进行实际润色。"
        )
    return result
