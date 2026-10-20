"""把一位灵的文件夹打包成模板配方。
用法：python3 tools/pack.py <spirit> [--check]
产出 spirits/<spirit>/dist/recipe.json（全部技能，安装技能用）和 template.json（薄模板：安装技能 + 入门对话 + 记忆）。
--check：只比对，不写文件；dist 不是最新就退出码 1（CI 用）。"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CONFIG, ROOT, parse_frontmatter


def build(spirit):
    sp = ROOT / "spirits" / spirit
    version = (sp / "VERSION").read_text().strip()
    subst = {"{{OWNER}}": CONFIG["github_owner"], "{{VERSION}}": version}

    def fill(t):
        for k, v in subst.items():
            t = t.replace(k, v)
        return t

    skills = []
    for d in sorted((sp / "skills").iterdir()):
        if not d.is_dir():
            continue
        text = fill((d / "SKILL.md").read_text(encoding="utf-8"))
        meta = parse_frontmatter(text)
        files = {f.name: fill(f.read_text(encoding="utf-8")) for f in sorted(d.iterdir()) if f.name != "SKILL.md"}
        skills.append({"name": meta["name"], "description": meta["description"], "content": text, "files": files})
    profile = json.loads(fill((sp / "profile.json").read_text(encoding="utf-8")))
    memory = fill((sp / "memory.md").read_text(encoding="utf-8"))
    recipe = {"spirit": spirit, "version": version, "repo": f"https://github.com/{CONFIG['github_owner']}/{CONFIG['repo']}",
              "tag": f"{spirit}-v{version}", "profile": profile, "memory": memory, "skills": skills}
    # 分享卡：按 Grok Bot 模板的字段（profile / memory / skills / gettingStarted）。
    # 第一轮由 gettingStarted 指向安装技能，保证先装再入门。
    card_skills = (f"{spirit}-install", f"{spirit}-getting-started")
    thin = {
        "profile": {"name": profile["name"], "description": profile["instructions"]},
        "memory": [{"kind": "log", "content": memory}],
        "skills": [{k: s[k] for k in ("name", "description", "content")} for s in skills if s["name"] in card_skills],
        "gettingStarted": {"skill": f"{spirit}-install"},
        "_meta": {"spirit": spirit, "version": version, "tag": recipe["tag"], "storefront": profile["description"]},
    }
    dump = lambda o: json.dumps(o, ensure_ascii=False, indent=1) + "\n"
    out = {sp / "dist" / "recipe.json": dump(recipe), sp / "dist" / "template.json": dump(thin)}
    if (sp / "install.sh").exists():
        out[sp / "dist" / "install.sh"] = fill((sp / "install.sh").read_text(encoding="utf-8"))
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check = "--check" in sys.argv
    spirits = args or [p.name for p in (ROOT / "spirits").iterdir() if p.is_dir()]
    stale = []
    for s in spirits:
        for path, content in build(s).items():
            if check:
                if not path.exists() or path.read_text(encoding="utf-8") != content:
                    stale.append(path.relative_to(ROOT))
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                print(f"wrote {path.relative_to(ROOT)} ({len(content.encode())} bytes)")
    if stale:
        print("FAIL dist 不是最新，请运行 python3 tools/pack.py：", *stale)
        return 1
    if check:
        print("OK dist 是最新的")
    return 0


if __name__ == "__main__":
    sys.exit(main())
