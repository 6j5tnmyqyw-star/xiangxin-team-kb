#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取天猫店铺最新上架商品列表（按店铺"新品"排序）

用法：
    python3 shop_new_items.py <店铺主页 URL>
    python3 shop_new_items.py <店铺主页 URL> --limit 10
    python3 shop_new_items.py <店铺主页 URL> --port 9224   # 指定已登录淘宝的 Chrome 调试端口

输出：JSON 到 stdout（含 shopName + items 列表）

依赖：browser-harness + 一个已登录淘宝的 Chrome。
      默认连 9227 调试端口；祥书机器上淘宝登录态常在 9224，用 --port 9224 即可。
"""

import argparse
import json
import os
import re
import subprocess
import sys

# 浏览器里执行的代码模板。{url} 会被实际店铺 URL 替换。
# 开隔离新标签抓取、抓完即关，不动用户/其他任务的当前标签
# （遵守 browser-harness "首次导航用 new_tab、不要用 goto_url 覆盖当前标签" 的铁律）。
BH_SNIPPET = r'''
import time, json

# 先开一个空白隔离标签并切到它，后面的 goto_url 只作用在这个新标签
new_tab("about:blank")

# 装 XHR hook，抓所有 mtop 响应（在导航前注册，新文档一加载就注入）
hook = r"""
(function(){
  if (window.__hook_shop_installed) return;
  window.__hook_shop_installed = true;
  window.__captured_mtop = {};
  var XO = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method, url) {
    this._url = url;
    return XO.apply(this, arguments);
  };
  var XS = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.send = function() {
    var self = this;
    this.addEventListener('load', function(){
      try {
        var u = self._url || '';
        if (!/mtop|h5api/.test(u)) return;
        var m = u.match(/[?&]api=([^&]+)/i) || u.match(/\/h5\/([^\/]+)\//);
        var api = m ? m[1].toLowerCase() : 'unknown';
        var txt = self.responseText || '';
        try { window.__captured_mtop[api] = JSON.parse(txt); } catch(_){ }
      } catch(_){}
    });
    return XS.apply(this, arguments);
  };
})();
"""
cdp("Page.addScriptToEvaluateOnNewDocument", source=hook)

goto_url("{url}")
wait_for_load()
human_sleep(5, 9)   # 随机化等待节奏（防 baxia 识别固定间隔）

# 读捕获的 shop.simple.fetch 数据
result = js(r"""
(function(){
  var d = window.__captured_mtop && window.__captured_mtop['mtop.taobao.shop.simple.fetch'];
  if (!d || !d.data) return JSON.stringify({err: 'no data captured'});
  var dto = d.data;
  return JSON.stringify({
    ok: true,
    shopName: dto.signInfoDTO && dto.signInfoDTO.shopName || '',
    fansNum: dto.signInfoDTO && dto.signInfoDTO.fansNum || 0,
    totalCnt: dto.itemInfoDTO && dto.itemInfoDTO.totalCnt || 0,
    items: (dto.itemInfoDTO && dto.itemInfoDTO.data || []).map(function(it){
      return {
        itemId: it.itemId,
        title: it.title,
        image: it.image,
        sold365: it.vagueSold365,
        benefits: (it.benefitPointList || []).map(function(b){return b.text;})
      };
    })
  });
})()
""")

print("<<<BH_JSON>>>")
print(result)
print("<<<BH_JSON_END>>>")

# 清理：关掉本次开的抓取标签，保持浏览器干净
try:
    info = cdp("Target.getTargetInfo")
    tid = info.get("targetInfo", {}).get("targetId")
    if tid:
        cdp("Target.closeTarget", targetId=tid)
except Exception:
    pass
'''


def fetch_shop_items(shop_url: str, port: int) -> dict:
    """调 browser-harness 抓店铺商品列表"""
    # 规范化店铺 URL：使用 search.htm + 按新品排序
    base = re.sub(r"/(shop/)?(view_shop|index|search)\.htm.*$", "", shop_url, count=1)
    base = base.rstrip("/")
    listing_url = f"{base}/search.htm?orderType=newOn_desc&pageNo=1"

    code = BH_SNIPPET.replace("{url}", listing_url)
    env = os.environ.copy()
    env["BU_CDP_URL"] = f"http://127.0.0.1:{port}"
    env["BU_NAME"] = f"tb{port}"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    proc = subprocess.run(
        ["browser-harness"],
        input=code,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
        raise RuntimeError(
            f"browser-harness 退出码 {proc.returncode}（端口 {port} 的 Chrome 是否在跑且已登录淘宝？）"
        )

    out = proc.stdout
    m = re.search(r"<<<BH_JSON>>>\s*\n(.*?)\n<<<BH_JSON_END>>>", out, re.DOTALL)
    if not m:
        sys.stderr.write(out)
        raise RuntimeError("没找到 JSON 分隔符（页面可能未加载出商品，或被风控拦截）")
    data = json.loads(m.group(1))
    if data.get("err"):
        raise RuntimeError(
            f"接口未捕获：{data['err']}（确认 URL 是天猫店铺主页，且该 Chrome 已登录淘宝）"
        )
    return data


# 过滤关键词（认为是清仓/福利款的标记）
CLEARANCE_KEYWORDS = ["福利款", "清仓", "限量款", "尾货", "断码", "处理价"]


def filter_and_pick(items, limit, skip_clearance):
    """先过滤、再按 itemId 倒序、取前 N"""
    if skip_clearance:
        items = [it for it in items if not any(kw in it["title"] for kw in CLEARANCE_KEYWORDS)]
    # itemId 倒序 = 上架时间倒序
    items_sorted = sorted(items, key=lambda x: int(x["itemId"]), reverse=True)
    return items_sorted[:limit]


def main():
    ap = argparse.ArgumentParser(description="天猫店铺新品列表抓取")
    ap.add_argument("shop_url", help="店铺主页 URL（如 https://kingloy.tmall.com）")
    ap.add_argument("--limit", type=int, default=10, help="返回前 N 个（默认 10）")
    ap.add_argument("--skip-clearance", action="store_true", default=True, help="过滤掉福利款/清仓款")
    ap.add_argument("--include-clearance", action="store_true", help="不过滤福利款")
    ap.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("BH_TB_PORT", 9227)),
        help="已登录淘宝的 Chrome 调试端口（默认 9227，可用 BH_TB_PORT 环境变量覆盖）",
    )
    args = ap.parse_args()

    skip = args.skip_clearance and not args.include_clearance

    print(f"[店铺采集] 打开 {args.shop_url}（端口 {args.port}）……", file=sys.stderr)
    data = fetch_shop_items(args.shop_url, args.port)
    raw_items = data["items"]

    picked = filter_and_pick(raw_items, args.limit, skip)

    print(f"[店铺采集] 店铺={data['shopName']} 粉丝={data['fansNum']} 全店={data['totalCnt']}", file=sys.stderr)
    print(f"[店铺采集] 接口返回 {len(raw_items)} 条，过滤后取前 {len(picked)} 条", file=sys.stderr)

    out = {
        "shopName": data["shopName"],
        "fansNum": data["fansNum"],
        "totalCnt": data["totalCnt"],
        "items": picked,
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
