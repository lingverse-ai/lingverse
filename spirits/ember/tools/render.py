"""Ember 默认渲染器 = v11 原版管线（字永远压在主角后面）。横版 16:9，1920×1080，30fps。
v11 代码原样在 tools/v11/src（render_v11 / render_v10 / common 不改），这里只把
project.json 的数据喂进去：镜头、场景素材、词与时间、beatmap（音乐驱动）、主角类型。

用法：
  python3 render.py project.json out/mv.mp4            # 全片：准备→逐帧→编码→自动 QC
  python3 render.py project.json --prepare              # 只抽帧 + 抠像（PNG 全幅 0-255 遮罩）
  python3 render.py project.json --frames 6.0,10.2      # 只出几帧测试（不出整片）
  python3 render.py project.json --qc                   # 12 帧拼图 + 字透人检查（>0.5% 判 FAIL）
  选项：--jobs N  --runroot DIR  --excerpt A-B（只出 A-B 秒）
project.json 里 "renderer": "legacy" 走旧渲染器 render_legacy.py（不再推荐）。

project.json 关键字段（v11 管线用）：
  subject_type: person | pet | object     person→u2net_human_seg；pet/object→isnet-general-use
  matte_model:  可选，强制指定 rembg 模型
  beatmap:      默认 beatmap.json（beats / downbeats / accent_hits / big_drops / bpm）
  audio, audio_start, duration
  shots: [{id, in, out, src(视频), raw_window:[a,b] 或 src_start}]（src 为 INTRO_CARD / color: 的镜头跳过）
  words: [{t, text, color, style?}]   t < 第一个视频镜头 in → 片头逐拍大字；之后 → 压在主角后面的大字
  endcard: {from, text, image?, credits?}   hud: {title, subtitle, chapters:[{t,label}]}
"""
import os, sys, json, subprocess, argparse, shutil, re
from pathlib import Path
T = Path(__file__).resolve().parent
V11 = T / "v11"
FPS = 30

def sh(cmd, **kw):
    print("+", " ".join(map(str, cmd))[:200], flush=True); subprocess.run(list(map(str, cmd)), check=True, **kw)

def ascii_up(s): return re.sub(r"[^\x20-\x7e]", "", s or "").strip().upper()

def matte_model(P):
    if P.get("matte_model_v11") or P.get("matte_model"): return P.get("matte_model_v11") or P["matte_model"]
    return "u2net_human_seg" if P.get("subject_type", "person") == "person" else "isnet-general-use"

def build_cfg(P, pdir, bm):
    shots = [s for s in P["shots"] if not str(s.get("src", "")).startswith(("INTRO_CARD", "color:"))]
    dur = float(P.get("duration") or bm["duration"])
    ec = P.get("endcard") or {}
    end_t = float(ec.get("from", shots[-1]["out"]))
    intro_end = float(shots[0]["in"])
    words, seen = [], set()
    for w in P.get("words", []):
        txt = ascii_up(w.get("glyph_of") or w["text"]); k = (w["t"], txt)
        if not txt or k in seen: continue
        seen.add(k); c = (w.get("colors") or [w.get("color", "#EFE6D2")])[0]
        words.append({"t": float(w["t"]), "text": txt, "color": str(c), "style": w.get("v11_style", "solid")})
    hud = P.get("hud") or {}
    title = ascii_up(P.get("title_en") or ec.get("text") or P.get("name"))
    artist = ascii_up((P.get("lead") or {}).get("name_en") or P.get("artist_en") or P.get("name"))
    mmss = "%d:%02d" % (int(round(dur)) // 60, int(round(dur)) % 60)
    chap = [[float(c["t"]), ascii_up(c["label"])] for c in hud.get("chapters", [])] or \
           [[0.0, "00 / INTRO"], [intro_end, "01 / " + (title.split()[0] if title else "TRACK")], [end_t, "OUTRO"]]
    t0 = next((x for x in bm.get("big_drops", []) if intro_end <= x < end_t - 3), intro_end)
    lines = ec.get("v11_lines")
    if not lines:
        ws = title.split() or ["THE", "END"]; n = len(ws)
        parts = [" ".join(ws[:max(1, n // 3)]), " ".join(ws[max(1, n // 3):max(2, 2 * n // 3)]), " ".join(ws[max(2, 2 * n // 3):])] if n >= 3 else ws
        parts = [p for p in parts if p][:3]
        lines = [[p, end_t + 0.418 * i, i == len(parts) - 1] for i, p in enumerate(parts)]
    return {"intro_end": intro_end, "end_t": end_t, "duration": dur,
            "shots": [{"id": s["id"], "in": float(s["in"])} for s in shots], "words": words,
            "hud": {"title": hud.get("v11_title") or ("> " + title), "subtitle": hud.get("v11_subtitle") or f"{artist} / TRACK 01 / {mmss}", "chapters": chap},
            "text_map": P["v11_text_map"] if "v11_text_map" in P else {"FUTURE ON THE BLOCK": title, "XIAOYE \u00b7 TRACK 01 \u00b7 0:22": f"{artist} \u00b7 TRACK 01 \u00b7 {mmss}", "143.6 BPM": "%.1f BPM" % bm["bpm"], "XIAOYE": artist or "ARTIST", "FUTURE": (title.split() or ["TRACK"])[0], "XIAOYE / TRACK 01 / 0:31": f"{artist} / TRACK 01 / {mmss}"},
            "terminal": P["v11_terminal"] if "v11_terminal" in P else {"from": t0, "to": t0 + 8.17, "lines": [f"> TRACK 01 // {artist} // {title}", "> MIC CHECK ... [OK]"]},
            "endcard": {"lines": lines, "credits": ec.get("v11_credits") or [artist, f"{title} / TRACK 01"]}}

def prepare(P, pdir, root, model):
    bmp = pdir / P.get("beatmap", "beatmap.json"); bm = json.load(open(bmp))
    bm.setdefault("strong_hits", bm.get("accent_hits", [])); bm.setdefault("rap_lyrics", [])
    for k in ("accent_hits", "big_drops", "downbeats"): bm.setdefault(k, [])
    work = root / "pack_v5" / "work"
    for d in (root / "src", root / "v3", root / "stills", root / "out", work / "fr", work / "matte", work / "out_frames"):
        d.mkdir(parents=True, exist_ok=True)
    for f in (V11 / "src").iterdir():   # v11 code, linked (not copied) so common.ROOT = runroot
        dst = root / "src" / f.name
        if not dst.exists() and f.name != "__pycache__": dst.symlink_to(f)
    if not (root / "src" / "driver.py").exists(): (root / "src" / "driver.py").symlink_to(V11 / "driver.py")
    for p in (root / "beatmap.json", root / "pack_v5" / "beatmap.json", root / "v3" / "beatmap_v3.json"):
        json.dump(bm, open(p, "w"))
    audio = pdir / P.get("audio", "audio/song.mp3"); dur = float(P.get("duration") or bm["duration"])
    for name in ("song_pcm.f32", "song_v3_pcm.f32"):
        if not (root / "src" / name).exists() or (root / "src" / name).is_symlink():
            sh(["ffmpeg", "-v", "error", "-y", "-ss", P.get("audio_start", 0), "-t", dur, "-i", audio, "-ac", "1", "-ar", 8000, "-f", "f32le", root / "src" / name])
    shots = [s for s in P["shots"] if not str(s.get("src", "")).startswith(("INTRO_CARD", "color:"))]
    for s in shots:   # 24fps JPG frames, 1920x1080 cover (= pack_v5/work/fr layout)
        od = work / "fr" / s["id"]
        if any(od.glob("f_*.jpg")): continue
        od.mkdir(parents=True, exist_ok=True)
        a, b = s.get("raw_window") or [s.get("src_start", 0), s.get("src_start", 0) + s["out"] - s["in"]]
        src = pdir / s["src"]
        if src.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            n = max(2, int(round((b - a) * 24)) + 1)
            sh(["ffmpeg", "-v", "error", "-y", "-loop", 1, "-i", src, "-frames:v", n, "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080", "-q:v", 2, od / "f_%03d.jpg"])
        else:
            sh(["ffmpeg", "-v", "error", "-y", "-ss", a, "-t", b - a + 1 / 24, "-i", src, "-vf", "fps=24,scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080", "-q:v", 2, od / "f_%03d.jpg"])
    ec = P.get("endcard") or {}
    eimg = ec.get("image")
    dst = root / "pack_v5" / "endcard_person.jpg"
    if not dst.exists():
        if eimg: sh(["ffmpeg", "-v", "error", "-y", "-i", pdir / eimg, "-q:v", 2, dst])
        else:
            last = sorted((work / "fr" / shots[-1]["id"]).glob("f_*.jpg"))[-1]; shutil.copy(last, dst)
    # PNG full-range mattes (960x540, 0-255) — never video mattes (those cap at 235)
    sh([sys.executable, T / "v11" / "matte_png.py", work / "fr", work / "matte", model])
    cfg = build_cfg(P, pdir, bm); json.dump(cfg, open(root / "v11cfg.json", "w"), indent=1, ensure_ascii=False)
    return cfg

def qc_times(cfg, n=12):
    a, b = cfg["intro_end"], cfg["end_t"]
    # sample inside each word window (where text exists), spread over the body
    ts = [w["t"] + 0.25 for w in cfg["words"] if a <= w["t"] < b - 0.3]
    if len(ts) < n: ts += [a + (b - a) * (i + 0.5) / n for i in range(n - len(ts))]
    ts = sorted(ts); step = len(ts) / n
    return [round(ts[int(i * step)], 3) for i in range(n)]

def run_qc(root, cfg, outdir):
    ts = qc_times(cfg)
    sh([sys.executable, root / "src" / "driver.py", root / "v11cfg.json", "qc", outdir, ",".join(map(str, ts))], cwd=root)
    res = json.load(open(outdir / "leak.json"))
    from PIL import Image, ImageDraw
    tiles = []
    for r in res:
        im = Image.open(outdir / ("q_%06.3f.png" % r["t"])).convert("RGB").resize((480, 270))
        d = ImageDraw.Draw(im); lk = r["leak"]
        lab = "%.2fs  leak %s" % (r["t"], "n/a" if lk is None else "%.2f%%" % (lk * 100))
        d.rectangle([0, 0, 200, 18], fill=(0, 0, 0)); d.text((4, 3), lab, fill=(255, 80, 60) if (lk or 0) > 0.005 else (120, 255, 120))
        tiles.append(im)
    grid = Image.new("RGB", (480 * 4, 270 * 3))
    for i, im in enumerate(tiles): grid.paste(im, ((i % 4) * 480, (i // 4) * 270))
    grid.save(outdir / "qc_grid.jpg", quality=88)
    worst = max([r["leak"] or 0 for r in res]); ok = worst <= 0.005
    rep = {"pass": ok, "worst_leak": worst, "threshold": 0.005, "frames": res, "grid": str(outdir / "qc_grid.jpg")}
    json.dump(rep, open(outdir / "qc.json", "w"), indent=1)
    print(("QC PASS" if ok else "QC FAIL") + "  worst text-in-subject leak %.3f%%  grid %s" % (worst * 100, outdir / "qc_grid.jpg"))
    return ok

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("project"); ap.add_argument("out", nargs="?")
    ap.add_argument("--prepare", action="store_true"); ap.add_argument("--frames"); ap.add_argument("--qc", action="store_true")
    ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 2) - 2)); ap.add_argument("--runroot")
    ap.add_argument("--excerpt"); g, rest = ap.parse_known_args()
    pj = Path(g.project).resolve(); P = json.load(open(pj)); pdir = pj.parent
    if P.get("renderer") == "legacy":
        os.execv(sys.executable, [sys.executable, str(T / "render_legacy.py")] + sys.argv[1:])
    root = Path(g.runroot or pdir / "v11run").resolve()
    cfg = prepare(P, pdir, root, matte_model(P))
    if g.prepare: return
    if g.frames:
        sh([sys.executable, root / "src" / "driver.py", root / "v11cfg.json", "frames", g.frames, root / "test_frames"], cwd=root); return
    if g.qc:
        sys.exit(0 if run_qc(root, cfg, root / "qc") else 1)
    if not g.out: ap.error("need out.mp4 (or --frames / --qc / --prepare)")
    sh([sys.executable, root / "src" / "driver.py", root / "v11cfg.json", "all", g.jobs], cwd=root)
    a, b = (map(float, g.excerpt.split("-")) if g.excerpt else (0, cfg["duration"]))
    out = Path(g.out); out.parent.mkdir(parents=True, exist_ok=True)
    sh(["ffmpeg", "-v", "error", "-y", "-framerate", FPS, "-start_number", int(a * FPS), "-i", root / "pack_v5/work/out_frames/f_%04d.png",
        "-ss", float(P.get("audio_start", 0)) + a, "-i", pdir / P.get("audio", "audio/song.mp3"), "-t", b - a,
        "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-crf", P.get("crf", 16), "-preset", "slow", "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-c:a", "aac", "-b:a", "320k", "-shortest", out])
    ok = run_qc(root, cfg, root / "qc"); print("wrote", out); sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
