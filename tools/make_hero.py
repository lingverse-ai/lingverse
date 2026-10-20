"""把底图做成 1600×640 的灵境主视觉，并用粗重字重叠加标题。
用法：python3 tools/make_hero.py <底图> [输出=assets/hero.png]"""
import sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1600, 640
FONT = "/home/box/.fonts/SourceHanSansSC-Heavy.otf"  # 思源黑体 Heavy


def main(src, out="assets/hero.png"):
    im = Image.open(src).convert("RGB")
    im = im.resize((W, round(im.height * W / im.width)), Image.LANCZOS)
    top = max(0, im.height - H - round(im.height * 0.02))
    im = im.crop((0, top, W, top + H))
    ov = Image.new("L", (W, H), 0)
    ImageDraw.Draw(ov).ellipse((360, 20, 1240, 330), fill=190)
    im = Image.composite(Image.new("RGB", (W, H), (6, 6, 8)), im, ov.filter(ImageFilter.GaussianBlur(70)))
    for y, text, size, fill in ((62, "灵境 Lingverse", 124, (246, 246, 243)), (222, "每位灵，只把一件事做到最好", 42, (210, 210, 205))):
        font = ImageFont.truetype(FONT, size)
        bb = ImageDraw.Draw(im).textbbox((0, 0), text, font=font)
        x = (W - (bb[2] - bb[0])) // 2 - bb[0]
        sh = Image.new("L", (W, H), 0)
        ImageDraw.Draw(sh).text((x + 3, y + 5), text, font=font, fill=230)
        im = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), im, sh.filter(ImageFilter.GaussianBlur(7)))
        ImageDraw.Draw(im).text((x, y), text, font=font, fill=fill)
    im.save(out, optimize=True)
    print(out, im.size)


if __name__ == "__main__":
    main(*sys.argv[1:])
