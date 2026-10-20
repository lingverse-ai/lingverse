"""流萤的字体（全部开源许可，SIL OFL 1.1）。新机器上第一次用会自动下载到 $EMBER_HOME/fonts。
  display  Anton                 —— 动效大字默认（v11 同款的超粗压缩无衬线）
  cjk      思源黑体 Heavy          —— 中文大字
  mono     JetBrains Mono ExtraBold —— HUD、终端逐字歌词
  pixel    Fusion Pixel 12px（简中）—— 方块世界预设
中文默认 = 思源黑体 Heavy（cjk）。以下可选字体只在 cn_font 指定时才下载（全部 OFL 1.1）：
  cn-heavy 思源黑体 Heavy（= cjk，默认） cn-smiley 得意黑 Smiley Sans   cn-kuaile 站酷快乐体
  cn-huangyou 站酷庆科黄油体          cn-serif 思源宋体 Heavy         cn-brush 马善政毛笔楷书
  project.json 写 "cn_font": "cn-smiley" 或主人自己字体的路径 "fonts/xx.ttf"（相对项目目录），所有中文字卡都会换。
用法：python3 fonts.py [display|cjk|mono|pixel|cn-…|all]   → 打印路径
      python3 fonts.py sheet 背景帧.png 出图.jpg "未来就在眼前"   → 6 款中文字体 A/B 对比图（给主人选）
      from fonts import font_for; font_for("FUTURE") / font_for("未来")  → 按文字自动选 display 或 cjk"""
import io, json, os, subprocess, sys, urllib.request, zipfile
from pathlib import Path

CACHE = Path(os.environ.get("EMBER_HOME", "/workspace/ember")) / "fonts"
try:
    CACHE.mkdir(parents=True, exist_ok=True)
except OSError:  # 没有 /workspace 写权限（如 CI）就放到用户缓存目录
    CACHE = Path.home() / ".cache" / "ember" / "fonts"
GH = "https://github.com"
SPEC = {  # 文件名, 下载地址, 本机已装时可直接用的 fc-match 名
    "display": ("Anton-Regular.ttf", f"{GH}/google/fonts/raw/main/ofl/anton/Anton-Regular.ttf", "Anton"),
    "cjk": ("SourceHanSansCN-Heavy.otf", f"{GH}/adobe-fonts/source-han-sans/raw/release/SubsetOTF/CN/SourceHanSansCN-Heavy.otf",
            "Source Han Sans SC:style=Heavy"),
    "mono": ("JetBrainsMono-ExtraBold.ttf", f"{GH}/JetBrains/JetBrainsMono/raw/master/fonts/ttf/JetBrainsMono-ExtraBold.ttf",
             "JetBrains Mono:style=ExtraBold"),
    "cn-smiley": ("SmileySans-Oblique.ttf", "zip:https://github.com/atelier-anchor/smiley-sans/releases/download/v2.0.1/smiley-sans-v2.0.1.zip", "Smiley Sans"),
    "cn-kuaile": ("ZCOOLKuaiLe-Regular.ttf", f"{GH}/google/fonts/raw/main/ofl/zcoolkuaile/ZCOOLKuaiLe-Regular.ttf", "ZCOOL KuaiLe"),
    "cn-huangyou": ("ZCOOLQingKeHuangYou-Regular.ttf", f"{GH}/google/fonts/raw/main/ofl/zcoolqingkehuangyou/ZCOOLQingKeHuangYou-Regular.ttf", "ZCOOL QingKe HuangYou"),
    "cn-serif": ("SourceHanSerifCN-Heavy.otf", f"{GH}/adobe-fonts/source-han-serif/raw/release/SubsetOTF/CN/SourceHanSerifCN-Heavy.otf", "Source Han Serif CN:style=Heavy"),
    "cn-brush": ("MaShanZheng-Regular.ttf", f"{GH}/google/fonts/raw/main/ofl/mashanzheng/MaShanZheng-Regular.ttf", "Ma Shan Zheng"),
    "pixel": ("fusion-pixel-12px-proportional-zh_hans.ttf", None, "Fusion Pixel 12px Proportional SC"),
}
FALLBACK_CJK = ["Source Han Sans CN:style=Heavy", "Noto Sans CJK SC:style=Black", "Noto Sans CJK SC:style=Bold"]


def _fc(name):
    r = subprocess.run(["fc-match", "-f", "%{file}|%{family}|%{style}", name], capture_output=True, text=True)
    path, fam, style = (r.stdout.split("|") + ["", "", ""])[:3]
    fam_ok = name.split(":")[0].lower() in fam.lower()
    style_ok = "style=" not in name or name.split("=")[1].lower() in style.lower()
    return path if path and fam_ok and style_ok and Path(path).exists() else None


def _pixel_download(dst):
    api = json.load(urllib.request.urlopen("https://api.github.com/repos/TakWolf/fusion-pixel-font/releases/latest", timeout=30))
    url = next(a["browser_download_url"] for a in api["assets"] if a["name"].startswith("fusion-pixel-font-12px-proportional-ttf-v"))
    z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(url, timeout=120).read()))
    dst.write_bytes(z.read(next(n for n in z.namelist() if n.endswith(dst.name))))


def find_font(kind="cjk"):
    if kind == "cn-heavy": kind = "cjk"
    fname, url, fc = SPEC[kind]
    local = CACHE / fname
    if local.exists(): return str(local)
    hit = _fc(fc) if kind == "cjk" else None  # 其余都下载固定文件，避免本机匹配到细体/可变字体
    if hit: return hit
    CACHE.mkdir(parents=True, exist_ok=True)
    try:
        if kind == "pixel": _pixel_download(local)
        elif url.startswith("zip:"):
            z = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(url[4:], timeout=120).read()))
            local.write_bytes(z.read(next(n for n in z.namelist() if n.endswith(fname))))
        else: urllib.request.urlretrieve(url, local)  # SIL OFL 1.1
        return str(local)
    except Exception as e:
        if kind in ("cjk", "display"):  # 断网兜底：本机任意粗体中文
            for n in FALLBACK_CJK:
                if _fc(n): return _fc(n)
        sys.exit(f"字体下载失败（{kind}）：{e}")


def font_for(text, cn="cjk"):
    """有中日韩字就用中文大字（默认思源黑体 Heavy，可换 cn-*），否则用 Anton。"""
    if not any(ord(c) > 0x2E80 for c in text): return find_font("display")
    return cn if cn and os.path.exists(cn) else find_font(cn or "cjk")


CN = [("cn-heavy", "思源黑体 Heavy"), ("cn-smiley", "得意黑"), ("cn-kuaile", "站酷快乐体"),
      ("cn-huangyou", "站酷庆科黄油体"), ("cn-serif", "思源宋体 Heavy"), ("cn-brush", "马善政毛笔楷书")]


def sheet(bg, out, text="未来就在眼前"):
    tmp = CACHE / "_sheet"; tmp.mkdir(exist_ok=True); (tmp / "t.txt").write_text(text, encoding="utf-8")
    lab = find_font("cjk"); tiles = []
    for i, (k, name) in enumerate(CN):
        (tmp / f"l{i}.txt").write_text(f"{chr(65 + i)}  {name} · SIL OFL 1.1", encoding="utf-8")
        col = "#EFE6D2" if i % 2 == 0 else "#F07A4A"
        o = tmp / f"{i}.png"; tiles.append(o)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", bg, "-vf",
            f"scale=960:540:force_original_aspect_ratio=increase,crop=960:540,drawtext=fontfile='{find_font(k)}':textfile='{tmp}/t.txt':fontsize=128:fontcolor={col}"
            f":borderw=6:bordercolor=black@0.85:shadowx=8:shadowy=8:shadowcolor=black@0.5:x=(w-text_w)/2:y=(h-text_h)/2-20,"
            f"drawbox=x=0:y=ih-62:w=iw:h=62:color=black@0.7:t=fill,drawtext=fontfile='{lab}':textfile='{tmp}/l{i}.txt':fontsize=30:fontcolor=white:x=24:y=h-47",
            "-frames:v", "1", str(o)], check=True)
    ins = sum([["-i", str(t)] for t in tiles], [])
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", "[0][1]hstack[a];[2][3]hstack[b];[4][5]hstack[c];[a][b][c]vstack=3",
                    "-q:v", "3", out], check=True)
    return out


if __name__ == "__main__":
    if sys.argv[1:2] == ["sheet"]:
        print(sheet(sys.argv[2], sys.argv[3], *(sys.argv[4:5]))); sys.exit()
    core = ["display", "cjk", "mono", "pixel"]  # 默认只装这 4 款
    kinds = core if (sys.argv[1:] or ["all"])[0] == "all" else list(SPEC) if sys.argv[1] == "extras" else sys.argv[1:]
    for k in kinds: print(k, find_font(k))
