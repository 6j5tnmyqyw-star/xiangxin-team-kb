#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
淘宝/天猫自家店铺商品图片批量下载器（卖家后台路线，零反爬）—— 可移植团队版

不依赖 browser-harness，直连 Chrome 调试端口（CDP），Windows / Mac 通用。
原理：打开自己商品的后台发布页 item.upload.taobao.com/sell/v2/publish.htm，
服务端把整份商品数据直出在 window.Json，按分类取图片 URL，从 img.alicdn.com CDN 直下。
全程只碰自己卖家后台，不开买家详情页（baxia/滑块高发区），不裸打接口。

前提：Chrome 已带调试端口启动且登录了目标店铺的千牛（启动命令见 SKILL.md）。

模式（环境变量 MODE）：
  MODE=ids   ITEM_IDS=逗号/空格分隔     —— 只下这些商品
  MODE=all                              —— 遍历全店所有在售商品全下
  MODE=scan                             —— 只下「上次跑之后新出现」的商品

其他环境变量：
  CDP_PORT   Chrome 调试端口（默认 9222）
  OUT_DIR    输出根目录（默认 ~/Downloads/淘宝店铺图片）
  STATE_DIR  扫新品状态目录（默认 脚本同目录/state）
  MAX_PAGES  全店遍历最大页数（默认 80）

依赖：pip install websocket-client
运行：MODE=all python3 shop_images_portable.py     （Windows 用 set MODE=all 后 python）
"""
import os, re, json, time, random, pathlib, urllib.request, urllib.parse, sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import websocket  # pip install websocket-client
except ImportError:
    print("缺依赖：先运行  pip install websocket-client  （或 pip3）"); sys.exit(1)

PORT      = int(os.environ.get("CDP_PORT", "9222"))
BASE      = f"http://127.0.0.1:{PORT}"
SCRIPT_DIR= pathlib.Path(__file__).resolve().parent
OUT_DIR   = pathlib.Path(os.path.expanduser(os.environ.get("OUT_DIR", "~/Downloads/淘宝店铺图片")))
STATE_DIR = pathlib.Path(os.path.expanduser(os.environ.get("STATE_DIR", str(SCRIPT_DIR / "state"))))
MODE      = os.environ.get("MODE", "ids").strip().lower()

LIST_URL  = "https://myseller.taobao.com/home.htm/SellManage/itemManage?current={cur}&pageSize=50"
EDIT_URL  = "https://item.upload.taobao.com/sell/v2/publish.htm?itemId={iid}&fromAIPublish=true"

# ---------------- 最小 CDP 客户端 ----------------
def _http(path, method="GET"):
    req = urllib.request.Request(BASE + path, method=method)
    with urllib.request.urlopen(req, timeout=10) as r:
        body = r.read().decode("utf-8", "replace")
    return json.loads(body) if body.strip() else {}

def check_chrome():
    try:
        v = _http("/json/version")
        print(f"已连上 Chrome（{v.get('Browser','?')}，端口 {PORT}）")
        return True
    except Exception:
        print(f"✗ 连不上 Chrome 调试端口 {PORT}。")
        print("  请先按 SKILL.md 用带 --remote-debugging-port 的命令启动 Chrome，并在里面登录千牛。")
        return False

class Tab:
    """一个浏览器标签页 + 它的 CDP websocket 连接。"""
    def __init__(self, url="about:blank"):
        q = urllib.parse.quote(url, safe=":/?&=._-%")
        try:
            t = _http("/json/new?" + q, "PUT")      # 新版 Chrome 要求 PUT
        except Exception:
            t = _http("/json/new?" + q)             # 老版兼容 GET
        self.id = t["id"]
        self.ws = websocket.create_connection(
            t["webSocketDebuggerUrl"], timeout=60, suppress_origin=True)
        self._mid = 0

    def call(self, method, **params):
        self._mid += 1
        self.ws.send(json.dumps({"id": self._mid, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self._mid:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg.get("result", {})

    def js(self, expr):
        r = self.call("Runtime.evaluate", expression=expr, returnByValue=True, awaitPromise=True)
        res = r.get("result", {})
        if res.get("subtype") == "error":
            return None
        return res.get("value")

    def goto(self, url):
        self.call("Page.navigate", url=url)

    def wait_load(self, timeout=30):
        end = time.time() + timeout
        while time.time() < end:
            try:
                if self.js("document.readyState") == "complete":
                    return True
            except Exception:
                pass
            time.sleep(0.5)
        return False

    def close(self):
        try: self.ws.close()
        except Exception: pass
        try: _http("/json/close/" + self.id)
        except Exception: pass

def human_sleep(a, b):
    time.sleep(random.uniform(a, b))

# ---------------- 提取 window.Json ----------------
EXTRACT_JS = r"""
(() => {
  const J = window.Json;
  if (!J || !J.components) return {err: 'no window.Json'};
  const comps = J.components;
  function norm(u){ if(!u) return u; u=u.trim(); if(u.startsWith('//')) u='https:'+u; return u; }
  function collect(o, acc, seen){
    if(!o || typeof o!=='object' || seen.has(o)) return; seen.add(o);
    for(const k in o){ let v; try{v=o[k];}catch(e){continue;}
      if(typeof v==='string'){
        const m = v.match(/(?:https?:)?\/\/[^ "'<>]+\/\d{6,}\/O1CN[^ "'<>)]+\.(?:jpg|jpeg|png|webp)/ig);
        if(m) m.forEach(x=>acc.push(norm(x)));
      } else if(v && typeof v==='object') collect(v, acc, seen);
    }
  }
  function compImgs(id){ const a=[]; if(comps[id]) collect(comps[id], a, new WeakSet()); return [...new Set(a)]; }
  const main = compImgs('mainImagesGroup');
  const three= compImgs('threeToFourImages');
  const desc = compImgs('desc');
  const skuComps = Object.keys(comps).filter(id=>/sku|saleprop/i.test(id) && !/struct-/i.test(id));
  let skuRaw=[]; skuComps.forEach(id=>{ const a=[]; collect(comps[id], a, new WeakSet()); skuRaw.push(...a); });
  const mainSet = new Set(main);
  const sku = [...new Set(skuRaw)].filter(u=>!mainSet.has(u));
  const vids=[];
  (function fv(o,seen){ if(!o||typeof o!=='object'||seen.has(o))return; seen.add(o);
    for(const k in o){ let v; try{v=o[k];}catch(e){continue;}
      if(typeof v==='string'){ if(/cloud\.video\.taobao|video\.taobao\.com|\.mp4(\?|$)/i.test(v) && v.length<400) vids.push(norm(v)); }
      else if(v&&typeof v==='object') fv(v,seen);
    }})(J, new WeakSet());
  let title=null;
  try{ const m=JSON.stringify(comps.title||{}).match(/"(?:value|text|defaultValue)"\s*:\s*"([^"]{4,120})"/); if(m) title=m[1]; }catch(e){}
  let sellerId=null;
  try{ const m=JSON.stringify(J).match(/"userId"\s*:\s*"?(\d{6,})"?/); if(m) sellerId=m[1]; }catch(e){}
  return {title, sellerId, main, three, desc, sku, video:[...new Set(vids)]};
})()
"""

GRAB_IDS_JS = r"""(() => [...new Set([...document.querySelectorAll('a')].map(a=>{
  const m=(a.href||'').match(/itemId=(\d{10,})/); return m?m[1]:null;
}).filter(Boolean))])()"""

# ---------------- 工具 ----------------
def safe_name(s, fallback):
    if not s: return fallback
    s = re.sub(r'[\\/:*?"<>|\n\r\t]', '', s).strip()
    return (s[:60] or fallback)

def orig_url(u):
    return re.sub(r'(\.(?:jpg|jpeg|png|webp))_\d+x\d+.*$', r'\1', u, flags=re.I)

def ext_of(url, default='.jpg'):
    m = re.search(r'\.(jpg|jpeg|png|webp|mp4)(?:[?_]|$)', url, re.I)
    return ('.' + m.group(1).lower()) if m else default

def download(url, dest):
    try:
        req = urllib.request.Request(orig_url(url), headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Referer": "https://www.taobao.com/"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        if not data or len(data) < 200: return False, "空/过小"
        dest.write_bytes(data); return True, len(data)
    except Exception as e:
        return False, str(e)[:80]

# ---------------- 全店遍历 itemId ----------------
def fetch_all_ids(tab, max_pages=int(os.environ.get("MAX_PAGES", "80"))):
    print("→ 遍历商品管理列表，收集全部 itemId …")
    all_ids, seen, empty_streak = [], set(), 0
    for cur in range(1, max_pages + 1):
        tab.goto(LIST_URL.format(cur=cur))
        tab.wait_load(); human_sleep(4, 7)
        ids = []
        for _ in range(3):
            ids = tab.js(GRAB_IDS_JS) or []
            if ids: break
            human_sleep(2, 3)
        fresh = [i for i in ids if i not in seen]
        for i in fresh: seen.add(i); all_ids.append(i)
        print(f"   第{cur}页: 本页{len(ids)} 新增{len(fresh)} 累计{len(all_ids)}")
        if not fresh:
            empty_streak += 1
            if empty_streak >= 2: break   # 连续两页无新增 = 到底
        else:
            empty_streak = 0
    print(f"→ 共收集 {len(all_ids)} 个商品")
    return all_ids

# ---------------- 下载单个商品 ----------------
def process(tab, item_id):
    print(f"\n===== 商品 {item_id} =====")
    tab.goto(EDIT_URL.format(iid=item_id))
    tab.wait_load(); human_sleep(5, 7)
    data = tab.js(EXTRACT_JS)
    if not data or data.get('err'):
        human_sleep(4, 6); data = tab.js(EXTRACT_JS)
    if not data or data.get('err'):
        print("  ✗ 提取失败，跳过（可能千牛没登录 / 不是本店商品）"); return {"id": item_id, "ok": False}
    title = safe_name(data.get('title'), item_id)
    folder = OUT_DIR / f"{title}_{item_id}"
    cats = {
        "01-主图": data.get('main', []),
        "02-3比4长主图": data.get('three', []),
        "03-SKU颜色图": data.get('sku', []),
        "04-详情长图": data.get('desc', []),
        "05-主图视频": data.get('video', []),
    }
    counts = {}
    for cat, urls in cats.items():
        urls = [u for u in urls if u]
        if not urls: continue
        sub = folder / cat; sub.mkdir(parents=True, exist_ok=True)
        ok = 0
        for i, u in enumerate(urls, 1):
            success, info = download(u, sub / f"{i:02d}{ext_of(u)}")
            ok += 1 if success else 0
            if not success: print(f"    ! {cat} 第{i}张失败: {info}")
            human_sleep(0.3, 0.8)
        counts[cat] = f"{ok}/{len(urls)}"
    print(f"  {title}  ->  {counts}")
    return {"id": item_id, "ok": True, "title": title, "counts": counts, "sellerId": data.get('sellerId')}

# ---------------- 主流程 ----------------
def main():
    if not check_chrome(): sys.exit(2)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"模式={MODE}  输出={OUT_DIR}")

    tab = Tab()
    try:
        if MODE == "ids":
            env = os.environ.get("ITEM_IDS", "")
            ids = [x for x in re.split(r"[,\s]+", env) if x.strip().isdigit()]
            all_now = None
        else:  # all / scan 都要先遍历全店
            ids = fetch_all_ids(tab)
            all_now = ids

        if not ids:
            print("没有商品 ID 可下载。"); return

        if MODE == "scan":
            state_file = STATE_DIR / "seen_items.json"
            seen = set(json.loads(state_file.read_text())) if state_file.exists() else set()
            new_ids = [i for i in all_now if i not in seen]
            print(f"扫新品: 全店 {len(all_now)} 件，其中新出现 {len(new_ids)} 件")
            if not new_ids:
                print("没有新商品，结束。")
                state_file.write_text(json.dumps(sorted(set(all_now))))
                return
            ids = new_ids

        print(f"\n开始下载 {len(ids)} 个商品 …")
        results = []
        for idx, iid in enumerate(ids):
            results.append(process(tab, iid))
            if idx < len(ids) - 1: human_sleep(4, 8)

        ok = [r for r in results if r.get("ok")]
        print(f"\n===== 完成: {len(ok)}/{len(results)} 个商品成功 =====")
        if MODE in ("scan", "all") and all_now:
            (STATE_DIR / "seen_items.json").write_text(json.dumps(sorted(set(all_now))))
        summary = {"mode": MODE, "total": len(results), "ok": len(ok),
                   "items": [{"id": r["id"], "title": r.get("title"), "counts": r.get("counts")} for r in ok]}
        (STATE_DIR / "last_run.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
        print(f"输出目录: {OUT_DIR}")
    finally:
        tab.close()   # 跑完关掉自己开的标签

if __name__ == "__main__":
    main()
