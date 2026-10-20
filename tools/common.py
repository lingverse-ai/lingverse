"""validate / pack / check_draft 共用的小工具。只用标准库。"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "tools" / "config.json").read_text(encoding="utf-8"))
TEXT_SUFFIXES = {".md", ".json", ".yml", ".yaml", ".py", ".txt", ".sh", ""}

# 平台关键词 → 规格卡里的章节标题关键词
PLATFORMS = {"X": "X Article", "公众号": "公众号", "抖音": "抖音", "小红书": "小红书", "知乎": "知乎", "微博": "微博"}
NO_DIVERSION = {"抖音", "小红书", "微博"}
NUM = re.compile(r"(?:≤|约)\s*(\d+)")
RATIO = re.compile(r"\d+(?:\.\d+)?:\d+")


def parse_frontmatter(text):
    """解析 SKILL.md 开头的 YAML 子集：name 和 description（支持 >- 折叠块）。"""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    meta, key, buf = {}, None, []
    for line in text[4:end].splitlines():
        m = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if m:
            if key:
                meta[key] = " ".join(buf).strip()
            key, val = m.group(1), m.group(2).strip()
            buf = [] if val in (">-", ">", "|") else [val]
        elif key:
            buf.append(line.strip())
    if key:
        meta[key] = " ".join(buf).strip()
    return meta


def platform_key(cell):
    for k in PLATFORMS:
        if k in cell:
            return k
    return None


def platform_card(path):
    """读 platforms.md：每个平台的标题上限、封面比例，以及禁用词清单。"""
    text = Path(path).read_text(encoding="utf-8")
    cards, cur = {}, None
    for line in text.splitlines():
        if line.startswith("## "):
            cur = platform_key(line)
            if cur:
                cards[cur] = {}
            continue
        if not cur:
            continue
        if line.startswith("- 标题") and "title" not in cards[cur]:
            m = NUM.search(line)
            if m:
                cards[cur]["title"] = int(m.group(1))
        if line.startswith("- 封面") and "cover" not in cards[cur]:
            m = RATIO.search(line)
            if m:
                cards[cur]["cover"] = m.group(0)
    banned = []
    m = re.search(r"导流禁用词搜索清单\*\*[^：:]*[：:](.+)", text)
    if m:
        for part in re.split(r"[、，,]", m.group(1)):
            part = part.strip().strip("。").strip()
            part = re.sub(r"^「|」$", "", part)
            if part:
                banned.append(part)
    return cards, banned


def tables(text):
    """返回 Markdown 表格的数据行（单元格列表），跳过表头和分隔行。"""
    rows, header_seen = [], False
    for line in text.splitlines():
        if not line.startswith("|"):
            header_seen = False
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            header_seen = True
            continue
        if header_seen:
            rows.append(cells)
    return rows


def xhs_len(s):
    """小红书计数：英文和数字算 0.5 个字。"""
    return sum(0.5 if re.match(r"[0-9A-Za-z]", ch) else 1 for ch in s)
