"""参考文献格式转换（规则化、完全离线、确定性强）。

支持输入：BibTeX；或自由文本（在模型可用时先转 BibTeX，再走规则化格式化）。
支持输出：GB/T 7714-2015（数字格式）、APA 7th。

这是本项目最适合放在"本地端"的能力：无需联网、保护未发表数据、结果可预期。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

try:
    import bibtexparser
except Exception:  # 允许在未安装时导入本模块（UI 会给出提示）
    bibtexparser = None  # type: ignore

from .llm import LLMRouter

TARGETS = ["GB/T 7714-2015", "APA 7th"]


@dataclass
class Reference:
    entry_type: str
    fields: Dict[str, str]

    def get(self, key: str, default: str = "") -> str:
        return (self.fields.get(key) or default).strip()


# ----------------------- 解析 -----------------------
def parse_bibtex(text: str) -> List[Reference]:
    if bibtexparser is None:
        raise RuntimeError("未安装 bibtexparser，请先 pip install bibtexparser")
    db = bibtexparser.loads(text)
    refs: List[Reference] = []
    for e in db.entries:
        entry_type = (e.get("ENTRYTYPE") or "misc").lower()
        fields = {k.lower(): v for k, v in e.items() if k not in ("ENTRYTYPE", "ID")}
        refs.append(Reference(entry_type=entry_type, fields=fields))
    return refs


def _split_authors(author_field: str) -> List[Tuple[str, List[str]]]:
    """返回 [(姓, [名的各部分]), ...]，兼容 'Last, First' 与 'First Last'。"""
    result: List[Tuple[str, List[str]]] = []
    if not author_field:
        return result
    for raw in author_field.replace("\n", " ").split(" and "):
        name = raw.strip()
        if not name:
            continue
        if "," in name:
            last, given = name.split(",", 1)
            last = last.strip()
            givens = [g for g in given.replace("-", " ").split() if g]
        else:
            tokens = name.split()
            last = tokens[-1] if tokens else name
            givens = [g for g in " ".join(tokens[:-1]).replace("-", " ").split() if g]
        result.append((last, givens))
    return result


def _initials(givens: List[str], with_dot: bool) -> List[str]:
    out = []
    for g in givens:
        ch = g[0].upper()
        out.append(f"{ch}." if with_dot else ch)
    return out


# ----------------------- GB/T 7714 -----------------------
def _authors_gbt(author_field: str) -> str:
    people = _split_authors(author_field)
    if not people:
        return ""
    names = []
    for last, givens in people:
        initials = " ".join(_initials(givens, with_dot=False))
        names.append(f"{last} {initials}".strip())
    if len(names) > 3:
        return ", ".join(names[:3]) + ", 等"
    return ", ".join(names)


def _pages(value: str) -> str:
    return value.replace("--", "-").strip()


def format_gbt7714(ref: Reference) -> str:
    authors = _authors_gbt(ref.get("author"))
    title = ref.get("title")
    year = ref.get("year")
    t = ref.entry_type

    if t == "article":
        vol = ref.get("volume")
        num = ref.get("number")
        vol_num = vol + (f"({num})" if num else "") if vol else ""
        pages = _pages(ref.get("pages"))
        tail = ", ".join(p for p in [year, vol_num] if p)
        s = f"{authors}. {title}[J]. {ref.get('journal')}"
        if tail:
            s += f", {tail}"
        if pages:
            s += f": {pages}"
        return s + "."

    if t == "book":
        addr = ref.get("address")
        pub = ref.get("publisher")
        place = f"{addr}: {pub}" if addr else pub
        return f"{authors}. {title}[M]. {place}, {year}.".replace(" ,", ",")

    if t in ("inproceedings", "conference"):
        addr = ref.get("address")
        pub = ref.get("publisher")
        place = f"{addr}: {pub}" if addr else pub
        pages = _pages(ref.get("pages"))
        s = f"{authors}. {title}[C]//{ref.get('booktitle')}."
        if place:
            s += f" {place},"
        s += f" {year}"
        if pages:
            s += f": {pages}"
        return s + "."

    if t in ("phdthesis", "mastersthesis"):
        school = ref.get("school")
        addr = ref.get("address")
        place = f"{addr}: {school}" if addr else school
        return f"{authors}. {title}[D]. {place}, {year}.".replace(" ,", ",")

    url = ref.get("url")
    s = f"{authors}. {title}[EB/OL]. {year}."
    if url:
        s += f" {url}."
    return s


# ----------------------- APA 7th -----------------------
def _authors_apa(author_field: str) -> str:
    people = _split_authors(author_field)
    if not people:
        return ""
    names = []
    for last, givens in people:
        initials = " ".join(_initials(givens, with_dot=True))
        names.append(f"{last}, {initials}".strip().rstrip(","))
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + ", & " + names[-1]


def format_apa(ref: Reference) -> str:
    authors = _authors_apa(ref.get("author"))
    year = ref.get("year") or "n.d."
    title = ref.get("title")
    t = ref.entry_type
    doi = ref.get("doi")
    doi_str = f" https://doi.org/{doi}" if doi else ""

    if t == "article":
        vol = ref.get("volume")
        num = ref.get("number")
        vol_num = f"{vol}({num})" if num else vol
        pages = _pages(ref.get("pages"))
        s = f"{authors} ({year}). {title}. {ref.get('journal')}"
        if vol_num:
            s += f", {vol_num}"
        if pages:
            s += f", {pages}"
        return s + "." + doi_str

    if t == "book":
        return f"{authors} ({year}). {title}. {ref.get('publisher')}." + doi_str

    if t in ("inproceedings", "conference"):
        pages = _pages(ref.get("pages"))
        s = f"{authors} ({year}). {title}. In {ref.get('booktitle')}"
        if pages:
            s += f" (pp. {pages})"
        pub = ref.get("publisher")
        if pub:
            s += f". {pub}"
        return s + "." + doi_str

    if t in ("phdthesis", "mastersthesis"):
        kind = "Doctoral dissertation" if t == "phdthesis" else "Master's thesis"
        return f"{authors} ({year}). {title} [{kind}]. {ref.get('school')}." + doi_str

    url = ref.get("url")
    s = f"{authors} ({year}). {title}."
    if url:
        s += f" {url}"
    return s


# ----------------------- 对外接口 -----------------------
def format_reference(ref: Reference, target: str) -> str:
    if target.startswith("GB/T"):
        return format_gbt7714(ref)
    return format_apa(ref)


def freeform_to_bibtex(text: str, router: Optional[LLMRouter] = None) -> Optional[str]:
    """自由文本 -> BibTeX（需模型）。模型不可用时返回 None。"""
    router = router or LLMRouter()
    system = "你是文献信息抽取专家，只输出规范 BibTeX，不要任何解释。"
    user = (
        "把下面的参考文献条目转换为 BibTeX（每条一个 entry，类型尽量准确）：\n\n" + text.strip()
    )
    result = router.chat(system, user, prefer="local", temperature=0.0)
    if not result.ok or "@" not in result.text:
        return None
    return result.text


def convert(text: str, target: str, router: Optional[LLMRouter] = None) -> Tuple[List[str], str]:
    """返回 (格式化后的条目列表, 提示信息)。"""
    text = (text or "").strip()
    if not text:
        return [], "请输入参考文献内容。"

    note = ""
    if "@" not in text:
        bib = freeform_to_bibtex(text, router=router)
        if bib is None:
            return [], "未检测到 BibTeX。请粘贴 BibTeX，或配置模型以支持自由文本解析。"
        text = bib
        note = "已通过模型将自由文本转换为 BibTeX 后再规则化格式化。"

    refs = parse_bibtex(text)
    if not refs:
        return [], "未能解析出任何文献条目，请检查 BibTeX 格式。"
    return [format_reference(r, target) for r in refs], note
