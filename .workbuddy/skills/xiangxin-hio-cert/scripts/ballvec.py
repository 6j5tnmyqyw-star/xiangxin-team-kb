"""矢量高尔夫球: 径向渐变球体 + 六方密堆凹点 + 左上高光 + 边缘体积暗角. 全矢量."""
import math
from reportlab.lib.colors import Color


def draw_vector_ball(c, cx, cy, R):
    """在 (cx,cy) 画半径 R 的矢量高尔夫球."""
    # ---- 1. 球体底: 径向渐变 (高光中心偏左上), clip 在球圆内 ----
    c.saveState()
    clip = c.beginPath()
    clip.circle(cx, cy, R)
    c.clipPath(clip, stroke=0, fill=0)
    hl_x = cx - R * 0.28          # 高光中心偏左上
    hl_y = cy + R * 0.30
    c.radialGradient(
        hl_x, hl_y, R * 1.65,
        [Color(1, 1, 1), Color(0.985, 0.985, 0.99),
         Color(0.93, 0.93, 0.945), Color(0.82, 0.82, 0.85)],
        positions=[0.0, 0.45, 0.8, 1.0],
    )
    c.restoreState()

    # ---- 2. 凹点 (六方密堆), 落在球内才画, 边缘按曲率压扁+缩小 ----
    rd = R * 0.056                # 凹点基准半径
    sp = rd * 2.08               # 行内间距
    row_h = sp * 0.866           # 六方行距
    n = int(R / row_h) + 2
    shadow = Color(0.86, 0.86, 0.89)   # 凹点阴影侧 (柔和淡灰环)
    hi = Color(0.965, 0.965, 0.975)    # 凹点内壁高光 (略低于纯白, 留出环)
    for ri in range(-n, n + 1):
        y = ri * row_h
        xoff = (sp / 2) if (ri % 2) else 0.0
        m = int(R / sp) + 2
        for ci in range(-m, m + 1):
            x = ci * sp + xoff
            dist = math.hypot(x, y)
            if dist > R * 0.965:
                continue
            # 球面曲率: z = sqrt(1-(d/R)^2); 边缘 z 小 -> 凹点缩小+压扁
            z = math.sqrt(max(0.0, 1 - (dist / R) ** 2))
            scale = 0.45 + 0.55 * z
            r_here = rd * scale
            if r_here < 0.4:
                continue
            px, py = cx + x, cy + y
            # 径向方向 (从球心指向凹点) -> 压扁方向
            ang = math.atan2(y, x)
            squash = 0.35 + 0.65 * z      # 沿径向压扁比例
            c.saveState()
            c.translate(px, py)
            c.rotate(math.degrees(ang))
            c.scale(squash, 1.0)          # 沿径向压扁 (x 已转到径向)
            # 凹点: 淡灰底圆(凹陷环) + 略偏左上的内壁高光圆 (光从左上来)
            c.setFillColor(shadow)
            c.circle(0, 0, r_here, stroke=0, fill=1)
            c.setFillColor(hi)
            c.circle(-r_here * 0.16, r_here * 0.16, r_here * 0.74, stroke=0, fill=1)
            c.restoreState()


if __name__ == "__main__":
    from reportlab.pdfgen import canvas
    c = canvas.Canvas("/tmp/ball_vec_test.pdf", pagesize=(420, 420))
    draw_vector_ball(c, 210, 210, 195)
    c.showPage(); c.save()
    print("OK /tmp/ball_vec_test.pdf")
