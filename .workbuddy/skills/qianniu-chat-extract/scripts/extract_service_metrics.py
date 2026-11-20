#!/usr/bin/env python3
"""生意参谋"服务"模块快照：每天访问 6 个 dashboard 页面，截图整页 + 抓文本，归档到知识库。

抓什么：
    - 真实体验分（含体验问题订单率）
    - 服务核心监控
    - 店铺绩效
    - 客服绩效
    - 售后退款保障
    - 物流洞察

为什么：仅有聊天明细看不到"店铺整体"健康度。截图 + 文本快照让以后能：
    - 时间轴对比（5/15 vs 6/15 体验分变化）
    - AI 复盘异常波动
    - 出周报 / 月报

输出：08-公司知识库/服务报表/YYYY-MM/YYYY-MM-DD/<店铺名>/<页面名>.png + .txt

依赖：和 qianniu_extract.py 共用 shops.json，通过 CDP 连同一个 Chrome。
"""
import argparse
import json
from pathlib import Path
from datetime import datetime
from playwright.sync_api import sync_playwright

OUT = Path.home() / "千牛产出"
CONFIG_PATH = OUT / "shops.json"
KB_ROOT = Path.home() / "/Users/mac/obsidian/祥子AI/08-公司知识库/服务报表"
RAW_API_ROOT = KB_ROOT / "_raw_api"  # sycm API 原始 JSON 响应（永久保留，做环比/趋势）

# 要抓的 6 个 dashboard 页面（祥书 2026-05-16 给的清单）
SERVICE_PAGES = [
    ("真实体验分",   "https://sycm.taobao.com/qos/frame/cds/experience#/monitor"),
    ("服务核心监控", "https://sycm.taobao.com/qos/service/core_monitor/new#/monitor"),
    ("店铺绩效",     "https://sycm.taobao.com/qos/service/frame/shop/performance/new#/shop"),
    ("客服绩效",     "https://sycm.taobao.com/qos/service/frame/customer/performance/new#/user"),
    ("售后退款保障", "https://sycm.taobao.com/qos/service/after_sale/activist?activeTab=refundProtectionNew#/"),
    ("物流洞察",     "https://sycm.taobao.com/qos/frame/cds/logistics/qn"),
]


def load_shops():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["shops"]


def dismiss_popups(page):
    """关掉常见的公告/广告/引导弹窗，避免遮挡数据"""
    page.evaluate("""
        () => {
            document.querySelectorAll('.ant-modal-close, .ant-modal-close-x, [class*="close"]').forEach(el => {
                try { el.click(); } catch(e) {}
            });
            document.querySelectorAll('[class*="guide"], [class*="popup"], [class*="announce"]').forEach(el => {
                if (el.style) el.style.display = 'none';
            });
        }
    """)


def trigger_lazy_load(page):
    """滚到底再回顶，触发懒加载图表渲染"""
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(1500)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(800)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(500)


def is_data_api(url, content_type):
    """筛选出真正承载数据的 sycm API（过滤掉静态资源、tracker、html 等）"""
    if 'sycm.taobao.com' not in url:
        return False
    if not content_type or 'json' not in content_type.lower():
        return False
    # 排除明显非数据的
    skip_paths = ['/favicon', '/login', '/logout', '/static/', '/assets/', '.js?', '.css?']
    if any(s in url for s in skip_paths):
        return False
    return True


def extract_one_page(page, name, url, out_dir, raw_api_dir):
    print(f"  ▶ {name}  ({url[:80]}...)")

    # API 拦截：本页所有 sycm 数据 API 响应都保存
    api_responses = []
    def on_response(resp):
        try:
            ct = resp.headers.get('content-type', '')
            if not is_data_api(resp.url, ct):
                return
            body = resp.body()  # bytes
            api_responses.append({
                'url': resp.url,
                'method': resp.request.method,
                'status': resp.status,
                'request_post_data': resp.request.post_data,
                'body': body.decode('utf-8', errors='replace'),
            })
        except Exception:
            # 静默忽略 listener 错误（不要影响主流程）
            pass
    page.on('response', on_response)

    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        print(f"    ✗ goto failed: {e}")
        page.remove_listener('response', on_response)
        return False
    page.wait_for_timeout(3000)
    dismiss_popups(page)
    try:
        page.wait_for_function(
            """() => {
                const charts = document.querySelectorAll('canvas, svg.echarts-svg, [class*=echarts]').length;
                const rows = document.querySelectorAll('tbody tr').length;
                const kpi = document.querySelectorAll('[class*=Card] [class*=number], [class*=value], [class*=kpi]').length;
                return charts > 0 || rows > 3 || kpi > 2;
            }""",
            timeout=15000
        )
        print(f"    数据区已渲染")
    except Exception:
        print(f"    ⚠ 数据区等待超时")
    page.wait_for_timeout(2500)
    trigger_lazy_load(page)
    page.wait_for_timeout(2000)
    dismiss_popups(page)

    # 停止收集 API
    page.remove_listener('response', on_response)

    # 保存截图 + 文本（同前）
    png_path = out_dir / f"{name}.png"
    txt_path = out_dir / f"{name}.txt"
    try:
        page.screenshot(path=str(png_path), full_page=True)
        text = page.evaluate("document.body.innerText || ''")
        txt_path.write_text(text, encoding="utf-8")
    except Exception as e:
        print(f"    ✗ screenshot/text failed: {e}")
        return False

    # 保存 API 响应到 JSONL（每行一个响应，永久原始数据）
    api_count = 0
    api_size = 0
    if api_responses:
        raw_api_dir.mkdir(parents=True, exist_ok=True)
        jsonl_path = raw_api_dir / f"{name}.jsonl"
        with jsonl_path.open('w', encoding='utf-8') as f:
            for r in api_responses:
                line = json.dumps(r, ensure_ascii=False)
                f.write(line + '\n')
                api_count += 1
                api_size += len(line)

    print(f"    ✓ {png_path.stat().st_size//1024} KB png + {len(text)} chars txt + {api_count} APIs ({api_size//1024} KB jsonl)")
    return True


def extract_one_shop(shop, target_date):
    print(f"\n========== {shop['name']} (slug={shop['slug']}, port={shop['port']}) ==========")
    out_dir = KB_ROOT / target_date[:7] / target_date / shop['name']
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_api_dir = RAW_API_ROOT / target_date[:7] / target_date / shop['name']

    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{shop['port']}")
        except Exception as e:
            print(f"  ✗ CDP 连不上 {shop['port']}：{e}")
            return None
        ctx = browser.contexts[0]
        pages = ctx.pages
        sycm = next((p for p in pages if "sycm.taobao.com" in p.url), None)
        if not sycm:
            sycm = ctx.new_page()
        sycm.bring_to_front()
        sycm.set_viewport_size({"width": 1600, "height": 1000})

        results = []
        for name, url in SERVICE_PAGES:
            ok = extract_one_page(sycm, name, url, out_dir, raw_api_dir)
            results.append({'name': name, 'ok': ok})

    success = sum(1 for r in results if r['ok'])
    print(f"\n  归档目录: {out_dir}")
    print(f"  成功 {success}/{len(SERVICE_PAGES)} 个页面")
    return {'shop': shop['name'], 'slug': shop['slug'], 'date': target_date,
            'out_dir': str(out_dir), 'results': results}


def main():
    ap = argparse.ArgumentParser()
    today = datetime.now().strftime("%Y-%m-%d")
    ap.add_argument("--date", default=today, help="归档使用的日期标签 YYYY-MM-DD（默认今天）")
    ap.add_argument("--shop", default="all", help="店铺 slug 或 all")
    args = ap.parse_args()
    print(f"Snapshot date: {args.date}")

    shops = load_shops()
    if args.shop != "all":
        shops = [s for s in shops if s['slug'] == args.shop]
        if not shops:
            raise SystemExit(f"未找到 slug='{args.shop}'")

    summary = []
    for shop in shops:
        result = extract_one_shop(shop, args.date)
        if result:
            summary.append(result)

    print("\n========== SUMMARY ==========")
    for s in summary:
        ok = sum(1 for r in s['results'] if r['ok'])
        print(f"  {s['shop']:<25} {ok}/{len(s['results'])} 页 → {s['out_dir']}")


if __name__ == "__main__":
    main()
