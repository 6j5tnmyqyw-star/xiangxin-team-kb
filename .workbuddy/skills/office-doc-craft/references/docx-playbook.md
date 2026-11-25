# Word（.docx）成品精工手册

> 提炼自 Anthropic 官方 `docx` 技能。

## 一、路线选择

- **新建文档**：用 `docx`（npm）或 `python-docx`；复杂商务文档/合同/报告推荐 `docx-js`。
- **编辑现有 `.docx`（保留原排版/批注/修订）**：解包 ZIP → 先跑 `scripts/merge_runs.py` 合并碎片 `<w:r>` → 原地改 `word/document.xml`（不要格式化缩进） → 重新打包 → `scripts/office/validate.py out.docx --original src.docx`。

---

## 二、`docx-js` 避坑清单

1. **纸张尺寸**：默认 A4（中文场景正好）；需要横版时仍传竖版宽高 + `orientation: PageOrientation.LANDSCAPE`。
2. **表格必须双设宽度**：既设表格 `columnWidths`，又设每个单元格 `width`，且**统一用 `WidthType.DXA`**（不用 `PERCENTAGE`，在线预览和 Google Docs/飞书易错位），列宽之和必须等于总宽。
3. **表格底纹用 `ShadingType.CLEAR`**，绝不用 `SOLID`（会渲成纯黑底！）。
4. **列表用 `numbering` 配置**，不要手打 `•` 字符。
5. **换段用多个 `Paragraph`**，不要在字符串里塞 `\n`；`PageBreak` 必须包在 `Paragraph` 里。
6. **各级标题显式设字体、段前段后距和 `keepNext: true`**（防止标题落在页尾、正文掉到下一页）。
7. **图片 `ImageRun` 必传 `type`**（`"png"` / `"jpg"`）。
8. **分割线用段落底边框**，不要拿空表格当横线。

---

## 三、交付前必做校验（防云端打不开）

```bash
# 1. 清掉 ZIP 里的目录项（飞书云盘/在线协作经常拒绝含目录项的 docx）
zip -d output.docx '*/' >/dev/null 2>&1 || true

# 2. OOXML 结构校验（加 --auto-repair 自动修常见 ID/空格属性问题）
python3 scripts/office/validate.py output.docx --auto-repair
```

如有修订留痕（Redlining）需求：
- 用 `<w:ins>` / `<w:del>` 包裹改动（删除文本标签是 `<w:delText>` 不是 `<w:t>`），跑 `validate.py out.docx --original src.docx --author "姓名"` 校验是否漏标无痕改动。
- 改旧稿前先跑 `python3 scripts/merge_runs.py unpacked/`，解决 Word 把一句话拆成七八个 `<w:r>` 导致搜不到原文的问题。
