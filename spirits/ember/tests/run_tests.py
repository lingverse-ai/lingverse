"""流萤工具测试：python3 spirits/ember/tests/run_tests.py （需要 ffmpeg + numpy）"""
import json, subprocess, sys, tempfile
from pathlib import Path

SP = Path(__file__).resolve().parent.parent; T = SP / "tools"; M = SP / "music"
tmp = Path(tempfile.mkdtemp(prefix="ember-test-")); fails = []


def py(*a):
    r = subprocess.run([sys.executable, *map(str, a)], capture_output=True, text=True)
    if r.returncode: fails.append(f"{a[0].name if hasattr(a[0], 'name') else a[0]} 退出码 {r.returncode}: {r.stderr[-400:]}{r.stdout[-400:]}")
    return r


def probe(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height:format=duration", "-of", "json", str(p)],
                       capture_output=True, text=True)
    j = json.loads(r.stdout); v = [s for s in j["streams"] if "width" in s][0]
    return v["width"], v["height"], float(j["format"]["duration"])


# 1. beatmap：BPM ±2、拍点相位误差 < 40ms
for name, bpm in (("ember-neon-140", 140), ("ember-sunrise-120", 120), ("ember-lofi-90", 90)):
    out = tmp / f"{name}.json"; py(T / "beatmap.py", M / f"{name}.mp3", out, "--bpm", bpm)
    b = json.loads(out.read_text()); per = 60 / bpm
    if abs(b["bpm"] - bpm) > 2: fails.append(f"{name}: BPM {b['bpm']} ≠ {bpm}")
    errs = sorted(abs((t + per / 2) % per - per / 2) for t in b["beats"] if t > 5)
    if errs[len(errs) // 2] > 0.04: fails.append(f"{name}: 拍点中位误差 {errs[len(errs) // 2]:.3f}s")
    for k in ("duration", "beats", "downbeats", "accent_hits", "big_drops", "sections"):
        if k not in b: fails.append(f"{name}: beatmap 缺 {k}")
    print(f"beatmap {name}: {b['bpm']} BPM ok")

# 2. songcut：两段拼接的时长
out = tmp / "cut.wav"
py(T / "songcut.py", M / "ember-neon-140.mp3", out, "--ranges", "3.429-10.286,17.143-24.0")
if out.exists():
    d = probe_d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                                       capture_output=True, text=True).stdout)
    if abs(d - 13.714) > 0.05: fails.append(f"songcut 时长 {d:.3f} ≠ 13.714")
    print(f"songcut: {d:.3f}s ok")

# 3. plan：切点都在拍上、铺满
bm = tmp / "ember-neon-140.json"; pj = tmp / "plan.json"
py(T / "plan.py", bm, "--duration", "20", "--intro-bars", "1", "--out", pj)
p = json.loads(pj.read_text()); beats = json.loads(bm.read_text())["beats"]
for s in p["shots"][1:]:
    if min(abs(s["in"] - t) for t in beats) > 1e-3: fails.append(f"plan: 切点 {s['in']} 不在拍上")
if p["shots"][0]["in"] != 0 or abs(p["shots"][-1]["out"] - 20) > 1e-3: fails.append("plan: 没有铺满 0–20s")
print(f"plan: {len(p['shots'])} 个镜头 ok")

# 4. render：示例工程（半分辨率预览 + 粗剪），查分辨率和时长；qc PASS
ex = SP / "examples" / "project.example.json"
for flag, size in (("--preview", (960, 540)), ("--rough", (1920, 1080))):
    out = tmp / f"r{flag}.mp4"; py(T / "render.py", ex, out, flag)
    if out.exists():
        w, h, d = probe(out)
        if (w, h) != size or abs(d - 10) > 0.1: fails.append(f"render {flag}: {w}x{h} {d:.2f}s")
        print(f"render {flag}: {w}x{h} {d:.2f}s ok")
r = py(T / "qc.py", tmp / "r--preview.mp4", "--expect", "960x540", "--dur", "10")
print("qc:", r.stdout.strip().splitlines()[-1] if r.stdout else "")

# 5. 进阶工具：LUT 调色、对比图、放大兜底、HUD/逐字歌词/跑马灯/LUT 渲染；有 rembg 时测抠像 + 字在人身后
fr = tmp / "f.png"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=640x360:d=1", "-frames:v", "1", str(fr)], check=True)
for lut in ("v11-street", "cyber-neon", "guofeng-ink", "retro-film", "anime-bright", "voxel-pop"):
    if not (SP / "luts" / f"{lut}.cube").exists(): fails.append(f"缺 LUT {lut}")
py(T / "grade.py", fr, tmp / "g.png", "--lut", "retro-film"); py(T / "grade.py", fr, tmp / "cmp.png", "--compare")
small = tmp / "r--preview.mp4"; py(T / "upscale.py", small, tmp / "up.mp4", "--size", "1920x1080", "--force-ffmpeg")
if (tmp / "up.mp4").exists() and probe(tmp / "up.mp4")[:2] != (1920, 1080): fails.append("upscale 尺寸不对")
fx = json.loads(ex.read_text()); fx.update(audio=str(M / "ember-neon-140.mp3"), lut="v11-street", hud={"title": "TEST"},
    lyrics=[{"t": 2, "until": 3.4, "text": "ONE LINE"}], ticker=[{"from": 3.4, "to": 6.8, "text": "TICKER — "}])
try:
    import rembg  # noqa
    fx["shots"][2]["src"] = str(fr); fx["words"].append({"t": 3.5, "until": 5, "text": "BEHIND", "behind": True})
except ImportError:
    print("（没装 rembg，跳过抠像测试）")
fxj = tmp / "fx.json"; fxj.write_text(json.dumps(fx)); py(T / "render.py", fxj, tmp / "fx.mp4", "--preview")
if (tmp / "fx.mp4").exists(): print("fx render:", probe(tmp / "fx.mp4"))
print("grade / upscale / fx ok" if not fails else "")

# 6. 流程工具：进度表 / 决定记录 / 后台任务、自检、歌词对时间（--even）、鼓点顶镜头 + 片段、分享版、闪烁检查
pd = tmp / "proj"; py(T / "state.py", "gate", pd, "brief", "ok"); py(T / "state.py", "decide", pd, "主人：要 v11 同款")
st = py(T / "state.py", "status", pd).stdout
if "✅ 1" not in st or "下一步" not in st or "v11 同款" not in (pd / "DECISIONS.md").read_text(): fails.append("state.py 进度/记录不对")
lt = tmp / "l.txt"; lt.write_text("[Hook]\nFUTURE ON THE BLOCK\n未来就在眼前\n", encoding="utf-8")
py(T / "lyrics_align.py", M / "ember-neon-140.mp3", lt, tmp / "w.json", "--even", "1", "5")
wj = json.loads((tmp / "w.json").read_text()); 
if len(wj["words"]) != 10 or len(wj["lines"]) != 2: fails.append(f"lyrics_align 词数不对 {len(wj['words'])}")
au = json.loads(ex.read_text()); au["lyrics"] = wj["lines"]; au["punch_on"] = [2.0, 4.0]; au["audio"] = str(M / "ember-neon-140.mp3")
aj = tmp / "au.json"; aj.write_text(json.dumps(au, ensure_ascii=False))
r = py(T / "audit.py", aj, "--words", tmp / "w.json")
if "歌词关 2/2" not in r.stdout: fails.append("audit 歌词关没过：" + r.stdout[-200:])
au["lyrics"] = []; aj.write_text(json.dumps(au))
if subprocess.run([sys.executable, str(T / "audit.py"), str(aj), "--words", str(tmp / "w.json")], capture_output=True).returncode == 0: fails.append("audit 漏词没拦住")
py(T / "render.py", aj, tmp / "ex.mp4", "--preview", "--excerpt", "2-6")
if not (tmp / "ex.mp4").exists() or abs(probe(tmp / "ex.mp4")[2] - 4) > 0.15: fails.append("--excerpt 片段长度不对")
r = py(T / "qc.py", tmp / "ex.mp4", "--dur", "4")
if "BT.709" in r.stdout or "闪烁" in r.stdout: fails.append("qc 色彩标记/闪烁误报：" + r.stdout[-200:])
py(T / "qc.py", "share", tmp / "ex.mp4", tmp / "sh.mp4", "--max-mb", "2")
if not (tmp / "sh.mp4").exists() or (tmp / "sh.mp4").stat().st_size > 2.2e6: fails.append("分享版超大小")
print("state / audit / align / excerpt / share ok" if not fails else "")

print("FAILED:\n- " + "\n- ".join(fails) if fails else "ALL PASS")
sys.exit(1 if fails else 0)
