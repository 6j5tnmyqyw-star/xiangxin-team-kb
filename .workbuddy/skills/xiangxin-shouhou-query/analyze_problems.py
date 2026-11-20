#!/usr/bin/env python3
"""祥新·售后归因分析 —— 把售后单按退款原因归因，区分【我们的问题】(可改进)、
【尺码引导】(半我们)、【买家主观】(非我们)、【中性/财务】，定位真正该改的问题点。

用法:
  python3 analyze_problems.py                      # 分析全表
  python3 analyze_problems.py --from 2026-01-01    # 今年至今
  python3 analyze_problems.py --shop 京东 --keyword 手套
"""
import argparse, glob, os, collections, warnings
from datetime import datetime
warnings.filterwarnings('ignore')
import openpyxl

SEARCH_DIRS = [
    os.path.expanduser('~/Downloads'),
    os.path.expanduser('/Users/mac/obsidian/祥子AI/03-公司/财务数据/吉客云销售/售后单'),
]

# 归因规则：(子类, [关键词])，按顺序先匹配（具体的「我们问题」→中性财务→尺码精确→买家主观宽泛）
RULES = [
    ('我们·质量',     ['质量', '瑕疵', '做工']),
    ('我们·发错漏发', ['发错货', '错发', '少件', '漏发', '发货错']),
    ('我们·缺货',     ['无货', '缺货']),
    ('我们·发货超时', ['时效', '未按时', '发货慢', '送达']),
    ('我们·描述不符', ['与描述不符', '描述不符', '与图片不符', '货不对板', '不符']),
    ('中性/财务',     ['赠品', '协商一致', '退运费', '红包', '补偿', '代客户', '价保', '差价', '买贵', '降价', '申请退差', '价格高于']),
    ('尺码引导',      ['尺码没选对', '尺寸不合适', '大小不合适', '码数', '偏大', '偏小', '不合脚', '尺码偏']),
    ('买家主观',      ['不想要', '拍错', '多拍', '错拍', '错选', '多选', '7天', '信息拍错', '信息填写', '地址', '电话', '重复', '买多', '买错', '换货', '不喜欢']),
    ('其他',          ['其他']),
]
OURS = {'我们·质量', '我们·发错漏发', '我们·缺货', '我们·发货超时', '我们·描述不符'}
HALF = {'尺码引导'}

def classify(reason):
    r = str(reason or '')
    for cat, kws in RULES:
        if any(k in r for k in kws):
            return cat
    return '未分类'

def find_latest():
    c = []
    for d in SEARCH_DIRS:
        c += glob.glob(os.path.join(d, '网店售后单*.xlsx'))
    return max(c, key=os.path.getmtime) if c else None

def load(path):
    wb = openpyxl.load_workbook(path)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    hdr = [str(c).strip() if c is not None else '' for c in rows[0]]
    return hdr, rows[1:]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file'); ap.add_argument('--from', dest='dfrom', default='')
    ap.add_argument('--to', dest='dto', default=''); ap.add_argument('--shop', default='')
    ap.add_argument('--keyword', default='')
    a = ap.parse_args()
    path = a.file or find_latest()
    if not path or not os.path.exists(path):
        print('✗ 找不到售后 xlsx，先导出。'); return
    hdr, data = load(path)
    H = {n: (hdr.index(n) if n in hdr else None) for n in
         ['网店订单号', '销售渠道', '网店售后单类型', '退款原因', '退款金额', '退款申请时间', '交易名称']}
    def g(r, n): i = H[n]; return r[i] if i is not None and i < len(r) else None

    def keep(r):
        t = str(g(r, '退款申请时间') or '')[:10]
        if a.dfrom and t < a.dfrom: return False
        if a.dto and t > a.dto: return False
        if a.shop and a.shop not in str(g(r, '销售渠道') or ''): return False
        if a.keyword and a.keyword.lower().replace(' ', '') not in str(g(r, '交易名称') or '').lower().replace(' ', ''): return False
        return True
    data = [r for r in data if keep(r)]
    if not data:
        print('✗ 该条件下无售后数据。'); return

    times = [str(g(r, '退款申请时间'))[:10] for r in data if g(r, '退款申请时间')]
    n_orders = len(set(g(r, '网店订单号') for r in data))
    print(f'数据源: {os.path.basename(path)}')
    print(f'覆盖: {min(times)} ~ {max(times)} | {len(data)} 条明细 / {n_orders} 个售后单')
    cond = ' '.join(x for x in [f'from={a.dfrom}' if a.dfrom else '', f'shop={a.shop}' if a.shop else '', f'kw={a.keyword}' if a.keyword else ''] if x)
    if cond: print('筛选:', cond)
    print()

    # 按订单去重做归因（一单可能多明细，取该单第一条原因）
    seen = {}
    for r in data:
        o = g(r, '网店订单号')
        if o not in seen:
            seen[o] = {'cat': classify(g(r, '退款原因')), 'reason': str(g(r, '退款原因') or ''),
                       'shop': g(r, '销售渠道'), 'amt': float(g(r, '退款金额') or 0),
                       'name': str(g(r, '交易名称') or '')}
    orders = list(seen.values())
    N = len(orders)

    # 大类汇总
    bucket = lambda c: '我们的问题' if c in OURS else ('尺码引导' if c in HALF else ('中性/财务' if c in ('中性/财务',) else ('买家主观' if c == '买家主观' else '其他')))
    big = collections.Counter(bucket(o['cat']) for o in orders)
    bigamt = collections.defaultdict(float)
    for o in orders: bigamt[bucket(o['cat'])] += o['amt']
    print('═══ 归因总览（按售后单去重）═══')
    for k in ['我们的问题', '尺码引导', '买家主观', '中性/财务', '其他']:
        if big.get(k):
            print(f'  {k:<8} {big[k]:>4} 单  ({big[k]/N*100:4.1f}%)   退款 ¥{bigamt[k]:,.0f}')
    ours_n = big.get('我们的问题', 0) + big.get('尺码引导', 0)
    print(f'\n  →【我们能改进的】(我们问题+尺码) = {ours_n} 单 ({ours_n/N*100:.1f}%)')

    # 我们的问题 子类明细
    print('\n═══ 我们的问题·子类明细 ═══')
    sub = collections.Counter(o['cat'] for o in orders if o['cat'] in OURS)
    for cat, c in sub.most_common():
        os_ = [o for o in orders if o['cat'] == cat]
        amt = sum(o['amt'] for o in os_)
        shops = collections.Counter(o['shop'] for o in os_).most_common(3)
        print(f'  ● {cat}: {c} 单, 退款 ¥{amt:,.0f}')
        print(f'      店铺: {dict(shops)}')
        for o in os_[:4]:
            print(f'      - [{o["shop"]}] {o["reason"]} | ¥{o["amt"]:.0f} | {o["name"][:36]}')

    # 尺码问题涉及的商品/品牌
    sz = [o for o in orders if o['cat'] == '尺码引导']
    if sz:
        print(f'\n═══ 尺码引导问题: {len(sz)} 单, 退款 ¥{sum(o["amt"] for o in sz):,.0f} ═══')
        brands = collections.Counter()
        for o in sz:
            nm = o['name']
            b = next((x for x in ['FIT39', 'Fit39', 'GFORE', 'Callaway', '卡拉威', 'Number', 'PING', 'Titleist', 'Footjoy', 'FootJoy'] if x.lower() in nm.lower()), nm[:8])
            brands[b] += 1
        print('  涉及品牌/商品 Top:', dict(brands.most_common(6)))

    # 各店铺 我们的问题 排行
    print('\n═══ 各店铺「我们的问题+尺码」单数 ═══')
    shop_ours = collections.Counter(o['shop'] for o in orders if o['cat'] in OURS or o['cat'] in HALF)
    for s, c in shop_ours.most_common(8):
        print(f'  {c:>3} 单  {s}')

    # 未分类提醒
    un = [o for o in orders if o['cat'] == '未分类']
    if un:
        print(f'\n⚠ 未分类 {len(un)} 单，原因样本:', list(set(o["reason"] for o in un))[:6])

if __name__ == '__main__':
    main()
