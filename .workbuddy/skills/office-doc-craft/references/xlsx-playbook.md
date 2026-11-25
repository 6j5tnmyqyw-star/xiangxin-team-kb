# Excel（.xlsx）成品精工手册

> 提炼自 Anthropic 官方 `xlsx` 技能，适配祥新电商/财务对账与经营报表场景。

## 一、交付前硬标准

1. **全表用公式，不用死数字**：合计、均价、毛利率、占比全写公式（如 `=SUM(B2:B9)`、`=IFERROR(C2/B2,0)`），保证对方改数自动联动。
2. **零公式报错**：交付前必须运行 `python3 scripts/audit_xlsx.py output.xlsx`，绝不允许残留 `#REF!`、`#DIV/0!`、`#VALUE!`、`#NAME?`、`#N/A`、`#NUM!`、括号不配平或表名超 31 字符。
3. **给别人填的表加「填表说明 + 1 行示例」**：新建供销售/运营/财务回填的表，放一行简短图例说明哪几列需要填，并给 1 行真实格式示例。**如果是改别人现有表，绝不擅自插示例行。**
4. **改旧表先看原规矩**：先识别原表哪些列是人工输入（底色/字体颜色不同）、哪些列是公式，只写输入区，不动原有公式和表头命名。
5. **所有假设与口径写明来源**：表尾或批注标明数据来源、截止日期和计算口径（如「吉客云销售明细，截至 2026-11-23，已剔除取消单」）。

---

## 二、公式兼容白名单（防 WPS / 旧 Excel / LibreOffice 炸 `#NAME?`）

| 类别 | 写法 | 说明 |
|---|---|---|
| **优先用（零兼容风险）** | `SUM`、`SUMIFS`、`COUNTIFS`、`AVERAGEIFS`、`INDEX`+`MATCH`、`IF`、`IFERROR`、`ROUND`、`SUMPRODUCT`、`VLOOKUP` | 2007 时代起全平台原生支持，无需前缀 |
| **必须加 `_xlfn.` 前缀的 6 个函数** | `_xlfn.TEXTJOIN`、`_xlfn.CONCAT`、`_xlfn.IFS`、`_xlfn.SWITCH`、`_xlfn.MAXIFS`、`_xlfn.MINIFS` | `openpyxl` 原样写进 XML，裸写会报 `#NAME?`（Excel 打开会自动隐藏前缀） |
| **禁用函数** | `XLOOKUP`、`XMATCH`、`SORT`、`FILTER`、`UNIQUE`、`SEQUENCE`、`LET`、`LAMBDA` | 低版本 Excel/LibreOffice 不支持，且 `openpyxl` 无动态数组 spill 元数据，易只填左上角或报错；查表用 `INDEX/MATCH`，排序/筛选/去重在 Python 里做完再写入 |

---

## 三、`openpyxl` 12 条高频暗坑

1. **读公式和读计算值必须 load 两次**：`load_workbook(fp, data_only=True)` 只拿到缓存值（公式全丢）；默认 `data_only=False` 只拿到公式字符串（无计算值）。
2. **`data_only=True` 打开的表绝不能 `.save()`**：一保存，全表公式永久变死数字！
3. **`openpyxl` 新写的公式没有缓存值**：没经过 LibreOffice 重算或 Excel/WPS 打开保存前，用 `pandas` 或 `data_only=True` 读回来都是 `None`。
4. **合并单元格只写左上角锚点**：合并区域内其他格子是只读 `MergedCell`，写入会报错。
5. **`.xlsm` 带宏表必须 `keep_vba=True`**：否则宏全丢。
6. **跨表引用含空格或特殊字符的表名必须加单引号**：`='销售明细 11月'!$B$5`，不加引号报 `#VALUE!`。
7. **带文本框/形状/切片器的表慎用 `openpyxl` 重存**：会丢掉 `xl/drawings/` 里的形状和 `xl/slicers/` 切片器，修改前先检查 ZIP 包里有没有。
8. **数字格式别漏写，每个新公式单元格都要显式设 `number_format`**：不设的话日期变 `45337`，30% 显示成 `0.3`。
9. **百分比存小数**：存 `0.15` + 格式 `0.0%` 显示 `15.0%`；存 `15` 会显示 `1500.0%`。
10. **年份用文本**：`"2026"`，别存数字避免格式化成 `2,026`。
11. **分母可能为 0 一律套 `IFERROR(..., 0)` 或 `IF(B2=0, "-", C2/B2)`**：防 `#DIV/0!`。
12. **图表防乱盖**：新建图表必设 `chart.roundedCorners = False`，图例和标题设 `.overlay = False`，非饼图设 `chart.x_axis.delete = False` / `chart.y_axis.delete = False`；用 `DateAxis` 时设 `chart.y_axis.crossAx = 500`。

---

## 四、财务与经营表配色/格式规范（无指定模板时默认用）

- **文字颜色语义**：蓝字（`0000FF`）= 手动输入/参数假设 · 黑字 = 本表公式 · 绿字（`008000`）= 跨 Sheet 引用 · 浅黄底（`FFF2CC`）= 需同事回填的列/关键假设。
- **数字格式**：金额 `¥#,##0` 或 `#,##0.00`（列头写清单位如「万元/元」）；零值可用 `#,##0;(#,##0);"-"` 显 `-`；百分比 `0.0%`。
- **基础可读性**：冻结首行（`ws.freeze_panes = "A2"`）、开启筛选、按内容自动估算列宽（中文按 2 字符宽算并留余量，防 `###` 截断）、开启表头换行。

---

## 五、校验命令

```bash
# 静态公式/错误/规范审计（无 LibreOffice 也可跑；有 LibreOffice 自动触发 recalc.py 重算）
python3 scripts/audit_xlsx.py output.xlsx

# 强制只跑静态审计（跳过 LibreOffice）
python3 scripts/audit_xlsx.py output.xlsx --static-only
```
