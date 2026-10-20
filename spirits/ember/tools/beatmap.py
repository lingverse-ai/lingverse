"""从音频做 beatmap.json：bpm、beats、downbeats、accent_hits、big_drops、sections。
用法：python3 beatmap.py song.mp3 [beatmap.json] [--bpm 140]
方法：ffmpeg 解码 → 短时傅里叶 → 频谱通量（起音强度）→ 自相关估速 → 找相位 → 每拍吸附到局部峰值；
低频（<150Hz）能量决定哪一拍是重拍（小节第一拍）。机器结果只是起点，人耳复核后再用。"""
import json, subprocess, sys
import numpy as np

SR, HOP, NFFT = 22050, 512, 2048


def load(path):
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


def spectra(y):
    y = np.concatenate([np.zeros(NFFT // 2, dtype=y.dtype), y])  # 居中分帧：第 i 帧的中心在 i*HOP
    n = 1 + max(0, (len(y) - NFFT) // HOP)
    win = np.hanning(NFFT)
    frames = np.stack([y[i * HOP:i * HOP + NFFT] * win for i in range(n)])
    mag = np.log1p(np.abs(np.fft.rfft(frames, axis=1)) * 10)
    freqs = np.fft.rfftfreq(NFFT, 1 / SR)
    flux = np.maximum(0, np.diff(mag, axis=0, prepend=mag[:1])).sum(1)
    low = np.maximum(0, np.diff(mag[:, freqs < 150], axis=0, prepend=mag[:1, freqs < 150])).sum(1)
    energy_low = np.exp(mag[:, freqs < 150]).sum(1)
    norm = lambda a: (a - a.mean()) / (a.std() + 1e-9)
    return norm(flux), norm(low), energy_low


def tempo(flux, hint=None):
    fps = SR / HOP
    ac = np.correlate(flux, flux, "full")[len(flux) - 1:]
    best, bpm = -1e18, 120.0
    for b in np.arange(70, 181, 0.25):
        lag = fps * 60 / b
        score = sum(np.interp(lag * k, np.arange(len(ac)), ac) / k for k in (1, 2, 4))
        score *= np.exp(-0.5 * (np.log2(b / (hint or 120)) / (0.3 if hint else 1.0)) ** 2)
        if score > best:
            best, bpm = score, b
    return bpm


def main(path, out="beatmap.json", hint=None, shift=0):
    y = load(path); dur = len(y) / SR
    flux, low, elow = spectra(y)
    fps = SR / HOP
    bpm = tempo(flux, hint)
    period = fps * 60 / bpm
    phases = np.arange(0, period, 0.5)
    drive = flux + 0.5 * low  # 相位以底鼓为准，避免锁到反拍的镲片上
    sc = [np.interp(np.arange(p, len(drive), period), np.arange(len(drive)), drive).sum() for p in phases]
    p0 = phases[int(np.argmax(sc))]
    beats = []
    for c in np.arange(p0, len(flux), period):
        lo, hi = int(max(0, c - period * 0.06)), int(min(len(flux), c + period * 0.06 + 1))
        beats.append((lo + int(np.argmax(drive[lo:hi]))) / fps if hi > lo else c / fps)
    beats = [round(b, 3) for b in beats if b < dur]
    bi = [int(b * fps) for b in beats]
    # 小节第一拍：底鼓起音 + 低频能量（贝斯落在第一拍）最强；不用全频通量，免得被军鼓带偏
    win = lambda a, i: a[max(0, i - 2):i + 3].max() if i < len(a) else 0
    strength = [win(low, i) + 0.5 * win(np.log(elow + 1e-9), i) for i in bi]
    start = int(np.argmax([np.mean(strength[k::4]) for k in range(4)])) if len(beats) >= 8 else 0
    start = (start + shift) % 4  # --shift N：耳朵听出重拍偏了 N 拍时手动校正
    downbeats = beats[start::4]
    order = np.argsort([-flux[i] for i in bi])
    accents = sorted(beats[i] for i in order[: max(4, len(beats) // 6)])
    # 大 drop：重拍处低频能量比前一小节跳升最多的位置
    seg = [elow[int(d * fps):int(d * fps + period * 4)].mean() if int(d * fps) < len(elow) else 0 for d in downbeats]
    jumps = sorted(range(1, len(seg)), key=lambda i: -(seg[i] - seg[i - 1]))[:3]
    drops = sorted(downbeats[i] for i in jumps)
    sections = [{"start": downbeats[i], "end": downbeats[i + 4] if i + 4 < len(downbeats) else round(dur, 3)}
                for i in range(0, len(downbeats), 4)]
    bm = {"source": path, "duration": round(dur, 3), "bpm": round(bpm, 2), "beats": beats, "downbeats": downbeats,
          "accent_hits": accents, "big_drops": drops, "sections": sections,
          "note": "机器检测，人耳复核：重拍错位就整体平移；歌词时间以主人写的歌词为准"}
    json.dump(bm, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"{out}: {bm['bpm']} BPM, {len(beats)} beats, {len(downbeats)} downbeats, drops {drops}")
    return bm


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="音乐 → beatmap.json（拍点/重拍/重音/大落点/段落）")
    ap.add_argument("audio"); ap.add_argument("out", nargs="?", default="beatmap.json")
    ap.add_argument("--bpm", type=float, help="已知 BPM（Suno 页面/提示词里写的），防止半速倍速误判")
    ap.add_argument("--shift", type=int, default=0, help="重拍整体后移 N 拍（耳朵复核后校正）")
    g = ap.parse_args()
    main(g.audio, g.out, g.bpm, g.shift)
