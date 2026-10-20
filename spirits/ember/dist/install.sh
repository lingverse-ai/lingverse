#!/usr/bin/env bash
# 流萤安装脚本（pack.py 填入版本后生成 dist/install.sh）。不需要 gh，不需要登录。
# 用法：curl -fsSL https://raw.githubusercontent.com/lingverse-ai/lingverse/ember-v0.1.0/spirits/ember/dist/install.sh | bash
# 做三件事：10 个技能写进技能目录；渲染工具、自带音乐和 LUT 放到 $EMBER_HOME（默认 /workspace/ember）；检查 ffmpeg / numpy / rembg、faster-whisper（可选）。
export GIT_TERMINAL_PROMPT=0
T=ember-v0.1.0; R=https://github.com/lingverse-ai/lingverse
RAWB=https://raw.githubusercontent.com/lingverse-ai/lingverse/$T/spirits/ember
W=/tmp/lingverse-$T; RJ=/tmp/recipe-$T.json; H=${EMBER_HOME:-/workspace/ember}; rm -rf "$W"
mkdir -p "$H/tools" "$H/music" "$H/luts" "$H/projects"
if git clone -q --depth 1 --branch "$T" "$R" "$W" 2>/dev/null; then
  cp "$W/spirits/ember/dist/recipe.json" "$RJ"
  cp "$W"/spirits/ember/tools/*.py "$H/tools/"; cp "$W"/spirits/ember/music/* "$H/music/"; cp "$W"/spirits/ember/luts/* "$H/luts/"
else
  curl -fsSL "$RAWB/dist/recipe.json" -o "$RJ" || { echo "FETCH_FAILED $R"; exit 1; }
  for f in audit.py beatmap.py fonts.py grade.py lyrics_align.py make_luts.py make_starter_music.py matte.py plan.py qc.py render.py songcut.py state.py upscale.py; do curl -fsSL "$RAWB/tools/$f" -o "$H/tools/$f" || echo "TOOL_FETCH_FAILED $f"; done
  for f in anime-bright.cube cyber-neon.cube guofeng-ink.cube retro-film.cube v11-street.cube voxel-pop.cube; do curl -fsSL "$RAWB/luts/$f" -o "$H/luts/$f" || echo "LUT_FETCH_FAILED $f"; done
  for f in LICENSES.md ember-lofi-90.mp3 ember-neon-140.mp3 ember-sunrise-120.mp3; do curl -fsSL "$RAWB/music/$f" -o "$H/music/$f" || echo "MUSIC_FETCH_FAILED $f"; done
fi
D=${EMBER_SKILL_DIR:-$(ls -d /home/box/agent-data/workflows /home/box/sand-data/workflows 2>/dev/null | head -1)}
python3 - "$RJ" "$D" <<'PY'
import json, os, sys
r = json.load(open(sys.argv[1])); d = sys.argv[2]
assert r["version"] == "0.1.0", "版本不对"
ok = [s for s in r["skills"] if s["name"].startswith("ember-") and len(s["content"].encode()) <= 6144]
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
command -v ffmpeg >/dev/null || echo "DEPS_MISSING ffmpeg（sudo apt-get install -y ffmpeg 或 brew install ffmpeg）"
python3 -c "import numpy" 2>/dev/null || pip install -q numpy 2>/dev/null || pip install -q --user numpy 2>/dev/null || python3 -m pip install -q --break-system-packages numpy 2>/dev/null || echo "DEPS_MISSING numpy（pip install numpy）"
python3 -c "import rembg" 2>/dev/null || pip install -q "rembg[cpu]" 2>/dev/null || python3 -m pip install -q --break-system-packages "rembg[cpu]" 2>/dev/null || echo "OPTIONAL_MISSING rembg（抠像不可用，其余功能正常）"
python3 -c "import faster_whisper" 2>/dev/null || pip install -q faster-whisper 2>/dev/null || python3 -m pip install -q --break-system-packages faster-whisper 2>/dev/null || echo "OPTIONAL_MISSING faster-whisper（歌词自动对时间不可用，可用 --even 粗分配）"
ls "$H/tools/render.py" >/dev/null 2>&1 && echo "TOOLS_OK $H/tools" || echo "TOOLS_MISSING $H/tools"
