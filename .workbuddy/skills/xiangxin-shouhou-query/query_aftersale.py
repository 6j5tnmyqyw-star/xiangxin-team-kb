#!/usr/bin/env python3
"""祥新·网店售后单查询 — 解析吉客云「网店售后单查询」导出的 xlsx，
按 品牌/商品/店铺/售后类型/原因/时间 筛选，输出明细 + 售后洞察。
给客服(迎客)/运营/账房自助查某个商品或品类的售后情况用。

用法:
  python3 query_aftersale.py --keyword FIT39
  python3 query_aftersale.py --keyword 手套 --type 退货 --days 30
  python3 query_aftersale.py --shop 京东FIT39 --reason 质量
  python3 query_aftersale.py --order 51164177XXXXXXXXXXX   # 按单号查
"""
import argparse, os, glob, collections, warnings, sys
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')
import openpyxl

# 「合并导出(主表和明细在同一行)」的列（吉客云固定表头）
COLS = ['网店订单号','销售渠道','网店售后单类型','处理状态','物流单号(退)','网店订单交易状态',
        '退款原因','退款描述','退款金额','退款申请时间','退款阶段','标记','退款状态','处理超时时间',
        '网店商品编码','网店规格编码','交易名称','交易规格','退款原因(货品)','数量','单价','优惠','金额']

# 查找最新导出文件的目录（下载目录 + vault 归档目录）
SEARCH_DIRS = [
    os.path.expanduser('~/Downloads'),
    os.path.expanduser('/Users/mac/obsidian/祥子AI/03-公司/财务数据/吉客云销售/售后单'),
]

def find_latest():
    cands = []
    for d in SEARCH_DIRS:
        cands += glob.glob(os.path.join(d, '网店售后单*.xlsx'))
    return max(cands, key=os.path.getmtime) if cands else None

def load(path):
    # 注意：吉客云写的 xlsx dimension 标签不准，read_only 模式只能读到 1 行，必须用完整模式强制扫描
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    hdr = [str(c).strip() if c is not None else '' for c in rows[0]]
    idx = {name: (hdr.index(name) if name in hdr else None) for name in COLS}
    return idx, rows[1:]

def g(row, idx, name):
    i = idx.get(name)
    return row[i] if (i is not None and i < len(row)) else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file', help='指定 xlsx；不填自动找最新')
    ap.add_argument('--keyword', default='', help='商品/品牌关键词，逗号分隔多个(交易名称+商品编码模糊匹配，忽略大小写空格)')
    ap.add_argument('--shop', default='', help='销售渠道(店铺)包含')
    ap.add_argument('--type', default='', help='售后类型：退款/退货/换货/维修/补寄')
    ap.add_argument('--reason', default='', help='退款原因包含')
    ap.add_argument('--order', default='', help='按网店订单号精确查')
    ap.add_argument('--days', type=int, default=0, help='只看近 N 天(按退款申请时间)')
    ap.add_argument('--limit', type=int, default=50, help='明细输出条数上限')
    a = ap.parse_args()

    path = a.file or find_latest()
    if not path or not os.path.exists(path):
        print('✗ 找不到「网店售后单」xlsx。先跑 export_aftersale.py 导出，或用 --file 指定路径。')
        sys.exit(1)

    idx, data = load(path)
    kws = [k.strip().lower().replace(' ', '') for k in a.keyword.split(',') if k.strip()]
    cutoff = (datetime.now() - timedelta(days=a.days)) if a.days > 0 else None

    def match(r):
        if a.order and a.order not in str(g(r, idx, '网店订单号') or ''):
            return False
        if kws:
            name = (str(g(r, idx, '交易名称') or '') + str(g(r, idx, '网店商品编码') or '')).lower().replace(' ', '')
            if not any(k in name for k in kws):
                return False
        if a.shop and a.shop not in str(g(r, idx, '销售渠道') or ''):
            return False
        if a.type and a.type not in str(g(r, idx, '网店售后单类型') or ''):
            return False
        if a.reason and a.reason not in str(g(r, idx, '退款原因') or ''):
            return False
        if cutoff:
            t = str(g(r, idx, '退款申请时间') or '')[:10]
            try:
                if datetime.strptime(t, '%Y-%m-%d') < cutoff:
                    return False
            except ValueError:
                pass
        return True

    rows = [r for r in data if match(r)]

    print(f'数据源: {os.path.basename(path)}')
    times = [str(g(r, idx, '退款申请时间'))[:10] for r in data if g(r, idx, '退款申请时间')]
    if times:
        print(f'数据覆盖: {min(times)} ~ {max(times)}（全表 {len(data)} 条明细 / {len(set(g(r,idx,"网店订单号") for r in data))} 单）')
    cond = f'kw={a.keyword or "-"} 店铺={a.shop or "-"} 类型={a.type or "-"} 原因={a.reason or "-"} 单号={a.order or "-"} 近{a.days}天' if (kws or a.shop or a.type or a.reason or a.order or a.days) else '全部'
    print(f'筛选: {cond}')
    n_orders = len(set(g(r, idx, '网店订单号') for r in rows))
    print(f'命中: {len(rows)} 条明细 / {n_orders} 个售后单\n')
    if not rows:
        print('（无匹配。换个关键词，或确认导出文件已含该时间段）')
        return

    # 洞察
    print('— 售后类型:', dict(collections.Counter(g(r, idx, '网店售后单类型') for r in rows)))
    print('— 退款原因 Top5:', collections.Counter(str(g(r, idx, '退款原因') or '') for r in rows).most_common(5))
    print('— 店铺分布:', dict(collections.Counter(g(r, idx, '销售渠道') for r in rows)))
    print('— 处理状态:', dict(collections.Counter(g(r, idx, '处理状态') for r in rows)))
    amt = sum(float(g(r, idx, '退款金额') or 0) for r in rows)
    print(f'— 退款金额合计: ¥{amt:.2f}\n')

    # 明细（按单号去重，一单可能多货品行）
    print('— 售后单明细（按单号去重）:')
    seen, n = set(), 0
    for r in rows:
        o = g(r, idx, '网店订单号')
        if o in seen:
            continue
        seen.add(o); n += 1
        if n > a.limit:
            print(f'  …还有 {n_orders - a.limit} 单，--limit 调大可看全。')
            break
        print(f'  {n}. {o} | {g(r,idx,"销售渠道")} | {g(r,idx,"网店售后单类型")} | {g(r,idx,"处理状态")} | '
              f'{g(r,idx,"退款原因")} | ¥{g(r,idx,"退款金额")} | {str(g(r,idx,"退款申请时间"))[:16]}')
        print(f'     货品: {str(g(r,idx,"交易名称"))[:50]} | {g(r,idx,"交易规格")}')

if __name__ == '__main__':
    main()
