#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
淘宝竞品价格监控 v2.0（browser-harness 版，已弃用 selenium-stealth）

流程：
  1) 逐型号搜索淘宝销量榜（scrape_search.py，走真 Chrome 防反爬）
  2) 按型号分组，丢弃接近中位数的"正常价"，只留异常价
  3) 异常价写入飞书多维表格「Garmin竞品」

用法：
    python3 monitor.py --port 9224 --limit 15           # 全部型号
    python3 monitor.py --port 9224 --only S70           # 只跑一个型号
    python3 monitor.py --dry-run                         # 抓+过滤但不写飞书

依赖：browser-harness + 已登录淘宝的 Chrome（默认 9224，与 jingpin-shangxin 共用）；lark-cli（写 Base）。
"""
import argparse
import json
import os
import random
import re
import shutil
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scrape_search  # noqa: E402

# ── 配置区 ────────────────────────────────────────────────────────
KEYWORDS = {
    "S70": "Garmin S70 高尔夫",
    "G82": "Garmin G82 高尔夫",
    "R50": "Garmin R50 高尔夫",
    "Z30": "Garmin Z30 高尔夫",
}
TOP_N = 15
NORMAL_PRICE_TOLERANCE = 0.03   # 偏离型号中位数 ≤ 3% 视为正常价 → 丢弃
MIN_RECORDS_FOR_FILTER = 3      # 该型号有效样本 < 3 不做过滤

BITABLE_TOKEN = "KkWWbX5goaoMKrsDcOvcb2Emn2d"
TABLE_ID = "tbl5JSiMcOVd2eMa"
COL = {
    "model": "型号", "rank": "排名", "title": "商品标题", "price": "价格",
    "final_price": "到手价", "sales": "月销量", "shop": "店铺名",
    "link": "商品链接", "time": "采集时间",
}


def clean_sales(raw: str) -> int:
    """'400+人付款' → 400; '1.2万+' → 12000"""
    raw = raw or ""
    if "万" in raw:
        m = re.search(r"([\d.]+)万", raw)
        if m:
            return int(float(m.group(1)) * 10000)
    nums = re.findall(r"\d+", raw.replace(",", ""))
    return int(nums[0]) if nums else 0


def _parse_price(raw):
    if raw is None:
        return None
    s = str(raw).replace(",", "").replace("¥", "").strip()
    if not s:
        return None
    try:
        v = float(s)
        return v if v > 0 else None
    except ValueError:
        return None


def filter_abnormal_prices(records):
    """按型号分组，丢弃接近中位数的"正常价"，保留异常价。"""
    by_model = defaultdict(list)
    for r in records:
        by_model[r["model"]].append(r)
    abnormal, stats = [], {}
    for model, items in by_model.items():
        prices = [p for p in (_parse_price(r["final_price"]) for r in items) if p]
        if len(prices) < MIN_RECORDS_FOR_FILTER:
            abnormal.extend(items)
            stats[model] = {"median": None, "kept": len(items), "dropped": 0,
                            "total": len(items), "note": f"样本<{MIN_RECORDS_FOR_FILTER}，全保留"}
            continue
        median = statistics.median(prices)
        kept = dropped = 0
        for r in items:
            p = _parse_price(r["final_price"])
            if p is None:
                abnormal.append(r); kept += 1; continue
            if abs(p - median) / median <= NORMAL_PRICE_TOLERANCE:
                dropped += 1
            else:
                abnormal.append(r); kept += 1
        stats[model] = {"median": median, "kept": kept, "dropped": dropped,
                        "total": len(items), "note": ""}
    return abnormal, stats


def write_to_feishu(records):
    if not shutil.which("lark-cli"):
        print("[跳过] 未找到 lark-cli，无法写入飞书")
        return
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    field_order = [COL[k] for k in ("model", "rank", "title", "price",
                                    "final_price", "sales", "shop", "link", "time")]
    rows = [[r["model"], r["rank"], r["title"], r["price"], r["final_price"],
             r["sales"], r["shop"], r["link"] or None, now_str] for r in records]
    BATCH = 200
    for i in range(0, len(rows), BATCH):
        batch = rows[i: i + BATCH]
        payload = {"fields": field_order, "rows": batch}
        cmd = ["lark-cli", "base", "+record-batch-create",
               "--base-token", BITABLE_TOKEN, "--table-id", TABLE_ID,
               "--json", json.dumps(payload, ensure_ascii=False)]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        out = (proc.stdout or proc.stderr or "").strip()
        print(f"  [飞书] {'✅ 写入 %d 条' % len(batch) if proc.returncode == 0 else '❌ 失败: ' + out[:400]}")


def search_one(model, keyword, port):
    """抓单型号 → 规范成 monitor 内部记录格式。"""
    data = scrape_search.scrape(keyword, port)
    if data.get("risk_control"):
        return None, "风控(需在9224 Chrome手动过验证)"
    if data.get("login_wall"):
        return None, "登录墙(需重登淘宝)"
    out = []
    for rank, it in enumerate(data.get("items", [])[:TOP_N], 1):
        out.append({
            "model": model, "rank": rank,
            "title": it.get("title", ""),
            "price": it.get("price", ""),
            "final_price": it.get("finalPrice") or it.get("price", ""),
            "sales": clean_sales(it.get("sales", "")),
            "shop": it.get("shop", ""),
            "link": it.get("link", ""),
        })
    return out, f"{len(out)} 条"


def main():
    ap = argparse.ArgumentParser(description="淘宝竞品价格监控（browser-harness 版）")
    ap.add_argument("--port", type=int, default=int(os.environ.get("BH_TB_PORT", 9224)))
    ap.add_argument("--limit", type=int, default=TOP_N)
    ap.add_argument("--only", help="只跑某个型号标签，如 S70")
    ap.add_argument("--dry-run", action="store_true", help="抓+过滤但不写飞书")
    args = ap.parse_args()

    targets = {args.only: KEYWORDS[args.only]} if args.only and args.only in KEYWORDS else KEYWORDS

    print("=" * 58)
    print(f"  淘宝竞品价格监控  {' / '.join(targets)}  （端口 {args.port}）")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 58)

    all_results, problems = [], []
    keys = list(targets)
    for idx, model in enumerate(keys):
        kw = targets[model]
        print(f"\n[{model}] 搜索: {kw}")
        try:
            res, status = search_one(model, kw, args.port)
        except Exception as e:
            res, status = None, f"抓取异常:{e}"
        print(f"  → {status}")
        if res is None:
            problems.append(f"{model}: {status}")
        else:
            all_results.extend(res)
        if idx != len(keys) - 1:
            wait = random.uniform(8, 18)   # 关键词间随机间隔，拉开频率防风控
            print(f"  等待 {wait:.0f}s 继续...")
            time.sleep(wait)

    print(f"\n合计抓取 {len(all_results)} 条，开始按型号过滤正常价...")
    abnormal, stats = filter_abnormal_prices(all_results)
    print("\n[过滤结果·按型号]")
    for model, s in stats.items():
        if s["note"]:
            print(f"  {model:5s}  {s['note']}  → 保留 {s['kept']} 条")
        else:
            print(f"  {model:5s}  中位价¥{s['median']:.0f}  "
                  f"异常 {s['kept']} 条 / 正常 {s['dropped']} 条已忽略  (共{s['total']})")

    total_kept = sum(s["kept"] for s in stats.values())
    total_dropped = sum(s["dropped"] for s in stats.values())
    print(f"\n合计：异常 {total_kept} 条 / 正常 {total_dropped} 条忽略")

    if abnormal and not args.dry_run:
        write_to_feishu(abnormal)
    elif args.dry_run:
        print("  [dry-run] 不写飞书。异常价预览：")
        for r in abnormal[:20]:
            print(f"    [{r['model']}] ¥{r['final_price']}  销量{r['sales']}  [{r['shop'][:12]}] {r['title'][:24]}")
    else:
        print("  [飞书] 今日全部价格均正常，未写入新记录")

    if problems:
        print("\n⚠️ 异常型号（需处理）：")
        for p in problems:
            print(f"  - {p}")
    print("\n✅ 完成")


if __name__ == "__main__":
    main()
