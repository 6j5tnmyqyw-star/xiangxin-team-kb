"""睿盛五金·HIO 纪念球 矢量 PDF 生成

第1页: 蓝色徽章版 (基于 版本K-HIO 改版风格)
第2页: 黑色极简戳章版 (基于 方向C 极简戳章)

技术: reportlab Canvas
- 球面 + 中央客户 logo: 嵌入位图 (本来就是栅格)
- 蓝色圆 / 圆环 / 星星 / 文字: 全矢量
"""
import math
import sys
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.lib.colors import Color, white, black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ballvec import draw_vector_ball          # 矢量高尔夫球
from svgpath import draw_logo                  # 矢量客户 logo

# === 字体注册 ===
pdfmetrics.registerFont(TTFont('HeitiTC', '/System/Library/Fonts/STHeiti Medium.ttc'))
pdfmetrics.registerFont(TTFont('ArialBold', '/System/Library/Fonts/Supplemental/Arial Bold.ttf'))
pdfmetrics.registerFont(TTFont('ArialNarrow', '/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf'))
# 中文楷书 (Kaiti.ttc 有5个子字体: 0=Regular, 2=Black 粗体)
_KAITI = '/System/Library/AssetsV2/com_apple_MobileAsset_Font7/54a2ad3dac6cac875ad675d7d273dc425010a877.asset/AssetData/Kaiti.ttc'
pdfmetrics.registerFont(TTFont('Kaiti', _KAITI, subfontIndex=0))
pdfmetrics.registerFont(TTFont('KaitiBold', _KAITI, subfontIndex=2))
# 英文花体 (SnellRoundhand 1=Bold, 2=Black)
pdfmetrics.registerFont(TTFont('Snell', '/System/Library/Fonts/Supplemental/SnellRoundhand.ttc', subfontIndex=0))
pdfmetrics.registerFont(TTFont('SnellBold', '/System/Library/Fonts/Supplemental/SnellRoundhand.ttc', subfontIndex=1))
pdfmetrics.registerFont(TTFont('SnellBlack', '/System/Library/Fonts/Supplemental/SnellRoundhand.ttc', subfontIndex=2))

# === 素材路径 ===
_HERE = Path(__file__).resolve().parent.parent
BALL_BG = _HERE / "assets" / "ball_clean.png"
CLIENT_LOGO = _HERE / "assets" / "client_logo_transparent.png"
CLIENT_LOGO_SVG = _HERE / "assets" / "client_logo_vector.svg"   # 矢量版 logo

# === 颜色 ===
DEEP_BLUE = Color(19/255, 55/255, 110/255)
GOLD = Color(212/255, 175/255, 55/255)
RED_FLAG = Color(220/255, 38/255, 38/255)

# === 页面尺寸: A5 (148x210mm) ===
PAGE_W, PAGE_H = A5

# === 印刷可用范围 (卡死铁律) ===
# 客户标注: logo/设计不得超出球面中央的圆形范围.
# 实测红圈直径 / 球直径 = 0.48 (2026-06-02 截图量定).
PRINT_RANGE_RATIO = 0.48      # 最大可印圆直径 / 球直径, 设计绝不可超
DESIGN_SAFETY = 0.96          # 设计外缘留 4% 安全边, 不顶到红线
# 设计最大半径 = 球半径 * PRINT_RANGE_RATIO * DESIGN_SAFETY

def draw_star_5(c, cx, cy, r_out, color, r_in_ratio=0.4, point_angle_deg=-90):
    """画 5 角星. point_angle_deg = 主尖朝向的屏幕角度 (默认 -90 = 朝上).
    PDF y 向上, 计算时用 y 翻转保持屏幕惯例"""
    path = c.beginPath()
    r_in = r_out * r_in_ratio
    for i in range(10):
        ang = math.radians(point_angle_deg + i * 36)
        r = r_out if i % 2 == 0 else r_in
        x = cx + r * math.cos(ang)
        y = cy - r * math.sin(ang)
        if i == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
    path.close()
    c.setFillColor(color)
    c.drawPath(path, stroke=0, fill=1)

def _split_camel(name):
    """HenryHuang -> Henry Huang (花体显示加空格)"""
    import re
    return re.sub(r'([a-z])([A-Z])', r'\1 \2', name)


def draw_arc_text(c, text, cx, cy, radius, start_deg, end_deg,
                  font_name, font_size, color, baseline_inward=True):
    """沿弧画矢量文字 (每字符旋转后画)
    PDF 坐标 y 向上, 屏幕 y 向下 — 这里 angle 用屏幕惯例 (0°右 90°下 -90°上)
    所以画时 y_pdf = cy - dy_screen
    """
    n = len(text)
    diff = end_deg - start_deg
    while diff > 180: diff -= 360
    while diff <= -180: diff += 360
    angles = [start_deg + diff * i / max(n-1, 1) for i in range(n)]
    c.setFillColor(color)
    c.setFont(font_name, font_size)
    for ch, ang_deg in zip(text, angles):
        a = math.radians(ang_deg)
        # 屏幕坐标的位移, PDF y 向上需翻转 dy
        px = cx + radius * math.cos(a)
        py = cy - radius * math.sin(a)
        # 字符旋转角: 屏幕坐标下 baseline_inward → char_rot = -(ang_deg+90)
        # PDF rotate 是 CCW (数学上的)
        # 屏幕翻转 y 后, ang_screen→ang_pdf: pdf 看到 cos(a) 同, -sin(a) 取反.
        # 等价于 ang_pdf = -ang_deg
        # 字底朝圆心: PDF rotate 角度 = ang_pdf + 90 = -ang_deg + 90
        if baseline_inward:
            pdf_rot = -ang_deg - 90
        else:
            pdf_rot = -ang_deg + 90
        c.saveState()
        c.translate(px, py)
        c.rotate(pdf_rot)
        # 居中绘制
        w = c.stringWidth(ch, font_name, font_size)
        c.drawString(-w/2, -font_size*0.35, ch)
        c.restoreState()

# ======================================================================
# 第 1 页: 蓝色徽章版
# ======================================================================
def page1_blue_badge(c, name_en="HenryHuang", name_cn="黃偉哲",
                     company="睿盛五金", course="費度", hole="六",
                     date="2026.05.31", ball_mode="vector"):
    """蓝色徽章版面布局
    Layout: 球面 + 蓝色圆盘 + 客户logo (中央) + 星星 + 4处弧文字
    ball_mode: 'vector' 全矢量球(0位图) | 'raster' 高清照片球
    """
    # === 1. 球面 (居中, 占页面 90%) ===
    ball_w = PAGE_W * 0.85
    ball_h = ball_w
    bx = (PAGE_W - ball_w) / 2
    by = (PAGE_H - ball_h) / 2
    if ball_mode == "vector":
        draw_vector_ball(c, PAGE_W / 2, PAGE_H / 2, ball_w / 2)
    else:
        c.drawImage(str(BALL_BG), bx, by, width=ball_w, height=ball_h, mask='auto')

    # logo 中心 = 球中心
    cx = PAGE_W / 2
    cy = PAGE_H / 2

    # === 2. 蓝色圆盘 (logo 背景) — 外径卡死在印刷可用范围内 ===
    # 蓝盘是最外元素, 其直径 = 球径 * PRINT_RANGE_RATIO * DESIGN_SAFETY, 绝不超红线
    R_OUTER = ball_w / 2 * PRINT_RANGE_RATIO * DESIGN_SAFETY
    c.setFillColor(DEEP_BLUE)
    c.circle(cx, cy, R_OUTER, stroke=0, fill=1)

    # === 3a. 白色底圆 ===
    R_WHITE_INNER = R_OUTER * 0.62
    c.setFillColor(white)
    c.circle(cx, cy, R_WHITE_INNER, stroke=0, fill=1)

    # === 3b. 中央客户 logo (矢量 path 嵌入, 占满白圆) ===
    R_INNER_LOGO = R_WHITE_INNER * 0.95
    logo_size = R_INNER_LOGO * 2
    draw_logo(c, str(CLIENT_LOGO_SVG), cx, cy, logo_size, DEEP_BLUE)

    # === 4. 4 颗金色星星 — 居中放在 4 段文字 gap 的正中央 (工整对齐) ===
    # 顶→右 gap 中心: (-55+(-24))/2 = -39.5°
    # 右→底 gap 中心: (24+50)/2 = +37°
    # 底→左 gap 中心: (130+156)/2 = +143°
    # 左→顶 gap 中心: (-156+(-125))/2 = -140.5°
    # 星星半径跟文字弧同心, 每颗星的主尖朝外辐射 (point_angle = ang_deg, 让尖向外)
    star_r = R_OUTER * 0.06
    star_radius = R_OUTER * 0.86  # 跟文字弧同径, 视觉真正"对齐"
    for ang_deg in [-140.5, -39.5, 37, 143]:
        a = math.radians(ang_deg)
        sx = cx + star_radius * math.cos(a)
        sy = cy - star_radius * math.sin(a)
        draw_star_5(c, sx, sy, star_r, GOLD, point_angle_deg=ang_deg)

    # === 5. 4 处弧文字 (全矢量) ===
    TEXT_R = R_OUTER * 0.86  # 文字弧半径
    fs_top = R_OUTER * 0.13   # 顶部字号
    fs_side = R_OUTER * 0.10  # 侧面字号

    # 顶部 公司名 (楷书粗体, 字底朝圆心) — 参考客户图风格
    draw_arc_text(c, company, cx, cy, TEXT_R,
                  -125, -55, 'KaitiBold', fs_top, white, baseline_inward=True)
    # 右侧 日期 (Arial Narrow Bold, 字底朝圆心)
    draw_arc_text(c, date, cx, cy, TEXT_R,
                  -24, +24, 'ArialNarrow', fs_side, white, baseline_inward=True)
    # 底部 英文名 — 手写花体 (Snell Black 粗一点更显眼)
    # 注意: name_en 在花体下"HenryHuang" 不如 "Henry Huang" 有空格好看
    name_en_display = name_en if ' ' in name_en else _split_camel(name_en)
    draw_arc_text(c, name_en_display, cx, cy, TEXT_R,
                  +130, +50, 'SnellBlack', fs_side*1.35, white, baseline_inward=False)
    # 左侧 球场+第+洞号+洞 (楷书, 字底朝圆心)
    left_text = f"{course}第{hole}洞"
    draw_arc_text(c, left_text, cx, cy, TEXT_R,
                  -156, +156, 'KaitiBold', fs_side*0.95, white, baseline_inward=True)

    # === 6. 页面标注 (左下角小字) ===
    c.setFillColor(Color(0.4, 0.4, 0.4))
    c.setFont('HeitiTC', 8)
    c.drawString(15, 15, f"睿盛五金·HIO 纪念球 矢量 PDF · 第 1 页/蓝色徽章版 · 印刷文件")

# ======================================================================
# 第 2 页: 黑色极简戳章版 (类似祥书发的图1风格)
# ======================================================================
def draw_tee_and_ball(c, x, y, scale=1.0, color=black):
    """画 tee + 球 装饰 (tee = 倒三角, 球 = 小圆)"""
    s = scale
    # 倒三角 tee (尖朝下)
    p = c.beginPath()
    p.moveTo(x - 5*s, y + 6*s)
    p.lineTo(x + 5*s, y + 6*s)
    p.lineTo(x, y - 4*s)
    p.close()
    c.setFillColor(color)
    c.drawPath(p, fill=1, stroke=0)
    # 球 (在 tee 上方)
    c.circle(x, y + 8*s, 3*s, fill=1, stroke=0)


def page2_hole_in_one(c, name_cn="黃亨利", hole_num="6",
                       date_cn="2026年5月31日", course_cn="費度", ball_mode="vector"):
    """图1 风格: 黑色 Hole In One 横版 + 右侧 4 行客户信息 + 旗杆+红旗

    布局 (页面分左右两半):
      左半 (~55%): Hole In One 艺术字 (3 行 H/I/O 大字 + 旁边小写)
                  + H 下方 tee+球, I 上方球, O 内球+tee
      右半 (~45%): 4 行竖排
                  - 黃亨利 (黑色)
                  - 6号洞 (红色, 粗)
                  - 2026年5月31日
                  - — 費度一桿進洞 — (红线装饰)
      左右之间: 旗杆 + 红色小旗 (旗杆斜向右上)
    """
    # === 1. 球面 (放大到 95% 让设计区有更多空间) ===
    ball_w = PAGE_W * 0.95
    ball_h = ball_w
    bx = (PAGE_W - ball_w) / 2
    by = (PAGE_H - ball_h) / 2
    if ball_mode == "vector":
        draw_vector_ball(c, PAGE_W / 2, PAGE_H / 2, ball_w / 2)
    else:
        c.drawImage(str(BALL_BG), bx, by, width=ball_w, height=ball_h, mask='auto')

    cx = PAGE_W / 2
    cy = PAGE_H / 2

    # 整体设计区: 球面中央可印面积 (球面赤道带, 约 50% 直径)
    design_w = ball_w * 0.50
    design_h = ball_w * 0.30
    dx0 = cx - design_w / 2
    dy0 = cy - design_h / 2

    # === 2. 左半: "Hole In One" 三行艺术字 ===
    # H/I/O 大字 (衬线粗体, 黑色)
    big_font = "Times-Bold"  # reportlab 内置
    small_font = "Times-Roman"
    big_size = design_h * 0.30
    small_size = design_h * 0.10

    # H 行 (第一行, 顶端)
    h_y = dy0 + design_h * 0.78
    c.setFillColor(black)
    c.setFont(big_font, big_size)
    c.drawString(dx0, h_y, "H")
    c.setFont(small_font, small_size)
    c.drawString(dx0 + big_size * 0.65, h_y + big_size * 0.45, "ole")

    # I 行 (第二行, 中)
    i_y = dy0 + design_h * 0.42
    c.setFont(big_font, big_size)
    c.drawString(dx0 + big_size * 0.12, i_y, "I")
    c.setFont(small_font, small_size)
    c.drawString(dx0 + big_size * 0.55, i_y + big_size * 0.45, "n")

    # O 行 (第三行, 底)
    o_y = dy0 + design_h * 0.06
    c.setFont(big_font, big_size)
    c.drawString(dx0, o_y, "O")
    c.setFont(small_font, small_size)
    c.drawString(dx0 + big_size * 0.70, o_y + big_size * 0.45, "ne")

    # 装饰: tee+ball
    # H 下方 tee+球 (在 H 的右下)
    draw_tee_and_ball(c, dx0 + big_size * 0.32, h_y - big_size * 0.05,
                      scale=big_size * 0.04, color=black)
    # I 上方小球
    c.setFillColor(black)
    c.circle(dx0 + big_size * 0.22, i_y + big_size * 0.95,
             big_size * 0.05, fill=1, stroke=0)
    # O 字内/下小球
    c.circle(dx0 + big_size * 0.28, o_y + big_size * 0.22,
             big_size * 0.07, fill=1, stroke=0)

    # === 3. 旗杆 + 红色小旗 (在中间偏右上, 连接左右) ===
    pole_x = cx + design_w * 0.10
    pole_top = dy0 + design_h * 1.18
    pole_bot = dy0 + design_h * 0.05
    c.setStrokeColor(black)
    c.setLineWidth(big_size * 0.025)
    c.line(pole_x, pole_bot, pole_x, pole_top)
    # 红色旗
    flag_h = big_size * 0.55
    c.setFillColor(RED_FLAG)
    p = c.beginPath()
    p.moveTo(pole_x, pole_top)
    p.lineTo(pole_x + flag_h * 1.1, pole_top - flag_h * 0.35)
    p.lineTo(pole_x, pole_top - flag_h * 0.7)
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    # 旗杆底 小三角(tee)
    p = c.beginPath()
    p.moveTo(pole_x - flag_h * 0.18, pole_bot)
    p.lineTo(pole_x + flag_h * 0.18, pole_bot)
    p.lineTo(pole_x, pole_bot - flag_h * 0.25)
    p.close()
    c.setFillColor(black)
    c.drawPath(p, fill=1, stroke=0)

    # === 4. 右半: 4 行客户信息 ===
    rx = pole_x + big_size * 0.45  # 右半起点
    text_size = design_h * 0.13
    red_size = design_h * 0.16
    line_gap = design_h * 0.22

    # 行 1: 黃亨利 (黑色, 中)
    c.setFillColor(black)
    c.setFont('HeitiTC', text_size)
    c.drawString(rx, dy0 + design_h * 0.78, name_cn)

    # 行 2: 6号洞 (红色, 粗, 大)
    c.setFillColor(RED_FLAG)
    c.setFont('HeitiTC', red_size)
    c.drawString(rx, dy0 + design_h * 0.52, f"{hole_num}号洞")

    # 行 3: 日期 (黑色)
    c.setFillColor(black)
    c.setFont('HeitiTC', text_size * 0.95)
    c.drawString(rx, dy0 + design_h * 0.28, date_cn)

    # 行 4: — 费度一桿進洞 — (红色横线装饰)
    decor_text = f"{course_cn}一桿進洞"
    decor_size = text_size * 0.85
    c.setFont('HeitiTC', decor_size)
    decor_w = c.stringWidth(decor_text, 'HeitiTC', decor_size)
    decor_y = dy0 + design_h * 0.06
    # 左横线
    c.setStrokeColor(RED_FLAG)
    c.setLineWidth(decor_size * 0.12)
    line_pad = decor_size * 0.3
    c.line(rx, decor_y + decor_size * 0.3,
           rx + decor_size * 0.6, decor_y + decor_size * 0.3)
    # 文字
    c.setFillColor(black)
    c.drawString(rx + decor_size * 0.8, decor_y, decor_text)
    # 右横线
    text_end_x = rx + decor_size * 0.8 + decor_w + decor_size * 0.3
    c.line(text_end_x, decor_y + decor_size * 0.3,
           text_end_x + decor_size * 0.6, decor_y + decor_size * 0.3)

    # === 5. 页面标注 ===
    c.setFillColor(Color(0.4, 0.4, 0.4))
    c.setFont('HeitiTC', 8)
    c.drawString(15, 15, "睿盛五金·HIO 纪念球 矢量 PDF · 第 2 页/Hole In One 横版 · 印刷文件")


# === 主流程 ===
def main(out_path):
    c = canvas.Canvas(out_path, pagesize=A5)
    c.setTitle("睿盛五金·HIO 纪念球·矢量印刷文件")
    c.setAuthor("祥新公司 AI")
    c.setSubject("Hole-In-One Commemorative Golf Ball")

    page1_blue_badge(c)
    c.showPage()
    page2_hole_in_one(c)
    c.showPage()
    c.save()
    print(f"OK -> {out_path}")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="HIO 纪念球 矢量 PDF (两版模板)")
    ap.add_argument("--name-en", default="HenryHuang", help="英文姓名 (底部弧)")
    ap.add_argument("--name-cn", default="黃亨利", help="中文姓名 (Page2 右侧)")
    ap.add_argument("--company", default="睿盛五金", help="公司名 (Page1 顶部)")
    ap.add_argument("--course", default="費度", help="球场名繁体")
    ap.add_argument("--hole", default="六", help="洞号繁体 (Page1)")
    ap.add_argument("--hole-num", default="6", help="洞号数字 (Page2)")
    ap.add_argument("--date-pdf1", default="2026.05.31", help="Page1 日期 YYYY.MM.DD")
    ap.add_argument("--date-pdf2", default="2026年5月31日", help="Page2 中式日期")
    ap.add_argument("--output", required=True, help="输出 PDF 路径")
    ap.add_argument("--page-only", choices=["1", "2", "both"], default="both",
                    help="只出 page1 / page2 / both (默认 both)")
    ap.add_argument("--ball", choices=["vector", "raster"], default="vector",
                    help="球面: vector=全矢量0位图(默认) | raster=高清照片球")
    args = ap.parse_args()
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A5
    c = canvas.Canvas(args.output, pagesize=A5)
    c.setTitle("HIO 纪念球·矢量印刷文件")
    if args.page_only in ("1", "both"):
        page1_blue_badge(c, name_en=args.name_en, company=args.company,
                         course=args.course, hole=args.hole, date=args.date_pdf1,
                         ball_mode=args.ball)
        c.showPage()
    if args.page_only in ("2", "both"):
        page2_hole_in_one(c, name_cn=args.name_cn, hole_num=args.hole_num,
                          date_cn=args.date_pdf2, course_cn=args.course,
                          ball_mode=args.ball)
        c.showPage()
    c.save()
    print(f"OK -> {args.output}")
