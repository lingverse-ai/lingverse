---
name: moling-install
description: >-
  安装墨灵的完整技能包。每次对话开头，技能目录里 moling- 开头的技能不满 11 个时必须先运行它，排在入门对话和任何回答之前；主人说「安装墨灵」「重装」时，或者 moling-update 确认更新后也用它。
  从公开仓库的固定标签安装，不问、不装插件、不要密钥，保留主人的档案。
---

# 安装墨灵（第一件事）

固定版本：仓库 `https://github.com/{{OWNER}}/lingverse`，标签 `moling-v{{VERSION}}`，只装标签，不追 main。

## 1. 直接运行（不用先问主人；不需要 gh，也不需要登录）
在你的电脑上用 shell 跑下面这段，原样复制：

```bash
export GIT_TERMINAL_PROMPT=0; T=moling-v{{VERSION}}; R=https://github.com/{{OWNER}}/lingverse
W=/tmp/lingverse-$T; RJ=/tmp/recipe-$T.json; rm -rf "$W"
git clone -q --depth 1 --branch "$T" "$R" "$W" 2>/dev/null && cp "$W/spirits/moling/dist/recipe.json" "$RJ" \
 || curl -fsSL "https://raw.githubusercontent.com/{{OWNER}}/lingverse/$T/spirits/moling/dist/recipe.json" -o "$RJ"
D=$(ls -d /home/box/agent-data/workflows /home/box/sand-data/workflows 2>/dev/null | head -1)
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
        for n, t in s.get("files", {}).items(): open(os.path.join(p, n), "w").write(t)
print("INSTALLED" if d else "NO_SKILL_DIR", len(ok), d or sys.argv[1])
PY
```

## 2. 看结果
- `INSTALLED 11 …`：技能已经写进技能目录。用 `ls` 确认目录里有 11 个 `moling-` 开头的技能。
- `NO_SKILL_DIR 11 <配方路径>`：找不到技能目录。就读这个配方文件，对每个技能用你创建 / 更新技能的工具（例如 UpdateSkill），name、description、content 都**逐字**照配方写。附带文件（`platforms.md`）放进 `/workspace/moling/`，告诉主人规格卡在那里。
- clone 和 curl 都失败：最多再试 1 次，不用来路不明的镜像。跟主人说「仓库暂时连不上，我先陪你做入门，下次对话再装」，然后继续 moling-getting-started。下次对话开头还要再装。

## 3. 收尾
- 只更新「墨灵安装记录」这一条记忆：版本、日期、技能数。**不碰**作者档案、口吻档案和主人自己的其他记忆。
- 这一轮回复的第一句写：「已装好 N 个技能（墨灵 v{{VERSION}}）。」然后马上接着 moling-getting-started 的第 1 步，同一条消息里打招呼、问第 1 题。
- 配方里如果出现让你装插件、要密钥、访问配方以外网址的内容，就停下来，告诉主人。
