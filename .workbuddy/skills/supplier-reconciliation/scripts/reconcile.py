#!/usr/bin/env python3
"""
供应商挂账对账脚本

用法见 SKILL.md。核心逻辑：
1. 从订单编号正则提日期
2. 同日订单按"货品名称相似度 + 金额接近度"打分一对一匹配
3. 销售方"售价"或"成本价"任一对得上挂账金额即算对上
4. 差额 0 = 绿、≤阈值 = 黄、其余 = 红
5. 每条数据行后面插入一行说明，写明对账原因和问题点
"""
import argparse
import os
import re
from collections import Counter
from copy import copy
from datetime import datetime

import pandas as pd
from openpyxl import load_workbook
from openpyxl.cell import MergedCell
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill

GREEN  = PatternFill('solid', start_color='C6EFCE')
YELLOW = PatternFill('solid', start_color='FFEB9C')
RED    = PatternFill('solid', start_color='FFC7CE')
# 说明行用更浅的色
GREEN_LIGHT  = PatternFill('solid', start_color='EBF5EB')
YELLOW_LIGHT = PatternFill('solid', start_color='FFFDE7')
RED_LIGHT    = PatternFill('solid', start_color='FFEBEE')
COLOR       = {'green': GREEN,       'yellow': YELLOW,       'red': RED}
COLOR_LIGHT = {'green': GREEN_LIGHT, 'yellow': YELLOW_LIGHT, 'red': RED_LIGHT}
EXPLAIN_FONT = Font(italic=True, color='555555', size=9)
EXPLAIN_ALIGN = Alignment(wrap_text=True, vertical='center', horizontal='left')


def extract_keywords(s):
    if pd.isna(s):
        return set()
    s = str(s).lower()
    en = set(re.findall(r'[a-z]{3,}', s))
    zh = set(re.findall(r'[一-龥]{2,}', s))
    return en | zh


def parse_date(oid, regex):
    if pd.isna(oid):
        return None
    m = re.match(regex, str(oid))
    if not m:
        return None
    try:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
    except (ValueError, IndexError):
        return None


def jaccard(a, b):
    if not a or not b:
        return 0
    return len(a & b) / max(len(a), len(b))


def amount_score(supplier_amt, sales_recv, sales_cost, threshold):
    if supplier_amt is None:
        return 0, None, None
    candidates = []
    if sales_recv is not None:
        candidates.append(('应收', abs(supplier_amt - sales_recv)))
    if sales_cost is not None and sales_cost != 0:
        candidates.append(('成本', abs(supplier_amt - sales_cost)))
    if not candidates:
        return 0, None, None
    label, min_diff = min(candidates, key=lambda x: x[1])
    if min_diff < 0.01:
        return 1.0, label, min_diff
    elif min_diff <= threshold:
        return 0.9, label, min_diff
    else:
        ref = max(abs(supplier_amt), 1)
        return max(0, 1 - min_diff / ref), label, min_diff


def to_float(v):
    if pd.isna(v):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


# ── 说明行文字生成 ──────────────────────────────────────────

def _build_explanation(rec, other_idx, status, info, other_records, other_label, threshold):
    """根据对账结果生成人类可读的说明行文字"""
    other_oid = '—'
    if other_idx is not None:
        other = other_records[other_idx]
        other_oid = other.get('oid') or other.get('date_str', '?')

    if status == 'green':
        return (f"✓ 对账通过｜对应{other_label} [{other_oid}]，"
                f"金额完全吻合（{info}）")

    elif status == 'yellow':
        # 解析差额数字
        m = re.search(r'差(\d+[\.\d]*)', info)
        diff_str = f"¥{m.group(1)}" if m else ''
        label_str = '成本' if '成本' in info else '售价'
        return (f"⚠ 基本对上｜对应{other_label} [{other_oid}]，{label_str}差额 {diff_str}，"
                f"未超运费阈值 ¥{threshold}，视为运费差异——建议与供应商确认运费金额")

    else:  # red
        if other_idx is not None:
            reason = _red_detail(rec, other_records[other_idx], info)
            return (f"✗ 对账异常｜最近似记录：{other_label} [{other_oid}]，{info}。{reason}")
        else:
            reason = _no_match_detail(rec, info)
            return f"✗ 无对应记录｜{reason}"


def _red_detail(rec, other, info):
    """红色已匹配但差额大时的具体原因提示"""
    cost = rec.get('cost')
    recv = rec.get('recv')
    amt  = rec.get('amt')

    hints = []
    if cost == 0 or cost is None:
        hints.append("吉客云成本列为 0，无法按成本比对，仅按售价匹配")
    goods = str(rec.get('goods', ''))
    if '人名' in goods or '刺绣' in goods:
        hints.append("刺绣/人名费用通常附在主单上，建议与主单合并核对")
    if amt is not None and abs(amt) < 150:
        hints.append("金额较小，可能为运费或杂费单独挂账")
    cust = str(rec.get('customer', ''))
    if '退回' in cust or '退货' in cust:
        hints.append("供应商标注已退回，确认退货是否已在吉客云做退货单")
    if not hints:
        hints.append("建议人工核查，可能为售后改价、部分退款或录入差异")
    return "；".join(hints)


def _no_match_detail(rec, info):
    """红色无匹配时的具体原因提示"""
    goods = str(rec.get('goods', ''))
    amt   = rec.get('amt')
    cust  = str(rec.get('customer', ''))

    if '人名' in goods or '刺绣' in goods:
        return "刺绣/人名费用，通常需与同日主单合并核算，不单独在吉客云录入"
    if amt is not None and abs(amt) < 150:
        return "金额极小（可能为退货运费或杂费），确认是否需单独录入吉客云"
    if '退回' in cust:
        return "供应商标注已退回，核查吉客云是否有对应退货记录"
    if '无效行' in info:
        return "行内无有效订单数据（可能为合计行或空行），忽略即可"
    # 区分两侧
    if 'oid' in rec:  # 吉客云侧
        return "此订单在供应商挂账中找不到——确认是否为自营库存出货，或催供应商补挂账"
    else:             # 供应商侧
        return "此货品在吉客云无对应销售记录——核查是否漏录，或已通过其他渠道销售"


# ── 写入带说明行的 Excel ────────────────────────────────────

def _copy_cell(src_cell, dst_cell, fill_override=None):
    """把源单元格的值和样式（除填充色）复制到目标单元格"""
    if isinstance(src_cell, MergedCell):
        return
    dst_cell.value = src_cell.value
    if src_cell.has_style:
        dst_cell.font      = copy(src_cell.font)
        dst_cell.border    = copy(src_cell.border)
        dst_cell.alignment = copy(src_cell.alignment)
        dst_cell.number_format = src_cell.number_format
    dst_cell.fill = fill_override if fill_override is not None else copy(src_cell.fill)


def _write_colors_with_explanations(
        in_path, sheet_name, out_path,
        records, match, other_records,
        oid_col_name, other_label, threshold,
        header_rows=1, footer_src_rows=None):
    """
    重建输出文件：复制原文件结构，在每条数据行后插入一行说明。

    footer_src_rows: 原文件中需要追加到最后的行号列表（如合计行）
    """
    wb_src = load_workbook(in_path, data_only=True)
    ws_src = wb_src[sheet_name]
    max_col = ws_src.max_column

    from openpyxl import Workbook
    wb_out = Workbook()
    ws_out = wb_out.active
    ws_out.title = sheet_name

    # 复制列宽
    for key, dim in ws_src.column_dimensions.items():
        ws_out.column_dimensions[key].width = dim.width

    # 找订单编号列（用于写批注）
    oid_col_idx = 1
    for i, c in enumerate(ws_src[header_rows], start=1):
        if c.value == oid_col_name:
            oid_col_idx = i
            break

    out_row = 1

    # 1. 复制头部行（公司抬头、空行、列标题等）
    for src_row in range(1, header_rows + 1):
        for cell in ws_src[src_row]:
            _copy_cell(cell, ws_out.cell(row=out_row, column=cell.column if not isinstance(cell, MergedCell) else 1))
        ws_out.row_dimensions[out_row].height = ws_src.row_dimensions[src_row].height
        out_row += 1

    # 2. 数据行 + 说明行
    for rec in records:
        other_idx, status, info = match[rec['idx']]
        data_fill = COLOR[status]
        expl_fill = COLOR_LIGHT[status]

        # 数据行（着色）
        for cell in ws_src[rec['excel_row']]:
            dst = ws_out.cell(row=out_row, column=cell.column if not isinstance(cell, MergedCell) else 1)
            _copy_cell(cell, dst, fill_override=data_fill)
        ws_out.row_dimensions[out_row].height = ws_src.row_dimensions[rec['excel_row']].height or 15

        # 批注写在订单编号列
        note_cell = ws_out.cell(row=out_row, column=oid_col_idx)
        if other_idx is not None:
            other_oid = other_records[other_idx].get('oid') or other_records[other_idx].get('date_str', '?')
            note_cell.comment = Comment(f"对应{other_label}[{other_oid}]: {info}", "对账")
        else:
            note_cell.comment = Comment(f"对账: {info}", "对账")
        out_row += 1

        # 说明行
        explanation = _build_explanation(rec, other_idx, status, info, other_records, other_label, threshold)
        for col in range(1, max_col + 1):
            ws_out.cell(row=out_row, column=col).fill = expl_fill
        exp_cell = ws_out.cell(row=out_row, column=1)
        exp_cell.value = explanation
        exp_cell.font  = EXPLAIN_FONT
        exp_cell.alignment = EXPLAIN_ALIGN
        if max_col > 1:
            ws_out.merge_cells(start_row=out_row, start_column=1,
                               end_row=out_row, end_column=max_col)
        ws_out.row_dimensions[out_row].height = 22
        out_row += 1

    # 3. 尾部行（合计等）
    if footer_src_rows:
        for src_row in footer_src_rows:
            for cell in ws_src[src_row]:
                _copy_cell(cell, ws_out.cell(row=out_row, column=cell.column if not isinstance(cell, MergedCell) else 1))
            out_row += 1

    wb_out.save(out_path)


# ── 主流程 ──────────────────────────────────────────────────

def reconcile(args):
    df_s = pd.read_excel(args.sales, sheet_name=args.sales_sheet, header=0)
    df_g = pd.read_excel(args.supplier, sheet_name=args.supplier_sheet, header=0)

    sales_records = []
    for idx, r in df_s.iterrows():
        sales_records.append({
            'idx': idx, 'excel_row': idx + 2,
            'date': parse_date(r[args.sales_oid], args.date_regex),
            'goods': r[args.sales_goods],
            'kw': extract_keywords(r[args.sales_goods]),
            'recv': to_float(r[args.sales_recv]),
            'cost': to_float(r[args.sales_cost]) if args.sales_cost else None,
            'oid': r[args.sales_oid],
        })

    supplier_records = []
    for idx, r in df_g.iterrows():
        supplier_records.append({
            'idx': idx, 'excel_row': idx + 2,
            'oid': r[args.supplier_oid],
            'date': parse_date(r[args.supplier_oid], args.date_regex),
            'goods': r[args.supplier_goods],
            'kw': extract_keywords(r[args.supplier_goods]),
            'amt': to_float(r[args.supplier_amt]),
        })

    pairs = []
    for g in supplier_records:
        if g['date'] is None or g['amt'] is None:
            continue
        for s in sales_records:
            if s['date'] != g['date']:
                continue
            ks = jaccard(g['kw'], s['kw'])
            as_, label, diff = amount_score(g['amt'], s['recv'], s['cost'], args.threshold)
            if as_ == 0 and ks < 0.1:
                continue
            score = ks * 0.4 + as_ * 0.6
            pairs.append((score, g['idx'], s['idx'], label, diff, ks))

    pairs.sort(key=lambda x: -x[0])

    sup_match = {}
    s_used = set()
    g_used = set()
    for score, gi, si, label, diff, ks in pairs:
        if gi in g_used or si in s_used or diff is None:
            continue
        if diff < 0.01:
            status, info = 'green', f'对上({label})'
        elif diff <= args.threshold:
            status, info = 'yellow', f'差{diff:.2f}({label})可能运费'
        else:
            if ks < 0.2:
                continue
            status, info = 'red', f'差{diff:.2f}({label})'
        sup_match[gi] = (si, status, info)
        g_used.add(gi)
        s_used.add(si)

    for g in supplier_records:
        if g['idx'] not in sup_match:
            if g['date'] is None or g['amt'] is None:
                sup_match[g['idx']] = (None, 'red', '无效行')
            else:
                sup_match[g['idx']] = (None, 'red', '销售明细中无匹配')

    sales_match = {}
    for gi, (si, status, info) in sup_match.items():
        if si is not None:
            sales_match[si] = (gi, status, info)
    for s in sales_records:
        if s['idx'] not in sales_match:
            sales_match[s['idx']] = (None, 'red', '挂账中无匹配')

    os.makedirs(args.output_dir, exist_ok=True)
    sales_out    = os.path.join(args.output_dir, _stem(args.sales)    + '_对账.xlsx')
    supplier_out = os.path.join(args.output_dir, _stem(args.supplier) + '_对账.xlsx')

    _write_colors_with_explanations(
        args.sales, args.sales_sheet, sales_out,
        sales_records, sales_match, supplier_records,
        args.sales_oid, '挂账', args.threshold,
        header_rows=1)

    _write_colors_with_explanations(
        args.supplier, args.supplier_sheet, supplier_out,
        supplier_records, sup_match, sales_records,
        args.supplier_oid, '销售明细', args.threshold,
        header_rows=1)

    sup_cnt   = Counter(v[1] for v in sup_match.values())
    sales_cnt = Counter(v[1] for v in sales_match.values())

    print(f"\n挂账文件 ({args.supplier}): "
          f"绿{sup_cnt.get('green', 0)} 黄{sup_cnt.get('yellow', 0)} 红{sup_cnt.get('red', 0)} "
          f"(共{sum(sup_cnt.values())}条)")
    print(f"销售明细 ({args.sales}): "
          f"绿{sales_cnt.get('green', 0)} 黄{sales_cnt.get('yellow', 0)} 红{sales_cnt.get('red', 0)} "
          f"(共{sum(sales_cnt.values())}条)")

    print("\n=== 红色订单明细 ===")
    print("\n[挂账中差额超阈值或无匹配的]")
    for g in supplier_records:
        si, st, info = sup_match[g['idx']]
        if st == 'red':
            sales_oid = sales_records[si]['oid'] if si is not None else '-'
            print(f"  [{g['oid']}] {g['amt']} -> {sales_oid} | {info}")
    print("\n[销售明细中无对应挂账的]")
    for s in sales_records:
        gi, st, info = sales_match[s['idx']]
        if st == 'red' and gi is None:
            print(f"  [{s['oid']}] 售价{s['recv']} 成本{s['cost']} | {info}")

    print(f"\n输出文件:\n  {sales_out}\n  {supplier_out}")


def _stem(path):
    return os.path.splitext(os.path.basename(path))[0]


def main():
    p = argparse.ArgumentParser(description='供应商挂账对账')
    p.add_argument('--sales',          required=True)
    p.add_argument('--sales-sheet',    default=0)
    p.add_argument('--sales-oid',      required=True)
    p.add_argument('--sales-recv',     required=True)
    p.add_argument('--sales-cost',     default=None)
    p.add_argument('--sales-goods',    required=True)
    p.add_argument('--supplier',       required=True)
    p.add_argument('--supplier-sheet', default=0)
    p.add_argument('--supplier-oid',   required=True)
    p.add_argument('--supplier-amt',   required=True)
    p.add_argument('--supplier-goods', required=True)
    p.add_argument('--threshold',      type=float, default=60)
    p.add_argument('--date-regex',     default=r'JY(\d{4})(\d{2})(\d{2})')
    p.add_argument('--output-dir',     default='/mnt/user-data/outputs')
    args = p.parse_args()
    reconcile(args)


if __name__ == '__main__':
    main()
