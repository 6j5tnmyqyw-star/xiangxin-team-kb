# PDF（.pdf）成品精工手册

> 提炼自 Anthropic 官方 `pdf` 技能，适配本机 `pypdf` + `fitz (PyMuPDF)` + `pdftoppm` 环境。

## 一、按任务选工具

| 任务 | 首选方案 | 说明 |
|---|---|---|
| **读文本 / 提取图片 / 渲染截图** | `fitz`（PyMuPDF，本机已装）或 `pypdf` | `fitz` 速度快、支持中文和直接转 PNG |
| **抽表格** | `pdfplumber`（若缺则按需 `pip install pdfplumber`）或 `fitz.find_tables()` | 复杂无线表格需核对列错位 |
| **合并 / 拆分 / 旋转 / 加水印 / 加密** | `pypdf`（`PdfReader` + `PdfWriter`） | 零依赖直接跑 |
| **制作精美排版 PDF**（简报/试卷/图册/SOP） | **HTML + CSS → 浏览器打印/Playwright/WeasyPrint** 优先；纯代码精细矢量图（如 HIO 球标）用 `reportlab` | HTML/CSS 控中文排版、分页、卡片远比手写坐标省心 |
| **扫描件 OCR** | `pdftoppm` 或 `fitz` 转图 → 视觉读取 / `pytesseract` | 先看清晰度，DPI 建议 ≥200 |

---

## 二、常见坑与红线

1. **ReportLab 禁用 Unicode 上下标字符**（`₀₁₂₃` / `⁰¹²³`）：内置字体缺字形会渲成实心黑方块！必须用 `<super>` / `<sub>` XML 标签（如 `H<sub>2</sub>O`），或在 Canvas 手调字号偏移。
2. **中文字体必须显式注册**：ReportLab 默认 Helvetica 不含中文会变黑块/乱码，务必绑定 macOS 系统字体（如 `PingFang` / `STHeiti` / `Songti`）或嵌入 TTF。
3. **HTML 转 PDF 防分页截断**：卡片/表格行加 `break-inside: avoid; page-break-inside: avoid;`，页眉页脚与 `@page` 边距显式设定，避免最后一行孤零零掉到下一页。
4. **填 PDF 表单先查有没有真表单域**：先用 `pypdf` 读 `reader.get_fields()`；如果为空说明是平图表单，需转图量坐标后用透明层覆盖文字再合并，**绝不瞎猜坐标**。

---

## 三、交付前必做视觉验收

```bash
# 转成每页图片，亲眼检查分页、中文乱码、截断与留白
rm -f /tmp/pdf-qa-*.png
pdftoppm -png -r 150 output.pdf /tmp/pdf-qa
ls -1 /tmp/pdf-qa-*.png
```

逐页检查：
- 标题/正文/页码是否被切边或叠字？
- 表格列有没有挤爆或文字溢出单元格？
- 中文字符和符号（¥、%、—）有没有方框乱码？
- 最后一页有没有只剩 1–2 行的「尾巴页」？有就微调行距或内容收进上一页。
