#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
淘宝/天猫自家店铺商品图片批量下载器（卖家后台路线，零反爬）—— 主程序

在 browser-harness 环境运行（连已登录千牛的真 Chrome，读卖家后台发布页 window.Json）。
不碰买家详情页、不刷新触发 baxia、不裸打接口；图片从 img.alicdn.com 公共 CDN 直下。

三种模式（用环境变量 MODE 选）：
  MODE=ids   ITEM_IDS=逗号/空格分隔   —— 只下这些商品
  MODE=all                            —— 遍历全店所有在售商品全下
  MODE=scan                           —— 只下「上次跑之后新出现」的商品（给定时任务用）

通用环境变量：
  OUT_DIR     输出根目录（默认 ~/Downloads/淘宝店铺图片）
  STATE_DIR   扫新品的状态记录目录（默认 脚本同目录/state）
运行：  MODE=all browser-harness < shop_images.py
"""
import os, re, json, time, pathlib, urllib.request

OUT_DIR   = pathlib.Path(os.path.expanduser(os.environ.get("OUT_DIR", "~/Downloads/淘宝店铺图片")))
# 注意：经 `browser-harness < 本脚本` 时 __file__ 指向 browser-harness 自身，不可用来定位 state。
# 固定到项目目录；.command 也会显式传 STATE_DIR 兜底。
STATE_DIR = pathlib.Path(os.path.expanduser(os.environ.get("STATE_DIR", "~/work/taobao-shop-images/state")))
MODE      = os.environ.get("MODE", "ids").strip().lower()

LIST_URL  = "https://myseller.taobao.com/home.htm/SellManage/itemManage?current={cur}&pageSize=50"
EDIT_URL  = "https://item.upload.taobao.com/sell/v2/publish.htm?itemId={iid}&fromAIPublish=true"

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
    return ('.'+m.group(1).lower()) if m else default

def download(url, dest):
    try:
        req = urllib.request.Request(orig_url(url), headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
            "Referer": "https://www.taobao.com/"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        if not data or len(data) < 200: return False, "空/过小"
        dest.write_bytes(data); return True, len(data)
    except Exception as e:
        return False, str(e)[:80]

# ---------------- 全店遍历 itemId ----------------
def fetch_all_ids(max_pages=int(os.environ.get("MAX_PAGES", "80"))):
    print("→ 遍历商品管理列表，收集全部 itemId …")
    all_ids, seen, empty_streak = [], set(), 0
    for cur in range(1, max_pages+1):
        new_tab(LIST_URL.format(cur=cur))
        wait_for_load(); human_sleep(4, 7)
        ids = []
        for _ in range(3):
            ids = js(GRAB_IDS_JS) or []
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
def process(item_id):
    print(f"\n===== 商品 {item_id} =====")
    new_tab(EDIT_URL.format(iid=item_id))
    wait_for_load(); human_sleep(5, 7)
    data = js(EXTRACT_JS)
    if not data or data.get('err'):
        human_sleep(4, 6); data = js(EXTRACT_JS)
    if not data or data.get('err'):
        print("  ✗ 提取失败，跳过（可能未登录/非本店商品）"); return {"id":item_id,"ok":False}
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
    return {"id":item_id,"ok":True,"title":title,"counts":counts,"sellerId":data.get('sellerId')}

# ---------------- 主流程 ----------------
def get_ids_for_mode():
    if MODE == "ids":
        env = os.environ.get("ITEM_IDS", "")
        ids = [x for x in re.split(r"[,\s]+", env) if x.strip().isdigit()]
        return ids, None
    # all / scan 都要先遍历全店
    ids = fetch_all_ids()
    return ids, ids

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"模式={MODE}  输出={OUT_DIR}")

    ids, all_now = get_ids_for_mode()
    if not ids:
        print("没有商品 ID 可下载。"); return

    state_file = None
    if MODE == "scan":
        # 用第一个商品探明 sellerId 命名 state 文件；先临时用通用名，跑完再按 sellerId 落定
        state_file = STATE_DIR / "seen_items.json"
        seen = set(json.loads(state_file.read_text())) if state_file.exists() else set()
        new_ids = [i for i in all_now if i not in seen]
        print(f"扫新品: 全店 {len(all_now)} 件，其中新出现 {len(new_ids)} 件")
        if not new_ids:
            print("没有新商品，结束。")
            # 仍更新快照（防止首次空跑后永远落不下）
            state_file.write_text(json.dumps(sorted(set(all_now))))
            return
        ids = new_ids

    print(f"\n开始下载 {len(ids)} 个商品 …")
    results = []
    for idx, iid in enumerate(ids):
        results.append(process(iid))
        if idx < len(ids)-1: human_sleep(4, 8)

    ok = [r for r in results if r.get("ok")]
    print(f"\n===== 完成: {len(ok)}/{len(results)} 个商品成功 =====")
    if MODE in ("scan", "all") and all_now:
        # 更新快照为「当前全店」，下次只下新增
        (STATE_DIR / "seen_items.json").write_text(json.dumps(sorted(set(all_now))))
    # 给定时任务留一份简报
    summary = {"mode": MODE, "total": len(results), "ok": len(ok),
               "items": [{"id": r["id"], "title": r.get("title"), "counts": r.get("counts")} for r in ok]}
    (STATE_DIR / "last_run.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"输出目录: {OUT_DIR}")

main()
