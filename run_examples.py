"""读取 examples/ 下的输入样例，依次测试三大功能并保存结果。

用法：
  python run_examples.py                  # 运行全部（按 .env 的 LLM_MODE，默认 cloud）
  python run_examples.py --task references # 仅测参考文献（纯本地规则、最快）
  python run_examples.py --task polish --style 简洁
  LLM_MODE=mock python run_examples.py    # 离线快速自测（不调模型，参考文献仍完全可用）

结果默认写入 examples/output/，加 --no-save 可关闭。
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from core.config import get_settings
from core.llm import LLMRouter
from core.outline import generate_outline
from core.polish import polish_text
from core.references import TARGETS, convert

ROOT = Path(__file__).resolve().parent
EX = ROOT / "examples"
OUT = EX / "output"


def banner(title: str) -> None:
    print("\n" + "=" * 64)
    print(title)
    print("=" * 64)


def run_references(router: LLMRouter, save: bool) -> None:
    bib = (EX / "references_input.bib").read_text(encoding="utf-8")
    for target in TARGETS:
        banner(f"参考文献格式转换 | 目标：{target}")
        start = time.time()
        items, note = convert(bib, target, router=router)
        if note:
            print(f"说明：{note}")
        print(f"共 {len(items)} 条 | 耗时 {time.time() - start:.2f}s\n")
        lines = []
        for i, item in enumerate(items, 1):
            print(f"[{i}] {item}")
            lines.append(f"[{i}] {item}")
        if save and items:
            fn = "references_gbt7714.txt" if target.startswith("GB/T") else "references_apa.txt"
            (OUT / fn).write_text("\n".join(lines), encoding="utf-8")


def run_polish(router: LLMRouter, save: bool, style: str, lang: str) -> None:
    text = (EX / "polish_input.txt").read_text(encoding="utf-8").strip()
    banner(f"学术润色 | 风格：{style} | 语言：{lang}")
    print(f"原文：{text}\n")
    start = time.time()
    res = polish_text(text, style, lang, router=router)
    print(f"执行端：{res.provider} | ok={res.ok} | 耗时 {time.time() - start:.1f}s\n")
    print(res.text)
    if save:
        (OUT / "polish_output.md").write_text(res.text, encoding="utf-8")


def run_outline(router: LLMRouter, save: bool) -> None:
    data = json.loads((EX / "outline_input.json").read_text(encoding="utf-8"))
    banner(f"提纲生成 | 题目：{data.get('topic', '')}")
    start = time.time()
    res = generate_outline(
        data.get("topic", ""),
        data.get("field", "通用"),
        data.get("paper_type", "学术论文"),
        data.get("extra", "无"),
        router=router,
    )
    print(f"执行端：{res.provider} | ok={res.ok} | 耗时 {time.time() - start:.1f}s\n")
    print(res.text)
    if save:
        (OUT / "outline_output.md").write_text(res.text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="学术写作规范助手 · 样例测试脚本")
    parser.add_argument(
        "--task",
        choices=["all", "references", "polish", "outline"],
        default="all",
        help="选择要测试的功能（默认 all）",
    )
    parser.add_argument("--style", default="严谨", help="润色风格：严谨/简洁/流畅/降AI味")
    parser.add_argument("--lang", default="中文", help="润色语言：中文/英文")
    parser.add_argument("--no-save", action="store_true", help="不保存结果到 examples/output/")
    args = parser.parse_args()

    save = not args.no_save
    if save:
        OUT.mkdir(parents=True, exist_ok=True)

    router = LLMRouter(get_settings())
    status = router.status()
    print(f"运行配置：mode={status['mode']} | 云端可用={status['cloud']} | 本地可用={status['local']}")
    print(f"云端模型={status['cloud_model']} | 本地模型={status['local_model']}")

    # 顺序：先快后慢（参考文献为本地规则、最快；提纲为长文本、最慢）
    if args.task in ("all", "references"):
        run_references(router, save)
    if args.task in ("all", "polish"):
        run_polish(router, save, args.style, args.lang)
    if args.task in ("all", "outline"):
        run_outline(router, save)

    if save:
        print(f"\n结果已保存至：{OUT}")


if __name__ == "__main__":
    main()
