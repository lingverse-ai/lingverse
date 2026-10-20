#!/usr/bin/env bash
# 墨灵安装脚本（pack.py 填入版本后生成 dist/install.sh）。不需要 gh，不需要登录。
# 用法：curl -fsSL https://raw.githubusercontent.com/{{OWNER}}/lingverse/moling-v{{VERSION}}/spirits/moling/dist/install.sh | bash
export GIT_TERMINAL_PROMPT=0
T=moling-v{{VERSION}}; R=https://github.com/{{OWNER}}/lingverse
RAW=https://raw.githubusercontent.com/{{OWNER}}/lingverse/$T/spirits/moling/dist/recipe.json
W=/tmp/lingverse-$T; RJ=/tmp/recipe-$T.json; rm -rf "$W"
git clone -q --depth 1 --branch "$T" "$R" "$W" 2>/dev/null && cp "$W/spirits/moling/dist/recipe.json" "$RJ" \
  || curl -fsSL "$RAW" -o "$RJ" || { echo "FETCH_FAILED $R"; exit 1; }
D=${MOLING_SKILL_DIR:-$(ls -d /home/box/agent-data/workflows /home/box/sand-data/workflows 2>/dev/null | head -1)}
python3 - "$RJ" "$D" <<'PY'
import json, os, sys
r = json.load(open(sys.argv[1])); d = sys.argv[2]
assert r["version"] == "{{VERSION}}", "版本不对"
ok = [s for s in r["skills"] if s["name"].startswith("moling-") and len(s["content"].encode()) <= 6144]
assert len(ok) == len(r["skills"]), "技能校验没过"
if d:
    for s in ok:
        p = os.path.join(d, s["name"]); os.makedirs(p, exist_ok=True)
        open(os.path.join(p, "SKILL.md"), "w").write(s["content"])
        for n, t in s.get("files", {}).items():
            open(os.path.join(p, n), "w").write(t)
    print("INSTALLED", len(ok), d)
else:
    print("NO_SKILL_DIR", len(ok), sys.argv[1])
PY
