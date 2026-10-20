"""生成流萤入门音乐包：用程序合成的原创鼓点 + 贝斯 + 和弦垫，灵境自有作品，CC0 发布。
用法：python3 make_starter_music.py <输出目录>。只依赖 numpy 和 ffmpeg。"""
import subprocess, sys, wave
from pathlib import Path
import numpy as np

SR = 44100
TRACKS = [  # 名字, BPM, 小节数, 根音序列(MIDI), 风格
    ("ember-neon-140", 140, 18, [45, 45, 41, 43], "trap"),
    ("ember-sunrise-120", 120, 16, [48, 43, 45, 41], "house"),
    ("ember-lofi-90", 90, 12, [50, 45, 47, 43], "lofi"),
]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def env(n, a=0.005, d=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / d)


def kick(n):
    t = np.arange(n) / SR
    f = 50 + 120 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, 0.25)


def snare(n, rng):
    return (rng.standard_normal(n) * 0.6 + np.sin(2 * np.pi * 190 * np.arange(n) / SR) * 0.4) * env(n, 0.001, 0.09)


def hat(n, rng):
    x = rng.standard_normal(n)
    x = np.diff(np.concatenate([[0], x]))  # 粗略高通
    return x * env(n, 0.001, 0.025) * 0.35


def make(name, bpm, bars, roots, style, out):
    rng = np.random.default_rng(len(name))
    beat = 60 / bpm; step = beat / 4
    total = int(SR * bars * 4 * beat) + SR
    mix = np.zeros(total)
    def add(sig, t, g):
        i = int(t * SR); j = min(total, i + len(sig)); mix[i:j] += sig[: j - i] * g
    for b in range(bars):
        root = roots[b % len(roots)]
        intro = b < 2
        for s in range(16):
            t = (b * 16 + s) * step
            if not intro:
                if style == "trap":
                    if s in (0, 7, 10): add(kick(int(SR * 0.5)), t, 0.9)
                    if s in (4, 12): add(snare(int(SR * 0.25), rng), t, 0.5)
                    if s % 2 == 0 or (b % 2 and s in (13, 15)): add(hat(int(SR * 0.05), rng), t, 0.6)
                elif style == "house":
                    if s % 4 == 0: add(kick(int(SR * 0.4)), t, 0.9)
                    if s in (4, 12): add(snare(int(SR * 0.2), rng), t, 0.35)
                    if s % 4 == 2: add(hat(int(SR * 0.06), rng), t, 0.8)
                else:
                    if s in (0, 10): add(kick(int(SR * 0.4)), t, 0.7)
                    if s in (4, 12): add(snare(int(SR * 0.25), rng), t, 0.3)
                    if s % 2 == 0: add(hat(int(SR * 0.04), rng), t, 0.35)
            if s in (0, 6, 8, 14) and not intro:  # 贝斯
                n = int(SR * step * 1.8); tt = np.arange(n) / SR
                add(np.tanh(2 * np.sin(2 * np.pi * hz(root - 12) * tt)) * env(n, 0.005, 0.3), t, 0.35)
        # 和弦垫：每小节一个小三和弦
        n = int(SR * 4 * beat); tt = np.arange(n) / SR
        pad = sum(np.sin(2 * np.pi * hz(root + k) * tt) + 0.3 * np.sin(2 * np.pi * hz(root + k) * 2.01 * tt) for k in (12, 15, 19))
        add(pad * np.minimum(1, tt / 0.3) * np.minimum(1, (n / SR - tt) / 0.3), b * 4 * beat, 0.06)
    mix = mix[: int(SR * bars * 4 * beat)]
    fade = int(SR * 0.6); mix[-fade:] *= np.linspace(1, 0, fade)
    mix = mix / (np.abs(mix).max() + 1e-9) * 0.89
    wav = Path(out) / f"{name}.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    mp3 = wav.with_suffix(".mp3")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(wav), "-ac", "2", "-b:a", "160k", str(mp3)], check=True)
    wav.unlink()
    print(mp3, f"{bpm} BPM", f"{bars * 4 * beat:.1f}s")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    Path(out).mkdir(parents=True, exist_ok=True)
    for t in TRACKS:
        make(*t, out)
