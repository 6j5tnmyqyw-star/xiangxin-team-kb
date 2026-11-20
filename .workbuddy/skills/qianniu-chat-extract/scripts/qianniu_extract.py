"""
千牛聊天明细抓取脚本（多店铺版 · macOS）

依赖：Playwright (pip3 install playwright; python3 -m playwright install chromium)
配置：~/千牛产出/shops.json 维护店铺列表
前置：Chrome 已通过 scripts/start_chrome.sh 启动并登录对应店铺

使用：
    python3 qianniu_extract.py                         # 跑所有店，默认昨日
    python3 qianniu_extract.py --shop xinshui          # 只跑祥新网商
    python3 qianniu_extract.py --shop taylormade-bj   # 只跑 Taylormade
    python3 qianniu_extract.py --date 2026-05-10      # 指定日期

产出（每店一份，落在 ~/千牛产出/）：
    qianniu_chats_<日期>_<slug>.json
    qianniu_chats_<日期>_<slug>.md
"""
from playwright.sync_api import sync_playwright
from pathlib import Path
import json, argparse, re, hashlib, random
from datetime import datetime, timedelta


def _jms(ms, frac=0.35):
    """随机化 playwright wait_for_timeout 的毫秒数，打散固定节奏防 baxia 风控。"""
    return int(ms * (1 + random.uniform(-frac, frac)))

OUT = Path.home() / "千牛产出"
OUT.mkdir(exist_ok=True)
CONFIG_PATH = OUT / "shops.json"
PERF_DETAIL_URL = "https://sycm.taobao.com/qos/service/frame/performance/detail/new#/detail"

# 归档到知识库的根目录（祥子AI Vault 下的公司知识库）
KB_ROOT = Path.home() / "/Users/mac/obsidian/祥子AI/08-公司知识库/客服话术/原始记录"


def load_shops():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))["shops"]


def mark_body_chat_links(page):
    # Robust: collect all '聊天明细' spans/anchors except those inside <thead>
    # (some pages have an open date-picker that adds extra tbody elements, so
    # we can't rely on the first tbody being the data table).
    return page.evaluate("""
        () => {
            const all = Array.from(document.querySelectorAll('a,span,button'))
                .filter(el => (el.innerText||'').trim() === '聊天明细')
                .filter(el => !el.closest('thead'))
                .filter(el => el.closest('tr'));  // must be inside a row
            all.forEach((el, i) => el.setAttribute('data-chat-idx', String(i)));
            return all.length;
        }
    """)


def get_row_meta(page, idx):
    return page.evaluate(f"""
        () => {{
            const link = document.querySelector("[data-chat-idx='{idx}']");
            if (!link) return null;
            const tr = link.closest('tr');
            if (!tr) return null;
            return Array.from(tr.querySelectorAll('td')).map(td => (td.innerText||'').trim());
        }}
    """)


def get_shop_name_on_page(page):
    """从页面顶部读出当前登录的店铺名（用于校验）。"""
    return page.evaluate("""
        () => {
            const els = Array.from(document.querySelectorAll('[class*=shop], [class*=Shop], [class*=name]'));
            for (const el of els) {
                const t = (el.innerText||'').trim();
                if (t && t.length < 30 && (t.includes('网商') || t.includes('精品店') || t.includes('店') || t.includes('Taylor'))) {
                    return t;
                }
            }
            return null;
        }
    """)


def extract_modal_messages(page):
    last = -1
    for _ in range(50):
        cur = page.evaluate("""
            () => {
                const modal = document.querySelector('.ant-modal-wrap');
                if (!modal) return -1;
                const scroller = modal.querySelector('[class*=ChatLog_scroll], [class*=ChatLog_container]')
                              || modal.querySelector('.ant-modal-body');
                if (scroller) scroller.scrollTop = scroller.scrollHeight;
                return modal.querySelectorAll('[class*=ChatLog_row]').length;
            }
        """)
        page.wait_for_timeout(_jms(350))
        if cur == last:
            break
        last = cur
    page.evaluate("""
        () => {
            const modal = document.querySelector('.ant-modal-wrap');
            if (!modal) return;
            const sc = modal.querySelector('[class*=ChatLog_scroll], [class*=ChatLog_container]')
                    || modal.querySelector('.ant-modal-body');
            if (sc) sc.scrollTop = 0;
        }
    """)
    page.wait_for_timeout(_jms(400))
    harvested = {}
    for _ in range(60):
        rows = page.evaluate("""
            () => {
                const modal = document.querySelector('.ant-modal-wrap');
                if (!modal) return [];
                const rs = modal.querySelectorAll('[class*=ChatLog_row]');
                const out = [];
                rs.forEach(r => {
                    const name = r.querySelector('[class*=ChatLog_name]');
                    const chat = r.querySelector('[class*=ChatLog_chat]');
                    const time = r.querySelector('[class*=ChatLog_time]');
                    out.push({
                        sender: (name && name.innerText || '').trim(),
                        content: (chat && chat.innerText || '').trim(),
                        time: (time && time.innerText || '').trim(),
                    });
                });
                return out;
            }
        """)
        for r in rows:
            # 用 (time, content) 做去重 key，sender 非空覆盖 sender 空（页面会重复渲染同一条消息）
            key = (r['time'], r['content'])
            if key not in harvested or (r['sender'] and not harvested[key].get('sender')):
                harvested[key] = r
        more = page.evaluate("""
            () => {
                const modal = document.querySelector('.ant-modal-wrap');
                if (!modal) return false;
                const sc = modal.querySelector('[class*=ChatLog_scroll], [class*=ChatLog_container]')
                        || modal.querySelector('.ant-modal-body');
                if (!sc) return false;
                const before = sc.scrollTop;
                sc.scrollTop = Math.min(sc.scrollHeight, sc.scrollTop + sc.clientHeight * 0.8);
                return sc.scrollTop > before + 5;
            }
        """)
        page.wait_for_timeout(_jms(250))
        if not more:
            break
    final = page.evaluate("""
        () => {
            const modal = document.querySelector('.ant-modal-wrap');
            if (!modal) return {meta:'', rows:[]};
            const meta = (modal.querySelector('[class*=ChatLog_meta]') || modal).innerText.split('\\n').slice(0,6).join(' | ');
            const rs = modal.querySelectorAll('[class*=ChatLog_row]');
            const out = [];
            rs.forEach(r => {
                const name = r.querySelector('[class*=ChatLog_name]');
                const chat = r.querySelector('[class*=ChatLog_chat]');
                const time = r.querySelector('[class*=ChatLog_time]');
                out.push({
                    sender: (name && name.innerText || '').trim(),
                    content: (chat && chat.innerText || '').trim(),
                    time: (time && time.innerText || '').trim(),
                });
            });
            return {meta, rows: out};
        }
    """)
    for r in final['rows']:
        key = (r['time'], r['content'])
        if key not in harvested or (r['sender'] and not harvested[key].get('sender')):
            harvested[key] = r
    # 过滤掉 time 不是时间戳的行（如 modal header 里的 "聊天时间" 等 label 文本）
    ts_re = re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}')
    items = [v for v in harvested.values() if v.get('time') and ts_re.match(v['time'])]
    items.sort(key=lambda x: x.get('time') or '')
    return {'meta': final['meta'], 'messages': items}


def close_modal(page):
    page.keyboard.press("Escape")
    page.wait_for_timeout(_jms(300))
    page.evaluate("""
        () => {
            const x = document.querySelector('.ant-modal-wrap .ant-modal-close, .ant-modal-close-x');
            if (x) x.click();
        }
    """)
    page.wait_for_timeout(_jms(400))


def switch_to_all_tab(page):
    """点击二级 Tab '旺旺咨询明细'（全量），避免被'有效接待明细'过滤掉真实买家咨询。"""
    clicked = page.evaluate("""
        () => {
            const tab = Array.from(document.querySelectorAll('.ant-tabs-tab-btn, .ant-tabs-tab'))
                .find(el => (el.innerText || '').trim() === '旺旺咨询明细');
            if (!tab) return 'tab-not-found';
            if (tab.closest('.ant-tabs-tab-active')) return 'already-active';
            tab.click();
            return 'clicked';
        }
    """)
    page.wait_for_timeout(_jms(2000))
    print(f"    切换全量 tab (旺旺咨询明细): {clicked}")
    return clicked


def reset_to_first_page(page):
    """点 ant-pagination 的'第 1 页'，确保从头抓。"""
    clicked = page.evaluate("""
        () => {
            const first = document.querySelector('.ant-pagination-item-1');
            const active = document.querySelector('.ant-pagination-item-active');
            if (first && !first.classList.contains('ant-pagination-item-active')) {
                const a = first.querySelector('a') || first;
                a.click();
                return 'clicked-first';
            }
            return active ? 'already-on-' + (active.title || active.innerText || '?') : 'no-pagination';
        }
    """)
    page.wait_for_timeout(_jms(1500))
    print(f"    pagination reset: {clicked}")


def has_next_page(page):
    return page.evaluate("""
        () => {
            const next = document.querySelector('.ant-pagination-next');
            if (!next) return false;
            return !next.classList.contains('ant-pagination-disabled');
        }
    """)


def click_next_page(page):
    # 先记录当前第一行的内容用于判断翻页是否完成
    prev_first_row = page.evaluate("""
        () => {
            const trs = document.querySelectorAll('tbody tr');
            for (const tr of trs) {
                const tds = Array.from(tr.querySelectorAll('td')).map(td => (td.innerText||'').trim());
                if (tds.some(t => t.match(/\\d{4}-\\d{2}-\\d{2}/))) return tds.join('|');
            }
            return '';
        }
    """)
    page.evaluate("""
        () => {
            const sel = '.ant-pagination-next a, .ant-pagination-next button';
            const el = document.querySelector(sel);
            if (el) el.click();
        }
    """)
    # 等待第一行变化（新页加载完）
    try:
        page.wait_for_function(f"""
            () => {{
                const trs = document.querySelectorAll('tbody tr');
                for (const tr of trs) {{
                    const tds = Array.from(tr.querySelectorAll('td')).map(td => (td.innerText||'').trim());
                    if (tds.some(t => t.match(/\\d{{4}}-\\d{{2}}-\\d{{2}}/))) {{
                        if (tds.join('|') !== {prev_first_row!r}) return true;
                    }}
                }}
                return false;
            }}
        """, timeout=10000)
    except Exception:
        # 兜底等一下
        page.wait_for_timeout(_jms(2000))
    page.wait_for_timeout(_jms(500))


def identify_buyer_id(messages, shop_name):
    """从 messages 的 sender 字段反推买家旺旺 ID。
    客服 sender 形如 '祥新网商:月阳' / 'tb49997053:月阳' 含冒号；
    其他非空 sender 视为买家。返回出现最多的那个。"""
    from collections import Counter
    candidates = []
    for m in messages:
        s = (m.get('sender') or '').strip()
        if not s:
            continue
        if ':' in s or '：' in s:        # 客服格式 'shop:name'
            continue
        if shop_name and (s == shop_name or shop_name in s):
            continue
        candidates.append(s)
    if not candidates:
        return None
    return Counter(candidates).most_common(1)[0][0]


def merge_same_customer_chats(raw_chats):
    """把同一天同一买家的多个会话行合并为一条按时间排序的会话。
    跨客服交接（上下班换人）会出现在同一合并会话里。"""
    from collections import defaultdict
    groups = defaultdict(list)
    for c in raw_chats:
        buyer = identify_buyer_id(c['messages'], c['shop'])
        date = c['row_summary'][0] if c['row_summary'] else ''
        key = (date, buyer) if buyer else (date, f"_anon_{c['global_index']}")
        groups[key].append(c)

    merged = []
    for (date, buyer), group in groups.items():
        # 合并所有消息并去重
        seen = set()
        unique_msgs = []
        for g in group:
            for m in g['messages']:
                k = (m.get('time'), m.get('sender'), m.get('content'))
                if k in seen:
                    continue
                seen.add(k)
                unique_msgs.append(m)
        unique_msgs.sort(key=lambda x: x.get('time') or '')
        # 接待该会话的客服列表（按首次接入时间排序）
        cs_agents = []
        for g in sorted(group, key=lambda x: x['row_summary'][1] if len(x['row_summary']) > 1 else ''):
            cs = g['row_summary'][4] if len(g['row_summary']) > 4 else ''
            if cs and cs not in cs_agents:
                cs_agents.append(cs)
        merged.append({
            'shop': group[0]['shop'],
            'shop_slug': group[0]['shop_slug'],
            'date': date,
            'buyer_id': buyer or '(未识别)',
            'cs_agents': cs_agents,
            'merged_from_count': len(group),
            'original_row_indices': [g.get('global_index') for g in group],
            'row_summaries': [g['row_summary'] for g in group],
            'messages': unique_msgs,
            'message_count': len(unique_msgs),
            'start_time': unique_msgs[0]['time'] if unique_msgs else '',
            'end_time': unique_msgs[-1]['time'] if unique_msgs else '',
        })
    merged.sort(key=lambda x: x.get('start_time') or '')
    for i, m in enumerate(merged):
        m['session_index'] = i
    return merged


def attach_buyer_history(merged_sessions, shop_slug, current_date):
    """对每个买家，扫描历史 JSON 找出他/她过去和本店的会话，附加到 historical_sessions 字段。
    只放摘要（日期、客服、消息数、首末消息），完整聊天内容需要时再去对应文件取。"""
    from collections import defaultdict
    history_by_buyer = defaultdict(list)
    for f in sorted(OUT.glob(f"qianniu_chats_*_{shop_slug}.json")):
        if "_raw" in f.name or f"_{current_date}_" in f.name:
            continue
        # 文件名 qianniu_chats_<date>_<slug>.json
        parts = f.stem.split('_')
        if len(parts) < 4:
            continue
        date = parts[2]
        try:
            sessions = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        # 兼容旧格式（list of raw chats）和新格式（merged sessions with buyer_id）
        for sess in sessions:
            buyer = sess.get('buyer_id')
            if not buyer:
                # 旧格式：从 messages 反推
                buyer = identify_buyer_id(sess.get('messages', []), sess.get('shop', ''))
            if not buyer:
                continue
            msgs = sess.get('messages', [])
            first_buyer_msg = next((m['content'] for m in msgs
                                    if m.get('sender') and ':' not in m['sender']), '')
            history_by_buyer[buyer].append({
                'date': date,
                'cs_agents': sess.get('cs_agents') or [sess.get('row_summary', ['', '', '', '', ''])[4]],
                'message_count': len(msgs),
                'first_buyer_msg': first_buyer_msg[:80],
                'source_file': f.name,
            })
    for s in merged_sessions:
        b = s.get('buyer_id')
        if b and b in history_by_buyer:
            s['historical_sessions'] = sorted(history_by_buyer[b], key=lambda x: x['date'])
        else:
            s['historical_sessions'] = []


def write_markdown(out_path, target_date, shop_name, sessions):
    md = [f"# 千牛聊天明细 {target_date} — {shop_name}",
          f"共 {len(sessions)} 个买家会话（合并后）\n"]
    multi_cs = [s for s in sessions if len(s['cs_agents']) > 1]
    if multi_cs:
        md.append(f"> ⚠ {len(multi_cs)} 个会话存在客服交接（{', '.join('#'+str(s['session_index']+1) for s in multi_cs)}）\n")
    for s in sessions:
        md.append(f"\n## 会话 #{s['session_index']+1} — {s['buyer_id']}")
        md.append(f"- 客服接力链：{' → '.join(s['cs_agents']) if s['cs_agents'] else '(无)'}")
        md.append(f"- 起止：{s['start_time']} → {s['end_time']}")
        md.append(f"- 消息数：{s['message_count']}（来自 {s['merged_from_count']} 行原始记录）")
        hist = s.get('historical_sessions') or []
        if hist:
            md.append(f"- 🔁 **老客户**：之前曾接触 {len(hist)} 次")
            for h in hist:
                md.append(f"  - {h['date']} 客服 {','.join(h['cs_agents'])} {h['message_count']}条 "
                          f"首条：{h['first_buyer_msg']!r}")
        md.append("")
        md.append("| 时间 | 发送方 | 内容 |")
        md.append("|---|---|---|")
        for m in s['messages']:
            content = (m['content'] or '').replace('|', '\\|').replace('\n', ' ')
            md.append(f"| {m['time']} | {m['sender']} | {content} |")
    out_path.write_text("\n".join(md), encoding="utf-8")


# ============ 自动切日期（best-effort）============
def set_page_date_to_yesterday(page, date_str):
    """把生意参谋日期筛选切到 date_str（YYYY-MM-DD）。
    生意参谋用淘宝自家 OUI 组件（.oui-date-picker），需要先点"日"按钮弹日历，
    再点对应日期格子。兼容老版 antd 作为回退。失败返回 False，由调用方兜底。"""
    target_dt = date_str  # 'YYYY-MM-DD'
    year, month, day = target_dt.split('-')
    year_i, month_i, day_i = int(year), int(month), int(day)

    # 模式 1：OUI date picker（淘宝生意参谋当前实际用的）
    if page.locator('.oui-date-picker-particle-button button:has-text("日")').count():
        try:
            page.locator('.oui-date-picker-particle-button button:has-text("日")').first.click()
            page.wait_for_timeout(_jms(800))
            # 翻到目标年月。日历头部 6 个 .oui-dt-calendar-control 的固定布局：
            #   [0]=prev年(◀◀) [1]=prev月(◀) [2]=.year显示 [3]=.month显示 [4]=next月(▶) [5]=next年(▶▶)
            # 策略：先把"年"翻到位，再翻"月"。每步重读当前年月，最多 48 步防死循环。
            for _ in range(48):
                ym = page.evaluate("""() => {
                    const y = document.querySelector('.oui-dt-calendar-control.year')?.innerText.trim();
                    const m = document.querySelector('.oui-dt-calendar-control.month')?.innerText.trim();
                    return y && m ? [parseInt(y), parseInt(m)] : null;
                }""")
                if not ym: break
                cy, cm = ym
                if cy == year_i and cm == month_i: break
                if cy > year_i:      idx = 0   # prev 年
                elif cy < year_i:    idx = 5   # next 年
                elif cm > month_i:   idx = 1   # prev 月
                else:                idx = 4   # next 月
                ok = page.evaluate(f"""() => {{
                    const ctrls = document.querySelectorAll('.oui-dt-calendar-control');
                    const el = ctrls[{idx}];
                    if (!el || (el.className || '').includes('disabled')) return false;
                    el.click(); return true;
                }}""")
                if not ok:
                    return False
                page.wait_for_timeout(_jms(350))
            # 点击 day 格子（排除 previous-month / next-month / disabled）
            clicked = page.evaluate(f"""() => {{
                const cells = document.querySelectorAll('.oui-dt-calendar-content.day td');
                for (const td of cells) {{
                    if (td.innerText.trim() === '{day_i}' &&
                        !td.className.includes('previous-month') &&
                        !td.className.includes('next-month') &&
                        !td.className.includes('disabled')) {{
                        td.click();
                        return true;
                    }}
                }}
                return false;
            }}""")
            if clicked:
                page.wait_for_timeout(_jms(2000))
                print(f"    日期切换: oui-date-picker → {date_str}")
                return True
        except Exception as e:
            print(f"    OUI date picker 切换异常: {e}")

    # 模式 2/3：antd 老版（保留为回退）
    result = page.evaluate(f"""
        () => {{
            const target = {date_str!r};
            const pickerInputs = document.querySelectorAll('.ant-picker-input input');
            if (pickerInputs.length) {{
                for (const inp of pickerInputs) {{
                    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    setter.call(inp, target);
                    inp.dispatchEvent(new Event('input', {{bubbles: true}}));
                    inp.dispatchEvent(new Event('change', {{bubbles: true}}));
                }}
                return 'ant-picker-input set';
            }}
            const calInputs = document.querySelectorAll('.ant-calendar-picker-input');
            if (calInputs.length) {{
                for (const inp of calInputs) {{
                    inp.focus();
                    inp.value = target;
                    inp.dispatchEvent(new Event('input', {{bubbles: true}}));
                }}
                return 'ant-calendar set';
            }}
            return 'no-date-picker-found';
        }}
    """)
    print(f"    日期切换尝试: {result} (target={date_str})")
    if 'set' not in result:
        return False
    page.keyboard.press("Enter")
    page.wait_for_timeout(_jms(2500))
    return True


# ============ 脱敏 ============
PHONE_RE = re.compile(r'(?<!\d)(1[3-9]\d)\d{4}(\d{4})(?!\d)')
ORDER_RE = re.compile(r'(?<!\d)(\d{12,20})(?!\d)')
ID_CARD_RE = re.compile(r'(?<!\d)(\d{6})\d{8}(\d{4})(?!\d)')  # 18位身份证

# 中文地址关键词触发脱敏（保留省/市，详细地址替换）
ADDR_KEYWORDS = ['路', '街', '号', '楼', '室', '小区', '苑', '园', '巷', '弄', '栋', '单元']

def buyer_alias_for(buyer_id, shop_slug):
    """把买家ID稳定映射成 客户A/B/C...（按 hash 取字母，超过 26 个就 客户A1/B1）"""
    if not buyer_id or buyer_id == '(未识别)':
        return '(未识别)'
    h = hashlib.md5(f"{shop_slug}|{buyer_id}".encode()).hexdigest()
    n = int(h[:6], 16)
    letter = chr(ord('A') + n % 26)
    suffix = (n // 26) % 100
    return f"客户{letter}{suffix if suffix > 0 else ''}"


def desensitize_text(text):
    """脱敏单段文本：手机号/订单号/身份证/含地址关键词的长句"""
    if not text:
        return text
    t = text
    t = PHONE_RE.sub(lambda m: f"{m.group(1)}****{m.group(2)}", t)
    t = ID_CARD_RE.sub(lambda m: f"{m.group(1)}********{m.group(2)}", t)
    # 订单号脱敏要在手机号之后做，避免把手机号识别成订单号
    t = ORDER_RE.sub(lambda m: '*' * len(m.group(1)), t)
    # 含地址关键词的长句 → 截断关键词及之后的内容（保留前面 + ***）
    for kw in ADDR_KEYWORDS:
        if kw in t and len(t) > 12:
            idx = t.find(kw)
            if idx > 6:
                t = t[:max(idx-3, 0)] + '***[地址脱敏]'
                break
    return t


def desensitize_sessions(sessions, shop_slug):
    """对 sessions（merged 结果）做深拷贝脱敏，用于写入知识库的 md。
    保留：客服名、时间、消息结构、客服交接信息。
    脱敏：买家ID→客户A/B、消息内容里的手机/订单/地址。"""
    out = []
    alias_map = {}
    for s in sessions:
        buyer = s.get('buyer_id', '(未识别)')
        if buyer not in alias_map:
            alias_map[buyer] = buyer_alias_for(buyer, shop_slug)
        alias = alias_map[buyer]
        new_msgs = []
        for m in s.get('messages', []):
            sender = m.get('sender', '')
            # 如果 sender 是买家ID（不含冒号），替换成别名
            if sender and ':' not in sender and '：' not in sender:
                sender = alias
            new_msgs.append({
                'time': m.get('time', ''),
                'sender': sender,
                'content': desensitize_text(m.get('content', '')),
            })
        new_hist = []
        for h in s.get('historical_sessions', []):
            new_hist.append({
                **h,
                'first_buyer_msg': desensitize_text(h.get('first_buyer_msg', '')),
            })
        out.append({
            **s,
            'buyer_id': alias,
            'messages': new_msgs,
            'historical_sessions': new_hist,
        })
    return out


# ============ 归档到知识库 ============
def archive_to_kb(md_text, target_date, shop_slug, shop_name):
    """把脱敏后的 md 落到 08-公司知识库/客服话术/原始记录/YYYY-MM/。
    幂等：文件已存在就跳过。"""
    year_month = target_date[:7]  # 2026-05
    dest_dir = KB_ROOT / year_month
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"qianniu_chats_{target_date}_{shop_slug}.md"
    if dest.exists():
        print(f"  ↷ 知识库已存在，跳过: {dest.relative_to(KB_ROOT.parent.parent.parent)}")
        return dest, 'skipped'
    # 在文件头加一个 frontmatter 方便 Vault 查询
    header = f"""---
date: {target_date}
shop: {shop_name}
shop_slug: {shop_slug}
source: qianniu-chat-extract
desensitized: true
---

"""
    dest.write_text(header + md_text, encoding="utf-8")
    print(f"  ✓ 归档到知识库: {dest.relative_to(KB_ROOT.parent.parent.parent)}")
    return dest, 'created'


def extract_one_shop(shop, target_date, auto_date=False):
    """对单个店铺执行抓取。返回会话列表。
    auto_date=True 时尝试把页面日期切到 target_date（best-effort）。"""
    print(f"\n========== {shop['name']} (slug={shop['slug']}, port={shop['port']}) ==========")
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{shop['port']}")
        except Exception as e:
            print(f"  ✗ 无法连接端口 {shop['port']}：{e}")
            print(f"    请先运行：bash scripts/start_chrome.sh {shop['slug']}  然后在弹出的 Chrome 里登录该店账号")
            return None
        pages = browser.contexts[0].pages
        sycm = next((pg for pg in pages if "performance/detail" in pg.url), None)
        if not sycm:
            sycm = next((pg for pg in pages if "sycm.taobao.com" in pg.url), pages[-1])
            sycm.goto(PERF_DETAIL_URL, wait_until="domcontentloaded")
            sycm.wait_for_timeout(_jms(2500))
        sycm.bring_to_front()
        sycm.keyboard.press("Escape")
        sycm.wait_for_timeout(_jms(500))

        # 校验店铺名
        detected = get_shop_name_on_page(sycm)
        if detected:
            print(f"  页面识别到店铺：{detected}")
            if shop['name'] not in detected and detected not in shop['name']:
                print(f"  ⚠ 配置店铺名 [{shop['name']}] 与页面 [{detected}] 不一致，请确认登录账号")

        # 显式切到"旺旺咨询明细"全量 tab（避免上次留在"有效接待明细"导致漏抓）
        switch_to_all_tab(sycm)

        # 可选：自动把页面日期切到 target_date（best-effort，失败会沿用页面当前值）
        if auto_date:
            set_page_date_to_yesterday(sycm, target_date)

        # 重置分页到第 1 页（之前的 tab 可能停在中间页）
        reset_to_first_page(sycm)

        all_chats = []
        page_no = 1
        global_idx = 0
        while True:
            print(f"  --- Page {page_no} ---")
            try:
                sycm.wait_for_function("document.querySelectorAll('tbody tr').length > 0", timeout=15000)
            except Exception:
                print("    ! 表格未加载，跳过")
                break
            n = mark_body_chat_links(sycm)
            print(f"    body chat links: {n}")
            if n == 0:
                break
            for i in range(n):
                meta_cells = get_row_meta(sycm, i)
                print(f"    [{page_no}.{i}] {meta_cells}")
                sycm.locator(f"[data-chat-idx='{i}']").click(timeout=8000)
                try:
                    sycm.wait_for_function(
                        "document.querySelector('.ant-modal-wrap') && document.querySelectorAll('[class*=ChatLog_row]').length > 0",
                        timeout=15000,
                    )
                except Exception as e:
                    print(f"      ! modal wait failed: {e}")
                sycm.wait_for_timeout(_jms(500))
                payload = extract_modal_messages(sycm)
                all_chats.append({
                    'shop': shop['name'],
                    'shop_slug': shop['slug'],
                    'page': page_no,
                    'row_index': i,
                    'global_index': global_idx,
                    'row_summary': meta_cells,
                    'meta': payload['meta'],
                    'messages': payload['messages'],
                    'message_count': len(payload['messages']),
                })
                global_idx += 1
                print(f"      -> {len(payload['messages'])} messages")
                close_modal(sycm)
                mark_body_chat_links(sycm)
            if has_next_page(sycm):
                click_next_page(sycm)
                sycm.wait_for_timeout(_jms(1500))
                page_no += 1
            else:
                break
        return all_chats


def main():
    ap = argparse.ArgumentParser()
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    ap.add_argument("--date", default=yesterday, help="目标日期 YYYY-MM-DD（默认昨日）")
    ap.add_argument("--shop", default="all", help="店铺 slug；'all' 表示全部")
    ap.add_argument("--auto-date", action="store_true",
                    help="尝试自动把页面日期筛选切到 --date 指定的日期（best-effort）")
    ap.add_argument("--no-archive", action="store_true",
                    help="跳过归档到知识库（默认会把脱敏后的 md 拷到 08-公司知识库/客服话术/原始记录/）")
    args = ap.parse_args()
    print(f"Target date: {args.date}")
    shops = load_shops()
    if args.shop != "all":
        shops = [s for s in shops if s['slug'] == args.shop]
        if not shops:
            raise SystemExit(f"未找到 slug='{args.shop}' 的店铺")

    summary = []
    for shop in shops:
        chats = extract_one_shop(shop, args.date, auto_date=args.auto_date)
        if chats is None:
            summary.append({'shop': shop['name'], 'slug': shop['slug'], 'status': 'connect_failed'})
            continue
        # 合并同买家会话
        merged = merge_same_customer_chats(chats)
        handoffs = sum(1 for s in merged if len(s['cs_agents']) > 1)
        # 关联跨天历史
        attach_buyer_history(merged, shop['slug'], args.date)
        returning = sum(1 for s in merged if s.get('historical_sessions'))
        print(f"  原始 {len(chats)} 行 → 合并后 {len(merged)} 个买家会话"
              f"（含 {handoffs} 个客服交接, {returning} 个老客户）")
        # 保存：merged 为主，raw 为备份
        raw_path = OUT / f"qianniu_chats_{args.date}_{shop['slug']}_raw.json"
        json_path = OUT / f"qianniu_chats_{args.date}_{shop['slug']}.json"
        md_path = OUT / f"qianniu_chats_{args.date}_{shop['slug']}.md"
        raw_path.write_text(json.dumps(chats, ensure_ascii=False, indent=2), encoding="utf-8")
        json_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
        write_markdown(md_path, args.date, shop['name'], merged)
        print(f"  ✓ saved: {json_path.name} (merged), {md_path.name}, {raw_path.name} (raw backup)")

        # 归档脱敏版到知识库（幂等：已存在跳过）
        kb_status = 'skipped'
        kb_path = None
        if not args.no_archive:
            desensitized = desensitize_sessions(merged, shop['slug'])
            kb_tmp = OUT / f"_kb_tmp_{args.date}_{shop['slug']}.md"
            write_markdown(kb_tmp, args.date, shop['name'], desensitized)
            kb_md = kb_tmp.read_text(encoding="utf-8")
            kb_tmp.unlink()
            kb_path, kb_status = archive_to_kb(kb_md, args.date, shop['slug'], shop['name'])

        summary.append({'shop': shop['name'], 'slug': shop['slug'],
                        'raw_rows': len(chats), 'merged_sessions': len(merged), 'handoffs': handoffs,
                        'json': str(json_path), 'md': str(md_path),
                        'kb': str(kb_path) if kb_path else None, 'kb_status': kb_status})

    print("\n========== SUMMARY ==========")
    for s in summary:
        print(f"  {s['shop']:<25} {s}")


if __name__ == "__main__":
    main()
