"""把整首歌剪成 MV 用的短版：每段从重拍切到重拍，接缝 30ms 等功率交叉淡化，开头 5ms 淡入，结尾 0.6s 淡出。
用法：python3 songcut.py full.wav song.mp3 --ranges 7.964-14.791,47.369-71.6 [--xfade 0.03] [--fade 0.6]
段落的起止点从 beatmap.py 跑出来的 downbeats 里挑（整首歌先跑一遍 beatmap）。"""
import argparse, subprocess, sys

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("out")
ap.add_argument("--ranges", required=True, help="a-b,c-d …（秒，原曲时间）")
ap.add_argument("--xfade", type=float, default=0.03); ap.add_argument("--fade", type=float, default=0.6)
g = ap.parse_args()
rs = [tuple(map(float, r.split("-"))) for r in g.ranges.split(",")]
parts, labels = [], []
for i, (a, b) in enumerate(rs):
    # 除最后一段外，每段尾巴多留 xfade 长度给交叉淡化吃掉，接缝正好落在重拍上
    tail = g.xfade if i < len(rs) - 1 else 0
    parts.append(f"[0:a]atrim={a}:{b + tail},asetpts=PTS-STARTPTS[p{i}]"); labels.append(f"[p{i}]")
chain, cur = [], labels[0]
for i, nxt in enumerate(labels[1:], 1):
    chain.append(f"{cur}{nxt}acrossfade=d={g.xfade}:c1=qsin:c2=qsin[x{i}]"); cur = f"[x{i}]"
total = sum(b - a for a, b in rs)
fc = ";".join(parts + chain) + f";{cur}afade=t=in:d=0.005,afade=t=out:st={total - g.fade:.3f}:d={g.fade}[out]"
r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", g.src, "-filter_complex", fc, "-map", "[out]", "-ar", "48000",
                    *(["-b:a", "320k"] if g.out.endswith(".mp3") else []), g.out])
if r.returncode: sys.exit(1)
acc, out_map = 0.0, []
for a, b in rs:
    out_map.append(f"成片 {acc:.3f}–{acc + b - a:.3f} = 原曲 {a}–{b}（成片时间 = 原曲 − {a - acc:.3f}）"); acc += b - a
print(f"OK {g.out} {total:.2f}s\n" + "\n".join(out_map))
