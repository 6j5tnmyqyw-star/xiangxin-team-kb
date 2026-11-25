#!/usr/bin/env python3
"""
Excel (.xlsx/.xlsm) 成品静态审计 + LibreOffice 自动重算入口。
- 零 LibreOffice 环境下也可完整检查：XML 合法性、表名超 31 字符、缓存公式错误、
  括号不配平、禁用动态数组函数、漏加 _xlfn. 前缀、跨表未加引号空格表名、合计行疑似写死数字。
- 若本机已安装 soffice（LibreOffice），默认先调用 recalc.py 重算并回填公式缓存值，再输出联合报告。

用法：
  python3 scripts/audit_xlsx.py path/to/file.xlsx
  python3 scripts/audit_xlsx.py path/to/file.xlsx --static-only
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.parsers import expat

from openpyxl import load_workbook

EXCEL_ERRORS = ("#VALUE!", "#DIV/0!", "#REF!", "#NAME?", "#NULL!", "#NUM!", "#N/A")

BANNED_DYNAMIC_FUNCS = {
    "XLOOKUP", "XMATCH", "SORT", "SORTBY", "FILTER", "UNIQUE", "SEQUENCE",
    "RANDARRAY", "LET", "LAMBDA", "VSTACK", "HSTACK", "TEXTSPLIT", "TEXTBEFORE", "TEXTAFTER",
}

NEEDS_XLFN_PREFIX = {
    "TEXTJOIN", "CONCAT", "IFS", "SWITCH", "MAXIFS", "MINIFS",
}

TOTAL_KEYWORDS = ("合计", "总计", "小计", "汇总", "total", "grand total", "subtotal")

_QUOTED_RE = re.compile(r'"[^"]*"|\'[^\']*\'')
_FUNC_RE = re.compile(r"(?<![A-Za-z0-9_.])([A-Za-z_][A-Za-z0-9_.]*)\s*\(")


def check_xml_and_zip(path: Path) -> list[str]:
    issues = []
    if not zipfile.is_zipfile(path):
        return ["文件不是合法的 .xlsx/.xlsm ZIP 包"]
    with zipfile.ZipFile(path) as zf:
        for info in zf.infolist():
            if info.filename.endswith((".xml", ".rels")) and info.file_size < 50_000_000:
                data = zf.read(info)
                if b"<!" in data[:200]:
                    continue
                try:
                    expat.ParserCreate().Parse(data, True)
                except expat.ExpatError as e:
                    issues.append(f"XML 语法损坏: {info.filename} ({e})")
    return issues


def audit_static(path: Path) -> dict:
    errors = []
    warnings = []
    formula_count = 0
    missing_cache_count = 0

    xml_issues = check_xml_and_zip(path)
    if xml_issues:
        return {"status": "errors_found", "xml_issues": xml_issues, "errors": xml_issues, "warnings": []}

    wb_f = load_workbook(path, data_only=False)
    wb_v = load_workbook(path, data_only=True)

    sheet_names = wb_f.sheetnames
    sheets_with_spaces = [s for s in sheet_names if " " in s or "-" in s]

    for sname in sheet_names:
        if len(sname) > 31:
            errors.append(f"表名超过 31 字符: {sname!r} ({len(sname)})")

        ws_f = wb_f[sname]
        ws_v = wb_v[sname]

        # 检查每个有值的单元格
        total_rows_seen = {}  # row_idx -> {"label": str, "nums": int, "formulas": int}

        for row in ws_f.iter_rows():
            row_idx = row[0].row if row else 0
            row_label = ""
            row_nums = 0
            row_formulas = 0

            for cell in row:
                val = cell.value
                cached = ws_v[cell.coordinate].value
                coord = f"{sname}!{cell.coordinate}"

                # 1. 检查缓存值里的 Excel 报错
                if isinstance(cached, str):
                    for err in EXCEL_ERRORS:
                        if err in cached:
                            errors.append(f"缓存错误 {err}: {coord}")

                if val is None:
                    continue

                if isinstance(val, str) and not val.startswith("="):
                    for err in EXCEL_ERRORS:
                        if err in val:
                            errors.append(f"单元格含错误字样 {err}: {coord}")
                    low = val.strip().lower()
                    if any(k in low for k in TOTAL_KEYWORDS) and not row_label:
                        row_label = val.strip()

                elif isinstance(val, (int, float)) and not isinstance(val, bool):
                    row_nums += 1

                elif isinstance(val, str) and val.startswith("="):
                    formula_count += 1
                    row_formulas += 1
                    if cached is None:
                        missing_cache_count += 1

                    # 去引号后做括号和函数名检查
                    stripped = _QUOTED_RE.sub("", val[1:])
                    if stripped.count("(") != stripped.count(")"):
                        errors.append(f"公式括号不配平: {coord} -> {val}")

                    for m in _FUNC_RE.finditer(stripped):
                        raw_fn = m.group(1)
                        upper_fn = raw_fn.upper()
                        bare = upper_fn.removeprefix("_XLFN.").removeprefix("_XLWS.")
                        if bare in BANNED_DYNAMIC_FUNCS:
                            errors.append(
                                f"禁用动态函数 {raw_fn}（易在旧版 Excel/WPS/LibreOffice 报错）: {coord}"
                            )
                        if upper_fn in NEEDS_XLFN_PREFIX:
                            errors.append(
                                f"函数 {raw_fn} 缺少 _xlfn. 前缀（openpyxl 裸写会报 #NAME?）: {coord}"
                            )

                    # 跨表引用含空格未加单引号检查
                    for sp_name in sheets_with_spaces:
                        if f"{sp_name}!" in val and f"'{sp_name}'!" not in val:
                            errors.append(f"跨表引用含空格/连字符未加单引号: {coord} -> {sp_name}")

            if row_label and row_nums >= 2 and row_formulas == 0:
                total_rows_seen[row_idx] = row_label

        for r_idx, lbl in total_rows_seen.items():
            warnings.append(
                f"疑似写死合计行（未用公式）: {sname} 第 {r_idx} 行「{lbl}」有多个纯数字但 0 条公式"
            )

    wb_f.close()
    wb_v.close()

    return {
        "status": "errors_found" if errors else "success",
        "file": str(path),
        "sheets": len(sheet_names),
        "total_formulas": formula_count,
        "missing_cached_values": missing_cache_count,
        "total_errors": len(errors),
        "errors": errors[:100],
        "warnings": warnings[:50],
    }


def main():
    ap = argparse.ArgumentParser(description="Audit Excel workbook formulas and structure")
    ap.add_argument("file", help="Path to .xlsx or .xlsm file")
    ap.add_argument("--static-only", action="store_true", help="Skip LibreOffice recalc even if installed")
    args = ap.parse_args()

    path = Path(args.file).expanduser().resolve()
    if not path.is_file():
        print(json.dumps({"error": f"文件不存在: {path}"}, ensure_ascii=False, indent=2))
        sys.exit(2)

    recalc_report = None
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    recalc_script = Path(__file__).resolve().parent / "recalc.py"

    if not args.static_only and soffice and recalc_script.is_file():
        proc = subprocess.run(
            [sys.executable, str(recalc_script), str(path)],
            capture_output=True, text=True, timeout=60,
        )
        try:
            recalc_report = json.loads(proc.stdout)
        except Exception:
            recalc_report = {"raw_stdout": proc.stdout[:500], "raw_stderr": proc.stderr[:500]}

    report = audit_static(path)
    report["libreoffice_available"] = bool(soffice)
    if recalc_report is not None:
        report["recalc"] = recalc_report
        if recalc_report.get("status") == "errors_found" or "error" in recalc_report:
            report["status"] = "errors_found"
    elif report["total_formulas"] > 0 and report["missing_cached_values"] > 0:
        report["note"] = (
            "本机未安装 LibreOffice，已完成全量静态公式审计；公式缓存值将在 Excel/WPS 打开时自动刷新。"
        )

    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report["status"] == "success" else 1)


if __name__ == "__main__":
    main()
