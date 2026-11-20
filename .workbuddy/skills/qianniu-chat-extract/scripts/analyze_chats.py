#!/usr/bin/env python3
"""客服聊天数据分析（方向 4 快捷短语 + 方向 1 问题主题）。

输入：~/千牛产出/ 下的 merged JSON（未脱敏，但报告里只输出话术不输出客户ID）
输出：08-公司知识库/客服话术/分析报告/ 下的 md

用法：
    analyze_chats.py --date 2026-05-15 --shop bsn-tmall          # 单日
    analyze_chats.py --since 2026-05-09 --shop bsn-tmall         # 多日
    analyze_chats.py --since 2026-05-09                          # 多日全部店

后续扩展（方向 2/3/5）见 OPTIMIZATION_BACKLOG.md。
"""
import argparse
import json
from pathlib import Path
from collections import Counter, defaultdict

INPUT_DIR = Path.home() / "千牛产出"
OUTPUT_DIR = Path.home() / "/Users/mac/obsidian/祥子AI/08-公司知识库/客服话术/分析报告"

# 问题主题分类关键词（按祥新业务调过）
TOPIC_KEYWORDS = {
    "型号对比": ["xm", "v7s", "v6", "v6s", "x3", "pro", "区别", "差别", "哪个", "推荐", "比较", "选哪", "选什么"],
    "价格优惠": ["价格", "多少钱", "便宜", "优惠", "贵", "降价", "折扣", "618", "活动", "券", "返", "减", "砍"],
    "功能咨询": ["测距", "测速", "风速", "红绿", "屏幕", "充电", "防水", "环境因素", "记忆", "精准", "距离", "码数", "震动"],
    "物流发货": ["发货", "快递", "几天", "运费", "包邮", "什么时候到", "配送", "物流", "顺丰", "京东快递"],
    "售后保修": ["退", "换", "保修", "质保", "坏了", "售后", "维修", "破损", "故障", "包修", "保固"],
    "配件耗材": ["电池", "皮套", "配件", "充电器", "说明书", "保护套", "镜片"],
    "使用方法": ["怎么用", "如何", "教程", "说明", "操作", "新手", "调", "设置", "校准"],
    "礼品发票": ["发票", "礼盒", "包装", "送", "礼物", "赠"],
}


def is_cs(sender):
    return bool(sender) and (':' in sender or ':' in sender)


def is_buyer(sender, shop_name):
    if not sender or is_cs(sender):
        return False
    if shop_name and (sender == shop_name or shop_name in sender or sender in shop_name):
        return False
    return True


def is_meaningful_phrase(content):
    if not content or len(content) < 4 or len(content) > 200:
        return False
    if content.startswith(('http://', 'https://')):
        return False
    if '人工客服' in content and '将为您服务' in content:
        return False
    if content.startswith('由 ') and '转交给' in content:
        return False
    return True


def load_sessions(since=None, until=None, shop='all'):
    sessions = []
    files_used = []
    for f in sorted(INPUT_DIR.glob("qianniu_chats_*.json")):
        if "_raw" in f.name:
            continue
        parts = f.stem.split('_')
        if len(parts) < 4:
            continue
        date = parts[2]
        slug = '_'.join(parts[3:])
        if since and date < since:
            continue
        if until and date > until:
            continue
        if shop != 'all' and slug != shop:
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  ! 跳过 {f.name}: {e}")
            continue
        files_used.append(f.name)
        for s in data:
            s['_source_date'] = date
            s['_source_slug'] = slug
            sessions.append(s)
    return sessions, files_used


def analyze_cs_phrases(sessions, top_n=30):
    """方向 4：客服快捷短语统计"""
    phrases = Counter()
    cs_phrase_map = defaultdict(Counter)
    for s in sessions:
        for m in s.get('messages', []):
            if not is_cs(m.get('sender')):
                continue
            content = (m.get('content') or '').strip()
            if not is_meaningful_phrase(content):
                continue
            phrases[content] += 1
            # 提取客服名（"店名:客服名"）
            sender = m['sender']
            cs_name = sender.rsplit(':', 1)[-1] if ':' in sender else sender.rsplit(':', 1)[-1]
            cs_phrase_map[cs_name][content] += 1
    return phrases.most_common(top_n), cs_phrase_map


def analyze_buyer_questions(sessions):
    """方向 1：买家问题分主题"""
    bucket = defaultdict(list)
    uncategorized = []
    for s in sessions:
        shop_name = s.get('shop', '')
        for m in s.get('messages', []):
            if not is_buyer(m.get('sender'), shop_name):
                continue
            content = (m.get('content') or '').strip()
            if len(content) < 3 or len(content) > 100:
                continue
            if content.startswith('由 ') or '人工客服' in content:
                continue
            if content.startswith(('http://', 'https://')):
                continue
            content_lower = content.lower()
            matched = False
            for topic, kws in TOPIC_KEYWORDS.items():
                if any(kw.lower() in content_lower for kw in kws):
                    bucket[topic].append(content)
                    matched = True
                    break
            if not matched:
                # 只把"看起来是问句的"加入未归类（避免短语污染）
                is_question = any(c in content for c in '?？吗呢') or \
                              any(content.startswith(k) for k in ['怎么', '什么', '为什么', '能不能', '可以', '是否', '请问'])
                if is_question:
                    uncategorized.append(content)
    return bucket, uncategorized


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', help='单日 YYYY-MM-DD')
    ap.add_argument('--since', help='起始日期 YYYY-MM-DD')
    ap.add_argument('--until', help='截止日期 YYYY-MM-DD（默认今天）')
    ap.add_argument('--shop', default='all', help='店铺 slug 或 all')
    args = ap.parse_args()

    if args.date:
        since = until = args.date
    else:
        since = args.since
        until = args.until or '9999-12-31'
    if not since:
        raise SystemExit("必须提供 --date 或 --since")

    sessions, files = load_sessions(since, until, args.shop)
    print(f"加载 {len(sessions)} 个会话（来自 {len(files)} 个文件）")
    if not sessions:
        print("无数据，退出")
        return

    top_phrases, cs_phrase_map = analyze_cs_phrases(sessions)
    questions_by_topic, uncategorized = analyze_buyer_questions(sessions)

    period = since if since == until else f"{since}_{until}"
    shop_label = args.shop if args.shop != 'all' else '全部店铺'
    md = [
        f"# 客服聊天分析报告 {period}",
        "",
        f"- 时间范围：{since}" + (f" → {until}" if since != until else ""),
        f"- 店铺：{shop_label}",
        f"- 会话总数：**{len(sessions)}**",
        f"- 数据文件：{len(files)} 份",
        "",
        "---",
        "",
        f"## 一、客服快捷短语 TOP {len(top_phrases)}（方向 4 · 出现 ≥ 1 次的高频回复）",
        "",
        "> 直接抄进千牛快捷回复模板。出现 ≥ 2 次的是真正可固化的短语。",
        "",
        "| # | 次数 | 话术 |",
        "|---|---|---|",
    ]
    for i, (phrase, count) in enumerate(top_phrases, 1):
        safe = phrase.replace('|', '\\|').replace('\n', ' ')
        if len(safe) > 100:
            safe = safe[:100] + '...'
        md.append(f"| {i} | **{count}** | {safe} |")

    md.extend(["", "### 按客服拆分", ""])
    for cs, phrases in sorted(cs_phrase_map.items(), key=lambda x: -sum(x[1].values())):
        total = sum(phrases.values())
        unique = len(phrases)
        top3 = ' / '.join(f'"{p}"' for p, _ in phrases.most_common(3))
        md.append(f"- **{cs}**：消息 {total} 条 · 不同短语 {unique} 种 · TOP 3：{top3}")

    md.extend([
        "",
        "---",
        "",
        "## 二、买家问题分主题（方向 1 · 按关键词分桶）",
        "",
    ])
    for topic, qs in sorted(questions_by_topic.items(), key=lambda x: -len(x[1])):
        md.append(f"### {topic}（{len(qs)} 条）")
        md.append("")
        for q in qs[:8]:
            md.append(f"- {q}")
        if len(qs) > 8:
            md.append(f"- _（还有 {len(qs)-8} 条）_")
        md.append("")

    if uncategorized:
        md.extend([
            f"### ⚠️ 未归类问句（{len(uncategorized)} 条 · 可能是 SOP 缺口）",
            "",
            "> 这些是关键词没匹配上的买家问句。多半是新的问题方向，值得人工看一眼是否要扩 SOP。",
            "",
        ])
        for q in uncategorized[:15]:
            md.append(f"- {q}")
        if len(uncategorized) > 15:
            md.append(f"- _（还有 {len(uncategorized)-15} 条）_")
        md.append("")

    md.extend([
        "---",
        "",
        "## 数据规模 & 后续",
        "",
        f"当前样本：**{len(sessions)} 个会话**。",
        "",
        "门槛参考：",
        "- 方向 4（快捷短语）：≥ 50 会话/店 才有信噪比",
        "- 方向 1（问题主题）：≥ 30 会话 才能稳定看到 TOP",
        "- 方向 2/3/5：暂未开发，见 [OPTIMIZATION_BACKLOG.md](../../../07-AI协作/skills/qianniu-chat-extract/OPTIMIZATION_BACKLOG.md)",
        "",
        f"_本报告由 analyze_chats.py 自动生成。_",
    ])

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    shop_part = args.shop if args.shop != 'all' else 'all'
    fname = f"analysis_{period}_{shop_part}.md"
    out_path = OUTPUT_DIR / fname
    out_path.write_text('\n'.join(md), encoding='utf-8')
    print(f"✓ 报告: {out_path}")


if __name__ == "__main__":
    main()
