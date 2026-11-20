"""高尔夫球印刷版式库 — 3 大类 x 多款, 全矢量 + 卡死球径 48% 圈.

类别:
  A 个人姓名/花押 (Monogram)
  B 企业/品牌 logo
  C 赛事/活动纪念

每款画一页 A5, 占位示例信息. 复用 render_pdf 的工具 + 范围铁律.
"""
import math
import sys
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5
from reportlab.lib.colors import Color, white, black

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_pdf as RP                              # 注册字体 + 工具函数
from render_pdf import (draw_arc_text, draw_star_5, _split_camel,
                        DEEP_BLUE, GOLD, RED_FLAG, PAGE_W, PAGE_H,
                        PRINT_RANGE_RATIO, DESIGN_SAFETY)
from ballvec import draw_vector_ball
from svgpath import draw_logo

CLIENT_LOGO_SVG = Path(__file__).resolve().parent.parent / "assets" / "client_logo_vector.svg"
NAVY = DEEP_BLUE
GREEN = Color(22/255, 101/255, 52/255)            # 高尔夫草绿 (备选主色)

# 球面 + 设计圈基准
BALL_W = PAGE_W * 0.85
CX, CY = PAGE_W / 2, PAGE_H / 2
R_MAX = BALL_W / 2 * PRINT_RANGE_RATIO * DESIGN_SAFETY    # 设计最大半径 (=球径46%)


def _ball(c):
    draw_vector_ball(c, CX, CY, BALL_W / 2)


def _ring(c, r, color, w):
    c.setStrokeColor(color); c.setLineWidth(w)
    c.circle(CX, CY, r, stroke=1, fill=0)


def _footer(c, label):
    c.setFillColor(Color(0.45, 0.45, 0.45)); c.setFont('HeitiTC', 7.5)
    c.drawString(14, 13, label)


def _deco_line(c, cx, y, half_w, color, lw=1.4):
    """中间带菱形点的细装饰线"""
    c.setStrokeColor(color); c.setLineWidth(lw)
    c.line(cx - half_w, y, cx - half_w * 0.18, y)
    c.line(cx + half_w * 0.18, y, cx + half_w, y)
    s = half_w * 0.05
    p = c.beginPath()
    p.moveTo(cx, y + s); p.lineTo(cx + s, y); p.lineTo(cx, y - s); p.lineTo(cx - s, y); p.close()
    c.setFillColor(color); c.drawPath(p, stroke=0, fill=1)


def _diamond(c, cx, cy, r, color, lw):
    c.setStrokeColor(color); c.setLineWidth(lw)
    p = c.beginPath()
    p.moveTo(cx, cy + r); p.lineTo(cx + r, cy); p.lineTo(cx, cy - r); p.lineTo(cx - r, cy); p.close()
    c.drawPath(stroke=1, fill=0, aPath=p)


def _shield(c, cx, cy, w, h, color, lw, fill=0):
    """盾形 (顶平, 底尖圆)"""
    p = c.beginPath()
    p.moveTo(cx - w/2, cy + h/2)
    p.lineTo(cx + w/2, cy + h/2)
    p.lineTo(cx + w/2, cy - h*0.12)
    p.curveTo(cx + w/2, cy - h*0.40, cx + w*0.22, cy - h/2, cx, cy - h/2)
    p.curveTo(cx - w*0.22, cy - h/2, cx - w/2, cy - h*0.40, cx - w/2, cy - h*0.12)
    p.close()
    if fill:
        c.setFillColor(color); c.drawPath(p, stroke=0, fill=1)
    else:
        c.setStrokeColor(color); c.setLineWidth(lw); c.drawPath(p, stroke=1, fill=0)


def _trophy(c, cx, cy, s, color):
    """简矢量奖杯"""
    c.setFillColor(color); c.setStrokeColor(color); c.setLineWidth(s*0.12)
    # 杯体
    p = c.beginPath()
    p.moveTo(cx - s*0.5, cy + s*0.9)
    p.lineTo(cx + s*0.5, cy + s*0.9)
    p.lineTo(cx + s*0.34, cy + s*0.2)
    p.curveTo(cx + s*0.34, cy, cx - s*0.34, cy, cx - s*0.34, cy + s*0.2)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    # 双耳
    c.circle(cx - s*0.5, cy + s*0.62, s*0.22, stroke=1, fill=0)
    c.circle(cx + s*0.5, cy + s*0.62, s*0.22, stroke=1, fill=0)
    # 杆 + 底座
    c.setLineWidth(s*0.14)
    c.line(cx, cy + s*0.2, cx, cy - s*0.25)
    p = c.beginPath()
    p.moveTo(cx - s*0.45, cy - s*0.55); p.lineTo(cx + s*0.45, cy - s*0.55)
    p.lineTo(cx + s*0.30, cy - s*0.25); p.lineTo(cx - s*0.30, cy - s*0.25); p.close()
    c.setFillColor(color); c.drawPath(p, stroke=0, fill=1)


def _ribbon(c, cx, cy, w, h, color):
    """横幅缎带 (两端燕尾)"""
    c.setFillColor(color)
    p = c.beginPath()
    p.moveTo(cx - w/2, cy + h/2); p.lineTo(cx + w/2, cy + h/2)
    p.lineTo(cx + w/2 - h*0.5, cy); p.lineTo(cx + w/2, cy - h/2)
    p.lineTo(cx - w/2, cy - h/2); p.lineTo(cx - w/2 + h*0.5, cy); p.close()
    c.drawPath(p, stroke=0, fill=1)


def _flag(c, x, y_bot, y_top, color):
    """旗杆+小三角旗"""
    c.setStrokeColor(black); c.setLineWidth((y_top-y_bot)*0.04)
    c.line(x, y_bot, x, y_top)
    fh = (y_top - y_bot) * 0.28
    c.setFillColor(color)
    p = c.beginPath()
    p.moveTo(x, y_top); p.lineTo(x + fh*1.1, y_top - fh*0.35); p.lineTo(x, y_top - fh*0.7); p.close()
    c.drawPath(p, stroke=0, fill=1)


def _green_hole(c, cx, cy, w, green=GREEN):
    """果岭进洞场景: 绿果岭椭圆 + 黑洞 + 旗杆红旗 + 白球"""
    c.setFillColor(green)
    c.ellipse(cx - w/2, cy - w*0.30, cx + w/2, cy + w*0.30, stroke=0, fill=1)
    hx, hy = cx + w*0.14, cy + w*0.05      # 洞位置
    c.setFillColor(black)
    c.ellipse(hx - w*0.075, hy - w*0.04, hx + w*0.075, hy + w*0.04, stroke=0, fill=1)
    _flag(c, hx, hy, hy + w*0.62, RED_FLAG)
    # 白球 (洞左下)
    bx, by = cx - w*0.14, cy - w*0.06
    c.setFillColor(white); c.setStrokeColor(Color(0.65, 0.65, 0.68)); c.setLineWidth(w*0.012)
    c.circle(bx, by, w*0.07, stroke=1, fill=1)


# ======================================================================
# A 类: 个人姓名 / 花押 (Monogram)
# ======================================================================
def A1_circle_monogram(c, initials="MC", name="Michael Chen", sub="GOLF"):
    """圆形花押: 中央大首字母 + 上弧全名 + 下弧 sub + 双细圈"""
    _ball(c)
    _ring(c, R_MAX * 0.98, NAVY, 2.2)
    _ring(c, R_MAX * 0.90, NAVY, 1.0)
    # 中央大首字母
    c.setFillColor(NAVY); c.setFont('Times-Bold', R_MAX * 0.62)
    w = c.stringWidth(initials, 'Times-Bold', R_MAX * 0.62)
    c.drawString(CX - w/2, CY - R_MAX * 0.22, initials)
    # 上弧全名
    draw_arc_text(c, name, CX, CY, R_MAX * 0.78, -135, -45,
                  'ArialBold', R_MAX * 0.11, NAVY, baseline_inward=True)
    # 下弧 sub
    draw_arc_text(c, sub, CX, CY, R_MAX * 0.78, 135, 45,
                  'ArialBold', R_MAX * 0.10, NAVY, baseline_inward=False)
    _footer(c, "A1 圆形花押 · 个人姓名款")


def A2_diamond_monogram(c, initials="MC", name="Michael Chen"):
    """菱形花押: 菱形框 + 中央首字母 + 下方全名"""
    _ball(c)
    _diamond(c, CX, CY + R_MAX*0.12, R_MAX * 0.62, NAVY, 2.4)
    _diamond(c, CX, CY + R_MAX*0.12, R_MAX * 0.54, NAVY, 0.9)
    c.setFillColor(NAVY); c.setFont('Times-Bold', R_MAX * 0.46)
    w = c.stringWidth(initials, 'Times-Bold', R_MAX * 0.46)
    c.drawString(CX - w/2, CY + R_MAX*0.12 - R_MAX*0.17, initials)
    # 下方全名
    c.setFont('ArialBold', R_MAX * 0.13)
    w = c.stringWidth(name, 'ArialBold', R_MAX * 0.13)
    c.drawString(CX - w/2, CY - R_MAX * 0.78, name)
    _deco_line(c, CX, CY - R_MAX*0.60, R_MAX*0.5, NAVY)
    _footer(c, "A2 菱形花押 · 个人姓名款")


def A3_script_name(c, name="Michael Chen", year="EST. 2026"):
    """优雅花体全名: 中央花体 + 上下装饰线 + 年份"""
    _ball(c)
    _ring(c, R_MAX * 0.98, GREEN, 1.6)
    nm = name if ' ' in name else _split_camel(name)
    c.setFillColor(GREEN); c.setFont('SnellBlack', R_MAX * 0.38)
    w = c.stringWidth(nm, 'SnellBlack', R_MAX * 0.38)
    # 自动缩字号避免超圈
    fs = R_MAX * 0.38
    while w > R_MAX * 1.5 and fs > 6:
        fs *= 0.95; w = c.stringWidth(nm, 'SnellBlack', fs)
    c.setFont('SnellBlack', fs)
    c.drawString(CX - w/2, CY - fs*0.30, nm)
    _deco_line(c, CX, CY + R_MAX*0.42, R_MAX*0.62, GREEN)
    _deco_line(c, CX, CY - R_MAX*0.42, R_MAX*0.62, GREEN)
    c.setFillColor(GREEN); c.setFont('ArialBold', R_MAX*0.10)
    w = c.stringWidth(year, 'ArialBold', R_MAX*0.10)
    c.drawString(CX - w/2, CY - R_MAX*0.66, year)
    _footer(c, "A3 优雅花体 · 个人姓名款")


# ======================================================================
# B 类: 企业 / 品牌 logo
# ======================================================================
def B1_corp_badge(c, company="睿盛五金", en="RUISHENG GOLF"):
    """企业徽章: logo居中 + 上弧中文名 + 下弧英文名 + 双圈 (无HIO星星)"""
    _ball(c)
    c.setFillColor(NAVY); c.circle(CX, CY, R_MAX*0.98, stroke=0, fill=1)
    c.setFillColor(white); c.circle(CX, CY, R_MAX*0.60, stroke=0, fill=1)
    draw_logo(c, str(CLIENT_LOGO_SVG), CX, CY, R_MAX*1.14, NAVY)
    draw_arc_text(c, company, CX, CY, R_MAX*0.78, -128, -52, 'KaitiBold', R_MAX*0.13, white)
    draw_arc_text(c, en, CX, CY, R_MAX*0.80, 128, 52, 'ArialBold', R_MAX*0.085, white, baseline_inward=False)
    _footer(c, "B1 企业徽章 · 品牌logo款")


def B2_corp_minimal(c, company="睿盛五金", en="RUISHENG GOLF CLUB"):
    """企业极简: logo居中偏上 + 下方公司名横排 + 装饰线"""
    _ball(c)
    _ring(c, R_MAX*0.98, NAVY, 1.8)
    draw_logo(c, str(CLIENT_LOGO_SVG), CX, CY + R_MAX*0.22, R_MAX*0.92, NAVY)
    _deco_line(c, CX, CY - R_MAX*0.34, R_MAX*0.6, NAVY)
    c.setFillColor(NAVY); c.setFont('KaitiBold', R_MAX*0.18)
    w = c.stringWidth(company, 'KaitiBold', R_MAX*0.18)
    c.drawString(CX - w/2, CY - R_MAX*0.56, company)
    c.setFont('ArialBold', R_MAX*0.075)
    w = c.stringWidth(en, 'ArialBold', R_MAX*0.075)
    c.drawString(CX - w/2, CY - R_MAX*0.72, en)
    _footer(c, "B2 企业极简 · 品牌logo款")


def B3_corp_dual(c, company="睿盛五金", slogan="精工品质 · 致敬挥杆"):
    """企业双弧: logo居中 + 上弧公司名 + 下弧slogan"""
    _ball(c)
    _ring(c, R_MAX*0.98, GREEN, 2.2)
    _ring(c, R_MAX*0.88, GREEN, 0.9)
    draw_logo(c, str(CLIENT_LOGO_SVG), CX, CY, R_MAX*1.02, GREEN)
    draw_arc_text(c, company, CX, CY, R_MAX*0.76, -130, -50, 'KaitiBold', R_MAX*0.135, GREEN)
    draw_arc_text(c, slogan, CX, CY, R_MAX*0.78, 145, 35, 'KaitiBold', R_MAX*0.078, GREEN, baseline_inward=False)
    _footer(c, "B3 企业双弧 · 品牌logo款")


# ======================================================================
# C 类: 赛事 / 活动纪念
# ======================================================================
def C1_event_badge(c, event="祥新高尔夫邀请赛", date="2026.06.15", place="三亚红峡谷"):
    """赛事圆徽: 顶弧赛事名 + 中央奖杯 + 底弧日期地点 + 两侧星星"""
    _ball(c)
    c.setFillColor(NAVY); c.circle(CX, CY, R_MAX*0.98, stroke=0, fill=1)
    c.setFillColor(GOLD); c.circle(CX, CY, R_MAX*0.90, stroke=0, fill=1)
    c.setFillColor(NAVY); c.circle(CX, CY, R_MAX*0.84, stroke=0, fill=1)
    _trophy(c, CX, CY + R_MAX*0.06, R_MAX*0.34, GOLD)
    draw_arc_text(c, event, CX, CY, R_MAX*0.70, -138, -42, 'KaitiBold', R_MAX*0.115, white)
    draw_arc_text(c, f"{date}  {place}", CX, CY, R_MAX*0.72, 142, 38, 'ArialBold', R_MAX*0.072, GOLD, baseline_inward=False)
    for ang in [-90+52, -90-52]:
        a = math.radians(ang)
        draw_star_5(c, CX + R_MAX*0.70*math.cos(a), CY - R_MAX*0.70*math.sin(a), R_MAX*0.06, GOLD, point_angle_deg=ang)
    _footer(c, "C1 赛事圆徽 · 活动纪念款")


def C2_event_horizontal(c, event="祥新高尔夫邀请赛", year="2026", date="2026.06.15", place="三亚红峡谷"):
    """赛事横版: 上赛事名 + 中央大年份 + 旗 + 下日期地点 + 横线"""
    _ball(c)
    half = R_MAX * 0.82
    c.setFillColor(NAVY); c.setFont('KaitiBold', R_MAX*0.14)
    w = c.stringWidth(event, 'KaitiBold', R_MAX*0.14)
    c.drawString(CX - w/2, CY + R_MAX*0.42, event)
    _deco_line(c, CX, CY + R_MAX*0.30, half, NAVY)
    # 大年份
    c.setFillColor(NAVY); c.setFont('Times-Bold', R_MAX*0.52)
    w = c.stringWidth(year, 'Times-Bold', R_MAX*0.52)
    c.drawString(CX - w/2, CY - R_MAX*0.10, year)
    _flag(c, CX + w/2 + R_MAX*0.18, CY - R_MAX*0.06, CY + R_MAX*0.34, RED_FLAG)
    _deco_line(c, CX, CY - R_MAX*0.30, half, NAVY)
    c.setFillColor(NAVY); c.setFont('ArialBold', R_MAX*0.085)
    txt = f"{date}   {place}"
    w = c.stringWidth(txt, 'ArialBold', R_MAX*0.085)
    c.drawString(CX - w/2, CY - R_MAX*0.50, txt)
    _footer(c, "C2 赛事横版 · 活动纪念款")


def C3_event_ribbon(c, event="祥新高尔夫邀请赛", year="2026", place="三亚红峡谷"):
    """赛事缎带: 上年份大字 + 中央缎带放赛事名 + 下地点 + 圈"""
    _ball(c)
    _ring(c, R_MAX*0.98, GREEN, 1.8)
    c.setFillColor(GREEN); c.setFont('Times-Bold', R_MAX*0.30)
    w = c.stringWidth(year, 'Times-Bold', R_MAX*0.30)
    c.drawString(CX - w/2, CY + R_MAX*0.40, year)
    _ribbon(c, CX, CY + R_MAX*0.02, R_MAX*1.55, R_MAX*0.34, GREEN)
    c.setFillColor(white); c.setFont('KaitiBold', R_MAX*0.135)
    w = c.stringWidth(event, 'KaitiBold', R_MAX*0.135)
    c.drawString(CX - w/2, CY - R_MAX*0.045, event)
    c.setFillColor(GREEN); c.setFont('KaitiBold', R_MAX*0.10)
    w = c.stringWidth(place, 'KaitiBold', R_MAX*0.10)
    c.drawString(CX - w/2, CY - R_MAX*0.52, place)
    _footer(c, "C3 赛事缎带 · 活动纪念款")


# ======================================================================
# H 类: 一杆进洞 (HIO) 扩展款 (经典蓝徽章版/HoleInOne横版在 render_pdf.py)
# ======================================================================
def H1_trophy_celebrate(c, name_cn="黃亨利", course="費度", hole="六", date="2026.05.31"):
    """金奖杯庆典圆徽: 深蓝盘+金环 + 上弧HOLE IN ONE + 中央奖杯 + 姓名 + 下弧球场日期 + 双星"""
    _ball(c)
    c.setFillColor(NAVY); c.circle(CX, CY, R_MAX*0.98, stroke=0, fill=1)
    c.setStrokeColor(GOLD); c.setLineWidth(R_MAX*0.028); c.circle(CX, CY, R_MAX*0.86, stroke=1, fill=0)
    _trophy(c, CX, CY + R_MAX*0.30, R_MAX*0.26, GOLD)
    draw_arc_text(c, "HOLE IN ONE", CX, CY, R_MAX*0.73, -142, -38, 'ArialBold', R_MAX*0.105, GOLD)
    c.setFillColor(white); c.setFont('KaitiBold', R_MAX*0.20)
    w = c.stringWidth(name_cn, 'KaitiBold', R_MAX*0.20)
    c.drawString(CX - w/2, CY - R_MAX*0.18, name_cn)
    draw_arc_text(c, f"{course}第{hole}洞 · {date}", CX, CY, R_MAX*0.75, 148, 32,
                  'ArialBold', R_MAX*0.07, white, baseline_inward=False)
    for ang in [-90+54, -90-54]:
        a = math.radians(ang)
        draw_star_5(c, CX + R_MAX*0.73*math.cos(a), CY - R_MAX*0.73*math.sin(a), R_MAX*0.055, GOLD, point_angle_deg=ang)
    _footer(c, "HIO-新1 金奖杯庆典版")


def H2_minimal_ace(c, name_cn="黃亨利", name_en="HenryHuang", course="費度", hole="六", date="2026.05.31"):
    """极简ACE: 绿圈 + 上HOLE IN ONE + 中央ACE大字 + 下分行姓名/球场/日期"""
    _ball(c)
    _ring(c, R_MAX*0.98, GREEN, 1.8)
    c.setFillColor(GREEN); c.setFont('ArialBold', R_MAX*0.11)
    w = c.stringWidth("HOLE IN ONE", 'ArialBold', R_MAX*0.11)
    c.drawString(CX - w/2, CY + R_MAX*0.50, "HOLE IN ONE")
    _deco_line(c, CX, CY + R_MAX*0.40, R_MAX*0.55, GREEN)
    # 中央 ACE 大字
    c.setFillColor(GREEN); c.setFont('Times-Bold', R_MAX*0.66)
    w = c.stringWidth("ACE", 'Times-Bold', R_MAX*0.66)
    c.drawString(CX - w/2, CY - R_MAX*0.12, "ACE")
    _deco_line(c, CX, CY - R_MAX*0.30, R_MAX*0.55, GREEN)
    c.setFillColor(GREEN); c.setFont('KaitiBold', R_MAX*0.12)
    line = f"{name_cn} · {course}第{hole}洞 · {date}"
    w = c.stringWidth(line, 'KaitiBold', R_MAX*0.12)
    fs = R_MAX*0.12
    while w > R_MAX*1.7 and fs > 5:
        fs *= 0.95; w = c.stringWidth(line, 'KaitiBold', fs)
    c.setFont('KaitiBold', fs)
    c.drawString(CX - w/2, CY - R_MAX*0.52, line)
    _footer(c, "HIO-新2 极简 ACE 版")


def H3_green_scene(c, name_cn="黃亨利", course="費度", hole="六", date="2026.05.31"):
    """果岭旗洞场景圆徽: 上弧HOLE IN ONE + 中央果岭进洞场景 + 下弧姓名球场日期"""
    _ball(c)
    _ring(c, R_MAX*0.98, NAVY, 2.0)
    _ring(c, R_MAX*0.90, NAVY, 0.8)
    _green_hole(c, CX, CY + R_MAX*0.06, R_MAX*0.95)
    draw_arc_text(c, "HOLE IN ONE", CX, CY, R_MAX*0.76, -140, -40, 'ArialBold', R_MAX*0.10, NAVY)
    draw_arc_text(c, f"{name_cn} · {course}第{hole}洞 · {date}", CX, CY, R_MAX*0.78, 152, 28,
                  'KaitiBold', R_MAX*0.072, NAVY, baseline_inward=False)
    _footer(c, "HIO-新3 果岭旗洞场景版")


def H4_ribbon_year(c, name_cn="黃亨利", course="費度", hole="六", date="2026.05.31", year="2026"):
    """缎带年份版: 大年份 + HOLE IN ONE缎带 + 下方姓名球场日期 + 圈"""
    _ball(c)
    _ring(c, R_MAX*0.98, NAVY, 2.0)
    c.setFillColor(NAVY); c.setFont('Times-Bold', R_MAX*0.34)
    w = c.stringWidth(year, 'Times-Bold', R_MAX*0.34)
    c.drawString(CX - w/2, CY + R_MAX*0.34, year)
    _ribbon(c, CX, CY - R_MAX*0.04, R_MAX*1.62, R_MAX*0.32, NAVY)
    c.setFillColor(white); c.setFont('ArialBold', R_MAX*0.12)
    w = c.stringWidth("HOLE IN ONE", 'ArialBold', R_MAX*0.12)
    c.drawString(CX - w/2, CY - R_MAX*0.105, "HOLE IN ONE")
    c.setFillColor(NAVY); c.setFont('KaitiBold', R_MAX*0.13)
    w = c.stringWidth(name_cn, 'KaitiBold', R_MAX*0.13)
    c.drawString(CX - w/2, CY - R_MAX*0.42, name_cn)
    c.setFont('KaitiBold', R_MAX*0.092)
    line = f"{course}第{hole}洞 · {date}"
    w = c.stringWidth(line, 'KaitiBold', R_MAX*0.092)
    c.drawString(CX - w/2, CY - R_MAX*0.58, line)
    _footer(c, "HIO-新4 缎带年份版")


HIO_TEMPLATES = [H1_trophy_celebrate, H2_minimal_ace, H3_green_scene, H4_ribbon_year]

TEMPLATES = [A1_circle_monogram, A2_diamond_monogram, A3_script_name,
             B1_corp_badge, B2_corp_minimal, B3_corp_dual,
             C1_event_badge, C2_event_horizontal, C3_event_ribbon]


SETS = {"abc": TEMPLATES, "hio": HIO_TEMPLATES, "all": TEMPLATES + HIO_TEMPLATES}


def main(out_path, which="abc"):
    fns = SETS[which]
    c = canvas.Canvas(out_path, pagesize=A5)
    c.setTitle("高尔夫球印刷版式库 v1")
    for fn in fns:
        fn(c); c.showPage()
    c.save()
    print(f"OK -> {out_path}  ({len(fns)} 款, set={which})")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--set", choices=list(SETS), default="abc", help="abc=三类9款 | hio=HIO扩展4款 | all=全部")
    a = ap.parse_args()
    main(a.output, a.set)
