#!/usr/bin/env python3
"""祥新·网店售后单 导出助手（协作模式）

用 browser-harness 连已登录的 Chrome：聚焦吉客云「网店售后单查询」页、关掉业务提醒弹窗，
然后【提示你手动点导出三下】，脚本自动监控下载完成并归档到 vault。

跑法（必须用 browser-harness 执行，helper 才预导入）:
  browser-harness < export_aftersale.py

为什么导出那一下要手动:
  实测确认——吉客云导出按钮只认真实硬件点击，CDP/browser-harness 的合成 click 点不开这个
  mini 菜单。所以「点导出」得人来点；解析/查询/归档全自动。无人值守需求请走 jky-cli API
  接口 omsapi-business.refund.listRefund（见 SKILL.md 路2，待配凭证）。
"""
import os, time, glob, shutil
from datetime import datetime

DL = os.path.expanduser('~/Downloads')
ARCHIVE = os.path.expanduser('/Users/mac/obsidian/祥子AI/03-公司/财务数据/吉客云销售/售后单')
IFRAME = 'online_after_sale_query'

def jk_tab():
    for t in cdp("Target.getTargets")["targetInfos"]:
        if "jackyun.com/home/mainframe" in t.get("url", ""):
            return t["targetId"]
    return None

def latest_xlsx():
    fs = glob.glob(os.path.join(DL, '网店售后单*.xlsx'))
    return max(fs, key=os.path.getmtime) if fs else None

def close_dialogs():
    """关掉吉客云「已发货退款需单号化处理」等业务提醒弹窗（会遮挡操作区）。最多清 3 个。"""
    for _ in range(3):
        c = js("""(() => {
          const find=(d,bx,by)=>{let el=null;d.querySelectorAll('a,span,button,div').forEach(e=>{
            const t=(e.textContent||'').trim();
            if((t==='知道了'||t==='我知道了'||t==='确定'||t==='关闭')&&e.children.length<=1){
              const r=e.getBoundingClientRect(); if(r.width>0&&r.width<200) el={x:Math.round(bx+r.left+r.width/2),y:Math.round(by+r.top+r.height/2)};}});
            return el;};
          let c=find(document,0,0); if(c) return c;
          const f=[...document.querySelectorAll('iframe')].find(x=>(x.src||'').includes('__IF__'));
          if(f){const fr=f.getBoundingClientRect(); c=find(f.contentDocument,fr.left,fr.top);} return c;
        })()""".replace('__IF__', IFRAME))
        if not c:
            break
        click_at_xy(c['x'], c['y']); time.sleep(0.8)

def main():
    tab = jk_tab()
    if not tab:
        print('✗ 没找到已登录的吉客云页面。请在 Chrome 登录吉客云后重跑。'); return
    switch_tab(tab)
    cdp("Target.activateTarget", targetId=tab)   # 把 tab 拉到前台，方便手动点
    time.sleep(0.6)

    if not js("(()=>!![...document.querySelectorAll('iframe')].find(x=>(x.src||'').includes('%s')))()" % IFRAME):
        print('✗ 「网店售后单查询」页未打开。吉客云顶部搜索框搜“网店售后单查询”打开它再重跑。'); return

    close_dialogs()
    before = latest_xlsx()
    before_m = os.path.getmtime(before) if before else 0

    print('—' * 30)
    print('请在吉客云页面点：【导出 → 导出所有页 → 合并导出(主表和明细在同一行)】')
    print('（确认时间筛选是「近一个月」或你要的范围）')
    print('正在监控下载… 最多等 150 秒')
    print('—' * 30)

    got = None
    for i in range(150):
        time.sleep(1)
        if i and i % 20 == 0:
            close_dialogs()   # 期间可能又弹业务提醒，顺手清掉
        f = latest_xlsx()
        if f and os.path.getmtime(f) > before_m + 0.5 and not f.endswith('.crdownload'):
            s = os.path.getsize(f); time.sleep(1)
            if s > 0 and os.path.getsize(f) == s:
                got = f; break
    if not got:
        print('✗ 没检测到新导出文件。确认点了「合并导出」、Chrome 下载没被拦截。'); return
    print('✓ 下载完成:', os.path.basename(got), '(%d bytes)' % os.path.getsize(got))

    os.makedirs(ARCHIVE, exist_ok=True)
    dst = os.path.join(ARCHIVE, '网店售后单_%s.xlsx' % datetime.now().strftime('%Y%m%d_%H%M'))
    shutil.copy2(got, dst)
    print('✓ 已归档:', dst)
    print('\n查询: python3 query_aftersale.py --keyword <品牌/商品关键词>')

main()
