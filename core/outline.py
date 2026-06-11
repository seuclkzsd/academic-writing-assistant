"""论文提纲生成（重任务，优先云端）。"""
from __future__ import annotations

from .llm import LLMResult, LLMRouter

_SYSTEM = (
    "你是一名资深学术写作导师，擅长为各学科论文搭建严谨、逻辑清晰的写作框架。"
    "请输出规范的学术论文提纲。"
)

_USER_TMPL = """请为以下论文生成结构化提纲。

题目/研究方向：{topic}
学科领域：{field}
论文类型：{paper_type}
补充要求：{extra}

输出要求：
1. 使用 Markdown 多级标题（#、##、###）组织章节。
2. 每个章节下用列表给出 2-4 个写作要点。
3. 关键章节附一句【写作提示】，说明该部分应回答什么问题。
4. 结构需符合 {paper_type} 的学术惯例，逻辑连贯、详略得当。
"""


def _offline_template(topic: str, field: str, paper_type: str) -> str:
    return f"""# {topic}

> 离线示例提纲（未连接模型）。配置云端或本地模型后将生成针对 **{field}** 领域、**{paper_type}** 类型的高质量提纲。

## 1. 引言
- 研究背景与意义
- 国内外研究现状
- 本文研究问题与贡献
- 【写作提示】回答"为什么研究这个问题、前人做到哪一步、本文补了什么空白"。

## 2. 相关工作 / 文献综述
- 主要技术路线梳理
- 现有方法的局限

## 3. 方法 / 研究设计
- 总体框架
- 关键模块与原理
- 【写作提示】让读者能据此复现你的工作。

## 4. 实验 / 结果分析
- 数据与设置
- 对比与消融
- 结果讨论

## 5. 结论与展望
- 主要结论
- 局限与未来工作
"""


def generate_outline(
    topic: str,
    field: str = "通用",
    paper_type: str = "学术论文",
    extra: str = "无",
    router: LLMRouter | None = None,
) -> LLMResult:
    router = router or LLMRouter()
    user = _USER_TMPL.format(
        topic=topic.strip(),
        field=field.strip() or "通用",
        paper_type=paper_type.strip() or "学术论文",
        extra=(extra.strip() or "无"),
    )
    result = router.chat(_SYSTEM, user, prefer="cloud", temperature=0.6)
    if not result.ok:
        result.text = _offline_template(topic.strip(), field, paper_type)
    return result
