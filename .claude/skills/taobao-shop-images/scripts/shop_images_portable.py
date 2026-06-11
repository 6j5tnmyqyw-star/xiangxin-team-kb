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
  MODE=all                              —— 遍历全店全下（断点续跑：已下过的自动跳过）
  MODE=scan                             —— 只下「上次跑之后新出现」的商品

除图片外还抓：SKU 名字（SKU 图按名字命名）、价格/库存/商家编码、产品属性、商品标题。
每个商品落 商品信息.json；跑完输出根目录汇总 _全店SKU台账.csv 和 _全店商品属性.csv。

其他环境变量：
  CDP_PORT   Chrome 调试端口（默认 9222）
  OUT_DIR    输出根目录（默认 ~/Downloads/淘宝店铺图片）
  STATE_DIR  扫新品状态目录（默认 脚本同目录/state）
  MAX_PAGES  全店遍历最大页数（默认 80）
  FORCE=1    忽略断点续跑标记，全部重下

依赖：pip install websocket-client
运行：MODE=all python3 shop_images_portable.py     （Windows 用 set MODE=all 后 python）
"""
import os, re, json, time, csv, random, pathlib, urllib.request, urllib.parse, sys
from concurrent.futures import ThreadPoolExecutor

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
FORCE     = os.environ.get("FORCE", "") == "1"

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
  // 表单权威数据在 J.models.formValues（不是 J.formValues，老写法取不到）
  const fv = J.formValues || (J.models && J.models.formValues) || {};
  // SKU：优先 formValues.sku —— 带名字/价格/库存/商家编码的权威结构
  let skuList = [];
  try {
    const arr = Array.isArray(fv.sku) ? fv.sku : [];
    skuList = arr.map(s => ({
      name: (s.props||[]).map(p=>p&&p.text).filter(Boolean).join('_'),
      url: norm((((s.skuPicture||[])[0]||{}).url)||null),
      skuId: s.skuId||null, outerId: s.skuOuterId||'',
      price: s.skuPrice||'', stock: (s.skuStock==null?'':s.skuStock)
    }));
  } catch(e) {}
  // 兜底：老办法从组件里扒 SKU 图（无名字）
  const skuComps = Object.keys(comps).filter(id=>/sku|saleprop/i.test(id) && !/struct-/i.test(id));
  let skuRaw=[]; skuComps.forEach(id=>{ const a=[]; collect(comps[id], a, new WeakSet()); skuRaw.push(...a); });
  const mainSet = new Set(main);
  const sku = [...new Set(skuRaw)].filter(u=>!mainSet.has(u));
  const vids=[];
  (function fvids(o,seen){ if(!o||typeof o!=='object'||seen.has(o))return; seen.add(o);
    for(const k in o){ let v; try{v=o[k];}catch(e){continue;}
      if(typeof v==='string'){ if(/cloud\.video\.taobao|video\.taobao\.com|\.mp4(\?|$)/i.test(v) && v.length<400) vids.push(norm(v)); }
      else if(v&&typeof v==='object') fvids(v,seen);
    }})(J, new WeakSet());
  let title=null;
  try{ if(typeof fv.title==='string' && fv.title.length>=4) title=fv.title; }catch(e){}
  if(!title){ try{ const m=JSON.stringify(comps.title||{}).match(/"(?:value|text|defaultValue)"\s*:\s*"([^"]{4,120})"/); if(m) title=m[1]; }catch(e){} }
  let sellerId=null;
  try{ const m=JSON.stringify(J).match(/"userId"\s*:\s*"?(\d{6,})"?/); if(m) sellerId=m[1]; }catch(e){}
  // 产品属性：属性名定义在 models.catProp.dataSource，选中值在 formValues.catProp
  let attrs=[];
  try {
    const defs=((J.models&&J.models.catProp&&J.models.catProp.dataSource)||[]);
    const labelMap={}; defs.forEach(d=>{ if(d&&d.name) labelMap[d.name]=d.label||d.name; });
    const pick=x=>(x&&typeof x==='object')?(x.text!=null?String(x.text):(x.value!=null?String(x.value):'')):(x==null?'':String(x));
    const sel=fv.catProp||{};
    for(const k in sel){
      const v=sel[k];
      const text=Array.isArray(v)?v.map(pick).filter(Boolean).join('、'):pick(v);
      if(text!=='') attrs.push({name:labelMap[k]||k, value:String(text).slice(0,300)});
    }
  } catch(e) {}
  let price=null, quantity=null, outerId=null;
  try{ price=fv.price!=null?String(fv.price):null; quantity=fv.quantity!=null?String(fv.quantity):null; outerId=fv.outerId!=null?String(fv.outerId):null; }catch(e){}
  return {title, sellerId, price, quantity, outerId, attrs, main, three, desc, sku, skuList, video:[...new Set(vids)]};
})()
"""

GRAB_IDS_JS = r"""(() => [...new Set([...document.querySelectorAll('a')].map(a=>{
  const m=(a.href||'').match(/itemId=(\d{10,})/); return m?m[1]:null;
}).filter(Boolean))])()"""

# ---------------- 工具 ----------------
def safe_name(s, fallback):
    if not s: return str(fallback)
    s = re.sub(r'[\\/:*?"<>|\n\r\t]', '', str(s)).strip()
    return (s[:60] or str(fallback))

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

def download_batch(pairs):
    """pairs: [(url, dest)]，CDN 不设防，并发直下"""
    ok = 0
    if not pairs: return 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        for (u, d), (success, info) in zip(pairs, ex.map(lambda p: download(*p), pairs)):
            if success: ok += 1
            else: print(f"    ! 下载失败 {d.name}: {info}")
    return ok

def find_done_folder(item_id):
    """断点续跑标记：已存在 商品信息.json 的商品文件夹"""
    for p in OUT_DIR.glob(f"*_{item_id}/商品信息.json"):
        return p.parent
    return None

# ---------------- 全店遍历 itemId ----------------
def fetch_all_ids(tab, max_pages=int(os.environ.get("MAX_PAGES", "80"))):
    # 12 小时内抓过的全店清单直接复用（断点续跑时省几十页翻页）
    cache = STATE_DIR / "all_ids_cache.json"
    if not FORCE and cache.exists():
        try:
            c = json.loads(cache.read_text())
            if time.time() - c.get("ts", 0) < 12*3600 and c.get("ids"):
                print(f"→ 复用 {time.strftime('%H:%M', time.localtime(c['ts']))} 抓的全店清单：{len(c['ids'])} 件")
                return c["ids"]
        except Exception:
            pass
    print("→ 遍历商品管理列表，收集全部 itemId …")
    all_ids, seen, empty_streak = [], set(), 0
    for cur in range(1, max_pages + 1):
        tab.goto(LIST_URL.format(cur=cur))
        tab.wait_load(); human_sleep(3, 5)
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
    cache.write_text(json.dumps({"ts": time.time(), "ids": all_ids}))
    return all_ids

# ---------------- 下载单个商品 ----------------
def process(tab, item_id):
    if not FORCE:
        done = find_done_folder(item_id)
        if done:
            print(f"⏭  {item_id} 已下过（{done.name}），跳过")
            return {"id": item_id, "ok": True, "skipped": True}
    print(f"\n===== 商品 {item_id} =====")
    tab.goto(EDIT_URL.format(iid=item_id))
    tab.wait_load(); human_sleep(4, 6)
    data = tab.js(EXTRACT_JS)
    if not data or data.get('err'):
        human_sleep(4, 6); data = tab.js(EXTRACT_JS)
    if not data or data.get('err'):
        print("  ✗ 提取失败，跳过（可能千牛没登录 / 不是本店商品）"); return {"id": item_id, "ok": False}
    title = safe_name(data.get('title'), item_id)
    folder = OUT_DIR / f"{title}_{item_id}"
    counts = {}

    # SKU 图：按 SKU 名字命名
    sku_list = [s for s in (data.get('skuList') or []) if s.get('url')]
    if sku_list:
        sub = folder / "03-SKU图"; sub.mkdir(parents=True, exist_ok=True)
        used, pairs = {}, []
        for s in sku_list:
            base = safe_name(s.get('name'), s.get('skuId'))
            n = used.get(base, 0) + 1; used[base] = n
            fname = f"{base}{'' if n == 1 else '-'+str(n)}{ext_of(s['url'])}"
            s['file'] = f"03-SKU图/{fname}"
            pairs.append((s['url'], sub / fname))
        counts["03-SKU图"] = f"{download_batch(pairs)}/{len(pairs)}"

    cats = {
        "01-主图": data.get('main', []),
        "02-3比4长主图": data.get('three', []),
        "04-详情长图": data.get('desc', []),
        "05-主图视频": data.get('video', []),
    }
    if not sku_list:  # 没有带名字的 SKU 结构时退回老办法
        cats["03-SKU颜色图"] = data.get('sku', [])
    for cat, urls in cats.items():
        urls = [u for u in urls if u]
        if not urls: continue
        sub = folder / cat; sub.mkdir(parents=True, exist_ok=True)
        pairs = [(u, sub / f"{i:02d}{ext_of(u)}") for i, u in enumerate(urls, 1)]
        counts[cat] = f"{download_batch(pairs)}/{len(pairs)}"

    # 信息落盘（同时是断点续跑的完成标记，最后写）
    folder.mkdir(parents=True, exist_ok=True)
    info = {"itemId": item_id, "title": data.get('title'), "sellerId": data.get('sellerId'),
            "price": data.get('price'), "quantity": data.get('quantity'), "outerId": data.get('outerId'),
            "attrs": data.get('attrs') or [],
            "skus": [{k: s.get(k) for k in ("name","skuId","outerId","price","stock","file","url")} for s in (data.get('skuList') or [])],
            "counts": counts, "downloadedAt": time.strftime("%Y-%m-%d %H:%M:%S")}
    (folder / "商品信息.json").write_text(json.dumps(info, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  {title}  ->  {counts}")
    return {"id": item_id, "ok": True, "title": title, "counts": counts, "sellerId": data.get('sellerId')}

# ---------------- 全店台账（从各商品 商品信息.json 重建，幂等）----------------
def build_manifest():
    rows, attr_rows = [], []
    for p in sorted(OUT_DIR.glob("*/商品信息.json")):
        try: info = json.loads(p.read_text(encoding="utf-8"))
        except Exception: continue
        skus = info.get("skus") or [{}]
        for s in skus:
            rows.append([info.get("itemId"), info.get("title"), s.get("name",""),
                         s.get("price",""), s.get("stock",""), s.get("outerId",""),
                         (p.parent.name + "/" + s["file"]) if s.get("file") else ""])
        attr_join = "；".join(f"{a.get('name')}:{a.get('value')}" for a in (info.get("attrs") or []))
        attr_rows.append([info.get("itemId"), info.get("title"), info.get("price",""),
                          info.get("outerId",""), attr_join])
    out = OUT_DIR / "_全店SKU台账.csv"
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["商品ID","标题","SKU名","价格","库存","商家编码","图片路径"])
        w.writerows(rows)
    print(f"→ SKU 台账：{out}（{len(rows)} 行）")
    out2 = OUT_DIR / "_全店商品属性.csv"
    with out2.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["商品ID","标题","一口价","商品编码","产品属性"])
        w.writerows(attr_rows)
    print(f"→ 属性台账：{out2}（{len(attr_rows)} 行）")

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
            try:
                r = process(tab, iid)
            except Exception as e:
                print(f"  ✗ {iid} 异常: {str(e)[:120]}（继续下一个）")
                r = {"id": iid, "ok": False}
            results.append(r)
            if r.get("ok") and not r.get("skipped") and idx < len(ids) - 1:
                human_sleep(3, 6)

        ok = [r for r in results if r.get("ok")]
        skipped = [r for r in results if r.get("skipped")]
        print(f"\n===== 完成: {len(ok)}/{len(results)} 个商品成功（其中 {len(skipped)} 个续跑跳过） =====")
        if MODE in ("scan", "all") and all_now:
            (STATE_DIR / "seen_items.json").write_text(json.dumps(sorted(set(all_now))))
        build_manifest()
        summary = {"mode": MODE, "total": len(results), "ok": len(ok), "skipped": len(skipped),
                   "items": [{"id": r["id"], "title": r.get("title"), "counts": r.get("counts")} for r in ok if not r.get("skipped")]}
        (STATE_DIR / "last_run.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
        print(f"输出目录: {OUT_DIR}")
    finally:
        tab.close()   # 跑完关掉自己开的标签

if __name__ == "__main__":
    main()
