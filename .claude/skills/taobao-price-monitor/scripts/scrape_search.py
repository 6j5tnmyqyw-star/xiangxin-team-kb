#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓淘宝搜索结果（按销量排序）的商品价格/销量/店铺，单个关键词一次。

防反爬核心：走 browser-harness 连一个**已登录淘宝的真 Chrome**（默认端口 9224，
与 xiangxin-jingpin-shangxin 共用同一个监控 profile），指纹是真 Chrome，
不再用 selenium-stealth 那套弱指纹，规避 rgv587/baxia 风控。

用法：
    python3 scrape_search.py "Garmin S70 高尔夫" --port 9224 --limit 15

输出 stdout JSON：{keyword, login_wall, risk_control, items:[{title,price,finalPrice,sales,shop,link}]}

依赖：browser-harness + 一个已登录淘宝的 Chrome（默认端口 9224）。
"""
import argparse
import json
import os
import re
import subprocess
import sys
from urllib.parse import quote

# 浏览器里执行的代码。{url} 会被替换。开隔离新标签抓完即关，不动其它标签。
# DOM 抽取逻辑沿用旧 garmin_monitor 的 doubleCard 选择器（已验证稳）。
BH_SNIPPET = r'''
import json
new_tab("{url}")
wait_for_load()
human_sleep(5, 9)   # 随机化等待节奏（防 baxia 识别固定间隔）

# 触发懒加载：淘宝搜索页要滚动事件才把卡片插进 DOM
try:
    h = js("return document.body.scrollHeight") or 3000
    for pct in [0.25, 0.5, 0.75, 1.0]:
        js("window.scrollTo(0, %d);" % int(h * pct)); human_sleep(0.8, 1.6)
    js("window.scrollTo(0, 0);"); human_sleep(1.2, 2)
except Exception:
    pass

loc = js("return location.href") or ""
title = js("return document.title") or ""
body = js("return document.body ? document.body.innerText.slice(0,3000) : ''") or ""
login_wall = ("login.taobao" in loc) or ("登录" in title and "搜索" not in title and "淘宝" not in title)
risk_control = ("rgv587" in body) or ("baxia" in body) or ("滑动验证" in body) or ("安全验证" in body)

result = js(r"""
return (() => {
    const cards = document.querySelectorAll('[class*="doubleCard--"]');
    const results = [];
    cards.forEach(card => {
        const titleEl = card.querySelector('[class*="title--"]');
        const t = titleEl?.getAttribute('title') || titleEl?.innerText?.trim() || '';
        const priceInt   = card.querySelector('[class*="priceInt--"]')?.innerText?.trim() || '';
        const priceFloat = card.querySelector('[class*="priceFloat--"]')?.innerText?.trim() || '';
        const price = priceInt ? (priceInt + priceFloat) : '';
        const sales = card.querySelector('[class*="realSales--"]')?.innerText?.trim() || '';
        const shop  = card.querySelector('[class*="shopNameText--"], [class*="shopName--"]')?.innerText?.trim() || '';
        const hrefs = [];
        const outerLink = card.closest('a[href]');
        if (outerLink?.href) hrefs.push(outerLink.href);
        for (const a of card.querySelectorAll('a[href]')) { if (a.href) hrefs.push(a.href); }
        let itemId = '';
        for (const href of hrefs) { const mId = href.match(/[?&]id=(\d{6,})/); if (mId) { itemId = mId[1]; break; } }
        const link = itemId ? ('https://item.taobao.com/item.htm?id=' + itemId) : '';
        let finalPrice = '';
        const allText = card.innerText || '';
        const mP = allText.match(/到手价?\s*¥?\s*([\d,]+\.?\d*)/);
        if (mP) finalPrice = mP[1].replace(/,/g, '');
        results.push({ title: t, price, finalPrice, sales, shop, link });
    });
    return JSON.stringify(results);
})();
""")

print("<<<BH_JSON>>>")
print(json.dumps({"login_wall": login_wall, "risk_control": risk_control, "title": title, "payload": result}))
print("<<<BH_JSON_END>>>")

try:
    info = cdp("Target.getTargetInfo"); tid = info.get("targetInfo", {}).get("targetId")
    if tid: cdp("Target.closeTarget", targetId=tid)
except Exception:
    pass
'''


def scrape(keyword: str, port: int) -> dict:
    url = f"https://s.taobao.com/search?q={quote(keyword)}&sort=sale-desc"
    code = BH_SNIPPET.replace("{url}", url)
    env = os.environ.copy()
    env["BU_CDP_URL"] = f"http://127.0.0.1:{port}"
    env["BU_NAME"] = f"tb{port}"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    proc = subprocess.run(
        ["browser-harness"], input=code, env=env,
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=150,
    )
    out = proc.stdout
    m = re.search(r"<<<BH_JSON>>>\s*\n(.*?)\n<<<BH_JSON_END>>>", out, re.DOTALL)
    if not m:
        sys.stderr.write((proc.stdout + proc.stderr)[-1500:])
        raise RuntimeError(f"browser-harness 无输出（端口 {port} Chrome 在跑且登录淘宝？）")
    wrap = json.loads(m.group(1))
    if wrap.get("risk_control"):
        return {"keyword": keyword, "risk_control": True, "login_wall": False, "items": []}
    if wrap.get("login_wall"):
        return {"keyword": keyword, "login_wall": True, "risk_control": False, "items": []}
    items = json.loads(wrap["payload"] or "[]")
    items = [it for it in items if it.get("title") and it.get("price")]
    return {"keyword": keyword, "login_wall": False, "risk_control": False, "items": items}


def main():
    ap = argparse.ArgumentParser(description="单关键词淘宝销量榜价格抓取")
    ap.add_argument("keyword")
    ap.add_argument("--port", type=int, default=int(os.environ.get("BH_TB_PORT", 9224)))
    ap.add_argument("--limit", type=int, default=15)
    args = ap.parse_args()
    data = scrape(args.keyword, args.port)
    data["items"] = data["items"][: args.limit]
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
