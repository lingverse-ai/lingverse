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

print("FAILED:\n- " + "\n- ".join(fails) if fails else "ALL PASS")
sys.exit(1 if fails else 0)
