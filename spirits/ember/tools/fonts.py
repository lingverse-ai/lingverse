"""流萤的字体（全部开源许可，SIL OFL 1.1）。新机器上第一次用会自动下载到 $EMBER_HOME/fonts。
  display  Anton                 —— 动效大字默认（v11 同款的超粗压缩无衬线）
  cjk      思源黑体 Heavy          —— 中文大字
  mono     JetBrains Mono ExtraBold —— HUD、终端逐字歌词
  pixel    Fusion Pixel 12px（简中）—— 方块世界预设
用法：python3 fonts.py [display|cjk|mono|pixel|all]   → 打印路径
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
    fname, url, fc = SPEC[kind]
    local = CACHE / fname
    if local.exists(): return str(local)
    hit = _fc(fc) if kind == "cjk" else None  # 其余都下载固定文件，避免本机匹配到细体/可变字体
    if hit: return hit
    CACHE.mkdir(parents=True, exist_ok=True)
    try:
        if kind == "pixel": _pixel_download(local)
        else: urllib.request.urlretrieve(url, local)  # SIL OFL 1.1
        return str(local)
    except Exception as e:
        if kind in ("cjk", "display"):  # 断网兜底：本机任意粗体中文
            for n in FALLBACK_CJK:
                if _fc(n): return _fc(n)
        sys.exit(f"字体下载失败（{kind}）：{e}")


def font_for(text):
    """有中日韩字就用中文粗体，否则用 Anton。"""
    return find_font("cjk" if any(ord(c) > 0x2E80 for c in text) else "display")


if __name__ == "__main__":
    kinds = list(SPEC) if (sys.argv[1:] or ["all"])[0] == "all" else sys.argv[1:]
    for k in kinds: print(k, find_font(k))
