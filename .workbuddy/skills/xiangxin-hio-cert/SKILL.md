---
name: xiangxin-hio-cert
description: 祥新公司专用·HIO(一杆进洞)纪念球印刷文件生成器。两种版式可选——Page1 蓝色徽章版(顶弧公司名+底弧英文名+左弧球场+右弧日期+4金星+中央客户logo),Page2 黑色 Hole In One 横版(左侧H/I/O艺术字+旗杆红旗+右侧4行客户信息)。输出矢量 PDF 直接给印刷厂(Illustrator 可一键转 .ai)。当祥书说『给XX做HIO纪念球/HIO球图/一杆进洞图/HIO 矢量PDF/印刷文件』时使用。
---

# xiangxin-hio-cert

给客户做 HIO 纪念高尔夫球的印刷文件。两种版式一次出 2 页 PDF,印刷厂任选。

## 两种版式

| Page | 风格 | 适合 |
|---|---|---|
| **1** | 蓝色徽章版 | 正式·客户公司 logo 突出, 4 段弧文字+4 金星对称 |
| **2** | Hole In One 横版 | 简洁·西式·适合英文为主的客户/纪念礼品 |

## 输入 → 输出 (矢量 PDF)

```bash
.venv/bin/python scripts/render_pdf.py \
  --name-en HenryHuang \
  --name-cn 黃亨利 \
  --company 睿盛五金 \
  --course 費度 \
  --hole 六 \
  --hole-num 6 \
  --date-pdf1 2026.05.31 \
  --date-pdf2 "2026年5月31日" \
  --ball vector \
  --output ./HIO_XXX.pdf
```

- `--ball vector` (默认) 全矢量 0 位图 | `--ball raster` 球面用高清照片
- 必须用 `.venv/bin/python` 跑 (见下方依赖)

参数:
- `--name-en` 英文姓名 (两页都用,如 `HenryHuang`)
- `--name-cn` 中文姓名/Henry中文 (Page2 右侧,如 `黃亨利`)
- `--company` 公司名 (Page1 顶部, 默认 `睿盛五金`)
- `--course` 球场名繁体 (默认 `費度`)
- `--hole` 洞号繁体 (Page1, 默认 `六`)
- `--hole-num` 洞号数字 (Page2, 默认 `6`)
- `--date-pdf1` YYYY.MM.DD (Page1 右弧)
- `--date-pdf2` 中式日期 (Page2)
- `--output` (必填) PDF 输出路径

## 也输出 PNG (单蓝色徽章版,跟之前 v7 兼容)

```bash
python3 scripts/render.py --name HenryHuang --date 2026.05.31 --output ./HIO_X.png
```

参见 [render.py](scripts/render.py) — 只输出 Page1 蓝色徽章版 PNG。

## 🔴 印刷范围铁律 (卡死, 勿改)

客户标注: **logo/设计绝不可超出球面中央的圆形可印范围**。
- 实测 (2026-06-02 截图量定): 红圈直径 / 球直径 = **0.48**, 红圈与球同心。
- 脚本常量 `PRINT_RANGE_RATIO = 0.48` + `DESIGN_SAFETY = 0.96` → 设计外缘卡在球径 **46%** (留 4% 安全边)。
- 蓝盘外径 = 最外元素, 由此自动卡位; logo/文字/星星按 `R_OUTER` 等比内缩, 全在圈内。
- 改板时**不要**手动放大 `R_OUTER` 突破此圈。

## 矢量度

✅ **全矢量, 0 位图** (默认 `--ball vector`): 球面(矢量凹点球) / 蓝盘 / 客户logo(potrace描摹路径) / 文字 / 4金星 / 旗杆 / 红旗 / 圆环 / 红横线
🟨 `--ball raster`: 仅球面用高清照片 (`ball_clean.png`), 其余仍全矢量 → 展示效果图更逼真
- logo 矢量源: `assets/client_logo_vector.svg` (potrace 描摹, 经 `scripts/svgpath.py` 嵌入)
- 印刷厂在 Illustrator 里 File → Open PDF → Save As .ai 一步转
- **认知**: 印到实体球上球面不印 (产品就是白球), 印刷厂只要中央设计圈 → 给印刷可出"纯设计稿"(去球面)

## 依赖 (首次)

```bash
cd <skill目录> && python3 -m venv .venv && .venv/bin/pip install reportlab
# 之后一律用 .venv/bin/python 跑 render_pdf.py (svgpath/ballvec 纯标准库, 无需额外装)
```

## Page1 布局 (蓝色徽章版)

```
       公司名         ← 顶部弧 (HeitiTC)
   ★              ★
左弧            右弧   ← 球场+洞号 / 日期(Narrow Bold)
   ★              ★
       英文名          ← 底部弧 (Arial Bold)
```

- 4 颗金星严格放在 4 段文字 gap 的正中央:
  - 顶右 gap 中心 `-39.5°`
  - 右底 gap 中心 `+37°`
  - 底左 gap 中心 `+143°`
  - 左顶 gap 中心 `-140.5°`
- 星星主尖朝外辐射 (per-star `point_angle_deg=ang_deg`)
- 文字角度严格不重叠

## Page2 布局 (Hole In One 横版)

```
                    ▽
   Hole             |    黃亨利
   In       (旗杆+红旗)  6号洞 (红)
   One              |    2026年5月31日
                    ▽    —費度一桿進洞—
```

- 左侧 H/I/O 三行衬线粗体大字(Times-Bold) + 旁边小写(`ole/n/ne`)
- 装饰: H 字带球, I 顶有小球, O 内有小球, 旗杆底有黑色 tee
- 旗杆从下到上, 顶部红色三角旗, 底部黑色三角 tee
- 右侧 4 行: 中文姓名 / 红色洞号 / 中式日期 / 红横线+球场一桿進洞+红横线

## 交付到飞书

```bash
# 1. 渲染
python3 scripts/render_pdf.py --output ./out.pdf [--其他参数]

# 2. 上传飞书云盘
lark-cli drive +upload --file ./out.pdf --name "HIO_客户名.pdf" --as user

# 3. 链接推祥书
~/.claude/skills/lark-push-xiangshu/scripts/send.py "HIO 矢量PDF: <url>"
```

## 文件结构

```
xiangxin-hio-cert/
├── SKILL.md
├── assets/
│   ├── ball_clean.png            ← 干净球底图 (无 logo)
│   ├── client_logo_transparent.png ← 客户透明 logo (倒三角)
│   ├── template.png              ← 原始 PNG 模板 (v7 用)
│   ├── example_HIO.pdf           ← 两版式样例 PDF
│   └── example_preview.png       ← 两版预览拼图
└── scripts/
    ├── render_pdf.py             ← 主脚本: 输出 2 页矢量 PDF (本文档主推)
    └── render.py                 ← 旧版: 只输出 Page1 PNG (兼容保留)
```

## 几何参数 (改板用)

如客户姓名/球场字数不匹配, 改 `render_pdf.py` 顶部常量:
- `R_OUTER = ball_w * 0.275` — logo 外径相对球面占比
- Page1 文字角度区间 (顶 `-125→-55`, 右 `-24→+24`, 底 `+130→+50`, 左 `-156→+156`)
- Page1 星星位置 (4 段 gap 正中)
- Page2 设计区 (`design_w = ball_w * 0.50, design_h = ball_w * 0.30`)

## 已知限制

- `Page2` 的 H/I/O 艺术字是用 Times-Bold + 简单 tee/球 矢量装饰拼的,跟设计师手绘的精雕 logo 比有差距; 要更精致需要 SVG 源
- 球面+客户 logo 是栅格嵌入(没有矢量源); 极限放大会糊但印刷 300 DPI 无差别
