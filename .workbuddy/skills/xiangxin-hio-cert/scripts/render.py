#!/usr/bin/env python3
"""HIO 纪念球 logo 渲染器

输入: 模板球图 + 客户姓名/球场/洞号/日期
输出: 改完文字的纪念球 PNG

模板几何参数 (实测于 assets/template.png):
  logo 中心 (547, 667), 半径 295, 文字弧半径 252
  4 颗星星: -147°/-33°/+33°/+148°, 半径 252 (跟文字弧同心圆)
  原"红圈"=金色双圈, 半径 194-216
  代表蓝 (19, 55, 110)
"""
import argparse
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import numpy as np

# ====== 模板几何 ======
CX, CY = 547, 667
TEXT_R = 252
BLUE = [19, 55, 110]

# ====== 字体 ======
FONT_ZH = "/System/Library/Fonts/STHeiti Medium.ttc"
FONT_EN = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_NARROW = "/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf"

# ====== 4 段文字角度区间 (严格避开 4 颗星星, 各侧留 ≥9° buffer) ======
TOP_S, TOP_E = -115, -65       # 顶 HIO  (跨 50°)
RIGHT_S, RIGHT_E = -24, +24    # 右 日期 (跨 48°, 在右上/右下星之间)
BOT_S, BOT_E = +136, +44       # 底 英文名 (跨 92°, cw 左到右)
LEFT_S, LEFT_E = -157, +157    # 左 球场+洞号 (跨 46°, 跨过 ±180°)


def erase_template(img):
    """擦掉模板上的原文字+原金色双圈, 保留星星/中央 logo/球面"""
    arr = np.array(img).astype(np.int32)
    H, W = arr.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    dist = np.sqrt((xx-CX)**2 + (yy-CY)**2)
    r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
    # 金色双圈半径 194-216, 涂白
    ring_mask = (dist >= 192) & (dist <= 216)
    not_pure_white = ~((r > 250) & (g > 250) & (b > 250))
    arr[ring_mask & not_pure_white] = [255, 255, 255]
    # 蓝环带 220-295 内 非深蓝 非金色(星星) 涂蓝
    in_ring = (dist >= 220) & (dist <= 295)
    is_golden = (r > 180) & (g > 140) & (g < 220) & (b < 100)
    blue_dist = np.sqrt((r-19)**2 + (g-55)**2 + (b-110)**2)
    arr[in_ring & (blue_dist > 25) & ~is_golden] = BLUE
    return Image.fromarray(arr.clip(0, 255).astype(np.uint8))


def _draw_char(img, ch, font, color, cx, cy, pil_rot):
    bbox = font.getbbox(ch)
    cw = max(bbox[2]-bbox[0]+30, 40)
    chh = max(bbox[3]-bbox[1]+30, 40)
    ch_img = Image.new("RGBA", (cw, chh), (0, 0, 0, 0))
    ImageDraw.Draw(ch_img).text((cw//2, chh//2), ch, font=font,
                                 fill=color, anchor="mm")
    rotated = ch_img.rotate(pil_rot, expand=True, resample=Image.BICUBIC)
    img.paste(rotated,
              (int(cx - rotated.width/2), int(cy - rotated.height/2)),
              rotated)


def arc_text(img, text, radius, start_deg, end_deg, font, color,
             baseline_inward):
    """沿短弧从 start_deg 到 end_deg 画 text 字符.

    baseline_inward=True  → 字底朝圆心 (顶/左/右用)
    baseline_inward=False → 字底朝外   (底用)
    """
    n = len(text)
    diff = end_deg - start_deg
    while diff > 180:
        diff -= 360
    while diff <= -180:
        diff += 360
    angles = [start_deg + diff * i / max(n-1, 1) for i in range(n)]
    for ch, ang_deg in zip(text, angles):
        a = math.radians(ang_deg)
        px = CX + radius * math.cos(a)
        py = CY + radius * math.sin(a)
        if baseline_inward:
            pil_rot = -(ang_deg + 90)
        else:
            pil_rot = -(ang_deg - 90)
        _draw_char(img, ch, font, color, px, py, pil_rot)


def render(template_path, name, course, hole, date, output_path,
           hio_text="HIO"):
    """渲染一份 HIO 纪念球 logo.

    参数:
      template_path: 模板 PNG (assets/template.png)
      name: 英文姓名 (如 HenryHuang) — 底部弧
      course: 球场名繁体 (如 費度) — 左弧前半
      hole: 洞号繁体 (如 六)         — 左弧中后
      date: 日期 YYYY.MM.DD          — 右侧弧
      output_path: 输出 PNG
      hio_text: 顶部弧文字 (默认 HIO)
    """
    img = Image.open(template_path).convert("RGB")
    img = erase_template(img)
    img_rgba = img.convert("RGBA")
    white = (255, 255, 255, 255)

    # 顶部 HIO
    arc_text(img_rgba, hio_text, TEXT_R, TOP_S, TOP_E,
             ImageFont.truetype(FONT_EN, 56), white, baseline_inward=True)

    # 右侧 日期 — Arial Narrow Bold 才塞得下 10 字符 + 留缝
    arc_text(img_rgba, date, TEXT_R, RIGHT_S, RIGHT_E,
             ImageFont.truetype(FONT_NARROW, 36), white, baseline_inward=True)

    # 底部 英文名 — 字底朝外
    arc_text(img_rgba, name, TEXT_R, BOT_S, BOT_E,
             ImageFont.truetype(FONT_EN, 32), white, baseline_inward=False)

    # 左侧 球场+第+洞号+洞 — 凑成 5 字
    left_text = f"{course}第{hole}洞"
    arc_text(img_rgba, left_text, TEXT_R, LEFT_S, LEFT_E,
             ImageFont.truetype(FONT_ZH, 36), white, baseline_inward=True)

    img_rgba.convert("RGB").save(output_path)
    return output_path


def main():
    ap = argparse.ArgumentParser(description="HIO 纪念球 logo 渲染")
    here = Path(__file__).resolve().parent.parent
    default_tpl = here / "assets" / "template.png"
    ap.add_argument("--template", default=str(default_tpl),
                    help="模板 PNG (默认 assets/template.png)")
    ap.add_argument("--name", required=True,
                    help="英文姓名, 底部弧, 如 HenryHuang")
    ap.add_argument("--course", default="費度",
                    help="球场名繁体, 左侧弧前半, 默认 費度")
    ap.add_argument("--hole", default="六",
                    help="洞号繁体, 默认 六")
    ap.add_argument("--date", required=True,
                    help="日期 YYYY.MM.DD")
    ap.add_argument("--output", required=True,
                    help="输出 PNG 路径")
    ap.add_argument("--hio-text", default="HIO",
                    help="顶部弧文字 (默认 HIO)")
    args = ap.parse_args()

    out = render(args.template, args.name, args.course, args.hole,
                 args.date, args.output, args.hio_text)
    print(f"OK -> {out}")


if __name__ == "__main__":
    main()
