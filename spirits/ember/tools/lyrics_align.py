"""歌词对时间：用 faster-whisper（CPU）听出每个词的时间，再对齐到主人自己写的歌词（文字永远以主人的为准）。
依赖（可选）：pip install faster-whisper（第一次运行自动下载模型，small 约 460MB，base 约 140MB）。
用法：python3 lyrics_align.py song.mp3 lyrics.txt words.json [--model base] [--lang en|zh]
lyrics.txt：每行一句，[Hook] 这类段落标记行会被跳过。
输出 words.json：{"words":[{"t0","t1","w","line"}], "lines":[{"t","until","text"}], "matched": 比例}
  lines 可直接放进 project.json 的 "lyrics"；words 用来让大字落在唱到那个词的瞬间（词跟人声，动作跟拍子）。
没装 whisper：--even 按段落起止时间平均分配（粗略，记得用耳朵复核）。"""
import argparse, difflib, json, re, sys

ap = argparse.ArgumentParser(); ap.add_argument("audio"); ap.add_argument("lyrics"); ap.add_argument("out")
ap.add_argument("--model", default="base"); ap.add_argument("--lang", default=None)
ap.add_argument("--even", nargs=2, type=float, metavar=("T0", "T1"), help="不用 whisper，在 T0–T1 之间平均分配")
g = ap.parse_args()

lines = [l.strip() for l in open(g.lyrics, encoding="utf-8") if l.strip() and not re.match(r"^\[.*\]$", l.strip())]
tok = lambda s: [x for x in re.findall(r"[A-Za-z0-9']+|[\u4e00-\u9fff]", s)]
norm = lambda x: x.lower().strip("'")
mine = [(w, i) for i, l in enumerate(lines) for w in tok(l)]

if g.even:
    a, b = g.even; n = len(mine); step = (b - a) / max(n, 1)
    words = [{"t0": round(a + k * step, 3), "t1": round(a + (k + 1) * step, 3), "w": w, "line": i} for k, (w, i) in enumerate(mine)]
    ratio = 0.0
else:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("ALIGN_DEPS_MISSING：pip install faster-whisper，或者用 --even T0 T1 粗略分配")
    model = WhisperModel(g.model, device="cpu", compute_type="int8")
    import subprocess, numpy as np  # 自己用 ffmpeg 解码，避开 PyAV 版本不兼容
    pcm = subprocess.run(["ffmpeg", "-v", "error", "-i", g.audio, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    segs, _ = model.transcribe(np.frombuffer(pcm, np.float32), word_timestamps=True, language=g.lang, vad_filter=False,
                               initial_prompt=" ".join(lines)[:400])  # 把主人的歌词当提示，提高命中率
    heard = []
    for s in segs:
        for w in s.words or []:
            for t in tok(w.word):  # 中文一个字一个 token，时间在词内平均
                heard.append((t, w.start, w.end))
    sm = difflib.SequenceMatcher(a=[norm(w) for w, _ in mine], b=[norm(h[0]) for h in heard], autojunk=False)
    times = [None] * len(mine)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            times[blk.a + k] = heard[blk.b + k][1:]
    ratio = sum(t is not None for t in times) / max(len(mine), 1)
    known = [k for k, t in enumerate(times) if t]
    for k in range(len(mine)):  # 没对上的词：在前后已知词之间线性插值
        if times[k] is None:
            p = max([j for j in known if j < k], default=None); q = min([j for j in known if j > k], default=None)
            if p is not None and q is not None:
                f = (k - p) / (q - p); t = times[p][1] + (times[q][0] - times[p][1]) * f; times[k] = (t, t + 0.2)
            elif p is not None: times[k] = (times[p][1] + 0.2 * (k - p), times[p][1] + 0.2 * (k - p) + 0.2)
            elif q is not None: times[k] = (max(0, times[q][0] - 0.2 * (q - k)), max(0.1, times[q][0] - 0.2 * (q - k) + 0.2))
            else: times[k] = (0, 0.2)
    words = [{"t0": round(t[0], 3), "t1": round(t[1], 3), "w": w, "line": i} for (w, i), t in zip(mine, times)]

out_lines = []
for i, l in enumerate(lines):
    ws = [w for w in words if w["line"] == i]
    if ws: out_lines.append({"t": ws[0]["t0"], "until": ws[-1]["t1"] + 0.3, "text": l})
json.dump({"words": words, "lines": out_lines, "matched": round(ratio, 2)}, open(g.out, "w"), ensure_ascii=False, indent=1)
print(f"OK {g.out}: {len(lines)} 句 {len(words)} 词，whisper 命中 {ratio:.0%}" + ("（低于 60%：用耳朵复核时间）" if ratio < 0.6 else ""))
