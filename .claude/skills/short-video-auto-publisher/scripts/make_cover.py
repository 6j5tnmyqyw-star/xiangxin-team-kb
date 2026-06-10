#!/usr/bin/env python3
"""给短视频封面叠中文标题大字。

底图来自 ChatGPT（干净、无中文字），本脚本把【正确的】中文标题叠上去——
绕开 GPT 生成中文易缺笔画/乱码的坑。用法见 references/cover-generation.md。

  python3 make_cover.py --bg bg.png --title "标题" --out cover.png \
      [--subtitle "副标题"] [--size 1080x1920] [--force]
"""
import argparse
import os
import sys

# 违禁词红线（封面文字同样不许出现），见 03-内容创作规范
BANNED = ["极致", "史上最低", "第一", "绝对", "国家级", "唯一", "顶级", "独家",
          "军用级", "百分百精准", "激光武器级", "超越同行"]
# "最"单字误伤太高（最看重/最纠结都正常），只拦营销极限组合
BANNED_ZUI = ["最低", "最好", "最便宜", "最强", "最高", "最优", "最佳", "最大", "最快", "最值钱"]


def check_banned(text, force):
    hits = [w for w in BANNED + BANNED_ZUI if w in text]
    if not hits:
        return
    if force:
        print(f"[违禁词][--force 已跳过] 命中：{hits}", file=sys.stderr)
        return
    print(f"[违禁词] 标题命中极限词 {hits}，按红线不许上封面。请改写；"
          f"若确为误伤（如『最看重』）加 --force。", file=sys.stderr)
    sys.exit(2)


def load_font(size):
    from PIL import ImageFont
    # (路径, ttc index)，靠前的更粗；逐个试，能加载就用
    candidates = [
        ("/System/Library/Fonts/PingFang.ttc", 8),
        ("/System/Library/Fonts/PingFang.ttc", 4),
        ("/System/Library/Fonts/PingFang.ttc", 2),
        ("/System/Library/Fonts/PingFang.ttc", 0),
        ("/System/Library/Fonts/STHeiti Medium.ttc", 0),
        ("/System/Library/Fonts/Hiragino Sans GB.ttc", 1),
        ("/Library/Fonts/Arial Unicode.ttf", 0),
    ]
    for path, idx in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size, index=idx)
            except Exception:
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
    return ImageFont.load_default()


def text_w(draw, s, font):
    try:
        return draw.textlength(s, font=font)
    except Exception:
        return font.getbbox(s)[2]


def wrap(draw, text, font, max_w):
    lines, cur = [], ""
    for ch in text:
        if ch == "\n":
            lines.append(cur)
            cur = ""
            continue
        if text_w(draw, cur + ch, font) > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def main():
    ap = argparse.ArgumentParser(description="给短视频封面叠中文标题大字")
    ap.add_argument("--bg", required=True, help="ChatGPT 出的无字底图路径")
    ap.add_argument("--title", required=True, help="封面标题（中文，会叠到顶部）")
    ap.add_argument("--subtitle", default="", help="可选副标题小字")
    ap.add_argument("--out", required=True, help="输出封面路径 .png")
    ap.add_argument("--size", default="1080x1920", help="目标尺寸 WxH，默认 1080x1920(9:16)")
    ap.add_argument("--force", action="store_true", help="跳过违禁词阻断（应对『最看重』类误伤）")
    args = ap.parse_args()

    check_banned(args.title, args.force)
    if args.subtitle:
        check_banned(args.subtitle, args.force)

    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("需要 Pillow：pip3 install Pillow", file=sys.stderr)
        sys.exit(1)

    try:
        W, H = (int(x) for x in args.size.lower().split("x"))
    except Exception:
        print(f"--size 格式应为 WxH，如 1080x1920；收到 {args.size!r}", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.bg):
        print(f"底图不存在：{args.bg}", file=sys.stderr)
        sys.exit(1)

    # 底图 cover 缩放 + 居中裁切到 WxH
    bg = Image.open(args.bg).convert("RGB")
    scale = max(W / bg.width, H / bg.height)
    bg = bg.resize((round(bg.width * scale), round(bg.height * scale)))
    left = (bg.width - W) // 2
    top = (bg.height - H) // 2
    bg = bg.crop((left, top, left + W, top + H))

    # 顶部半透明黑色渐变遮罩，保证白字在任何背景上都清晰
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    grad_h = int(H * 0.42)
    for y in range(grad_h):
        a = int(150 * (1 - y / grad_h))
        od.line([(0, y), (W, y)], fill=(0, 0, 0, a))
    bg = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")

    draw = ImageDraw.Draw(bg)
    margin = int(W * 0.07)
    max_w = W - 2 * margin

    # 标题字号自适应：从大往小试，最多 3 行
    size = int(W / 8)
    floor = int(W / 16)
    while size > floor:
        font = load_font(size)
        if len(wrap(draw, args.title, font, max_w)) <= 3:
            break
        size -= 6
    font = load_font(size)
    lines = wrap(draw, args.title, font, max_w)

    y = int(H * 0.07)
    line_h = size + int(size * 0.28)
    stroke = max(2, size // 18)
    for ln in lines:
        draw.text((margin, y), ln, font=font, fill=(255, 255, 255),
                  stroke_width=stroke, stroke_fill=(0, 0, 0))
        y += line_h

    if args.subtitle:
        sf_size = int(size * 0.5)
        sf = load_font(sf_size)
        y += int(size * 0.15)
        for ln in wrap(draw, args.subtitle, sf, max_w):
            draw.text((margin, y), ln, font=sf, fill=(255, 226, 168),
                      stroke_width=2, stroke_fill=(0, 0, 0))
            y += sf_size + int(sf_size * 0.4)

    out_dir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(out_dir, exist_ok=True)
    bg.save(args.out, quality=92)
    print(args.out)


if __name__ == "__main__":
    main()
