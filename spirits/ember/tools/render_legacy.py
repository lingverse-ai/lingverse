"""project.json → 成片 mp4（ffmpeg 一把出）。只依赖 python3 + ffmpeg。
用法：python3 render.py project.json out.mp4 [--preview] [--rough] [--excerpt 8-30]
  进阶字段：lut（调色）、words[].behind（字压在人身后，需 rembg）、lyrics（逐字歌词）、hud、ticker（跑马灯）
  --preview 半分辨率；--rough 粗剪（只有镜头和歌）；--excerpt A-B 只出 A–B 秒片段先审
  punch_on（鼓点时间表）= 镜头跟鼓点顶一下；输出带 BT.709 色彩标记
project.json 字段见 ember-beat-edit/edit-recipes.md；所有时间单位为秒，都是成片时间轴。"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fonts import find_font, font_for


def pick_font(spec, text):
    """spec：None=按文字自动（英文 Anton / 中文思源黑体 Heavy）；display|cjk|mono|pixel；或字体文件路径。"""
    from fonts import SPEC
    if not spec: return font_for(text, CN_FONT[0])
    return find_font(spec) if spec in SPEC or spec == "cn-heavy" else spec


CN_FONT = [None]  # project.json 的 cn_font（中文字体 A/B 选中的那款）

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


def fit(text, size, w, frac=0.9, latin=0.62):
    """字太长就缩小，保证不出画：中日韩字按 1em 估宽，拉丁字按 latin em（Anton 这类压缩体约 0.5）。"""
    em = sum(1.0 if ord(c) > 0x2E80 else latin for c in text) or 1
    return min(size, frac * w / em)


def mono_font():
    return find_font("mono")


def word_filter(wd, w, h, k, font):
    pos = {"center": ("(w-text_w)/2", "(h-text_h)/2"), "top": ("(w-text_w)/2", "h*0.12"),
           "bottom": ("(w-text_w)/2", "h*0.80-text_h"), "left": ("w*0.07", "(h-text_h)/2")}
    a, b = wd["t"], wd.get("until", wd["t"] + 0.5)
    font = pick_font(wd.get("font") or font, wd["text"])
    size = fit(wd["text"], wd.get("size", 240) * k, w, latin=0.44 if "Anton" in font else 0.62)
    pop = f"{size:.0f}*(1+0.05*clip(1-(t-{a})/0.1,0,1))"  # 105%→100% 缩放冲击，约 3 帧
    x, y = pos.get(wd.get("pos", "center"), pos["center"])
    box = f":box=1:boxcolor={wd['box']}:boxborderw={int(28 * k)}" if wd.get("box") else ""
    return (f"drawtext=fontfile='{font}':expansion=none:textfile='{esc(wd['text'])}':fontsize='{pop}':fontcolor={wd.get('color', '#EFE6D2')}"
            f":borderw={int(wd.get('border', 6) * k)}:bordercolor=black@0.85{box}:x={x}:y={y}:enable='between(t,{a},{b})'")


def behind_chain(p, w, h, font):
    """要压在人身后的大字（words 里 behind=true）：先画在画面上，再用遮罩把人贴回最上层。"""
    k = min(w, h) / 1080
    return ",".join(word_filter(wd, w, h, k, font) for wd in p.get("words", []) if wd.get("behind"))


def hud_lyrics_ticker(p, w, h, fps, font, k):
    f, mono = [], mono_font()
    hud = p.get("hud")
    if hud:  # 等宽小字 HUD：四角标签、时间码、闪烁 REC、角标线
        hud = hud if isinstance(hud, dict) else {}
        fs, m, c = int(26 * k), int(40 * k), hud.get("color", "white@0.85")
        tc = Path(tempfile.mkstemp(prefix="ember-txt-", suffix=".txt")[1]); tc.write_text("%{pts:hms}"); TXT.append(tc)
        f.append(f"drawtext=fontfile='{mono}':expansion=none:textfile='{esc(hud.get('title', 'EMBER // LINGVERSE'))}':fontsize={fs}:fontcolor={c}:x={m}:y={m}")
        f.append(f"drawtext=fontfile='{mono}':textfile='{tc}':fontsize={fs}:fontcolor={c}:x=w-text_w-{m}:y={m}")
        f.append(f"drawtext=fontfile='{mono}':expansion=none:textfile='{esc(hud.get('label', 'TRACK 01'))}':fontsize={fs}:fontcolor={c}:x={m}:y=h-text_h-{m}")
        f.append(f"drawtext=fontfile='{mono}':expansion=none:textfile='{esc('● REC')}':fontsize={fs}:fontcolor=0xFF4040:x=w-text_w-{m}:y=h-text_h-{m}:enable='lt(mod(t,1),0.6)'")
        L, T = int(60 * k), max(2, int(3 * k))
        for x, y in ((m // 2, m // 2), (f"w-{m // 2}-{L}", m // 2), (m // 2, f"h-{m // 2}-{T}"), (f"w-{m // 2}-{L}", f"h-{m // 2}-{T}")):
            f.append(f"drawbox=x={x}:y={y}:w={L}:h={T}:color={c}:t=fill")
    cps = p.get("lyric_cps", 20)  # 逐字打出的速度（字/秒）
    for ln in p.get("lyrics", []):  # 终端风逐字歌词：> 开头，左下角，半透明黑底
        a, b, txt = ln["t"], ln.get("until", ln["t"] + 2), ln["text"]
        fs = int(ln.get("size", 40) * k); y = f"h*{ln.get('y', 0.70)}"
        for i in range(1, len(txt) + 1):
            t0 = a + (i - 1) / cps; t1 = b if i == len(txt) else min(b, a + i / cps)
            if t0 >= b: break
            cur = "_" if i < len(txt) else ""
            f.append(f"drawtext=fontfile='{mono}':expansion=none:textfile='{esc('> ' + txt[:i] + cur)}':fontsize={fs}:fontcolor=white"
                     f":box=1:boxcolor=black@0.45:boxborderw={int(10 * k)}:x=w*0.06:y={y}:enable='between(t,{t0:.3f},{t1:.3f})'")
    for tk in p.get("ticker", []):  # 横向滚动字幕（跑马灯）
        a, b = tk["from"], tk["to"]; sp = tk.get("speed", 600) * k
        size = int(tk.get("size", 140) * k); y = f"h*{tk.get('y', 0.5)}-text_h/2"
        f.append(f"drawtext=fontfile='{pick_font(tk.get('font') or font, tk['text'])}':expansion=none:textfile='{esc(tk['text'])}':fontsize={size}:fontcolor={tk.get('color', 'white')}"
                 f":borderw={int(5 * k)}:bordercolor=black@0.8:x=w-mod((t-{a})*{sp:.0f}\\,w+text_w):y={y}:enable='between(t,{a},{b})'")
    return f


def overlay_chain(p, w, h, fps, font):
    f, k = [], min(w, h) / 1080  # 字号按短边 1080 设计，横竖版都按短边缩放
    hits = p.get("punch_on", [])  # 镜头跟着鼓点"顶"一下：落点瞬间放大 punch 倍，0.25s 内回落
    if hits:
        amt = p.get("punch", 0.06)
        z = "+".join(f"{amt}*between(t,{t},{t + 0.25:.3f})*(1-(t-{t})/0.25)" for t in hits)
        f.append(f"scale=w='trunc({w}*(1+{z})/2)*2':h='trunc({h}*(1+{z})/2)*2':eval=frame,crop={w}:{h}")
    for t in p.get("flash_on", []):  # 白闪 1–2 帧
        f.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=white@0.85:t=fill:enable='between(t,{t},{t + 1.5 / fps:.4f})'")
    for t in p.get("glitch_on", []):  # 大落点 2 帧 RGB 错位
        f.append(f"rgbashift=rh={int(-14 * k)}:bh={int(14 * k)}:enable='between(t,{t},{t + 2 / fps:.4f})'")
    for wd in p.get("words", []):
        if not wd.get("behind"):
            f.append(word_filter(wd, w, h, k, font))
    f += hud_lyrics_ticker(p, w, h, fps, font, k)
    ec = p.get("endcard")
    if ec:
        a = ec["from"]
        f.append(f"drawbox=x=0:y=0:w=iw:h=ih:color=black@0.55:t=fill:enable='gte(t,{a})'")
        f.append(f"drawtext=fontfile='{pick_font(ec.get('font') or font, ec['text'])}':expansion=none:textfile='{esc(ec['text'])}':fontsize={int(fit(ec['text'], ec.get('size', 150) * k, w))}:fontcolor=white"
                 f":x=(w-text_w)/2:y=(h-text_h)/2-{int(40 * k)}:alpha='clip((t-{a})/0.3,0,1)':enable='gte(t,{a})'")
        if ec.get("sub"):
            f.append(f"drawtext=fontfile='{pick_font(ec.get('font') or font, ec['sub'])}':expansion=none:textfile='{esc(ec['sub'])}':fontsize={int(56 * k)}:fontcolor=white@0.9"
                     f":x=(w-text_w)/2:y=h/2+{int(90 * k)}:alpha='clip((t-{a}-0.2)/0.3,0,1)':enable='gte(t,{a})'")
    if p.get("grain", 4):
        f.append(f"noise=alls={p.get('grain', 4)}:allf=t")
    fade = p.get("fade", 0.6)
    f.append(f"fade=t=out:st={p['duration'] - fade:.3f}:d={fade}")
    f.append("format=yuv420p,setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv")
    return ",".join(f)


def render(pj, out, preview=False, rough=False, excerpt=None):
    pj = Path(pj); p = json.loads(pj.read_text(encoding="utf-8")); base = pj.parent
    if rough:  # 粗剪：只有镜头 + 歌，不加字、不闪、不颗粒（v11 第 6 步）
        p = dict(p, words=[], flash_on=[], glitch_on=[], grain=0, endcard=None, lyrics=[], ticker=[], hud=None, lut=None)
    w, h = p.get("size", [1920, 1080]); fps = p.get("fps", 30)
    if preview: w, h = w // 2 // 2 * 2, h // 2 // 2 * 2
    dur = p["duration"]
    shots = sorted(p["shots"], key=lambda s: s["in"])
    assert abs(shots[0]["in"]) < 1e-6 and abs(shots[-1]["out"] - dur) < 0.05, "shots 必须从 0 铺满到 duration"
    for a, b in zip(shots, shots[1:]):
        assert abs(a["out"] - b["in"]) < 1e-3, f"镜头之间有缝/重叠：{a['out']} vs {b['in']}"
    cf = p.get("cn_font")  # 内置名（cn-…）或主人自己的字体文件（相对项目目录）
    if cf and cf not in __import__("fonts").SPEC and cf != "cn-heavy":
        cf = str((base / cf).resolve()) if not os.path.isabs(cf) else cf
        assert os.path.exists(cf), f"找不到字体文件 {cf}（放到项目的 fonts/ 里）"
    CN_FONT[0] = cf
    font = p.get("font")  # None = 按文字自动选（Anton / 思源黑体 Heavy）
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
        pre = ""
        if p.get("lut"):  # 调色 LUT（grade.py 同一套 .cube）
            from grade import lut_filter
            pre = lut_filter(p["lut"]) + ","
        bc = behind_chain(p, w, h, font)
        if bc:  # 字压在人身后：matte.py 先出遮罩
            mask = tmp / "mask.mp4"
            run([sys.executable, str(Path(__file__).parent / "matte.py"), str(tmp / "cat.mp4"), str(mask), "--width", str(p.get("matte_width", 512))])
            cmd += ["-i", str(mask)]; mi = 2 if p.get("audio") else 1
            graph = (f"[0:v]{pre}format=gbrp,split[b0][b1];[b1]{bc}[t];[{mi}:v]scale={w}:{h},format=gray,format=gbrp[m];"
                     f"[t][b0][m]maskedmerge[mm];[mm]{vf}[v]")
        else:
            graph = f"[0:v]{pre}{vf}[v]"
        if excerpt:  # 先出 20–40s 片段给主人看，确认了再出整片
            graph = graph[:-3] + f",trim=start={excerpt[0]}:end={excerpt[1]},setpts=PTS-STARTPTS[v]"
        cmd += ["-filter_complex", graph, "-map", "[v]"]
        if p.get("audio"):
            fade = p.get("fade", 0.6)
            cmd += ["-map", "1:a", "-af", f"afade=t=in:d=0.03,afade=t=out:st={dur - fade:.3f}:d={fade}" + (",loudnorm=I=-14:TP=-1.5:LRA=11,alimiter=limit=0.85:level=disabled" if p.get("loudnorm", True) else ""), "-c:a", "aac", "-b:a", "192k"]
            if excerpt: cmd[-5] += f",atrim=start={excerpt[0]}:end={excerpt[1]},asetpts=PTS-STARTPTS"
        cmd += ["-t", str(dur if not excerpt else excerpt[1] - excerpt[0]), "-c:v", "libx264", "-preset", "medium", "-crf", "23" if preview else str(p.get("crf", 18)),
                "-pix_fmt", "yuv420p", "-r", str(fps),
                "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv", "-movflags", "+faststart", str(out)]
        run(cmd)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        for f in TXT: f.unlink(missing_ok=True)
    print(f"OK {out}  {w}x{h}@{fps}  {dur}s  {len(shots)} 镜头  {len(p.get('words', []))} 个字卡")


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    if len(a) < 2: sys.exit(__doc__)
    ex = None
    if "--excerpt" in sys.argv:
        i = sys.argv.index("--excerpt"); ex = tuple(float(x) for x in sys.argv[i + 1].split("-"))
        a = [x for x in a if x != sys.argv[i + 1]]
    render(a[0], a[1], "--preview" in sys.argv, "--rough" in sys.argv, ex)
