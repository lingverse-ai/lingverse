#!/usr/bin/env bash
# 流萤安装脚本（pack.py 填入版本后生成 dist/install.sh）。不需要 gh，不需要登录。
# 用法：curl -fsSL https://raw.githubusercontent.com/{{OWNER}}/lingverse/ember-v{{VERSION}}/spirits/ember/dist/install.sh | bash
# 标签还没发布（预发布期）：curl -fsSL https://raw.githubusercontent.com/{{OWNER}}/lingverse/main/spirits/ember/dist/install.sh | EMBER_REF=main bash
#   不写 EMBER_REF 时先装标签，标签不存在会自动改装 main，并打印 REF_FALLBACK main。
# 做三件事：10 个技能写进技能目录；渲染工具、自带音乐和 LUT 放到 $EMBER_HOME（默认 /workspace/ember）；检查 ffmpeg / numpy / pillow / rembg + 两个抠像模型、faster-whisper（可选）。
export GIT_TERMINAL_PROMPT=0
T=ember-v{{VERSION}}; R=https://github.com/{{OWNER}}/lingverse
[ -n "$EMBER_REF" ] && T=$EMBER_REF
if [ -z "$EMBER_REF" ] && ! git ls-remote --exit-code --tags "$R" "$T" >/dev/null 2>&1 \
   && ! curl -fsI "https://raw.githubusercontent.com/{{OWNER}}/lingverse/$T/spirits/ember/dist/recipe.json" >/dev/null 2>&1; then
  echo "REF_FALLBACK main（标签 $T 还没发布）"; T=main
fi
echo "REF $T"
RAWB=https://raw.githubusercontent.com/{{OWNER}}/lingverse/$T/spirits/ember
W=/tmp/lingverse-$T; RJ=/tmp/recipe-$T.json; H=${EMBER_HOME:-/workspace/ember}; rm -rf "$W"
mkdir -p "$H/tools" "$H/music" "$H/luts" "$H/projects"
if git clone -q --depth 1 --branch "$T" "$R" "$W" 2>/dev/null; then
  cp "$W/spirits/ember/dist/recipe.json" "$RJ"
  cp "$W"/spirits/ember/tools/*.py "$H/tools/"; rm -rf "$H/tools/v11"; cp -r "$W"/spirits/ember/tools/v11 "$H/tools/v11"; cp "$W"/spirits/ember/music/* "$H/music/"; cp "$W"/spirits/ember/luts/* "$H/luts/"
else
  curl -fsSL "$RAWB/dist/recipe.json" -o "$RJ" || { echo "FETCH_FAILED $R"; exit 1; }
  for f in {{TOOL_FILES}}; do curl -fsSL "$RAWB/tools/$f" -o "$H/tools/$f" || echo "TOOL_FETCH_FAILED $f"; done
  for f in {{V11_FILES}}; do mkdir -p "$(dirname "$H/tools/v11/$f")"; curl -fsSL "$RAWB/tools/v11/$f" -o "$H/tools/v11/$f" || echo "TOOL_FETCH_FAILED v11/$f"; done
  for f in {{LUT_FILES}}; do curl -fsSL "$RAWB/luts/$f" -o "$H/luts/$f" || echo "LUT_FETCH_FAILED $f"; done
  for f in {{MUSIC_FILES}}; do curl -fsSL "$RAWB/music/$f" -o "$H/music/$f" || echo "MUSIC_FETCH_FAILED $f"; done
fi
D=${EMBER_SKILL_DIR:-$(ls -d /home/box/agent-data/workflows /home/box/sand-data/workflows 2>/dev/null | head -1)}
python3 - "$RJ" "$D" <<'PY'
import json, os, sys
r = json.load(open(sys.argv[1])); d = sys.argv[2]
assert r["version"] == "{{VERSION}}", "版本不对"
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
python3 -c "import PIL" 2>/dev/null || pip install -q pillow 2>/dev/null || pip install -q --user pillow 2>/dev/null || python3 -m pip install -q --break-system-packages pillow 2>/dev/null || echo "DEPS_MISSING pillow（pip install pillow）"
python3 -c "import rembg, onnxruntime" 2>/dev/null || pip install -q "rembg[cpu]" 2>/dev/null || pip install -q --user "rembg[cpu]" 2>/dev/null || python3 -m pip install -q --break-system-packages "rembg[cpu]" 2>/dev/null || echo "DEPS_MISSING rembg（v11 渲染要抠像：pip install \"rembg[cpu]\"）"
# 抠像模型：人 u2net_human_seg，宠物/物品 isnet-general-use（下载到 ~/.u2net，已有就跳过）
python3 -c "from rembg import new_session; [new_session(m) for m in ('u2net_human_seg', 'isnet-general-use')]" >/dev/null 2>&1 && echo "MODELS_OK u2net_human_seg isnet-general-use" || echo "MODELS_MISSING（首次渲染时会自动下载）"
python3 -c "import faster_whisper" 2>/dev/null || pip install -q faster-whisper 2>/dev/null || python3 -m pip install -q --break-system-packages faster-whisper 2>/dev/null || echo "OPTIONAL_MISSING faster-whisper（歌词自动对时间不可用，可用 --even 粗分配）"
python3 -c "import pypinyin" 2>/dev/null || pip install -q pypinyin 2>/dev/null || python3 -m pip install -q --break-system-packages pypinyin 2>/dev/null || echo "OPTIONAL_MISSING pypinyin（中文歌词体检少了押韵/多音字）"
ls "$H/tools/render.py" "$H/tools/v11/driver.py" "$H/tools/v11/matte_png.py" "$H/tools/v11/src/render_v11.py" "$H/tools/v11/src/fonts/Anton-Regular.ttf" >/dev/null 2>&1 && echo "TOOLS_OK $H/tools" || echo "TOOLS_MISSING $H/tools"
