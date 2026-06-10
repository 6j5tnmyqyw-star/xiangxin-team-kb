#!/usr/bin/env python3
"""客服快捷短语库累积器。

每次抓取后调用，扫客服话术，把新短语合并到短语库；已存在的更新计数和"最近出现"。

数据流：
    源数据  : ~/千牛产出/qianniu_chats_*.json (merged 后的)
    数据库  : ~/千牛产出/phrase_library.json (机器可读，源)
    渲染产物: 08-公司知识库/客服话术/快捷短语库.md (人读)

设计原则：
- 数据库是 source of truth，md 每次重新渲染
- 人工编辑应该在飞书 Base（未来）或数据库 JSON 里改"状态/备注"字段
- 不要在 md 里手改——会被覆盖

用法：
    update_phrase_library.py                  # 增量扫所有 JSON
    update_phrase_library.py --date 2026-05-15  # 只扫指定日期
    update_phrase_library.py --rebuild        # 重置数据库，从头扫
"""
import argparse
import json
import re
from pathlib import Path
from datetime import datetime

INPUT_DIR = Path.home() / "千牛产出"
DB_PATH = INPUT_DIR / "phrase_library.json"
KB_MD = Path.home() / "/Users/mac/obsidian/祥子AI/08-公司知识库/客服话术/快捷短语库.md"

# 场景分类关键词（按顺序匹配，第一个命中胜出）
SCENE_RULES = [
    ("开场欢迎", ["欢迎您光临", "我是您的专属销售", "为您服务", "在的", "您好亲", "请问您是有什么"]),
    ("售后保障", ["保修", "质保", "退换", "无理由", "运费险", "二次销售", "包修", "售后", "维修"]),
    ("价格优惠", ["价格", "优惠", "618", "活动", "原价", "原来卖", "便宜", "返", "券", "折扣", "降"]),
    ("产品对比", ["区别", "差别", "对比", "哪个", "更实用", "够用", "就够", "建议",
                "一般咱们", "最好用", "适合", "推荐", "职业球员", "业余玩家", "比较大", "比较小",
                "更小", "更轻", "更大", "更重", "更准", "v7s 是", "xm 是", "x3 是"]),
    ("功能介绍", ["测距", "测速", "风速", "记忆功能", "屏幕", "充电", "防水", "环境因素",
                "精准", "误差", "码数", "震动", "olEd", "oled", "可以用", "多一个", "多了一个"]),
    ("促单催单", ["拍下", "下单", "现在拍", "今天拍", "今晚", "结算", "付款", "现货",
                "库存", "马上", "尽快"]),
    ("物流发货", ["发货", "快递", "顺丰", "几天到", "包邮", "运费", "配送", "物流"]),
    ("通用回应", ["是的", "嗯", "好的", "没问题", "没有的亲", "可以的亲", "对的", "明白了"]),
]


def classify_scene(text):
    t = text.lower()
    for scene, kws in SCENE_RULES:
        for kw in kws:
            if kw.lower() in t:
                return scene
    return "其它"


def is_cs(sender):
    return bool(sender) and (':' in sender or ':' in sender)


def is_meaningful_phrase(content):
    if not content or len(content) < 4 or len(content) > 200:
        return False
    if content.startswith(('http://', 'https://')):
        return False
    if '人工客服' in content and '将为您服务' in content:
        return False
    if content.startswith('由 ') and '转交给' in content:
        return False
    # 含商品规格表的（淘宝详情粘贴）
    if content.count('|') >= 4 or '放大倍率:' in content:
        return False
    return True


def extract_cs_name(sender):
    """从 'shop:name' 提取客服名"""
    for sep in (':', ':'):
        if sep in sender:
            return sender.rsplit(sep, 1)[-1].strip()
    return sender.strip()


def load_db():
    if DB_PATH.exists():
        return json.loads(DB_PATH.read_text(encoding='utf-8'))
    return {"version": 1, "updated_at": "", "phrases": {}}


def save_db(db):
    db['updated_at'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    DB_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding='utf-8')


def load_sessions(date_filter=None):
    sessions = []
    files = []
    for f in sorted(INPUT_DIR.glob("qianniu_chats_*.json")):
        if "_raw" in f.name:
            continue
        parts = f.stem.split('_')
        if len(parts) < 4:
            continue
        date = parts[2]
        slug = '_'.join(parts[3:])
        if date_filter and date != date_filter:
            continue
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
        except Exception as e:
            print(f"  ! skip {f.name}: {e}")
            continue
        files.append(f.name)
        for s in data:
            s['_date'] = date
            s['_slug'] = slug
            sessions.append(s)
    return sessions, files


def merge_into_db(db, sessions):
    """累积新短语，更新已有短语的计数 + 最近出现"""
    new_count = 0
    updated_count = 0
    for s in sessions:
        date = s.get('_date', '')
        slug = s.get('_slug', '')
        for m in s.get('messages', []):
            sender = m.get('sender') or ''
            if not is_cs(sender):
                continue
            content = (m.get('content') or '').strip()
            if not is_meaningful_phrase(content):
                continue
            cs_name = extract_cs_name(sender)
            if content not in db['phrases']:
                db['phrases'][content] = {
                    "text": content,
                    "scene": classify_scene(content),
                    "cs_names": [cs_name],
                    "shop_slugs": [slug],
                    "count": 1,
                    "first_seen": date,
                    "last_seen": date,
                    "status": "待审核",  # 待审核 / 已采用 / 待优化 / 废弃
                    "notes": "",
                }
                new_count += 1
            else:
                p = db['phrases'][content]
                p['count'] += 1
                if date > p['last_seen']:
                    p['last_seen'] = date
                if date < p['first_seen']:
                    p['first_seen'] = date
                if cs_name not in p['cs_names']:
                    p['cs_names'].append(cs_name)
                if slug not in p['shop_slugs']:
                    p['shop_slugs'].append(slug)
                updated_count += 1
    return new_count, updated_count


def render_md(db):
    """把数据库渲染成人读 md"""
    phrases = list(db['phrases'].values())
    # 按场景分组
    by_scene = {}
    for p in phrases:
        by_scene.setdefault(p['scene'], []).append(p)

    # 场景显示顺序
    scene_order = ["开场欢迎", "产品对比", "功能介绍", "价格优惠", "售后保障",
                   "促单催单", "物流发货", "通用回应", "其它"]
    scene_order_idx = {s: i for i, s in enumerate(scene_order)}

    total = len(phrases)
    high_freq = sum(1 for p in phrases if p['count'] >= 2)
    approved = sum(1 for p in phrases if p['status'] == '已采用')

    lines = [
        "# 客服快捷短语库",
        "",
        f"> **本文档由 `update_phrase_library.py` 自动累积维护，不要手动改本地文件！**",
        f"> 想改【状态】或加【备注】请直接编辑 `~/千牛产出/phrase_library.json`，或在飞书版本里改（如有同步）。",
        "",
        f"- 收录短语：**{total}** 条 · 高频（≥2 次）：**{high_freq}** 条 · 已采用：**{approved}** 条",
        f"- 最后更新：**{db.get('updated_at', '?')}**",
        f"- 数据库文件：`~/千牛产出/phrase_library.json`",
        "",
        "## 使用方式",
        "",
        "1. **客服**：浏览本文档找适合的话术，复制到千牛快捷回复设置里",
        "2. **运营/管理**：评审【待审核】短语，标【已采用】/【待优化】/【废弃】",
        "3. **优秀话术**：出现频次 ≥ 3 的可以群推送给所有客服",
        "",
        "## 短语清单（按场景分类）",
        "",
    ]

    for scene in sorted(by_scene.keys(), key=lambda s: scene_order_idx.get(s, 999)):
        items = by_scene[scene]
        # 排序：已采用 > 高频 > 文本字典序
        items.sort(key=lambda p: (
            0 if p['status'] == '已采用' else 1,
            -p['count'],
            p['text']
        ))
        lines.append(f"### {scene}（{len(items)} 条）")
        lines.append("")
        for p in items:
            status_icon = {
                '已采用': '⭐',
                '待审核': '🔵',
                '待优化': '🟡',
                '废弃': '🗑️',
            }.get(p['status'], '🔵')
            text = p['text'].replace('\n', ' ')
            meta = f"_{','.join(p['cs_names'])}_ · {p['count']} 次 · {p['first_seen']}"
            if p['last_seen'] != p['first_seen']:
                meta += f" → {p['last_seen']}"
            line = f"- {status_icon} **{text}**  \n  {meta}"
            if p.get('notes'):
                line += f"  \n  📝 {p['notes']}"
            lines.append(line)
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 状态图例",
        "",
        "- ⭐ 已采用：已加入千牛快捷回复，全员可用",
        "- 🔵 待审核：新短语，运营/管理评审中",
        "- 🟡 待优化：内容不错但措辞要调",
        "- 🗑️ 废弃：不建议使用",
        "",
    ])

    KB_MD.parent.mkdir(parents=True, exist_ok=True)
    KB_MD.write_text('\n'.join(lines), encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', help='只扫指定日期 YYYY-MM-DD')
    ap.add_argument('--rebuild', action='store_true', help='重置数据库，从头扫所有 JSON')
    args = ap.parse_args()

    db = {"version": 1, "updated_at": "", "phrases": {}} if args.rebuild else load_db()
    sessions, files = load_sessions(args.date)
    print(f"加载 {len(sessions)} 个会话（{len(files)} 个文件）")

    new, updated = merge_into_db(db, sessions)
    print(f"新增 {new} 条短语，更新 {updated} 次")

    save_db(db)
    render_md(db)
    print(f"✓ 数据库: {DB_PATH}")
    print(f"✓ 渲染:   {KB_MD}")


if __name__ == "__main__":
    main()
