"""剪辑工程自检（出片前跑）：把"好看的 MV"变成能检查的规矩。PASS 后写 audit.ok。
用法：python3 audit.py project.json [--beatmap beatmap.json] [--words words.json]
检查：镜头铺满不留缝；每条素材只用一次；镜头不太碎也不太拖；切点落在拍子上；
     大字落在拍子或唱到的词上；一段字卡不跨切点；每句歌词都上了屏（歌词关）；
     开头 2 秒内有钩子（大字或闪）；层数（画面 + 字/HUD/跑马灯 + 颗粒/调色）≥3；闪烁不过密。"""
import json, sys
from pathlib import Path

a = sys.argv[1:]
if not a: sys.exit(__doc__)
opt = lambda k: a[a.index(k) + 1] if k in a else None
pj = Path(a[0]); p = json.loads(pj.read_text(encoding="utf-8")); base = pj.parent
bm = opt("--beatmap") or (base / "beatmap.json" if (base / "beatmap.json").exists() else None)
wj = opt("--words") or (base / "words.json" if (base / "words.json").exists() else None)
beats = json.loads(Path(bm).read_text())["beats"] if bm else []
words = json.loads(Path(wj).read_text(encoding="utf-8")) if wj else None
bad, warn = [], []
near = lambda t, xs, tol=0.07: any(abs(t - x) <= tol for x in xs)
shots = sorted(p["shots"], key=lambda s: s["in"]); dur = p["duration"]

if abs(shots[0]["in"]) > 1e-3 or abs(shots[-1]["out"] - dur) > 0.05: bad.append("镜头没有从 0 铺满到结尾")
for x, y in zip(shots, shots[1:]):
    if abs(x["out"] - y["in"]) > 1e-3: bad.append(f"{x['out']}s 处有缝/重叠")
srcs = [s.get("src") for s in shots if s.get("src") not in (None, "INTRO_CARD")]
dup = sorted({s for s in srcs if srcs.count(s) > 1 and not any(t.get("src") == s and t.get("src_start") for t in shots)})
if dup: warn.append(f"同一素材重复用（不同 src_start 可以）：{dup}")
lens = [s["out"] - s["in"] for s in shots]
if min(lens) < 0.25: bad.append(f"有镜头短于 0.25s（{min(lens):.2f}s），看不清")
if max(lens) > 4.5 and not any(s.get("src") == "INTRO_CARD" for s in shots): warn.append(f"有镜头长 {max(lens):.1f}s，副歌里会拖")
if len(shots) < dur / 3.0: warn.append(f"{len(shots)} 个镜头对 {dur:.0f}s 偏少（v11 约每 1–2 拍一切）")
if beats:
    off = [s["in"] for s in shots[1:] if not near(s["in"], beats)]
    if off: bad.append(f"{len(off)} 个切点不在拍子上：{off[:6]}（用 beatmap 的 beats 或 --shift 修相位）")
wt = [w["t0"] for w in words["words"]] if words else []
for w in p.get("words", []):
    if beats and not near(w["t"], beats) and not near(w["t"], wt, 0.09): warn.append(f"字卡「{w['text']}」{w["t"]}s 既不在拍上也不在唱词上")
    for s in shots:
        if w["t"] < s["out"] - 0.05 < w.get("until", w["t"] + 0.5) - 0.1 and not w.get("span"): warn.append(f"字卡「{w['text']}」跨过 {s['out']}s 的切点"); break
if words:
    import re
    cl = lambda x: re.sub(r"[^\w\u4e00-\u9fff]+", " ", x.lower()).strip()
    shown = cl(" ".join([w.get("text", "") for w in p.get("words", [])] + [l.get("text", "") for l in p.get("lyrics", [])]))
    miss = [l["text"] for l in words["lines"] if l["t"] < dur and cl(l["text"]) not in shown]
    n = len([l for l in words["lines"] if l["t"] < dur])
    print(f"歌词关 {n - len(miss)}/{n}")
    if miss: bad.append(f"这些歌词没上屏：{miss[:4]}（放进 lyrics，或主人说了不要歌词就删 words.json）")
if not any(w["t"] < 2.0 for w in p.get("words", [])) and not any(t < 2.0 for t in p.get("flash_on", [])) and not any(s.get("src") == "INTRO_CARD" for s in shots):
    warn.append("开头 2 秒没有钩子（大字/闪/标题卡），刷视频的人会划走")
layers = 1 + bool(p.get("words") or p.get("lyrics")) + bool(p.get("hud") or p.get("ticker")) + bool(p.get("grain", 4) or p.get("lut"))
if layers < 3: warn.append(f"只有 {layers} 层（画面/字/HUD 或跑马灯/颗粒或调色），v11 级别要 ≥3")
fl = sorted(p.get("flash_on", []))
if any(fl[i + 3] - fl[i] < 1.0 for i in range(len(fl) - 3)): bad.append("1 秒内超过 3 次白闪（光敏风险）")
if p.get("endcard") is None: warn.append("没有片尾卡")
for m in warn: print("提醒:", m)
if bad:
    print("不通过:\n- " + "\n- ".join(bad)); (base / "audit.ok").unlink(missing_ok=True); sys.exit(1)
(base / "audit.ok").write_text("PASS\n"); print("PASS")
