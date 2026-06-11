"""学术写作规范助手 —— Streamlit 入口。"""
from __future__ import annotations

import streamlit as st

from core.config import get_settings
from core.llm import LLMRouter
from core.outline import generate_outline
from core.polish import STYLES, polish_text
from core.references import TARGETS, convert

st.set_page_config(page_title="学术写作规范助手", page_icon="📝", layout="wide")


@st.cache_resource
def get_router() -> LLMRouter:
    return LLMRouter(get_settings())


def render_sidebar(router: LLMRouter) -> None:
    status = router.status()
    st.sidebar.title("📝 学术写作规范助手")
    st.sidebar.caption("学习与科研赋能 · 写得更规范")
    st.sidebar.divider()
    st.sidebar.subheader("混合架构状态")
    st.sidebar.write(f"运行模式：`{status['mode']}`")

    cloud_icon = "🟢" if status["cloud"] else "⚪"
    local_icon = "🟢" if status["local"] else "⚪"
    st.sidebar.write(f"{cloud_icon} 云端：{status['cloud_model']}")
    st.sidebar.write(f"{local_icon} 本地端：{status['local_model']}")

    if not status["cloud"] and not status["local"]:
        st.sidebar.warning("当前为离线模式：参考文献功能完全可用；提纲/润色返回示例。")
    st.sidebar.divider()
    st.sidebar.caption(
        "当前实验：模型调用统一走云端；本地接口已保留，设 LLM_MODE=auto 可启用混合架构。"
        "参考文献转换为本地规则引擎，任何模式下都在本地执行。"
    )


def tab_outline(router: LLMRouter) -> None:
    st.subheader("论文提纲生成")
    st.caption("输入题目与方向，生成结构化写作框架（重任务，优先云端）。")
    col1, col2 = st.columns([2, 1])
    with col1:
        topic = st.text_input("题目 / 研究方向", placeholder="例如：基于大模型的错题分析与个性化复习系统")
    with col2:
        paper_type = st.selectbox(
            "论文类型", ["学术论文", "毕业论文", "综述", "开题报告", "课程论文"]
        )
    field = st.text_input("学科领域", placeholder="例如：计算机科学 / 教育技术 / 临床医学")
    extra = st.text_area("补充要求（可选）", placeholder="例如：需包含实验设计章节，篇幅约 1.5 万字", height=80)

    if st.button("生成提纲", type="primary", use_container_width=True):
        if not topic.strip():
            st.warning("请先输入题目 / 研究方向。")
            return
        with st.spinner("正在生成提纲…"):
            result = generate_outline(topic, field, paper_type, extra, router=router)
        st.success(f"完成 · 执行端：{result.provider}")
        st.markdown(result.text)
        st.download_button("下载 Markdown", result.text, file_name="outline.md")


def tab_polish(router: LLMRouter) -> None:
    st.subheader("学术表达润色")
    st.caption("段落级润色，多风格可选（隐私敏感，优先本地端）。")
    col1, col2 = st.columns(2)
    with col1:
        style = st.selectbox("润色风格", list(STYLES.keys()))
    with col2:
        lang = st.selectbox("语言", ["中文", "英文"])
    text = st.text_area("待润色文本", height=200, placeholder="粘贴需要润色的段落…")

    if st.button("开始润色", type="primary", use_container_width=True):
        if not text.strip():
            st.warning("请先输入待润色文本。")
            return
        with st.spinner("正在润色…"):
            result = polish_text(text, style, lang, router=router)
        st.success(f"完成 · 执行端：{result.provider}")
        st.markdown(result.text)


def tab_references(router: LLMRouter) -> None:
    st.subheader("参考文献格式转换")
    st.caption("BibTeX / 自由文本 → GB/T 7714-2015、APA 7th（规则化，完全离线可用）。")
    target = st.selectbox("目标格式", TARGETS)
    sample = (
        "@article{zhang2024llm,\n"
        "  author = {Zhang, San and Li, Si and Wang, Wu and Zhao, Liu},\n"
        "  title = {A Survey on Large Language Models for Education},\n"
        "  journal = {Journal of Educational Technology},\n"
        "  year = {2024},\n"
        "  volume = {12},\n"
        "  number = {3},\n"
        "  pages = {101--118}\n"
        "}"
    )
    text = st.text_area("BibTeX 或参考文献文本", value=sample, height=220)

    if st.button("转换格式", type="primary", use_container_width=True):
        with st.spinner("正在转换…"):
            items, note = convert(text, target, router=router)
        if note:
            st.info(note)
        if not items:
            st.warning("没有可输出的结果，请检查输入。")
            return
        st.success(f"共 {len(items)} 条 · 目标格式：{target}")
        lines = []
        for i, item in enumerate(items, 1):
            st.markdown(f"**[{i}]** {item}")
            lines.append(f"[{i}] {item}")
        st.download_button("下载结果", "\n".join(lines), file_name="references.txt")


def tab_about() -> None:
    st.subheader("关于 · 混合架构")
    st.markdown(
        """
本应用面向 **学习与科研赋能赛道**，围绕"写得更规范"提供论文提纲、学术润色、参考文献格式三大能力。

**云端 + 本地端混合架构（对应赛道附加分）**

| 任务 | 设计执行端 | 原因 |
| --- | --- | --- |
| 参考文献格式转换 | 本地规则引擎 | 确定性高、离线、保护未发表数据 |
| 学术润色 | 本地小模型 | 文稿隐私敏感、响应快 |
| 论文提纲生成 | 云端大模型 | 需要更强结构化与领域知识 |
| 任一端不可用 | 自动降级 | 保证演示不中断 |

> 当前实验阶段：`LLM_MODE=cloud`，所有模型调用直连云端，便于结果稳定可复现。
> 本地接口完整保留，演示混合架构时把 `LLM_MODE` 改为 `auto` 即可启用（无需改代码）。

- 本地端：Ollama（如 `qwen2.5:7b`）。
- 云端：任意 OpenAI 兼容接口（通义千问 / DeepSeek / 火山方舟 / OpenAI 等）。
- 开发：使用编程工具辅助。
        """
    )


def main() -> None:
    router = get_router()
    render_sidebar(router)
    st.title("学术写作规范助手")
    t1, t2, t3, t4 = st.tabs(["📑 提纲生成", "✒️ 学术润色", "📚 参考文献", "ℹ️ 关于"])
    with t1:
        tab_outline(router)
    with t2:
        tab_polish(router)
    with t3:
        tab_references(router)
    with t4:
        tab_about()


if __name__ == "__main__":
    main()
