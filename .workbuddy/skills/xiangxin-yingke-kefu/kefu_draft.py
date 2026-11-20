#!/usr/local/bin/python3
"""迎客·客服副驾 —— 起草 询单/售后 回复

AI 只起草，客服人工确认后再发（不自动发）。会注入公司客服红线 +
按关键词从客服知识库捞相关产品/政策文件，并对客户隐私做脱敏。

用法：
  python3 kefu_draft.py --type 询单 "Bushnell V6 和 V7 有啥区别，能便宜点吗"
  python3 kefu_draft.py --type 售后 --file q.txt --product "倍视能 V6 测距仪"
  echo "客户问题" | python3 kefu_draft.py --type 询单
"""
import argparse
import glob
import json
import os
import re
import sys
import urllib.request

VAULT_DIR = "/Users/mac/obsidian/祥子AI"
KB_DIR = os.path.join(VAULT_DIR, "03-公司/SOP与流程/销售客服")
# 核心知识文件：公司沉淀的 190 条标准客服问答（同源飞书「客服销售问答」wiki + 速查库 Base）。
# 它是最权威的标准答案，检索时温和加权，优先于其余 180 篇——但不碾压真正更相关的专门文档。
CORE_FILES = ("004-1-48",)
CORE_BOOST = 1.3
# 销冠话术库：议价/挽留/比价/促成场景的销冠话术，温和加权，确保带型号词的砍价类 query 也能进 top-k
SALES_FILES = ("100-销冠话术库",)
SALES_BOOST = 1.25
# 议价/挽留/比价/促成信号词：query 命中任一，就确保 top-k 里至少有一个销冠话术块。
# （带型号的砍价 query，型号词会把产品 QA 顶满 top-k，光靠加权挤不进，故强制保一席。
#  纯参数题不含这些词、不触发，零污染。）
SALES_SIGNAL = ("贵", "便宜", "优惠", "降价", "少点", "最低", "底价", "抹零", "划算",
                "别家", "网上", "日本", "海外", "代购", "退款", "退货", "退了", "不要了",
                "再考虑", "赠", "送个", "便宜点", "讲价", "还能少", "议价", "压价")
MODEL = "claude-sonnet-4-6"   # 客服话术起草：速度/质量平衡（祥书定）
MAX_TOKENS = 1500

REDLINES = """【客服红线 · 每条必须遵守】
1. 平台订单(天猫/京东/淘宝)的退款/退差价/补偿，一律走原平台原路退回，严禁答应微信等私下退款或返利（客服-006）。
2. 大额订单(客单≥1万 / 数量≥5 / 涉及定制 / 单品≥4000)出现卡单信号(犹豫、要退、反复比价、"再考虑")→ 第一时间加微信转私域。话术参考："方案和优惠要发表格、图，平台发不方便，加个微信我直接发您"。
3. 禁绝对化/极限词(最、第一、全网最低、绝对、顶级、唯一)和违禁词；不夸大功效、不乱承诺疗效/效果。
4. 价格/比价以天猫为基准，不主动报京东价压价；先问预算/机型/用途，别一上来报最高价。
5. 圈t/调货不优先香港渠道(时效不稳)，优先大陆。
6. 客户隐私(姓名/手机/地址/订单号)不写进话术正文、不外传。"""

TONE = ("【话术原则】先共情表态度 → 核实问题/需求 → 给清楚的解决方案或产品建议 → 推进下一步(成交/好评/回访)。"
        "语气专业又亲和、口语化，别官腔；该问清的(预算/机型/用途/订单情况)先问再答。")

GUIDE = {
    "询单": "客户在咨询/比价阶段。目标：解答疑问 + 建立信任 + 推进成交。留意是否大额卡单信号，是就按红线2提醒转私域。",
    "售后": "客户已购买后的问题。按售后流程：表达抱歉 → 核实订单与原因 → 给方案。退款类严守红线1(原路退回)。提醒客服千牛插旗备注 + 后续回访。",
    "跟进": "客户咨询后沉默 / 老顾客回访。轻触达、不催、不逼单，给价值（新到货 / 适合 TA 的点 / 时令优惠）；给一条不打扰的跟进话术 + 一个合适的再跟进时机。绝不要群发感。",
    "群答疑": "内部工作群里同事(客服/采购/运营)@我提问。直接要点回答，不啰嗦。详见 BRIEF_SYSTEM。",
}

# 群答疑模式专用 system —— 内部同事面向、要点式、简洁。
# 跟客户话术(询单/售后/跟进)分开：那几个要共情+推进成交，这个只要"把事说清楚"。
BRIEF_SYSTEM = """你是祥新高尔夫电商「三方发货」内部工作群的答疑助手。群里是客服/采购/运营同事（群里也有供应商），他们 @ 你问产品、价格、订单/物流/售后政策，或贴一段客户消息问"这个怎么回"。

【铁律 · 必须遵守，但绝不在回答里复述这些规则】
- 成本/拿货价/拿货折扣对内部同事公开（祥书定的），可以答：据知识库里的「拿货折扣参考」回答，并带一句「草稿统计值、以供应商当时实时报价为准」。⚠️但供应商返利/返点更敏感、不在知识库，别答。
- 平台订单(天猫/京东/淘宝)退款/退差价一律原平台原路退回，不答应微信私下退款或返利。
- 不用绝对化/极限词(最/第一/全网最低/绝对/唯一)和违禁词，不夸大功效、不乱承诺疗效。
- 比价以天猫为基准，不主动报京东价。圈t/调货不优先香港(时效不稳)。
- 客户隐私(姓名/手机/地址/订单号)不写进回答。
- 据下面给的知识库回答；库里没有就老实说"没查到"，**绝不**编参数/价格/型号/政策。

【怎么答 —— 直接要点，别啰嗦】
- 事实题(参数/区别/有没有货/价格/政策)：直接给答案，要点式，1~4 行说完，能一句说清就一句。不要寒暄、不要"请问您…"、不要营销式推进。
- 让你"怎么回这个客户 / 这个售后怎么处理"：给一条能直接复制发客户的话术，2~4 句，口语亲和、不违规，只给话术本身。
- 问题里提到"上面/这个/这些"但你看不到具体内容(读不到群历史)：别瞎猜，就回一句「我看不到上面的消息，把客户原话贴出来我直接给你话术」。
- 订单类：发货时效/退换货/物流规则这种"政策"问题，据知识库答。但具体某个订单的状态(发了吗/到哪了/某客户的单)你查不到，别编，回一句「具体订单状态去吉客云查或找对应同事，这群我不查单」，且绝不在群里说客户姓名/单号。
- 有需要提醒/不确定的点，最后单起一行以 ⚠️ 开头，一句话；没有就不加。
- 不要用【】小标题、不要分"草稿/备选/需核实"，直接给最终答案。"""

# 中文检索停用词（避免高频字/词的 n-gram 噪音）
CHINESE_STOP = set("的了吗呢吧啊呀和与或个有没是不在这那我你他她它们就都也要会能可"
                   "对到着过把被给让从向往咱们一下这个那个什么怎么可以没有还是这款")


def _relay_config():
    """relay 的 base url + token：先环境变量，没有就从 ~/.zshrc 解析
    （launchd 起的 daemon 不继承 shell 环境，所以要兜底读 zshrc 里 export 的两行）。"""
    base = os.environ.get("ANTHROPIC_BASE_URL")
    token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
    if base and token:
        return base, token
    try:
        with open(os.path.expanduser("~/.zshrc"), encoding="utf-8") as f:
            for line in f:
                m = re.match(
                    r'^\s*export\s+(ANTHROPIC_BASE_URL|ANTHROPIC_AUTH_TOKEN)\s*=\s*["\']?([^"\'\s]+)',
                    line)
                if not m:
                    continue
                if m.group(1) == "ANTHROPIC_BASE_URL" and not base:
                    base = m.group(2)
                elif m.group(1) == "ANTHROPIC_AUTH_TOKEN" and not token:
                    token = m.group(2)
    except OSError:
        pass
    return base, token


def claude_api(system_blocks, user_text, timeout=120):
    """直 POST relay 的 Messages API（不启 claude agent，省掉 ~12s 冷启动）。
    relay 是直连 IP，用空 ProxyHandler 绕开环境里的 Clash 代理。失败返回空串。"""
    base, token = _relay_config()
    if not base or not token:
        print("✗ 缺 relay 配置（ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN）", file=sys.stderr)
        return ""
    body = {
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "system": system_blocks,
        "messages": [{"role": "user", "content": user_text}],
    }
    req = urllib.request.Request(
        base.rstrip("/") + "/v1/messages",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    req.add_header("anthropic-version", "2023-06-01")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("x-api-key", token)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 直连，不走代理
    try:
        with opener.open(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"✗ relay 请求失败：{e}", file=sys.stderr)
        return ""
    return "".join(
        b.get("text", "") for b in (payload.get("content") or [])
        if b.get("type") == "text"
    ).strip()


def scrub_pii(text):
    """脱敏明显的隐私：手机号、长数字串(订单号)。返回(脱敏后文本, 是否动过)"""
    orig = text
    text = re.sub(r"1[3-9]\d{9}", "[手机号已脱敏]", text)
    text = re.sub(r"\b\d{12,}\b", "[订单号已脱敏]", text)
    return text, (text != orig)


def _split_blocks(text):
    """把一篇文档切成检索块：按 QA 条目(**数字.)/markdown 标题切，大段再按空行拆。"""
    text = re.sub(r"^---.*?---", "", text, count=1, flags=re.S).strip()  # 去 frontmatter
    text = re.sub(r"(?m)^>.*$", "", text)                  # 去"自动拉取"等引用提示行
    text = re.sub(r"!\[.*?\]\(.*?\)", "[配图]", text)       # 图片链接→占位（不干扰检索、留痕给客服）
    text = re.sub(r"<cite[^>]*?>(?:</cite>)?", "", text)    # 去飞书 cite 标签
    blocks = []
    for p in re.split(r"(?m)^(?=(?:\*\*\d+[.、]|#{1,6}\s))", text):
        p = p.strip()
        if len(p) < 8:
            continue
        if len(p) > 1400:
            blocks.extend(s.strip()[:1400] for s in re.split(r"\n\s*\n", p) if len(s.strip()) >= 8)
        else:
            blocks.append(p)
    if not blocks and text.strip():
        blocks = [text.strip()[:1400]]
    return blocks


def _query_terms(query):
    """从客户问题提取检索词：英文/型号词整词(高权重) + 中文 2~3gram。"""
    terms = {}
    for w in re.findall(r"[a-z0-9]{2,}", query.lower()):
        terms[w] = max(terms.get(w, 0), 2.0)
    for run in re.findall(r"[一-鿿]+", query):
        for n in (3, 2):
            for i in range(len(run) - n + 1):
                g = run[i:i + n]
                if all(c in CHINESE_STOP for c in g):
                    continue
                terms[g] = max(terms.get(g, 0), 1.5 if n == 3 else 1.0)
    return terms


def _index_kb():
    """把整个知识库切成内容块 [(文件名, 块原文, 块小写)]。读全库约 80ms。"""
    idx = []
    for f in glob.glob(os.path.join(KB_DIR, "*.md")):
        fname = os.path.basename(f).replace(".md", "")
        try:
            with open(f, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            continue
        for block in _split_blocks(text):
            idx.append((fname, block, block.lower()))
    return idx


def retrieve_kb(query, k=4, max_chars=1000, min_score=0.0):
    """全库内容检索：按 query 词在每个内容块里的命中给块打分，返回最相关 top-k 块。
    核心文件(CORE_FILES，190 条标准 QA)命中分数温和加权优先。
    取代旧的「文件名匹配 + 硬编码白名单 + 只读前 1500 字」——那样 190 条问答库基本调不出来。"""
    terms = _query_terms(query)
    if not terms:
        return []
    scored = []
    for fname, block, bl in _index_kb():
        score = 0.0
        for t, w in terms.items():
            c = bl.count(t)
            if c:
                score += w * (1 + 0.3 * (c - 1))  # 命中即得分，重复命中递减加成
        if score > 0:
            if any(cf in fname for cf in CORE_FILES):
                score *= CORE_BOOST  # 核心标准 QA 优先（温和加权，势均力敌时胜出）
            elif any(sf in fname for sf in SALES_FILES):
                score *= SALES_BOOST  # 销冠话术：议价/挽留类命中分高，加权后稳进 top-k；纯参数题命中分低不会污染
            scored.append((score, fname, block))
    scored.sort(key=lambda x: -x[0])
    if not scored:
        return []
    cutoff = max(min_score, scored[0][0] * 0.18)  # 砍长尾/极弱匹配：搜不到时返回空而非硬凑
    out, seen = [], set()
    for sc, fname, block in scored:
        if sc < cutoff:
            break
        key = block[:40]
        if key in seen:
            continue
        seen.add(key)
        out.append((fname, block[:max_chars]))
        if len(out) >= k:
            break
    # 议价/挽留/比价/促成类 query：确保至少注入一个销冠话术块（型号词多时它易被产品 QA 全挤出 top-k）
    if any(s in query for s in SALES_SIGNAL) and not any(
            any(sf in n for sf in SALES_FILES) for n, _ in out):
        for sc, fname, block in scored:
            if any(sf in fname for sf in SALES_FILES):
                pair = (fname, block[:max_chars])
                if out:
                    out[-1] = pair  # 挤掉最末一名产品 QA，换上销冠话术
                else:
                    out.append(pair)
                break
    return out


def build_system():
    """固定不变的部分（红线+话术原则+输出格式）→ system，并打 cache_control。
    各 --type 共用同一 system，缓存命中率更高。"""
    return [{
        "type": "text",
        "text": (
            "你是祥新高尔夫电商的资深客服。给客服同事【起草】一条可直接发给客户的回复（人工会再确认）。\n\n"
            f"{REDLINES}\n\n{TONE}\n\n"
            "按下面格式输出（纯文本，别用 JSON）：\n"
            "【红线提醒】适用的红线或风险，一句话；没有就写「无」\n"
            "【回复草稿】可直接发给客户的话术（口语、亲和、不违规）\n"
            "【备选语气】(可选)换个角度/更简短的一版\n"
            "【需先核实】(如有)需要客服先问清或查证的点(订单情况/机型/预算等)，列点"
        ),
        "cache_control": {"type": "ephemeral"},
    }]


def build_system_brief():
    """群答疑模式的 system（要点式、面向同事），打 cache_control 提缓存命中。"""
    return [{"type": "text", "text": BRIEF_SYSTEM, "cache_control": {"type": "ephemeral"}}]


def build_user_brief(content, product, kb):
    """群答疑 user：知识库参考 + 同事的问题。"""
    kb_block = ""
    if kb:
        kb_block = "\n\n【知识库参考（据此回答，别编）】\n" + \
            "\n".join(f"# {name}\n{txt}" for name, txt in kb)
    product_block = f"\n相关产品/场景：{product}" if product else ""
    return f"{product_block}{kb_block}\n\n=== 同事的问题 ===\n{content}\n=== 问题结束 ==="


def build_user(ctype, content, product, kb):
    """每次都变的部分（类型说明 + 知识库检索结果 + 客户消息）→ user。"""
    kb_block = ""
    if kb:
        kb_block = "\n\n【公司知识库参考（据此回答产品/政策，别编）】\n" + \
            "\n".join(f"# {name}\n{txt}" for name, txt in kb)
    product_block = f"\n客户咨询的产品/场景：{product}" if product else ""
    return (
        f"类型说明：{GUIDE.get(ctype, '')}{product_block}{kb_block}\n\n"
        f"=== 客户消息 ===\n{content}\n=== 客户消息结束 ==="
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", required=True, choices=list(GUIDE.keys()))
    ap.add_argument("--file", help="客户消息文件路径")
    ap.add_argument("--product", help="客户咨询的产品/场景，补充上下文")
    ap.add_argument("--no-kb", action="store_true", help="跳过知识库检索")
    ap.add_argument("content", nargs="*", help="客户消息(也可走 --file / stdin)")
    args = ap.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            content = f.read()
    elif args.content:
        content = " ".join(args.content)
    elif not sys.stdin.isatty():
        content = sys.stdin.read()
    else:
        print("✗ 没有客户消息（用 --file / 直接传参 / stdin）", file=sys.stderr)
        sys.exit(2)

    content = content.strip()
    if not content:
        print("✗ 客户消息为空", file=sys.stderr)
        sys.exit(2)

    content, scrubbed = scrub_pii(content)
    kb = [] if args.no_kb else retrieve_kb(content + " " + (args.product or ""))

    brief = args.type == "群答疑"
    if brief:
        draft = claude_api(build_system_brief(), build_user_brief(content, args.product, kb))
    else:
        draft = claude_api(build_system(), build_user(args.type, content, args.product, kb))
    if not draft:
        print("⚠️ 副驾没返回（relay 超时/出错），稍后再试", file=sys.stderr)
        sys.exit(1)

    if brief:
        # 群答疑：stdout 只放最终答案（daemon 直接发群），诊断信息走 stderr 不污染正文。
        if kb:
            names = list(dict.fromkeys(n for n, _ in kb))
            print(f"📚 参考：{', '.join(names)}", file=sys.stderr)
        if scrubbed:
            print("⚠️ 已脱敏客户隐私", file=sys.stderr)
        print(draft)
        return

    print(f"🎧 客服副驾草稿 · {args.type}（人工确认后再发）")
    if scrubbed:
        print("⚠️ 已自动脱敏客户隐私（手机号/订单号）；发回客户前自行核对")
    if kb:
        names = list(dict.fromkeys(n for n, _ in kb))
        print(f"📚 参考知识库：{', '.join(names)}")
    print("─" * 40)
    print(draft)
    print("─" * 40)
    print("提示：发出前可让「校官」复核一遍 → python3 ../xiangxin-jiaoguan-review/check.py --type 文案")


if __name__ == "__main__":
    main()
