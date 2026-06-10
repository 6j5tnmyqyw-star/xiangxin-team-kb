#!/usr/bin/env python3
"""
吉客云总库存分析 + 周对比
用法: analyze.py <current.xlsx> [previous.xlsx]
不传 previous 时自动从同目录找日期排序的上一份。
输出: _待整理/YYYY-MM-DD-吉客云库存周报.md
"""
import sys
import os
import re
import warnings
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
import pandas as pd

VAULT = Path("/Users/mac/obsidian/祥子AI")
INBOX = VAULT / "_待整理"

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


SUM_COLS = ["库存数量", "可用库存", "库存金额", "锁定待发", "采购在途",
            "入库申请", "出库申请", "渠道预留", "调拨在途", "生产在途",
            "退货在途", "订购量", "可订购量"]


def load(xlsx_path):
    df = pd.read_excel(xlsx_path, sheet_name=0)
    # 同 SKU 跨仓/货主多行 → 按货品编号聚合
    agg_map = {c: "sum" for c in SUM_COLS if c in df.columns}
    for c in ["货品名称", "零售价", "规格", "单位", "条码", "货品类型", "主条码", "当前成本价", "支撑天数"]:
        if c in df.columns:
            agg_map[c] = "first"
    df = df.groupby("货品编号", as_index=False).agg(agg_map)
    df["货品名称_str"] = df["货品名称"].astype(str)
    # 品牌分类
    df["品牌"] = "其他/配件/二手球"
    for name, pat in BRAND_PATTERNS:
        mask = df["货品名称_str"].str.contains(pat, case=False, regex=True, na=False)
        df.loc[mask & (df["品牌"] == "其他/配件/二手球"), "品牌"] = name
    return df


def fmt_money(x):
    return f"¥{x:,.0f}"


def fmt_delta(cur, prev):
    if prev is None or prev == 0:
        return ""
    diff = cur - prev
    pct = diff / abs(prev) * 100 if prev else 0
    sign = "+" if diff >= 0 else ""
    return f" ({sign}{diff:,.0f} / {sign}{pct:.1f}%)"


def section_overview(df, prev_df):
    lines = ["## 一、总览\n"]
    metrics = [
        ("SKU 档案总数",    len(df),                  len(prev_df) if prev_df is not None else None),
        ("有库存 SKU",      (df["库存数量"] > 0).sum(), (prev_df["库存数量"] > 0).sum() if prev_df is not None else None),
        ("库存数量合计",    df["库存数量"].sum(),     prev_df["库存数量"].sum() if prev_df is not None else None),
        ("可用库存合计",    df["可用库存"].sum(),     prev_df["可用库存"].sum() if prev_df is not None else None),
        ("锁定待发",        df["锁定待发"].sum(),     prev_df["锁定待发"].sum() if prev_df is not None else None),
        ("采购在途",        df["采购在途"].sum(),     prev_df["采购在途"].sum() if prev_df is not None else None),
        ("**库存金额合计**", df["库存金额"].sum(),    prev_df["库存金额"].sum() if prev_df is not None else None),
    ]
    lines.append("| 指标 | 本周 | 周变化 |")
    lines.append("|---|---:|---|")
    for name, cur, prev in metrics:
        if "金额" in name:
            v = fmt_money(cur)
            delta = fmt_delta(cur, prev) if prev is not None else ""
        else:
            v = f"{cur:,}"
            delta = fmt_delta(cur, prev) if prev is not None else ""
        lines.append(f"| {name} | {v} | {delta.strip(' ()')} |")
    return "\n".join(lines) + "\n"


def section_brands(df, prev_df):
    cur = df.groupby("品牌").agg(SKU数=("货品编号", "count"), 库存数量=("库存数量", "sum"), 库存金额=("库存金额", "sum")).sort_values("库存金额", ascending=False)
    lines = ["\n## 二、品牌结构\n"]
    if prev_df is not None:
        prev = prev_df.groupby("品牌")["库存金额"].sum()
    else:
        prev = None
    lines.append("| 品牌 | SKU数 | 库存数量 | 库存金额 | 占比 | 周变化 |")
    lines.append("|---|---:|---:|---:|---:|---|")
    total = cur["库存金额"].sum()
    for brand, row in cur.iterrows():
        pct = row["库存金额"] / total * 100 if total else 0
        delta = fmt_delta(row["库存金额"], prev.get(brand, 0) if prev is not None else None) if prev is not None else ""
        lines.append(f"| {brand} | {int(row['SKU数'])} | {int(row['库存数量']):,} | {fmt_money(row['库存金额'])} | {pct:.1f}% | {delta.strip(' ()')} |")
    return "\n".join(lines) + "\n"


def section_top_money(df, prev_df):
    top = df.nlargest(20, "库存金额").copy()
    lines = ["\n## 三、Top 20 资金占用 SKU\n"]
    if prev_df is not None:
        prev_money = prev_df.set_index("货品编号")["库存金额"].to_dict()
        prev_top_codes = set(prev_df.nlargest(20, "库存金额")["货品编号"])
    else:
        prev_money, prev_top_codes = {}, set()
    lines.append("| 货品编号 | 名称 | 库存 | 库存金额 | 支撑天数 | 周变化 | 标记 |")
    lines.append("|---|---|---:|---:|---:|---|---|")
    cur_codes = set(top["货品编号"])
    for _, r in top.iterrows():
        code = r["货品编号"]
        name = str(r["货品名称"])[:30]
        days = "" if pd.isna(r["支撑天数"]) else f"{r['支撑天数']:.0f}"
        delta = ""
        flag = ""
        if prev_df is not None:
            prev_amt = prev_money.get(code)
            if prev_amt is not None:
                delta = fmt_delta(r["库存金额"], prev_amt).strip(" ()")
                if code not in prev_top_codes:
                    flag = "🆕 新晋"
            else:
                flag = "🆕 新晋"
        lines.append(f"| {code} | {name} | {int(r['库存数量']):,} | {fmt_money(r['库存金额'])} | {days} | {delta} | {flag} |")
    # 掉出 top20 的
    if prev_df is not None:
        dropped = prev_top_codes - cur_codes
        if dropped:
            lines.append("\n**本周掉出 Top 20**：")
            for code in dropped:
                row = prev_df[prev_df["货品编号"] == code].iloc[0]
                cur_row = df[df["货品编号"] == code]
                cur_amt = cur_row["库存金额"].iloc[0] if len(cur_row) else 0
                lines.append(f"- {code} {str(row['货品名称'])[:30]}: 上周 {fmt_money(row['库存金额'])} → 本周 {fmt_money(cur_amt)}")
    return "\n".join(lines) + "\n"


def section_movers(df, prev_df):
    if prev_df is None:
        return ""
    cur_qty = df.set_index("货品编号")["库存数量"]
    prev_qty = prev_df.set_index("货品编号")["库存数量"]
    common = cur_qty.index.intersection(prev_qty.index)
    diff = (cur_qty.loc[common] - prev_qty.loc[common]).sort_values()
    names = df.set_index("货品编号")["货品名称"].to_dict()

    lines = ["\n## 四、周内动销 Top（库存下降 = 卖出）\n"]
    lines.append("| 货品编号 | 名称 | 上周库存 | 本周库存 | 减少 |")
    lines.append("|---|---|---:|---:|---:|")
    for code, d in diff.head(15).items():
        if d >= 0:
            continue
        lines.append(f"| {code} | {str(names.get(code, ''))[:30]} | {int(prev_qty[code]):,} | {int(cur_qty[code]):,} | {int(d):,} |")

    lines.append("\n## 五、周内补货 Top（库存上升）\n")
    lines.append("| 货品编号 | 名称 | 上周库存 | 本周库存 | 增加 |")
    lines.append("|---|---|---:|---:|---:|")
    for code, d in diff.tail(15)[::-1].items():
        if d <= 0:
            continue
        lines.append(f"| {code} | {str(names.get(code, ''))[:30]} | {int(prev_qty[code]):,} | {int(cur_qty[code]):,} | +{int(d):,} |")
    return "\n".join(lines) + "\n"


def section_red_flags(df, prev_df):
    lines = ["\n## 六、🔴 红灯清单\n"]

    # 超卖
    neg = df[df["可用库存"] < 0].sort_values("可用库存")
    lines.append(f"### 6.1 可用库存为负 ({len(neg)} 个 SKU)\n")
    if len(neg):
        lines.append("| 货品编号 | 名称 | 库存 | 可用 | 锁定待发 |")
        lines.append("|---|---|---:|---:|---:|")
        for _, r in neg.head(5).iterrows():
            lines.append(f"| {r['货品编号']} | {str(r['货品名称'])[:30]} | {int(r['库存数量'])} | {int(r['可用库存'])} | {int(r['锁定待发'])} |")

    # 7天内断货
    urgent = df[(df["支撑天数"] > 0) & (df["支撑天数"] <= 7) & (df["可用库存"] > 0)].sort_values("支撑天数")
    lines.append(f"\n### 6.2 七日内可能断货 ({len(urgent)} 个 SKU)\n")
    if len(urgent):
        lines.append("| 货品编号 | 名称 | 可用 | 支撑天数 | 采购在途 |")
        lines.append("|---|---|---:|---:|---:|")
        for _, r in urgent.head(10).iterrows():
            lines.append(f"| {r['货品编号']} | {str(r['货品名称'])[:30]} | {int(r['可用库存'])} | {r['支撑天数']:.0f} | {int(r['采购在途'])} |")

    # 重度滞销
    slow = df[(df["支撑天数"] > 365) & (df["库存金额"] > 10000)].sort_values("库存金额", ascending=False)
    lines.append(f"\n### 6.3 重度滞销（>1年周转 且 占资>1万）{len(slow)} 个\n")
    if len(slow):
        lines.append(f"占用资金 **{fmt_money(slow['库存金额'].sum())}**\n")
        lines.append("| 货品编号 | 名称 | 库存 | 库存金额 | 支撑天数 |")
        lines.append("|---|---|---:|---:|---:|")
        for _, r in slow.head(10).iterrows():
            lines.append(f"| {r['货品编号']} | {str(r['货品名称'])[:30]} | {int(r['库存数量'])} | {fmt_money(r['库存金额'])} | {r['支撑天数']:.0f} |")

    # 新增滞销（上周还有销售，本周变 0）
    if prev_df is not None:
        prev_active = set(prev_df[(prev_df["支撑天数"] > 0) & (prev_df["库存数量"] > 0)]["货品编号"])
        cur_dead = set(df[(df["支撑天数"] == 0) & (df["库存数量"] > 0)]["货品编号"])
        new_dead = (prev_active & cur_dead)
        if new_dead:
            new_dead_df = df[df["货品编号"].isin(new_dead)].nlargest(10, "库存金额")
            lines.append(f"\n### 6.4 新增滞销（上周还动 / 本周停了）{len(new_dead)} 个\n")
            lines.append("| 货品编号 | 名称 | 库存 | 库存金额 |")
            lines.append("|---|---|---:|---:|")
            for _, r in new_dead_df.iterrows():
                lines.append(f"| {r['货品编号']} | {str(r['货品名称'])[:30]} | {int(r['库存数量'])} | {fmt_money(r['库存金额'])} |")

    return "\n".join(lines) + "\n"


def summary(df, prev_df):
    total = df["库存金额"].sum()
    bushnell = df[df["品牌"] == "Bushnell 倍视能"]["库存金额"].sum()
    neg_count = (df["可用库存"] < 0).sum()
    urgent_count = ((df["支撑天数"] > 0) & (df["支撑天数"] <= 7) & (df["可用库存"] > 0)).sum()
    slow_money = df[(df["支撑天数"] > 365) & (df["库存金额"] > 10000)]["库存金额"].sum()

    delta_total = ""
    if prev_df is not None:
        delta_total = fmt_delta(total, prev_df["库存金额"].sum()).strip(" ()")

    lines = ["## 0. 执行摘要\n"]
    lines.append(f"- **库存总金额** {fmt_money(total)}" + (f"（{delta_total}）" if delta_total else ""))
    lines.append(f"- **Bushnell 占** {bushnell/total*100:.1f}%（{fmt_money(bushnell)}）")
    lines.append(f"- **超卖** {neg_count} 个 SKU | **7天断货** {urgent_count} 个 | **重度滞销资金** {fmt_money(slow_money)}")
    return "\n".join(lines) + "\n"


def find_previous(current_path: Path):
    pat = re.compile(r"(\d{4}-\d{2}-\d{2})-总库存查询\.xlsx$")
    candidates = []
    for f in current_path.parent.glob("*-总库存查询.xlsx"):
        m = pat.search(f.name)
        if m and f != current_path:
            candidates.append((m.group(1), f))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def main():
    if len(sys.argv) < 2:
        print("用法: analyze.py <current.xlsx> [previous.xlsx]")
        sys.exit(1)
    current = Path(sys.argv[1])
    if not current.exists():
        print(f"❌ 找不到文件: {current}")
        sys.exit(1)

    previous = Path(sys.argv[2]) if len(sys.argv) >= 3 else find_previous(current)
    if previous:
        print(f"✅ 对比上期: {previous.name}")
    else:
        print("ℹ️  首次运行，跳过对比")

    df = load(current)
    prev_df = load(previous) if previous else None

    today = datetime.now().strftime("%Y-%m-%d")
    parts = [
        f"---",
        f"类型: 库存周报",
        f"来源: 吉客云 总库存查询",
        f"本期快照: {current.name}",
        f"对比期: {previous.name if previous else '（首期，无对比）'}",
        f"目标位置: 03-公司/库存分析/周报/",
        f"状态: 待整理",
        f"---",
        f"",
        f"# 吉客云库存周报（{today}）",
        f"",
        summary(df, prev_df),
        section_overview(df, prev_df),
        section_brands(df, prev_df),
        section_top_money(df, prev_df),
        section_movers(df, prev_df),
        section_red_flags(df, prev_df),
    ]
    report = "\n".join(parts)

    INBOX.mkdir(parents=True, exist_ok=True)
    out = INBOX / f"{today}-吉客云库存周报.md"
    out.write_text(report, encoding="utf-8")
    print(f"📄 周报写入: {out}")
    print(f"\n----- 摘要 -----")
    print(summary(df, prev_df))


if __name__ == "__main__":
    main()
