"""成片/素材质检：时长、分辨率、帧率、码率、响度、黑帧，外加一张联系表（contact sheet）。
用法：python3 qc.py video.mp4 [--expect 1920x1080] [--dur 30] [--sheet out.jpg] [--every 1]
      python3 qc.py clips qc.jpg clips/*.mp4     （素材 QC 表：每条 5 帧一行）"""
import json, re, subprocess, sys


def probe(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                       capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def loudness(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr); tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", r.stderr)
    return (float(i[-1]) if i else None), (float(tp[-1]) if tp else None)


def black_frames(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-vf", "blackdetect=d=0.15:pix_th=0.08", "-an", "-f", "null", "-"],
                       capture_output=True, text=True)
    return re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", r.stderr)


def sheet(path, out, every=1.0, cols=5):
    """按精确时间点逐帧取（-ss 精确寻址），拼成联系表；每格标时间。"""
    import os, tempfile
    d = float(probe(path)["format"]["duration"]); n = max(1, int(d / every + 1e-6))
    tmp = tempfile.mkdtemp(prefix="ember-sheet-")
    for k in range(n):
        t = min(k * every + 0.02, d - 0.05)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1", "-vf",
                        f"scale=384:216:force_original_aspect_ratio=decrease,pad=384:216:-1:-1,drawtext=text='{t:.2f}s':x=8:y=8:fontsize=22:fontcolor=yellow:borderw=2",
                        os.path.join(tmp, f"{k:04d}.png")], check=True)
    rows = (n + cols - 1) // cols
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(tmp, "%04d.png"), "-vf", f"tile={cols}x{rows}",
                    "-frames:v", "1", out], check=True)
    return out


def clip_sheet(clips, out, n=5):
    """每条素材均匀抽 n 帧排一行，所有素材上下叠成一张 QC 表；每格标「文件名 秒数」。"""
    import os, tempfile
    tmp = tempfile.mkdtemp(prefix="ember-qc-"); rows = []
    for c in clips:
        d = float(probe(c)["format"]["duration"]); row = os.path.join(tmp, f"{len(rows):03d}.png")
        cells = []
        for j in range(n):
            t = d * (j + 0.5) / n; cell = os.path.join(tmp, f"c{len(rows)}_{j}.png")
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", c, "-frames:v", "1", "-vf",
                            f"scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:-1:-1,drawtext=text='{os.path.basename(c)[:18]} {t:.1f}s':x=6:y=6:fontsize=16:fontcolor=yellow:borderw=2", cell], check=True)
            cells.append(cell)
        ins = sum([["-i", x] for x in cells], [])
        subprocess.run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", f"hstack={n}", row], check=True); rows.append(row)
    ins = sum([["-i", x] for x in rows], [])
    subprocess.run(["ffmpeg", "-y", "-v", "error", *ins, "-filter_complex", f"vstack={len(rows)}" if len(rows) > 1 else "null", out], check=True)
    return out


def main():
    a = sys.argv[1:]
    if a and a[0] == "clips":  # python3 qc.py clips out.jpg a.mp4 b.mp4 …
        print("QC 表:", clip_sheet(a[2:], a[1])); return
    path = a[0]
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    info = probe(path); v = next(s for s in info["streams"] if s["codec_type"] == "video")
    au = [s for s in info["streams"] if s["codec_type"] == "audio"]
    dur = float(info["format"]["duration"]); size = f"{v['width']}x{v['height']}"
    num, den = map(int, v["r_frame_rate"].split("/")); fps = num / den
    mb = int(info["format"]["size"]) / 1e6
    lufs, tp = loudness(path) if au else (None, None)
    blacks = black_frames(path)
    problems = []
    if opt("--expect") and size != opt("--expect"): problems.append(f"分辨率 {size} ≠ {opt('--expect')}")
    if opt("--dur") and abs(dur - float(opt("--dur"))) > 0.15: problems.append(f"时长 {dur:.2f}s ≠ {opt('--dur')}s")
    if v.get("pix_fmt") != "yuv420p": problems.append(f"像素格式 {v.get('pix_fmt')}（平台要 yuv420p）")
    if not au: problems.append("没有音轨")
    if lufs is not None and not -16 <= lufs <= -9: problems.append(f"响度 {lufs} LUFS（建议 -14±2）")
    if tp is not None and tp > -0.5: problems.append(f"真峰值 {tp} dBFS 过高（会破音）")
    if [b for b in blacks if float(b[0]) < dur - 1.0]: problems.append(f"中途黑帧 {blacks}")
    print(f"{path}: {size} {fps:.2f}fps {dur:.2f}s {mb:.1f}MB 音轨={'有' if au else '无'} 响度={lufs} LUFS 峰值={tp}")
    if opt("--sheet"): print("联系表:", sheet(path, opt("--sheet"), float(opt("--every", 1))))
    print("PASS" if not problems else "问题:\n- " + "\n- ".join(problems))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
