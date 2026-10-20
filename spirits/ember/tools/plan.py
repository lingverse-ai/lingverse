"""beatmap.json → 卡点切点 + project.json 骨架（给 render.py 用）。
用法：python3 plan.py beatmap.json --duration 30 [--intro-bars 2] [--bars 1] [--fast-from 15 --fast-bars 0.5] [--out project.json]
规则：切点都落在重拍上（--fast-bars 0.5 时用半小节=第 3 拍）；开场 intro-bars 小节留给纯字幕；最后一个镜头到 duration。"""
import argparse, json

ap = argparse.ArgumentParser()
ap.add_argument("beatmap"); ap.add_argument("--duration", type=float)
ap.add_argument("--intro-bars", type=int, default=0, help="开场纯字幕占几个小节（0 = 不要）")
ap.add_argument("--bars", type=float, default=1, help="正常段每个镜头几小节（1 或 2）")
ap.add_argument("--fast-from", type=float, default=None, help="从第几秒起加快切换（副歌/drop）")
ap.add_argument("--fast-bars", type=float, default=0.5)
ap.add_argument("--audio", default="audio/song.mp3"); ap.add_argument("--out", default="project.json")
g = ap.parse_args()
b = json.load(open(g.beatmap)); dur = g.duration or b["duration"]
beats = [t for t in b["beats"] if t < dur - 0.3]
db = set(b["downbeats"]); idx = [i for i, t in enumerate(beats) if t in db]
first = idx[0] if idx else 0
cuts, i = [0.0], first + g.intro_bars * 4 if g.intro_bars else first
if i < len(beats) and beats[i] > 0.2: cuts.append(beats[i])
while True:
    step = g.fast_bars if g.fast_from is not None and beats[min(i, len(beats) - 1)] >= g.fast_from else g.bars
    i += int(round(step * 4))
    if i >= len(beats) or beats[i] > dur - 0.8: break
    cuts.append(beats[i])
cuts = sorted(set(round(c, 3) for c in cuts)) + [round(dur, 3)]
shots = []
for k, (a, z) in enumerate(zip(cuts, cuts[1:])):
    intro = g.intro_bars and k == 0 and a == 0
    shots.append({"id": f"{k:02d}", "src": "INTRO_CARD" if intro else f"clips/{k:02d}.mp4", "in": a, "out": z, "src_start": 0,
                  "move": "push"})
drops = [t for t in b.get("big_drops", []) if t < dur]
proj = {"size": [1920, 1080], "fps": 30, "audio": g.audio, "audio_start": 0, "duration": round(dur, 3), "shots": shots,
        "words": [{"t": s["in"], "until": s["out"], "text": "WORD", "pos": "center"} for s in shots],
        "flash_on": [s["in"] for s in shots[1:]], "glitch_on": drops, "grain": 4, "fade": 0.6,
        "endcard": {"from": shots[-1]["in"], "text": "TITLE", "sub": "subtitle"}}
json.dump(proj, open(g.out, "w"), ensure_ascii=False, indent=1)
print(f"{len(shots)} 个镜头 → {g.out}")
for s in shots: print(f"{s['id']}  {s['in']:7.3f}–{s['out']:7.3f}  ({s['out'] - s['in']:.2f}s)  {s['src']}")
