#!/usr/bin/env python3
"""祥新·售后率对比 —— 同期「卖了多少 vs 退了几单」，算售后率，看哪些商品/品牌售后偏高。
销量来自吉客云销售明细 csv，售后来自网店售后单 xlsx，按订单去重、同口径(货品名含关键词)。

用法:
  python3 compare_sales.py --keyword FIT39
  python3 compare_sales.py --keyword FIT39,手套,GFORE      # 多个分别对比
  python3 compare_sales.py --keyword 手套 --from 2026-01-01 --to 2026-05-21
"""
import argparse, csv, glob, os, warnings, collections
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')
import openpyxl

SALES_DIR = os.path.expanduser('/Users/mac/obsidian/祥子AI/03-公司/财务数据/吉客云销售/原始明细')
SH_DIRS = [os.path.expanduser('~/Downloads'),
           os.path.expanduser('/Users/mac/obsidian/祥子AI/03-公司/财务数据/吉客云销售/售后单')]

def norm(s): return (s or '').lower().replace(' ', '')

def load_sales(dfrom, dto):
    rows = []
    for fn in glob.glob(os.path.join(SALES_DIR, 'jky_销售明细_*.csv')):
        try:
            with open(fn, encoding='utf-8-sig') as f:
                for r in csv.DictReader(f):
                    t = (r.get('下单时间') or '')[:10]
                    if dfrom <= t <= dto:
                        rows.append(r)
        except Exception:
            pass
    return rows

def load_shouhou():
    c = []
    for d in SH_DIRS:
        c += glob.glob(os.path.join(d, '网店售后单*.xlsx'))
    if not c:
        return None, None
    wb = openpyxl.load_workbook(max(c, key=os.path.getmtime))
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    hdr = [str(x).strip() if x is not None else '' for x in rows[0]]
    return hdr, rows[1:]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--keyword', required=True, help='商品/品牌关键词,逗号分隔多个分别对比')
    ap.add_argument('--from', dest='dfrom', default='')
    ap.add_argument('--to', dest='dto', default='')
    a = ap.parse_args()
    dto = a.dto or datetime.now().strftime('%Y-%m-%d')
    dfrom = a.dfrom or (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

    sales = load_sales(dfrom, dto)
    hdr, sh = load_shouhou()
    if not sales:
        print(f'✗ 没找到销售明细 csv（目录 {SALES_DIR}），无法算售后率。'); return
    if not sh:
        print('✗ 没找到售后 xlsx，先导出。'); return
    H = {n: (hdr.index(n) if n in hdr else None) for n in ['交易名称', '网店订单号', '退款申请时间', '退款金额', '网店售后单类型']}

    st = [(r.get('下单时间') or '')[:10] for r in sales if r.get('下单时间')]
    smax = max(st) if st else '?'
    print(f'对比窗口 {dfrom} ~ {dto}（销量数据实际覆盖到 {smax}；售后按退款申请时间，均按订单去重）')
    if smax < dto:
        print(f'⚠ 销量数据只到 {smax}，售后率分母可能偏小（建议把 --to 设到 {smax} 对齐）')
    print()
    print(f'{"商品/品牌":<14}{"卖出(单)":<11}{"卖出(件)":<11}{"售后(单)":<11}{"售后率":<10}{"退款额":<10}{"售后类型"}')
    for kw in a.keyword.split(','):
        kw = kw.strip()
        if not kw:
            continue
        k = norm(kw)
        so, sq = set(), 0
        for r in sales:
            if k in norm(r.get('货品摘要')):
                so.add(r.get('订单编号'))
                try: sq += float(r.get('货品数量') or 0)
                except (TypeError, ValueError): pass
        ao, am, ty = set(), 0, collections.Counter()
        for r in sh:
            t = str(r[H['退款申请时间']] or '')[:10]
            nm = str(r[H['交易名称']] or '')
            if dfrom <= t <= dto and k in norm(nm):
                o = r[H['网店订单号']]
                if o not in ao:
                    try: am += float(r[H['退款金额']] or 0)
                    except (TypeError, ValueError): pass
                ao.add(o)
                ty[r[H['网店售后单类型']]] += 1
        rate = f'{len(ao)/len(so)*100:.1f}%' if so else '-'
        print(f'{kw:<14}{len(so):<13}{int(sq):<13}{len(ao):<13}{rate:<12}¥{int(am):<9}{dict(ty)}')

if __name__ == '__main__':
    main()
