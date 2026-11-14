#!/usr/bin/env python3
"""
补货建议 v2（科学版）：吉客云库存快照 → ABC分类 → 服务水平差异化安全库存 → 再订货点ROP → 该补哪些/补多少/找谁拿。

v2 升级（2026-06-15，对标库存管理标准方法）：
  · 多份快照算动销：用 SNAP_DIR 里全部快照的净出库序列估 日均μ 和 波动σ（不再只靠两份）
  · ABC 分类：按「动销吞吐价值」(日均×成本) 累计 80/95 分 A/B/C
  · 安全库存 SS = z·σ·√L（z 按 ABC 服务水平：A 98% / B 90% / C 85%）
  · 再订货点 ROP = 日均·提前期L + SS（提前期按品牌配，独家供应商更长）
  · 补货点触发：库存头寸(可用+在途) ≤ ROP 才补；补到 ROP + 复盘周期需求
  · EOQ 经济订货量给参考批量

用法:
  advise.py                  # 自动用 99-附件/吉客云导出/ 全部快照
  advise.py latest.xlsx prev.xlsx   # 只用指定两份做端点

输出: _待整理/YYYY-MM-DD-补货建议.md
口径：吉客云「支撑天数」字段公司没维护(1%非空)，不用；自己从快照净出库算。
"""
import sys, re, math, os, warnings
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
import pandas as pd

# 库根目录：装到自己电脑后，用环境变量 KB_VAULT 指到你的 Obsidian 库
VAULT = Path(os.environ.get("KB_VAULT", str(Path.home() / "obsidian/团队知识库")))
INBOX = VAULT / "_待整理"
SNAP_DIR = VAULT / "03-公司/财务数据/吉客云销售/库存快照"   # 每日定时任务(com.xiangshu.jackyun-inventory 03:20)写入处

# ────── 可调参数（祥书可改）──────
# ABC 服务水平 → 正态分位 z（缺货保护程度）
SERVICE_Z = {"A": 2.05, "B": 1.28, "C": 1.04}      # A=98% B=90% C=85%
ABC_CUT = (0.80, 0.95)                              # 累计吞吐价值 ≤80%=A, ≤95%=B, 其余 C
# 需求波动假设：σ 至少不低于 CV×日均（快照少时兜底，A 类货稳、C 类货散）
CV_FLOOR = {"A": 0.4, "B": 0.6, "C": 0.8}
# 采购提前期 L（天）：下单到可售。独家/进口长，多家可比价短。
LEAD_TIME_DEFAULT = 10
LEAD_TIME = {
    "Bushnell 倍视能": 14,   # 北京豪俊独家
    "Honma 本间": 14, "PXG": 14,
    "Garmin 佳明": 7, "Ping": 7, "Callaway 卡拉威": 7,
    "TaylorMade 泰勒梅": 7, "Titleist": 7, "Mizuno 美津浓": 10,
}
REVIEW_PERIOD = 7          # 复盘周期：多久跑一次补货（补到 ROP + R×日均）
ORDER_COST = 50            # 每次下单固定成本(元)，算 EOQ 用
HOLDING_RATE = 0.25        # 年持有成本率(占货值)，算 EOQ 用
TOP_WATCH = 25             # 🟢/⚠️ 档只列 Top N
MIN_SUGGEST = 1
MAX_SNAPS = 8              # 只取最近 N 份快照估动销：每天定时新增，全量读会越来越慢；近 8 天足够估 μ/σ，也避开早期异常大文件

BRAND_PATTERNS = [
    ("Bushnell 倍视能", r"Bushnell|倍视能"), ("Ping", r"Ping(?![a-z])|PING"),
    ("Garmin 佳明", r"Garmin|佳明"), ("Honma 本间", r"Honma|本间"),
    ("Titleist", r"Titleist|泰特利斯"), ("Callaway 卡拉威", r"Callaway|卡拉威|卡羅威|卡拉"),
    ("PXG", r"PXG"), ("TaylorMade 泰勒梅", r"TaylorMade|泰勒梅"),
    ("Mizuno 美津浓", r"Mizuno|美津浓"), ("Cleveland", r"Cleveland|克里夫兰"),
    ("Cobra", r"Cobra"), ("Srixon", r"Srixon"),
]
PRIMARY_SUPPLIER = {
    "Bushnell 倍视能": "北京豪俊科贸（独家）",
    "Garmin 佳明": "上海牧诚 / 深圳时尚体育（5家可比价）",
    "Ping": "上海星邑 / 北京三木兰（PING 14家）",
    "Callaway 卡拉威": "深圳时尚体育 / 北京铖鑫",
    "TaylorMade 泰勒梅": "北京铭达广通 / 东莞高准",
    "Titleist": "上海牧诚 / 北京铖鑫", "Honma 本间": "杭州广昊 / 北京加西亚",
    "PXG": "广州臻精彩 / 广州度方", "Mizuno 美津浓": "上海牧诚 / 橄榄枝",
}

NUM_COLS = ["库存数量", "可用库存", "采购在途", "库存金额", "当前成本价", "零售价"]


def load(xlsx_path):
    df = pd.read_excel(xlsx_path, sheet_name=0)
    for c in NUM_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    agg = {c: "sum" for c in ["库存数量", "可用库存", "采购在途", "库存金额"] if c in df.columns}
    for c in ["货品名称", "当前成本价", "零售价"]:
        if c in df.columns:
            agg[c] = "first"
    df = df.groupby("货品编号", as_index=False).agg(agg)
    df["货品名称_str"] = df["货品名称"].astype(str)
    df["品牌"] = "其他/配件/二手球"
    for name, pat in BRAND_PATTERNS:
        m = df["货品名称_str"].str.contains(pat, case=False, regex=True, na=False)
        df.loc[m & (df["品牌"] == "其他/配件/二手球"), "品牌"] = name
    return df


def date_of(p):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", Path(p).name)
    return m.group(1) if m else None


def find_snaps():
    # 定时任务归档名为「仓库库存详情」，旧手动导出名为「总库存查询」，两者同 schema，都收。
    seen = {}
    for pat in ("*-仓库库存详情.xlsx", "*-总库存查询.xlsx"):
        for f in SNAP_DIR.glob(pat):
            d = date_of(f)
            if d:
                seen.setdefault(d, f)  # 同日优先「仓库库存详情」
    fs = sorted(seen.items())  # 升序 (date, path)
    return fs[-MAX_SNAPS:]     # 只留最近 MAX_SNAPS 份


def unit_cost(row):
    if row["当前成本价"] > 0:
        return row["当前成本价"]
    if row["库存数量"] > 0 and row["库存金额"] > 0:
        return row["库存金额"] / row["库存数量"]
    return 0.0


def build_demand(snap_files):
    """用全部快照算每个 SKU 的 日均μ 和 波动σ（按相邻快照净出库率序列）。"""
    series = {}  # 货品编号 -> list of (qty, date)
    for d, f in snap_files:
        df = load(f)
        for _, r in df[["货品编号", "库存数量"]].iterrows():
            series.setdefault(r["货品编号"], []).append((r["库存数量"], d))
    rates = {}  # 货品编号 -> list of daily_out_rate
    for code, pts in series.items():
        pts.sort(key=lambda x: x[1])
        rs = []
        for (q0, d0), (q1, d1) in zip(pts, pts[1:]):
            days = max(1, (datetime.strptime(d1, "%Y-%m-%d") - datetime.strptime(d0, "%Y-%m-%d")).days)
            net_out = max(0.0, q0 - q1)
            rs.append(net_out / days)
        rates[code] = rs
    return rates


def mu_sigma(rs):
    if not rs:
        return 0.0, 0.0
    mu = sum(rs) / len(rs)
    if len(rs) >= 2:
        var = sum((x - mu) ** 2 for x in rs) / len(rs)
        sigma = math.sqrt(var)
    else:
        sigma = 0.0
    return mu, sigma


def abc_classify(items):
    """按 动销吞吐价值(日均×成本) 累计分 A/B/C。items: list of dict 含 'value'。"""
    moving = [it for it in items if it["mu"] > 0 and it["value"] > 0]
    total = sum(it["value"] for it in moving) or 1.0
    for it in sorted(moving, key=lambda x: -x["value"]):
        pass
    moving.sort(key=lambda x: -x["value"])
    cum = 0.0
    for it in moving:
        cum += it["value"]
        share = cum / total
        it["abc"] = "A" if share <= ABC_CUT[0] else ("B" if share <= ABC_CUT[1] else "C")
    for it in items:
        it.setdefault("abc", "C" if it["mu"] > 0 else "-")
    return items


def fmt_money(x):
    return f"¥{x:,.0f}"


def grade(avail, position, ss, rop, mu):
    if mu <= 0:
        return "⚠️ 负库存待核" if avail < 0 else None
    if avail < 0:
        return "🔴 超卖急补"
    if position < ss:
        return "🔴 紧急(破安全库存)"
    if position <= rop:
        return "🟡 到补货点(下单)"
    if position <= rop * 1.3:
        return "🟢 接近补货点(备货)"
    return None


def build(snap_files):
    cur = load(snap_files[-1][1])              # 最新快照取现状
    rates = build_demand(snap_files)
    items = []
    for _, r in cur.iterrows():
        nm = r["货品名称_str"]
        if "二手球" in nm or "清仓" in nm:
            continue
        mu, sigma = mu_sigma(rates.get(r["货品编号"], []))
        uc = unit_cost(r)
        items.append({
            "code": r["货品编号"], "name": str(r["货品名称"])[:34], "brand": r["品牌"],
            "avail": float(r["可用库存"]), "intransit": float(r["采购在途"]),
            "mu": mu, "sigma": sigma, "uc": uc, "value": mu * uc,
        })
    abc_classify(items)

    rows = []
    for it in items:
        mu, sigma, uc = it["mu"], it["sigma"], it["uc"]
        abc = it["abc"] if it["abc"] in SERVICE_Z else "C"
        z = SERVICE_Z.get(abc, SERVICE_Z["C"])
        L = LEAD_TIME.get(it["brand"], LEAD_TIME_DEFAULT)
        # σ 兜底：快照少时用 CV×μ 防止低估缺货风险
        sigma_eff = max(sigma, CV_FLOOR.get(abc, 0.6) * mu) if mu > 0 else 0.0
        ss = z * sigma_eff * math.sqrt(L)
        rop = mu * L + ss
        position = it["avail"] + it["intransit"]
        g = grade(it["avail"], position, ss, rop, mu)
        if g is None:
            continue
        if g == "⚠️ 负库存待核":
            sug, money, eoq = "待核", 0.0, 0
        else:
            target = rop + REVIEW_PERIOD * mu          # 补到补货点 + 一个复盘周期
            need = target - position
            if it["avail"] < 0:
                need = max(need, -it["avail"] - it["intransit"])  # 至少补平超卖
            sug = max(0, math.ceil(need))
            if sug < MIN_SUGGEST:
                continue
            money = sug * uc
            D = mu * 365
            H = max(uc * HOLDING_RATE, 1e-6)
            eoq = math.ceil(math.sqrt(2 * D * ORDER_COST / H)) if D > 0 else 0
        rows.append({
            **it, "abc": abc, "L": L, "ss": math.ceil(ss), "rop": math.ceil(rop),
            "grade": g, "sug": sug, "money": money, "eoq": eoq,
        })
    return rows


RANK = {"🔴 超卖急补": 0, "🔴 紧急(破安全库存)": 1, "🟡 到补货点(下单)": 2,
        "🟢 接近补货点(备货)": 3, "⚠️ 负库存待核": 4}


def table(rows):
    head = "| 货品编号 | 货品名称 | 品牌 | ABC | 可用 | 在途 | 日均 | 安全库存 | 补货点ROP | 建议补货 | EOQ | 预估占款 | 找谁拿 |"
    sep = "|---|---|---|:-:|--:|--:|--:|--:|--:|--:|--:|--:|---|"
    out = [head, sep]
    for r in rows:
        out.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | **{}** | {} | {} | {} |".format(
            r["code"], r["name"], r["brand"], r["abc"], int(r["avail"]), int(r["intransit"]),
            round(r["mu"], 2), r["ss"], r["rop"], r["sug"], r["eoq"] if r["sug"] != "待核" else "—",
            fmt_money(r["money"]), PRIMARY_SUPPLIER.get(r["brand"], "→ 见 supplier-finder")))
    return "\n".join(out)


def main():
    if len(sys.argv) >= 3:
        snaps = [(date_of(Path(sys.argv[2])), Path(sys.argv[2])), (date_of(Path(sys.argv[1])), Path(sys.argv[1]))]
        snaps = [(d, f) for d, f in snaps if d]
        snaps.sort()
    else:
        snaps = find_snaps()
    if len(snaps) < 2:
        print("⚠️ 至少要两份库存快照才能估动销。先跑 jackyun-inventory-weekly 再导一份。")
        sys.exit(1)
    print(f"✅ 用 {len(snaps)} 份快照：{', '.join(d for d, _ in snaps)}")

    rows = build(snaps)
    rows.sort(key=lambda r: (RANK.get(r["grade"], 9), -r["money"]))

    urgent = [r for r in rows if r["grade"].startswith("🔴")]
    order = [r for r in rows if r["grade"] == "🟡 到补货点(下单)"]
    watch = [r for r in rows if r["grade"] == "🟢 接近补货点(备货)"]
    recheck = [r for r in rows if r["grade"] == "⚠️ 负库存待核"]
    watch_top = sorted(watch, key=lambda r: -r["money"])[:TOP_WATCH]
    recheck_top = sorted(recheck, key=lambda r: r["avail"])[:TOP_WATCH]

    total_money = sum(r["money"] for r in rows)
    urgent_money = sum(r["money"] for r in urgent)
    oversold = sum(1 for r in urgent if r["grade"] == "🔴 超卖急补")
    abc_cnt = {k: sum(1 for r in rows if r["abc"] == k) for k in ["A", "B", "C"]}
    today = datetime.now().strftime("%Y-%m-%d")
    win = f"{snaps[0][0]} → {snaps[-1][0]}"

    parts = [
        "---", "类型: 补货建议", "来源: 吉客云 总库存查询（多快照科学版v2）",
        f"快照: {', '.join(d for d,_ in snaps)}", "目标位置: 03-公司/库存分析/补货建议/",
        "状态: 待整理", "---", "",
        f"# 补货建议 v2·科学版（{today}）", "",
        f"> **算法**：{len(snaps)} 份快照({win})净出库估 日均μ/波动σ → ABC分类 → "
        f"安全库存 SS=z·σ·√L → 再订货点 ROP=μ·L+SS → 头寸(可用+在途)≤ROP 才补，补到 ROP+{REVIEW_PERIOD}天需求。",
        "",
        "## 0. 摘要",
        f"- 🔴 急补 **{len(urgent)}**（超卖在动销 {oversold}）｜🟡 到补货点 **{len(order)}**｜🟢 接近 **{len(watch)}**｜⚠️ 负库存待核 **{len(recheck)}**",
        f"- 动销 SKU 分级：A **{abc_cnt['A']}** · B **{abc_cnt['B']}** · C **{abc_cnt['C']}**（A 类高价值，服务水平 98%）",
        f"- 建议补货预估占款 **{fmt_money(total_money)}**（🔴 急补占 {fmt_money(urgent_money)}）",
        "",
        "## ⚙️ 参数（可在 advise.py 顶部改）",
        f"- 服务水平 z：A=98%(2.05) B=90%(1.28) C=85%(1.04)；提前期 L：独家品牌(Bushnell/Honma/PXG)14天，多家可比价7天，默认10天",
        f"- σ 兜底 CV：A 0.4 / B 0.6 / C 0.8（快照仅 {len(snaps)} 份，σ 估计偏粗，按 CV 兜底防低估缺货）",
        f"- ⚠️ 提前期/订单成本是**配置估值**，不是实测——舒怡那边能给各供应商真实到货天数就更准。",
        "",
        f"## 一、🔴 紧急（超卖在动销 / 头寸跌破安全库存）— {len(urgent)} 个",
        table(urgent) if urgent else "（无）", "",
        f"## 二、🟡 到补货点该下单（头寸 ≤ ROP）— {len(order)} 个",
        table(order) if order else "（无）", "",
        f"## 三、🟢 接近补货点·备货观察（ROP~1.3×ROP，占款 Top {TOP_WATCH}）— 共 {len(watch)} 个",
        table(watch_top) if watch_top else "（无）", "",
        f"## 四、⚠️ 负库存待核（可用为负但近期无动销，多为对账/盘点问题，交库管核对，不计补货）— 共 {len(recheck)} 个，列 Top {TOP_WATCH}",
        table(recheck_top) if recheck_top else "（无）",
    ]
    report = "\n".join(parts)

    INBOX.mkdir(parents=True, exist_ok=True)
    out = INBOX / f"{today}-补货建议.md"
    out.write_text(report, encoding="utf-8")
    print(f"📄 补货建议 v2 写入: {out}")
    print(f"\n----- 摘要 -----")
    print(f"🔴 急补 {len(urgent)}（超卖 {oversold}）| 🟡 到补货点 {len(order)} | 🟢 接近 {len(watch)} | ⚠️ 待核 {len(recheck)}")
    print(f"ABC: A {abc_cnt['A']} / B {abc_cnt['B']} / C {abc_cnt['C']} | 建议补货占款 {fmt_money(total_money)}（🔴 {fmt_money(urgent_money)}）")
    if urgent[:5]:
        print("\n🔴 急补 Top 5:")
        for r in urgent[:5]:
            print(f"  [{r['abc']}] {r['code']} {r['name'][:18]} | 可用{int(r['avail'])} ROP{r['rop']} | 补{r['sug']}(EOQ{r['eoq']}) | {PRIMARY_SUPPLIER.get(r['brand'],'见supplier-finder')}")


if __name__ == "__main__":
    main()
