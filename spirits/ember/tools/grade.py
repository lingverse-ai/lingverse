"""调色：给视频/图片套 LUT（ffmpeg lut3d），或者出一张「6 种滤镜对比图」让主人选。
用法：python3 grade.py in.mp4 out.mp4 --lut v11-street [--mix 0.8]
      python3 grade.py frame.jpg compare.jpg --compare          （同一帧套全部 LUT 拼成对比图）
LUT 名字对应 $EMBER_HOME/luts/<名>.cube（自带 6 个，CC0）；也可以直接给 .cube 路径。"""
import argparse, os, subprocess, sys
from pathlib import Path

HOME = Path(os.environ.get("EMBER_HOME", "/workspace/ember"))
DIRS = [HOME / "luts", Path(__file__).resolve().parent.parent / "luts"]


def lut_path(name):
    if name.endswith(".cube") and Path(name).exists(): return str(Path(name).resolve())
    for d in DIRS:
        if (d / f"{name}.cube").exists(): return str(d / f"{name}.cube")
    sys.exit(f"找不到 LUT：{name}（可选：{', '.join(all_luts())}）")


def all_luts():
    return sorted({p.stem for d in DIRS if d.is_dir() for p in d.glob("*.cube")})


def lut_filter(name, mix=1.0):
    f = f"lut3d=file='{lut_path(name)}':interp=tetrahedral"
    return f if mix >= 1 else f"split[a][b];[b]{f}[g];[a][g]blend=all_expr='A*(1-{mix})+B*{mix}'"


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--lut", default="v11-street"); ap.add_argument("--mix", type=float, default=1.0)
    ap.add_argument("--compare", action="store_true"); g = ap.parse_args()
    if g.compare:
        names = ["原片"] + all_luts(); n = len(names)
        fc = f"[0]scale=640:-2,split={n}" + "".join(f"[s{i}]" for i in range(n)) + ";"
        for i, nm in enumerate(names):
            lab = "none" if i == 0 else nm
            fc += f"[s{i}]" + ("" if i == 0 else lut_filter(nm) + ",") + f"drawtext=text='{lab}':x=10:y=10:fontsize=28:fontcolor=white:borderw=3[o{i}];"
        cols = 4; rows = (n + cols - 1) // cols
        lay = "|".join(("+".join(["w0"] * (i % cols)) or "0") + "_" + ("+".join(["h0"] * (i // cols)) or "0") for i in range(n))
        fc += "".join(f"[o{i}]" for i in range(n)) + f"xstack=inputs={n}:layout={lay}:fill=black"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", g.src, "-filter_complex", fc, "-frames:v", "1", g.out], check=True)
    else:
        img = g.src.lower().endswith((".png", ".jpg", ".jpeg"))
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", g.src, "-filter_complex", lut_filter(g.lut, g.mix)]
                       + ([] if img else ["-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "copy"]) + [g.out], check=True)
    print("OK", g.out)
