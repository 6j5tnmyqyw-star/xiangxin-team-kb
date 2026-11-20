"""把 potrace 生成的 SVG path 直接画进 reportlab canvas (纯标准库, 全矢量, 0 位图).

potrace 输出形如:
  <svg viewBox="0 0 408 398">
    <g transform="translate(0,398) scale(0.1,-0.1)" fill="#000000">
      <path d="M1760 3815 c-244 -34 ... z M... z"/>
      ...
"""
import re
import xml.etree.ElementTree as ET


def _tokenize(d):
    """把 path d 字符串拆成 [命令字母 | 数字] 流"""
    # 数字: 可带正负号、小数、科学计数; 命令: 单个字母
    return re.findall(r'[A-Za-z]|-?\d*\.?\d+(?:[eE][-+]?\d+)?', d)


def parse_path_to_ops(d):
    """解析一个 path 的 d, 返回 reportlab 操作列表 (全绝对 raw 坐标).
    支持 potrace 用到的: M/m L/l H/h V/v C/c S/s Z/z (够 potrace).
    返回 [('m',x,y), ('l',x,y), ('c',x1,y1,x2,y2,x3,y3), ('z',)] 序列.
    """
    toks = _tokenize(d)
    i = 0
    ops = []
    cx = cy = 0.0          # current point
    sx = sy = 0.0          # subpath start
    prev_c2 = None         # 上一条曲线的第二控制点 (给 S/s 用)
    cmd = None

    def num():
        nonlocal i
        v = float(toks[i]); i += 1
        return v

    while i < len(toks):
        t = toks[i]
        if re.match(r'[A-Za-z]', t):
            cmd = t; i += 1
        # else: 隐式重复上一个命令

        if cmd in ('M', 'm'):
            x = num(); y = num()
            if cmd == 'm':
                x += cx; y += cy
            cx, cy = x, y; sx, sy = x, y
            ops.append(('m', cx, cy))
            cmd = 'l' if cmd == 'M' else 'l'  # 后续隐式点当 lineto
            prev_c2 = None
        elif cmd in ('L', 'l'):
            x = num(); y = num()
            if cmd == 'l':
                x += cx; y += cy
            cx, cy = x, y
            ops.append(('l', cx, cy))
            prev_c2 = None
        elif cmd in ('H', 'h'):
            x = num()
            if cmd == 'h':
                x += cx
            cx = x
            ops.append(('l', cx, cy))
            prev_c2 = None
        elif cmd in ('V', 'v'):
            y = num()
            if cmd == 'v':
                y += cy
            cy = y
            ops.append(('l', cx, cy))
            prev_c2 = None
        elif cmd in ('C', 'c'):
            x1 = num(); y1 = num(); x2 = num(); y2 = num(); x = num(); y = num()
            if cmd == 'c':
                x1 += cx; y1 += cy; x2 += cx; y2 += cy; x += cx; y += cy
            ops.append(('c', x1, y1, x2, y2, x, y))
            prev_c2 = (x2, y2); cx, cy = x, y
        elif cmd in ('S', 's'):
            x2 = num(); y2 = num(); x = num(); y = num()
            if cmd == 's':
                x2 += cx; y2 += cy; x += cx; y += cy
            # 第一控制点 = 当前点关于上一第二控制点的反射
            if prev_c2 is not None:
                x1 = 2 * cx - prev_c2[0]; y1 = 2 * cy - prev_c2[1]
            else:
                x1, y1 = cx, cy
            ops.append(('c', x1, y1, x2, y2, x, y))
            prev_c2 = (x2, y2); cx, cy = x, y
        elif cmd in ('Z', 'z'):
            ops.append(('z',))
            cx, cy = sx, sy
            prev_c2 = None
        else:
            i += 1  # 跳过未知
    return ops


def load_svg(svg_path):
    """读 potrace SVG, 返回 (viewbox_w, viewbox_h, g_transform_str, [path_d,...])."""
    tree = ET.parse(svg_path)
    root = tree.getroot()
    ns = {'svg': 'http://www.w3.org/2000/svg'}
    vb = root.get('viewBox')
    if vb:
        _, _, vw, vh = [float(x) for x in vb.split()]
    else:
        vw = float(re.sub(r'[^\d.]', '', root.get('width', '408')))
        vh = float(re.sub(r'[^\d.]', '', root.get('height', '398')))
    g = root.find('svg:g', ns)
    g_tf = g.get('transform', '') if g is not None else ''
    paths = [p.get('d') for p in root.iter('{http://www.w3.org/2000/svg}path')]
    return vw, vh, g_tf, paths


def _parse_transform(tf):
    """解析 'translate(a,b) scale(c,d)' -> (tx,ty,sx,sy). 够 potrace 用."""
    tx = ty = 0.0; sx = sy = 1.0
    m = re.search(r'translate\(\s*([-\d.]+)[ ,]+([-\d.]+)\s*\)', tf)
    if m:
        tx, ty = float(m.group(1)), float(m.group(2))
    m = re.search(r'scale\(\s*([-\d.]+)(?:[ ,]+([-\d.]+))?\s*\)', tf)
    if m:
        sx = float(m.group(1))
        sy = float(m.group(2)) if m.group(2) else sx
    return tx, ty, sx, sy


def draw_logo(c, svg_path, dest_cx, dest_cy, dest_size, color):
    """把 potrace SVG logo 画进 reportlab canvas, 居中于 (dest_cx, dest_cy),
    最长边缩放到 dest_size, 填充 color. 全矢量."""
    vw, vh, g_tf, paths = load_svg(svg_path)
    tx, ty, gsx, gsy = _parse_transform(g_tf)
    scale = dest_size / max(vw, vh)
    draw_w, draw_h = vw * scale, vh * scale

    c.saveState()
    c.setFillColor(color)
    # 1. 移到目标框左下角并居中
    c.translate(dest_cx - draw_w / 2, dest_cy - draw_h / 2)
    # 2. viewBox -> 目标尺寸 (SVG y 向下, reportlab y 向上 -> 翻转)
    c.scale(scale, scale)
    c.translate(0, vh)
    c.scale(1, -1)
    # 3. 应用 potrace 的 g transform (translate + scale)
    c.translate(tx, ty)
    c.scale(gsx, gsy)
    # 4. 画所有 path (奇偶填充处理 logo 镂空)
    p = c.beginPath()
    for d in paths:
        for op in parse_path_to_ops(d):
            if op[0] == 'm':
                p.moveTo(op[1], op[2])
            elif op[0] == 'l':
                p.lineTo(op[1], op[2])
            elif op[0] == 'c':
                p.curveTo(op[1], op[2], op[3], op[4], op[5], op[6])
            elif op[0] == 'z':
                p.close()
    from reportlab.pdfgen.canvas import FILL_EVEN_ODD
    c.drawPath(p, stroke=0, fill=1, fillMode=FILL_EVEN_ODD)
    c.restoreState()
