#!/usr/bin/env python3
"""
补货建议：基于吉客云库存快照（两份对比算动销）输出"该补哪些货、补多少、找谁拿"。

用法:
  advise.py                      # 自动取 99-附件/吉客云导出/ 里日期最新的两份快照
  advise.py latest.xlsx          # 指定本期，自动找比它旧的最近一份做对比
  advise.py latest.xlsx prev.xlsx

输出: _待整理/YYYY-MM-DD-补货建议.md

口径说明：吉客云导出的「支撑天数」字段公司基本没维护（多为空），所以这里用
最近两份快照的"净出库"自己估算动销速度，再按"补到 TARGET_COVER_DAYS 天可售"给补货量。
窗口短、噪声大；积累更多快照后更准，或改用 jky-cli 拉近 30 天真实销量升级。
"""
import sys
import re
import math
import warnings
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
import pandas as pd

VAULT = Path("/Users/mac/obsidian/祥子AI")
INBOX = VAULT / "_待整理"
SNAP_DIR = VAULT / "99-附件/吉客云导出"

# ────── 可调参数（祥书可改）──────
TARGET_COVER_DAYS = 30   # 补货目标：把库存补到能卖多少天
T_URGENT = 7             # 可售 ≤ 7 天 → 🔴 紧急
T_WARN = 14              # 7–14 天 → 🟡 提醒
T_WATCH = 21             # 14–21 天 → 🟢 备货观察；> 21 天不建议补
TOP_WATCH = 20           # 🟢 档只列建议占款 Top N（避免表太长）
MIN_SUGGEST = 1          # 建议补货量 < 此值不输出

BRAND_PATTERNS = [
    ("Bushnell 倍视能", r"Bushnell|倍视能"),
    ("Ping",            r"Ping(?![a-z])|PING"),
    ("Garmin 佳明",     r"Garmin|佳明"),
    ("Honma 本间",      r"Honma|本间"),
    ("Titleist",        r"Titleist|泰特利斯"),
    ("Callaway 卡拉威", r"Callaway|卡拉威|卡羅威|卡拉"),
    ("PXG",             r"PXG"),
    ("TaylorMade 泰勒梅", r"TaylorMade|泰勒梅"),
    ("Mizuno 美津浓",   r"Mizuno|美津浓"),
    ("Cleveland",       r"Cleveland|克里夫兰"),
    ("Cobra",           r"Cobra"),
    ("Srixon",          r"Srixon"),
]

# 品牌 → 主力供应商（取自 03-公司/供应商/00-供应商信息汇总.md；多家比价用 supplier-finder skill）
PRIMARY_SUPPLIER = {
    "Bushnell 倍视能":  "北京豪俊科贸（独家）",
    "Garmin 佳明":      "上海牧诚 / 深圳时尚体育（5家可比价）",
    "Ping":             "上海星邑 / 北京三木兰（PING 14家）",
    "Callaway 卡拉威":  "深圳时尚体育 / 北京铖鑫",
    "TaylorMade 泰勒梅": "北京铭达广通 / 东莞高准",
    "Titleist":         "上海牧诚 / 北京铖鑫",
    "Honma 本间":       "杭州广昊 / 北京加西亚",
    "PXG":              "广州臻精彩 / 广州度方",
    "Mizuno 美津浓":    "上海牧诚 / 橄榄枝",
}

NUM_COLS = ["库存数量", "可用库存", "锁定待发", "采购在途", "库存金额", "当前成本价", "零售价"]
SUM_COLS = ["库存数量", "可用库存", "锁定待发", "采购在途", "库存金额"]


def load(xlsx_path):
    df = pd.read_excel(xlsx_path, sheet_name=0)
    for c in NUM_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    agg = {c: "sum" for c in SUM_COLS if c in df.columns}
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
    fs = []
    for f in SNAP_DIR.glob("*-总库存查询.xlsx"):
        d = date_of(f)
        if d:
            fs.append((d, f))
    fs.sort(reverse=True)
    return fs


def resolve_args(argv):
    if len(argv) >= 3:
        return Path(argv[1]), Path(argv[2])
    snaps = find_snaps()
    if len(argv) == 2:
        latest = Path(argv[1])
        ld = date_of(latest)
        prev = next((f for d, f in snaps if d < ld), None)
        return latest, prev
    if len(snaps) >= 2:
        return snaps[0][1], snaps[1][1]
    if len(snaps) == 1:
        return snaps[0][1], None
    return None, None


def unit_cost(row):
    if row["当前成本价"] > 0:
        return row["当前成本价"]
    if row["库存数量"] > 0 and row["库存金额"] > 0:
        return row["库存金额"] / row["库存数量"]
    return 0.0


def grade(q, cover, daily):
    if daily <= 0:
        # 无动销：可用为负的多半是对账/盘点问题，单独待核；其余不补
        return "⚠️ 负库存待核" if q < 0 else None
    if q < 0:
        return "🔴 超卖急补"      # 超卖且仍在动销 → 真急补
    if cover <= T_URGENT:
        return "🔴 紧急"
    if cover <= T_WARN:
        return "🟡 提醒"
    if cover <= T_WATCH:
        return "🟢 备货"
    return None


def suggest_qty(q, daily, intransit):
    target = daily * TARGET_COVER_DAYS
    need = target - q - intransit
    if q < 0:
        need = max(need, -q - intransit)   # 至少补平超卖
    return max(0, math.ceil(need))


def fmt_money(x):
    return f"¥{x:,.0f}"


def build(latest, prev):
    cur = load(latest)
    days = 7
    if prev is not None:
        pdf = load(prev)
        d1, d0 = date_of(latest), date_of(prev)
        if d1 and d0:
            days = max(1, (datetime.strptime(d1, "%Y-%m-%d") - datetime.strptime(d0, "%Y-%m-%d")).days)
        psmall = pdf[["货品编号", "库存数量"]].rename(columns={"库存数量": "prev_库存数量"})
        cur = cur.merge(psmall, on="货品编号", how="left")
    else:
        cur["prev_库存数量"] = pd.NA

    cur["期间出库"] = (cur["prev_库存数量"] - cur["库存数量"]).clip(lower=0)
    cur["日均"] = (cur["期间出库"] / days).fillna(0)
    cur["周销"] = cur["日均"] * 7
    cur["可售天数"] = cur.apply(
        lambda r: (r["可用库存"] / r["日均"]) if r["日均"] > 0 else float("inf"), axis=1)

    rows = []
    for _, r in cur.iterrows():
        nm = r["货品名称_str"]
        if "二手球" in nm or "清仓" in nm:   # 二手球是回收货、清仓品正在清，都不补
            continue
        g = grade(r["可用库存"], r["可售天数"], r["日均"])
        if g is None:
            continue
        uc = unit_cost(r)
        if g == "⚠️ 负库存待核":
            sug_display, money = "待核", 0.0
        else:
            sug = suggest_qty(r["可用库存"], r["日均"], r["采购在途"])
            if sug < MIN_SUGGEST:
                continue
            sug_display, money = sug, sug * uc
        rows.append({
            "编号": r["货品编号"],
            "名称": str(r["货品名称"])[:34],
            "品牌": r["品牌"],
            "可用": int(r["可用库存"]),
            "在途": int(r["采购在途"]),
            "周销": round(r["周销"], 1),
            "可售天数": r["可售天数"],
            "档": g,
            "建议补货": sug_display,
            "占款": money,
            "供应商": PRIMARY_SUPPLIER.get(r["品牌"], "→ 见 supplier-finder"),
        })
    return rows, days


RANK = {"🔴 超卖急补": 0, "🔴 紧急": 1, "🟡 提醒": 2, "🟢 备货": 3, "⚠️ 负库存待核": 4}


def cover_str(g, cover):
    if "超卖" in g or "负库存" in g:
        return "超卖"
    if cover == float("inf"):
        return "—"
    return f"{cover:.0f}"


def table(rows):
    head = "| 货品编号 | 货品名称 | 品牌 | 可用 | 在途 | 周销 | 可售天数 | 建议补货 | 预估占款 | 找谁拿 |"
    sep = "|---|---|---|---:|---:|---:|---:|---:|---:|---|"
    out = [head, sep]
    for r in rows:
        out.append("| {} | {} | {} | {} | {} | {} | {} | **{}** | {} | {} |".format(
            r["编号"], r["名称"], r["品牌"], r["可用"], r["在途"], r["周销"],
            cover_str(r["档"], r["可售天数"]), r["建议补货"], fmt_money(r["占款"]), r["供应商"]))
    return "\n".join(out)


def main():
    latest, prev = resolve_args(sys.argv)
    if latest is None or not Path(latest).exists():
        print("❌ 找不到库存快照。先跑 jackyun-inventory-weekly 导一份，或手动指定 xlsx。")
        sys.exit(1)
    if prev is None:
        print("⚠️ 只有一份快照，无法估算动销 → 补货建议需要两份快照对比。先再导一份。")
        sys.exit(1)
    print(f"✅ 本期 {Path(latest).name}  对比 {Path(prev).name}")

    rows, days = build(latest, prev)
    rows.sort(key=lambda r: (RANK.get(r["档"], 9), -r["占款"]))

    urgent = [r for r in rows if r["档"].startswith("🔴")]
    warn = [r for r in rows if r["档"] == "🟡 提醒"]
    watch = [r for r in rows if r["档"] == "🟢 备货"]
    recheck = [r for r in rows if r["档"] == "⚠️ 负库存待核"]
    watch_top = sorted(watch, key=lambda r: -r["占款"])[:TOP_WATCH]
    recheck_top = sorted(recheck, key=lambda r: r["可用"])[:TOP_WATCH]

    total_money = sum(r["占款"] for r in rows)
    urgent_money = sum(r["占款"] for r in urgent)
    oversold = sum(1 for r in urgent if r["档"] == "🔴 超卖急补")
    today = datetime.now().strftime("%Y-%m-%d")

    parts = [
        "---",
        "类型: 补货建议",
        "来源: 吉客云 总库存查询（两份快照估算动销）",
        f"本期快照: {Path(latest).name}",
        f"对比快照: {Path(prev).name}",
        f"动销窗口: {days} 天",
        "目标位置: 03-公司/库存分析/补货建议/",
        "状态: 待整理",
        "---",
        "",
        f"# 补货建议（{today}）",
        "",
        f"> 口径：用最近两份库存快照（{date_of(prev)} → {date_of(latest)}，相隔 {days} 天）的净出库估算动销，"
        f"按「补到 {TARGET_COVER_DAYS} 天可售」给量。窗口短噪声大，仅供采购参考；"
        f"要更准可积累更多快照或用 jky-cli 拉近 30 天真实销量。供应商只给主力，多家比价用 supplier-finder。",
        "",
        "## 0. 摘要",
        f"- 🔴 急补 **{len(urgent)}** 个（其中超卖在动销 {oversold}）｜🟡 提醒 **{len(warn)}** 个｜🟢 备货 **{len(watch)}** 个｜⚠️ 负库存待核 **{len(recheck)}** 个",
        f"- 建议补货预估占款合计 **{fmt_money(total_money)}**（🔴 急补占 {fmt_money(urgent_money)}）",
        "",
        f"## 一、🔴 紧急补货（超卖在动销 / {T_URGENT} 天内断货）— {len(urgent)} 个",
        table(urgent) if urgent else "（无）",
        "",
        f"## 二、🟡 提醒（{T_URGENT}–{T_WARN} 天可售）— {len(warn)} 个",
        table(warn) if warn else "（无）",
        "",
        f"## 三、🟢 备货观察（{T_WARN}–{T_WATCH} 天，占款 Top {TOP_WATCH}）— 共 {len(watch)} 个",
        table(watch_top) if watch_top else "（无）",
        "",
        f"## 四、⚠️ 负库存待核（可用为负但近期无动销，多为对账/盘点问题，请库管核对，不计入补货）— 共 {len(recheck)} 个，列 Top {TOP_WATCH}",
        table(recheck_top) if recheck_top else "（无）",
    ]
    report = "\n".join(parts)

    INBOX.mkdir(parents=True, exist_ok=True)
    out = INBOX / f"{today}-补货建议.md"
    out.write_text(report, encoding="utf-8")
    print(f"📄 补货建议写入: {out}")
    print(f"\n----- 摘要 -----")
    print(f"🔴 急补 {len(urgent)}（超卖在动销 {oversold}）| 🟡 提醒 {len(warn)} | 🟢 备货 {len(watch)} | ⚠️ 负库存待核 {len(recheck)}")
    print(f"建议补货预估占款 {fmt_money(total_money)}（🔴 {fmt_money(urgent_money)}）")
    if urgent[:5]:
        print("\n🔴 急补 Top 5:")
        for r in urgent[:5]:
            print(f"  {r['编号']} {r['名称'][:20]} | 可用{r['可用']} 周销{r['周销']} | 补{r['建议补货']} | {r['供应商']}")


if __name__ == "__main__":
    main()
