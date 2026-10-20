"""project.json → 成片 mp4（ffmpeg 一把出）。只依赖 python3 + ffmpeg。
用法：python3 render.py project.json out.mp4 [--preview] [--rough]
  --preview = 半分辨率快速预览；--rough = 粗剪（只有镜头和歌，不加字/闪/颗粒）
project.json 字段见 ember-beat-edit/edit-recipes.md；所有时间单位为秒，都是成片时间轴。"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fonts import find_font

IMG = {".png", ".jpg", ".jpeg", ".webp"}


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit("ffmpeg 失败：\n" + " ".join(cmd) + "\n" + r.stderr[-2500:])


TXT = []


def esc(s):  # 文本写进临时文件再用 textfile= 引用：冒号、百分号、引号都不用转义
    f = Path(tempfile.mkstemp(prefix="ember-txt-", suffix=".txt")[1]); f.write_text(s, encoding="utf-8"); TXT.append(f)
    return str(f)


def cover(w, h, fx=0.5):  # 等比放大铺满再裁切（不拉伸、不留黑边）；fx = 横向取景位置 0 左 … 1 右（竖版重新构图用）
    return f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}:(iw-{w})*{fx}:(ih-{h})/2,setsar=1"


def shot_segment(s, w, h, fps, base, out):
    n = max(1, round((s["out"] - s["in"]) * fps))
    if s["src"] == "INTRO_CARD" or s["src"].startswith("color:"):  # 纯色底（开场纯字幕段），字由 words 叠上去
        c = s["src"][6:] if s["src"].startswith("color:") else "black"
        run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={c}:s={w}x{h}:r={fps}", "-frames:v", str(n),
             "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", out])
        return n
    src = str((base / s["src"]).resolve())
    mv, amt = s.get("move", "push"), s.get("amount", 0.12)
    if Path(src).suffix.lower() in IMG:
        z = {"push": f"1+{amt}*on/{n}", "pull": f"1+{amt}-{amt}*on/{n}", "still": "1"}.get(mv, f"1+{amt / 2}")
        x = {"pan_left": f"(iw-iw/zoom)*(1-on/{n})", "pan_right": f"(iw-iw/zoom)*on/{n}"}.get(mv, "iw/2-(iw/zoom/2)")
        fx = s.get("focus", 0.5)
        vf = (f"{cover(w * 2, h * 2, fx)},zoompan=z='{z}':x='{x}':y='ih/2-(ih/zoom/2)':d={n}:s={w}x{h}:fps={fps},"
              f"trim=end_frame={n},setpts=PTS-STARTPTS,format=yuv420p")
        cmd = ["ffmpeg", "-y", "-loop", "1", "-i", src, "-vf", vf, "-frames:v", str(n)]
    else:  # 视频片段：src_start 起取 n 帧；不够长就定格最后一帧
        vf = (f"fps={fps},{cover(w, h, s.get('focus', 0.5))},tpad=stop_mode=clone:stop_duration=5,"
              f"trim=end_frame={n},setpts=PTS-STARTPTS,format=yuv420p")
        if s.get("speed"): vf = f"setpts=PTS/{s['speed']}," + vf
        cmd = ["ffmpeg", "-y", "-ss", str(s.get("src_start", 0)), "-i", src, "-an", "-vf", vf, "-frames:v", str(n)]
    run(cmd + ["-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-r", str(fps), out])
    return n


def fit(text, size, w, frac=0.88):
    """字太长就缩小，保证不出画：中日韩字按 1em 估宽，其余按 0.62em。"""
    em = sum(1.0 if ord(c) > 0x2E80 else 0.62 for c in text) or 1
    return min(size, frac * w / em)


def overlay_chain(p, w, h, fps, font):
    f, k = [], min(w, h) / 1080  # 字号按短边 1080 设计，横竖版都按短边缩放
    for t in p.get("flash_on", []):  # 白闪 1–2 帧
        f.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.85:t=fill:enable='between(t,{t},{t + 1.5 / fps:.4f})'")
    for t in p.get("glitch_on", []):  # 大落点 2 帧 RGB 错位
        f.append(f"rgbashift=rh={int(-14 * k)}:bh={int(14 * k)}:enable='between(t,{t},{t + 2 / fps:.4f})'")
    pos = {"center": ("(w-text_w)/2", "(h-text_h)/2"), "top": ("(w-text_w)/2", "h*0.12"),
           "bottom": ("(w-text_w)/2", "h*0.80-text_h"), "left": ("w*0.07", "(h-text_h)/2")}
    for wd in p.get("words", []):
        a, b = wd["t"], wd.get("until", wd["t"] + 0.5)
        size = fit(wd["text"], wd.get("size", 170) * k, w)
        pop = f"{size:.0f}*(1+0.05*clip(1-(t-{a})/0.1,0,1))"  # 105%→100% 缩放冲击，约 3 帧
        x, y = pos.get(wd.get("pos", "center"), pos["center"])
        box = f":box=1:boxcolor={wd['box']}:boxborderw={int(28 * k)}" if wd.get("box") else ""
        f.append(f"drawtext=fontfile='{font}':expansion=none:textfile='{esc(wd['text'])}':fontsize='{pop}':fontcolor={wd.get('color', 'white')}"
                 f":borderw={int(wd.get('border', 6) * k)}:bordercolor=black@0.85{box}:x={x}:y={y}"
                 f":enable='between(t,{a},{b})'")
    ec = p.get("endcard")
    if ec:
        a = ec["from"]
        f.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=black@0.55:t=fill:enable='gte(t,{a})'")
        f.append(f"drawtext=fontfile='{font}':expansion=none:textfile='{esc(ec['text'])}':fontsize={int(fit(ec['text'], ec.get('size', 150) * k, w))}:fontcolor=white"
                 f":x=(w-text_w)/2:y=(h-text_h)/2-{int(40 * k)}:alpha='clip((t-{a})/0.3,0,1)':enable='gte(t,{a})'")
        if ec.get("sub"):
            f.append(f"drawtext=fontfile='{font}':expansion=none:textfile='{esc(ec['sub'])}':fontsize={int(56 * k)}:fontcolor=white@0.9"
                     f":x=(w-text_w)/2:y=h/2+{int(90 * k)}:alpha='clip((t-{a}-0.2)/0.3,0,1)':enable='gte(t,{a})'")
    if p.get("grain", 4):
        f.append(f"noise=alls={p.get('grain', 4)}:allf=t")
    fade = p.get("fade", 0.6)
    f.append(f"fade=t=out:st={p['duration'] - fade:.3f}:d={fade}")
    f.append("format=yuv420p")
    return ",".join(f)


def render(pj, out, preview=False, rough=False):
    pj = Path(pj); p = json.loads(pj.read_text(encoding="utf-8")); base = pj.parent
    if rough:  # 粗剪：只有镜头 + 歌，不加字、不闪、不颗粒（v11 第 6 步）
        p = dict(p, words=[], flash_on=[], glitch_on=[], grain=0, endcard=None)
    w, h = p.get("size", [1920, 1080]); fps = p.get("fps", 30)
    if preview: w, h = w // 2 // 2 * 2, h // 2 // 2 * 2
    dur = p["duration"]
    shots = sorted(p["shots"], key=lambda s: s["in"])
    assert abs(shots[0]["in"]) < 1e-6 and abs(shots[-1]["out"] - dur) < 0.05, "shots 必须从 0 铺满到 duration"
    for a, b in zip(shots, shots[1:]):
        assert abs(a["out"] - b["in"]) < 1e-3, f"镜头之间有缝/重叠：{a['out']} vs {b['in']}"
    font = p.get("font") or find_font()
    tmp = Path(tempfile.mkdtemp(prefix="ember-"))
    try:
        segs, frames = [], 0
        for i, s in enumerate(shots):  # 按帧累计，避免浮点误差导致音画漂移
            want = round(s["out"] * fps) - frames
            s = dict(s, out=s["in"] + want / fps)
            seg = str(tmp / f"s{i:03d}.mp4"); frames += shot_segment(s, w, h, fps, base, seg); segs.append(seg)
        (tmp / "list.txt").write_text("".join(f"file '{x}'\n" for x in segs))
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"), "-c", "copy", str(tmp / "cat.mp4")])
        vf = overlay_chain(p, w, h, fps, font)
        cmd = ["ffmpeg", "-y", "-i", str(tmp / "cat.mp4")]
        if p.get("audio"):
            cmd += ["-ss", str(p.get("audio_start", 0)), "-t", str(dur), "-i", str((base / p["audio"]).resolve())]
        cmd += ["-filter_complex", f"[0:v]{vf}[v]", "-map", "[v]"]
        if p.get("audio"):
            fade = p.get("fade", 0.6)
            cmd += ["-map", "1:a", "-af", f"afade=t=in:d=0.03,afade=t=out:st={dur - fade:.3f}:d={fade}" + (",loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.85:level=disabled" if p.get("loudnorm", True) else ""), "-c:a", "aac", "-b:a", "192k"]
        cmd += ["-t", str(dur), "-c:v", "libx264", "-preset", "medium", "-crf", "23" if preview else str(p.get("crf", 18)),
                "-pix_fmt", "yuv420p", "-r", str(fps), "-movflags", "+faststart", str(out)]
        run(cmd)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        for f in TXT: f.unlink(missing_ok=True)
    print(f"OK {out}  {w}x{h}@{fps}  {dur}s  {len(shots)} 镜头  {len(p.get('words', []))} 个字卡")


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if len(a) < 2: sys.exit(__doc__)
    render(a[0], a[1], "--preview" in sys.argv, "--rough" in sys.argv)
