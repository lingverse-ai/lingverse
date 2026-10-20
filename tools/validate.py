"""仓库检查。用法：python3 tools/validate.py [仓库根目录] [--online <spirit>]
--online：发布时推完标签再跑，检查该灵的配方和 install.sh 在标签下能打开。
失败时退出码为 1，并逐条列出问题。只用标准库。"""
import hashlib, json, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CONFIG, TEXT_SUFFIXES, RATIO, NUM, parse_frontmatter, platform_card, platform_key, tables

LIM = CONFIG["limits"]
SKIP_DIRS = {".git", "__pycache__"}


def text_files(root):
    for p in sorted(root.rglob("*")):
        if p.is_file() and not (set(p.relative_to(root).parts) & SKIP_DIRS) and p.suffix in TEXT_SUFFIXES:
            yield p


def norm(t):
    return "".join(t.lower().split())


def hash_hits(text, entries):
    t = norm(text)
    want = {(e["len"], e["sha256"]) for e in entries}
    hits = set()
    for n in {e["len"] for e in entries}:
        for i in range(len(t) - n + 1):
            if (n, hashlib.sha256(t[i:i + n].encode()).hexdigest()) in want:
                hits.add(t[i:i + n][:1] + "…")  # 不回显完整词
    return hits


def check_spirit(sp, errors, warns):
    name = sp.name
    skills_dir = sp / "skills"
    skill_names = {d.name for d in skills_dir.iterdir() if d.is_dir()}
    total = 0
    ver = (sp / "VERSION").read_text().strip() if (sp / "VERSION").exists() else None
    if not ver or not re.fullmatch(r"\d+\.\d+\.\d+", ver):
        errors.append(f"[version] {name}: VERSION 缺失或不是 x.y.z")
    for req in (f"{name}-install", f"{name}-update"):
        if req not in skill_names:
            errors.append(f"[skills] {name}: 缺少 {req}")
    # profile
    prof = sp / "profile.json"
    if not prof.exists():
        errors.append(f"[profile] {name}: 缺少 profile.json")
    else:
        b = prof.stat().st_size
        total += b
        pj = json.loads(prof.read_text(encoding="utf-8"))
        for k in ("name", "description", "intro", "instructions"):
            if not pj.get(k):
                errors.append(f"[profile] {name}: 缺少 {k}")
        if len(pj.get("description", "")) > LIM["description_chars"]:
            errors.append(f"[profile] description 超过 {LIM['description_chars']} 字符")
        if b > LIM["profile_bytes"]:
            errors.append(f"[budget] profile.json {b} 字节 > {LIM['profile_bytes']}")
    mem = sp / "memory.md"
    if mem.exists():
        total += mem.stat().st_size
    # skills
    corpus = {}
    for d in sorted(skills_dir.iterdir()):
        if not d.is_dir():
            continue
        f = d / "SKILL.md"
        if not f.exists():
            errors.append(f"[frontmatter] {d.name}: 没有 SKILL.md")
            continue
        text = f.read_text(encoding="utf-8")
        corpus[d.name] = text
        meta = parse_frontmatter(text)
        if not meta or not meta.get("name") or not meta.get("description"):
            errors.append(f"[frontmatter] {d.name}: 缺 name 或 description")
        else:
            if meta["name"] != d.name:
                errors.append(f"[frontmatter] {d.name}: name 是 {meta['name']}，和目录名不一致")
            if not meta["name"].startswith(name + "-"):
                errors.append(f"[frontmatter] {d.name}: name 必须以 {name}- 开头")
            if len(meta["description"]) > LIM["description_chars"]:
                errors.append(f"[frontmatter] {d.name}: description 超过 {LIM['description_chars']} 字符")
        for extra in d.iterdir():
            b = extra.stat().st_size
            if extra.name == "SKILL.md":
                total += b  # 合计只算导入时会回放的：SKILL.md + profile + memory
                if b > LIM["skill_bytes"]:
                    errors.append(f"[budget] {d.name}/SKILL.md {b} 字节 > {LIM['skill_bytes']}")
            elif b > LIM["reference_bytes"]:
                errors.append(f"[budget] {d.name}/{extra.name} 参考文件 {b} 字节 > {LIM['reference_bytes']}")
    if total > LIM["total_bytes"]:
        errors.append(f"[budget] {name} 合计 {total} 字节 > {LIM['total_bytes']}")
    # 交叉引用
    all_files = {p.name for p in sp.parent.parent.rglob("*") if p.is_file()}
    pool = dict(corpus)
    if mem.exists():
        pool["memory.md"] = mem.read_text(encoding="utf-8")
    for src, text in pool.items():
        for ref in set(re.findall(rf"\b{name}-[a-z][a-z-]*[a-z]\b", text)):
            if ref not in skill_names:
                errors.append(f"[xref] {src}: 引用了不存在的技能 {ref}")
        for ref in set(re.findall(r"`([\w./-]+\.md)`", text)):
            if Path(ref).name not in all_files:
                errors.append(f"[xref] {src}: 引用了不存在的文件 {ref}")
    # 平台数字一致
    card_path = next(skills_dir.rglob("platforms.md"), None)
    if card_path:
        cards, banned = platform_card(card_path)
        if len(banned) < 10:
            errors.append("[platform] platforms.md 里没解析出导流禁用词清单")
        for src, text in corpus.items():
            for row in tables(text):
                k = platform_key(row[0]) if row else None
                if not k or k not in cards:
                    continue
                c = cards[k]
                head = " ".join(row[1:2])
                m = NUM.search(head)
                if m and "title" in c and int(m.group(1)) != c["title"]:
                    errors.append(f"[platform] {src}: {k} 标题上限写 {m.group(1)}，规格卡是 {c['title']}")
                ratios = [RATIO.search(cell) for cell in row[1:]]
                ratios = [r.group(0) for r in ratios if r]
                if ratios and "cover" in c and ratios[0] != c["cover"]:
                    errors.append(f"[platform] {src}: {k} 封面写 {ratios[0]}，规格卡是 {c['cover']}")
    release_checks(sp, ver, skill_names, errors)
    return total


def release_checks(sp, ver, skill_names, errors, online=False):
    """发布检查（RELEASE.md 第 1 节）：防止「分享卡里没有技能」再发生。对每一位灵都跑。"""
    from pack import build
    name, owner, repo = sp.name, CONFIG["github_owner"], CONFIG["repo"]
    tag, inst = f"{name}-v{ver}", f"{name}-install"
    raw = f"https://raw.githubusercontent.com/{owner}/{repo}/{tag}/spirits/{name}/dist"
    E = lambda m: errors.append(f"[release] {name}: {m}")
    if not (sp / "install.sh").exists():
        return E("缺少 install.sh")
    try:
        out = {p.name: c for p, c in build(name).items()}
    except Exception as e:  # 比如某个 SKILL.md 头部坏了：上面的 [frontmatter] 已经报过
        return E(f"打包失败，先修上面的错误（{type(e).__name__}）")
    tpl, rec, sh = json.loads(out["template.json"]), json.loads(out["recipe.json"]), out.get("install.sh", "")
    if tpl.get("gettingStarted", {}).get("skill") != inst:
        E(f"gettingStarted 必须是 {inst}")
    card = {s["name"] for s in tpl.get("skills", [])}
    if inst not in card or f"{name}-getting-started" not in card:
        E(f"分享卡技能必须含 {inst} 和 {name}-getting-started")
    mems = tpl.get("memory", [])
    if not mems or any(m.get("kind") != "profile" for m in mems):
        E("安装记忆必须是 kind=profile")
    store = tpl.get("_meta", {}).get("storefront", "")
    for need, what in ((inst, "安装技能名"), (f"github.com/{owner}/{repo}", "仓库"), (tag, "标签")):
        if need not in store:
            E(f"店面介绍（profile.description）没写{what} {need}")
    if f"T={tag}" not in sh or "{{" in sh:
        E(f"install.sh 的标签不是 {tag}（或还有没填的占位符）")
    n = len(rec["skills"])
    one_liner = f"{raw}/install.sh | bash"
    for label, text in (("人设 instructions", tpl["profile"]["description"]), ("安装记忆", " ".join(m["content"] for m in mems))):
        for need in (one_liner, f"{raw}/recipe.json", f"https://github.com/{owner}/{repo}", f"{n} 个技能"):
            if need not in text:
                E(f"{label} 缺少 {need}")
    ic = next((s["content"] for s in rec["skills"] if s["name"] == inst), "")
    for need in (one_liner, f"{raw}/recipe.json", "已装好 N 个技能", "NO_SKILL_DIR"):
        if need not in ic:
            E(f"{inst} 缺少 {need}")
    if online:
        import urllib.request
        for u in (f"{raw}/recipe.json", f"{raw}/install.sh"):
            try:
                with urllib.request.urlopen(urllib.request.Request(u, method="HEAD"), timeout=15) as r:
                    ok = r.status == 200
            except Exception:
                ok = False
            if not ok:
                E(f"配方地址打不开（标签推了吗？）：{u}")


def main(root):
    root = Path(root).resolve()
    errors, warns = [], []
    hashes = json.loads((root / "tools" / "scrub_hashes.json").read_text(encoding="utf-8"))
    for p in text_files(root):
        rel = p.relative_to(root)
        if rel.as_posix() == "tools/scrub_hashes.json":
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        allow = set(CONFIG.get("private_allow", {}).get(rel.as_posix(), []))
        if hash_hits(text, [e for e in hashes["private"] if e["sha256"] not in allow]):
            errors.append(f"[private] {rel}: 命中私人词名单")
        if hash_hits(text, hashes["creators"]):
            errors.append(f"[trace] {rel}: 命中其他创作者名单")
        if rel.parts[0] not in ("tools", "tests") and re.search(r"(?<![\w-])refs/", text):
            errors.append(f"[refs] {rel}: 还有 refs/ 路径")
    totals = {}
    for sp in sorted((root / "spirits").iterdir()):
        if sp.is_dir():
            totals[sp.name] = check_spirit(sp, errors, warns)
    for sp in ONLINE:  # --online <spirit>：发布流程里，推完标签后检查配方能不能拉到
        d = root / "spirits" / sp
        release_checks(d, (d / "VERSION").read_text().strip(), set(), errors, online=True)
    if CONFIG["github_owner"] in ("", "OWNER_PENDING"):
        warns.append("[owner] tools/config.json 的 github_owner 还没定")
    for w in warns:
        print("WARN ", w)
    for e in errors:
        print("FAIL ", e)
    print(f"{'OK' if not errors else 'FAILED'}：{len(errors)} 个错误，{len(warns)} 个提醒｜" + "，".join(f"{k} {v} 字节" for k, v in totals.items()))
    return 1 if errors else 0


ONLINE = []

if __name__ == "__main__":
    a = sys.argv[1:]
    if "--online" in a:  # python3 tools/validate.py --online ember
        i = a.index("--online"); ONLINE.append(a[i + 1]); del a[i:i + 2]
    sys.exit(main(a[0] if a else Path(__file__).resolve().parent.parent))
