---
name: office-doc-craft
description: "制作、修改、核查高质量 Excel (.xlsx/.csv)、PDF (.pdf)、PPT (.pptx) 与 Word (.docx) 成品的精工技能。吸收自 Anthropic 官方 skills 最佳实践：强制动态公式与零报错自检、防排版溢出与 AI 廉价模板味、渲染转图肉眼验收。只要用户要生成、编辑、修复、美化或检查电子表格、PDF 报告/表单、演示文稿或 Word 文档（包括对账表、分析报表、给客户/团队的方案文档、讲义、汇报 PPT），就必须使用本技能。纯飞书在线文档或纯网页看板不触发。"
version: 1.0.0
---

# Office 与 PDF 成品精工技能（office-doc-craft）

> 核心目标：**交付的每一个表格、PDF、PPT、Word 都能直接打开、零报错、不串行、不乱码、像专业人士手做的。**
> 先按文件类型读对应的 `references/<type>-playbook.md`，再动手写脚本，最后必走本技能的校验闭环。

## 一、快速路由（按产出类型先读手册）

| 文件类型 | 必读手册 | 推荐工具 | 必跑验收 |
|---|---|---|---|
| **Excel** (`.xlsx` / `.xlsm`) | `references/xlsx-playbook.md` | `openpyxl`（带公式/排版） / `pandas`（大批量清洗） | `python3 scripts/audit_xlsx.py <file>`（有 LibreOffice 时自动调 `recalc.py` 重算） |
| **PDF** (`.pdf`) | `references/pdf-playbook.md` | `pypdf` / `fitz(PyMuPDF)` / `pdfplumber` / `reportlab` / HTML→PDF | `pdftoppm -png -r 150` 转图并逐页视觉检查 |
| **PPT** (`.pptx`) | `references/pptx-playbook.md` | `pptxgenjs`(新建) / XML 解包精修(改模板) / `python-pptx` | `scripts/slide_text.py` + `scripts/office/validate.py` + 转图视觉检查 |
| **Word** (`.docx`) | `references/docx-playbook.md` | `docx`(npm 新建) / XML 解包+`merge_runs.py`(改原稿) | `zip -d out.docx '*/'` + `scripts/office/validate.py` + 转图视觉检查 |

---

## 二、全品类通用的 6 条铁律

1. **宁用真公式，绝不写死算好的数（Excel）**：合计、占比、毛利率一律写 Excel 公式（`=SUM(...)`、`=IFERROR(...)`），让接收者改一个数全表联动；绝不把 Python 算完的死数字直接填进合计行。
2. **禁止「跑完脚本就算交差」**：AI 写代码生成的文档第一次渲染几乎必然有小瑕疵（文字截断、公式 `#NAME?`、表格溢出、合并单元格错位）。**必须跑结构/公式校验，有视觉排版的必须转图亲眼看一遍再交付。**
3. **修改别人发来的原文件，原规矩大于本手册**：先读原表的配色、列宽、公式位置和输入区约定，只动该动的区域，不擅自推倒重排或往编辑稿里乱插「示例行」。
4. **避开高危兼容坑**：
   - Excel 禁用 `XLOOKUP`/`XMATCH`/`FILTER`/`SORT`/`UNIQUE`/`SEQUENCE`（低版本 Excel / WPS / LibreOffice 易炸 `#NAME?` 或不溢出），改用 `INDEX`/`MATCH` 和 `SUMIFS`；
   - Word/PPT 改完后清掉 ZIP 里的空目录项，否则飞书/在线协作预览可能拒开。
5. **去 AI 廉价模板味（PPT / 报告）**：禁止在标题下方画装饰横线、禁止给卡片边缘贴竖条色块、禁止整套全默认浅米色背景、禁止满屏纯文字无视觉锚点。
6. **严守隐私与数据口径**：不往给团队/客户的文件里带入脱敏前客户手机号、内部底价或未核实的脏数据；缺数标「缺失/待核」，绝不填成 `0`。

---

## 三、本机环境兼容说明（Mac / Windows WorkBuddy 通用）

- **已就绪免重装**：`python3`（`openpyxl` / `pandas` / `pypdf` / `PIL` / `fitz` / `defusedxml` / `lxml`）、`pdftoppm`、`node`。
- **若本机无 LibreOffice（`soffice`）**：
  - Excel 跑 `python3 scripts/audit_xlsx.py out.xlsx`：自动执行全量静态审计（XML 结构、表名长度、公式括号配平、禁用函数、`_xlfn.` 前缀漏写、缓存报错、`合计`行是否漏写公式）；同时如实告知用户「本机未装 LibreOffice，公式缓存值将在 Excel/WPS 打开时自动刷新」。
  - 若本机已装 LibreOffice：`audit_xlsx.py` 自动联动 `scripts/recalc.py` 完成重算并回填缓存值。
- **缺包处理**：先直接运行，只有报 `ModuleNotFoundError` 时再按需安装单个缺包，别上来就跑一堆 `pip install`。

---

## 四、配套文件索引

- `references/xlsx-playbook.md` — Excel 公式白名单、`_xlfn.` 6 函数坑、`openpyxl` 12 条避坑、财务表配色与数字格式
- `references/pdf-playbook.md` — PDF 读写/拆合/抽表/OCR/生成与 Unicode 上下标黑块避坑
- `references/pptx-playbook.md` — PPT 结构化母版、10 套配色、安全字体、去 AI 味禁忌与 14 项视觉 QA 清单
- `references/docx-playbook.md` — Word 表格双宽度、底纹 `CLEAR`、修订留痕（redlining）与批注脚本用法
- `scripts/audit_xlsx.py` — Excel 零依赖静态公式审计 + LibreOffice 自动重算入口
- `scripts/recalc.py` — Excel LibreOffice 公式重算与错误扫描器
- `scripts/slide_text.py` — PPT 全文/表格/图表/备注 Markdown 提取器
- `scripts/merge_runs.py` — Word XML 碎片 `<w:r>` 合并器（改稿前必跑）
- `scripts/office/validate.py` — Word / PPT OOXML XSD 结构校验与 `--auto-repair` 修复器
