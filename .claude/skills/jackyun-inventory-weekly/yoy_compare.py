#!/usr/bin/env python3
"""
吉客云库存同比对比（去年同期 vs 今天）
- 历史快照来源：决策 → 供应链 → 库存 → 历史库存趋势分析（按指定日期 + 库存金额）
- 当期快照来源：总库存查询（已有 analyze.py 用的同款 xlsx）

用法: yoy_compare.py <历史快照xlsx> <当期快照xlsx>
输出: _待整理/YYYY-MM-DD-吉客云库存同比.md
"""
import sys
import re
import warnings
from pathlib import Path
from datetime import datetime

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
import pandas as pd

VAULT = Path("/Users/mac/obsidian/祥子AI")
INBOX = VAULT / "_待整理"

# 把"历史趋势分析"的品牌名 → 标准化为今天的口径
BRAND_NORMALIZE = {
    "Bushnell倍视能": "Bushnell 倍视能",
    "ping": "Ping",
    "PING": "Ping",
    "Garmin佳明": "Garmin 佳明",
    "HONMA": "Honma 本间",
    "TaylorMade泰勒梅": "TaylorMade 泰勒梅",
    "卡拉威": "Callaway 卡拉威",
    "Callaway": "Callaway 卡拉威",
    "Titleist": "Titleist",
    "泰特利斯": "Titleist",
}

# 今天的 xlsx 没"品牌"列，用名称正则匹配 — 跟 analyze.py 保持一致
BRAND_PATTERNS = [
    ("Bushnell 倍视能", r"Bushnell|倍视能"),
    ("Ping", r"Ping(?![a-z])|PING"),
    ("Garmin 佳明", r"Garmin|佳明"),
    ("Honma 本间", r"Honma|本间|HONMA"),
    ("Titleist", r"Titleist|泰特利斯"),
    ("Callaway 卡拉威", r"Callaway|卡拉威|卡羅威"),
    ("PXG", r"PXG"),
    ("TaylorMade 泰勒梅", r"TaylorMade|泰勒梅"),
    ("Mizuno 美津浓", r"Mizuno|美津浓"),
    ("SWAG", r"SWAG"),
    ("GFORE", r"GFORE|G/FORE"),
    ("耐克 Nike", r"Nike|耐克"),
    ("迪士尼", r"迪士尼|Disney"),
    ("FootJoy", r"FootJoy"),
    ("Adidas 阿迪达斯", r"adidas|阿迪达斯|Adidas"),
    ("MAJESTY 玛嘉斯帝", r"MAJESTY|玛嘉斯帝"),
    ("PUMA", r"PUMA|彪马"),
    ("Saintnine", r"Saintnine"),
    ("HELIX", r"HELIX|喜力克斯"),
]


def normalize_brand(name):
    """把历史趋势的品牌名归一到当前口径"""
    if pd.isna(name):
        return "其他/未分类"
    n = str(name).strip()
    if n in BRAND_NORMALIZE:
        return BRAND_NORMALIZE[n]
    # 用 BRAND_PATTERNS 兜底
    for std, pat in BRAND_PATTERNS:
        if re.search(pat, n, re.IGNORECASE):
            return std
    return f"其他({n})"


def classify_by_name(name):
    s = str(name)
    for std, pat in BRAND_PATTERNS:
        if re.search(pat, s, re.IGNORECASE):
            return std
    return "其他/配件/二手球"


def load_history(xlsx):
    """历史快照（决策-历史库存趋势分析 导出）"""
    df = pd.read_excel(xlsx)
    date_col = [c for c in df.columns if re.match(r"\d{2}-\d{2}", str(c))]
    assert date_col, f"未找到日期列: {list(df.columns)}"
    money_col = date_col[0]
    df = df.rename(columns={money_col: "库存金额"})
    df["品牌_标准"] = df["品牌"].apply(normalize_brand)
    return df


def load_current(xlsx):
    """当期总库存查询"""
    df = pd.read_excel(xlsx)
    # 同 SKU 跨仓多行 → 聚合
    df = df.groupby("货品编号", as_index=False).agg({
        "货品名称": "first",
        "库存数量": "sum",
        "库存金额": "sum",
    })
    df["品牌_标准"] = df["货品名称"].apply(classify_by_name)
    return df


def fmt_money(x):
    return f"¥{x:,.0f}"


def fmt_delta(cur, prev):
    if prev == 0:
        return f"+∞" if cur > 0 else "—"
    diff = cur - prev
    pct = diff / abs(prev) * 100
    sign = "+" if diff >= 0 else ""
    return f"{sign}{diff:,.0f} / {sign}{pct:.1f}%"


def main():
    if len(sys.argv) < 3:
        print("用法: yoy_compare.py <历史快照xlsx> <当期快照xlsx>")
        sys.exit(1)

    hist_path = Path(sys.argv[1])
    cur_path = Path(sys.argv[2])

    hist = load_history(hist_path)
    cur = load_current(cur_path)

    hist_total = hist["库存金额"].sum()
    cur_total = cur["库存金额"].sum()

    # 品牌汇总
    hist_brand = hist.groupby("品牌_标准")["库存金额"].sum()
    cur_brand = cur.groupby("品牌_标准")["库存金额"].sum()
    all_brands = sorted(set(hist_brand.index) | set(cur_brand.index),
                        key=lambda b: -max(hist_brand.get(b, 0), cur_brand.get(b, 0)))

    today = datetime.now().strftime("%Y-%m-%d")
    # 历史快照日期从文件名拿
    m = re.search(r"(\d{4}-\d{2}-\d{2})", hist_path.name)
    hist_date = m.group(1) if m else "去年同期"

    lines = [
        "---",
        "类型: 库存同比",
        f"对比期: {hist_date} vs {today}",
        f"历史快照: {hist_path.name}",
        f"当期快照: {cur_path.name}",
        "目标位置: 03-公司/库存分析/同比/",
        "状态: 待整理",
        "---",
        "",
        f"# 吉客云库存同比对比 · {hist_date} → {today}",
        "",
        "## 0. 一句话结论",
        "",
        f"- 库存总金额: **{fmt_money(hist_total)} → {fmt_money(cur_total)}**（{fmt_delta(cur_total, hist_total)}）",
        f"- 历史快照口径: 决策-历史库存趋势分析（按当日库存金额，仓库×SKU 拆开 {len(hist):,} 行）",
        f"- 当期快照口径: 总库存查询（按 SKU 聚合 {len(cur):,} 行）",
        "",
        "> ⚠️ 两份数据源不同，金额数字可能有 ±5% 系统口径差。趋势方向可靠，绝对值参考。",
        "",
        "## 1. 品牌结构同比",
        "",
        "| 品牌 | 去年同期 | 当期 | 同比变化 |",
        "|---|---:|---:|---|",
    ]
    # 只展示金额 > 1 万 的品牌
    for b in all_brands:
        h = hist_brand.get(b, 0)
        c = cur_brand.get(b, 0)
        if max(h, c) < 10000:
            continue
        lines.append(f"| {b} | {fmt_money(h)} | {fmt_money(c)} | {fmt_delta(c, h)} |")

    # 新增/消失品牌
    lines.append("")
    lines.append("## 2. 关键变化")
    lines.append("")
    # 品牌大涨大跌 Top
    deltas = []
    for b in all_brands:
        h = hist_brand.get(b, 0)
        c = cur_brand.get(b, 0)
        if max(h, c) < 50000:
            continue
        deltas.append((b, h, c, c - h))
    deltas.sort(key=lambda x: x[3])
    lines.append("### 2.1 缩水最多 Top 5")
    lines.append("")
    lines.append("| 品牌 | 去年 | 当期 | 减少 |")
    lines.append("|---|---:|---:|---:|")
    for b, h, c, d in deltas[:5]:
        if d >= 0: break
        lines.append(f"| {b} | {fmt_money(h)} | {fmt_money(c)} | {fmt_money(d)} |")

    lines.append("")
    lines.append("### 2.2 增长最多 Top 5")
    lines.append("")
    lines.append("| 品牌 | 去年 | 当期 | 增加 |")
    lines.append("|---|---:|---:|---:|")
    for b, h, c, d in deltas[::-1][:5]:
        if d <= 0: break
        lines.append(f"| {b} | {fmt_money(h)} | {fmt_money(c)} | +{fmt_money(d)} |")

    # SKU 集中度
    lines.append("")
    lines.append("## 3. 集中度变化")
    lines.append("")
    bushnell_h = hist_brand.get("Bushnell 倍视能", 0)
    bushnell_c = cur_brand.get("Bushnell 倍视能", 0)
    lines.append(f"- **Bushnell 占比**: {bushnell_h/hist_total*100:.1f}% → {bushnell_c/cur_total*100:.1f}%")
    garmin_h = hist_brand.get("Garmin 佳明", 0)
    garmin_c = cur_brand.get("Garmin 佳明", 0)
    lines.append(f"- **Garmin 占比**: {garmin_h/hist_total*100:.1f}% → {garmin_c/cur_total*100:.1f}%")
    ping_h = hist_brand.get("Ping", 0)
    ping_c = cur_brand.get("Ping", 0)
    lines.append(f"- **Ping 占比**: {ping_h/hist_total*100:.1f}% → {ping_c/cur_total*100:.1f}%")

    report = "\n".join(lines)
    INBOX.mkdir(parents=True, exist_ok=True)
    out = INBOX / f"{today}-吉客云库存同比.md"
    out.write_text(report, encoding="utf-8")
    print(f"📄 同比报告写入: {out}")
    print()
    print(report)


if __name__ == "__main__":
    main()
