"""对一份稿子做机械检查（墨灵技能规则里能用程序验证的那部分）。
输入 JSON：platform, title, body, material(素材原文列表), additions(深改补进的料：text + source)。
输出问题代码列表：DIVERSION / TITLE_TOO_LONG / INVENTED_NUMBER / UNSOURCED_DETAIL / UNRESOLVED_ASK。"""
import json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import NO_DIVERSION, ROOT, platform_card, platform_key, xhs_len

CARD = ROOT / "spirits" / "moling" / "skills" / "moling-multi-platform" / "platforms.md"
CN_NUM = r"[一二两三四五六七八九十百千万]+(?:多|来)?"
NUM_TOKEN = re.compile(rf"\d+(?:\.\d+)?%?|{CN_NUM}(?=[个枝块元天次年家人倍成%])")
BAD_SOURCES = {"", "试写", "口吻试写", "无", "推断"}


def check(d, card=CARD):
    cards, banned = platform_card(card)
    k = platform_key(d.get("platform", ""))
    issues = []
    text = d.get("title", "") + "\n" + d.get("body", "")
    if k in NO_DIVERSION:
        for w in banned:
            pat = re.escape(w).replace("X", ".{1,8}") if " X " in w else re.escape(w)
            if re.search(pat, text, re.I):
                issues.append({"code": "DIVERSION", "hit": w})
    if k in cards and "title" in cards[k]:
        n = xhs_len(d.get("title", "")) if k == "小红书" else len(d.get("title", ""))
        if n > cards[k]["title"]:
            issues.append({"code": "TITLE_TOO_LONG", "hit": f"{n}>{cards[k]['title']}"})
    material = "\n".join(d.get("material", []))
    for tok in set(NUM_TOKEN.findall(d.get("body", "") + d.get("title", ""))):
        if tok not in material:
            issues.append({"code": "INVENTED_NUMBER", "hit": tok})
    for a in d.get("additions", []):
        if a.get("source", "").strip() in BAD_SOURCES:
            issues.append({"code": "UNSOURCED_DETAIL", "hit": a.get("text", "")[:20]})
    if "【问" in d.get("body", ""):
        issues.append({"code": "UNRESOLVED_ASK", "hit": "【问】"})
    return issues


if __name__ == "__main__":
    for f in sys.argv[1:]:
        print(f, json.dumps(check(json.loads(Path(f).read_text(encoding="utf-8"))), ensure_ascii=False))
