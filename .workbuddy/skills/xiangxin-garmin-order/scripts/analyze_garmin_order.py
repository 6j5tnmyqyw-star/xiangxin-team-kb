#!/usr/bin/env python3
"""
Garmin 佳明每周订货分析计算器（通用便携版：支持阿祥本地 Vault 自动探测，也支持采购手工导表路径）。

核心口径（2026-11-27 祥书审定）：
1. 按「货品编号 + 规格」双键拆解（同码不同色/不同表径绝不混算）。
2. 剔除取消/作废/退货/赠品，并剔除「无货品编号且大数量极低均价(>=10件且均价<50)或<=200元定金测试单」。
3. 保留正常成交的代销售需求（识别被迫转代销的真实断货需求）。
4. 品牌方（上海佳明航电）10 台起订、每周可订一次；表带均走第三方采购，不计入 10 台凑单。
5. 陈年僵尸在途（最近采购超过 90 天且近 90 天无动销）不计入可用头寸，单列异常待核清单。
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import io
import math
import pathlib
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import defaultdict


GARMIN_RE = re.compile(r"garmin|佳明", re.I)
BAD_STATUS_RE = re.compile(r"取消|作废|关闭")
REFUND_TYPE_RE = re.compile(r"退款|售后退货")


def _to_float(val, default: float = 0.0) -> float:
    if val is None:
        return default
    s = str(val).strip().replace(",", "")
    if not s or s.lower() in {"nan", "none", "null", "-"}:
        return default
    try:
        return float(s)
    except ValueError:
        return default


def _parse_date(val) -> dt.datetime | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in {"nan", "none", "nat"}:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    # Excel serial date fallback
    try:
        num = float(s)
        if 30000 < num < 70000:
            return dt.datetime(1899, 12, 30) + dt.timedelta(days=num)
    except ValueError:
        pass
    return None


def _read_xlsx_pure(path: pathlib.Path) -> list[dict[str, str]]:
    """Pure-stdlib .xlsx reader fallback when pandas/openpyxl are unavailable."""
    ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with zipfile.ZipFile(path) as zf:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall(f"{ns}si"):
                parts = [t.text or "" for t in si.iter(f"{ns}t")]
                shared.append("".join(parts))

        sheet_candidates = sorted(
            n for n in zf.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")
        )
        if not sheet_candidates:
            return []
        sroot = ET.fromstring(zf.read(sheet_candidates[0]))

        def col_idx(ref: str) -> int:
            letters = "".join(ch for ch in ref if ch.isalpha())
            idx = 0
            for ch in letters:
                idx = idx * 26 + (ord(ch.upper()) - 64)
            return max(0, idx - 1)

        matrix: list[list[str]] = []
        for row_el in sroot.iter(f"{ns}row"):
            row_vals: list[str] = []
            for c in row_el.findall(f"{ns}c"):
                r_ref = c.attrib.get("r", "")
                idx = col_idx(r_ref) if r_ref else len(row_vals)
                while len(row_vals) <= idx:
                    row_vals.append("")
                t_attr = c.attrib.get("t", "")
                if t_attr == "inlineStr":
                    txt = "".join(t.text or "" for t in c.iter(f"{ns}t"))
                else:
                    v_el = c.find(f"{ns}v")
                    raw = v_el.text if v_el is not None and v_el.text is not None else ""
                    if t_attr == "s" and raw != "":
                        txt = shared[int(raw)]
                    else:
                        txt = raw
                row_vals[idx] = txt
            if any(x.strip() for x in row_vals):
                matrix.append(row_vals)

        if not matrix:
            return []
        headers = [h.strip() for h in matrix[0]]
        out: list[dict[str, str]] = []
        for r in matrix[1:]:
            d = {}
            for i, h in enumerate(headers):
                if h:
                    d[h] = r[i] if i < len(r) else ""
            out.append(d)
        return out


def read_table(path: pathlib.Path, filter_garmin: bool = False) -> list[dict]:
    """Read .pkl, .xlsx, .csv, or .csv.gz into list[dict] with optional Garmin pre-filter."""
    suf = "".join(path.suffixes).lower()
    if path.suffix.lower() == ".pkl":
        import pandas as pd  # type: ignore

        df = pd.read_pickle(path)
        if filter_garmin and "货品名称" in df.columns:
            df = df[df["货品名称"].astype(str).str.contains(GARMIN_RE, na=False)]
        return df.to_dict(orient="records")

    if path.suffix.lower() == ".xlsx":
        try:
            import pandas as pd  # type: ignore

            df = pd.read_excel(path, sheet_name=0)
            if filter_garmin and "货品名称" in df.columns:
                df = df[df["货品名称"].astype(str).str.contains(GARMIN_RE, na=False)]
            return df.to_dict(orient="records")
        except ImportError:
            rows = _read_xlsx_pure(path)
            if filter_garmin:
                rows = [r for r in rows if GARMIN_RE.search(str(r.get("货品名称", "")))]
            return rows

    # .csv or .csv.gz
    if suf.endswith(".csv.gz"):
        opener = lambda: gzip.open(path, "rt", encoding="utf-8-sig", errors="replace")
    else:
        opener = lambda: open(path, "rt", encoding="utf-8-sig", errors="replace")

    out: list[dict] = []
    with opener() as f:
        reader = csv.DictReader(f)
        for row in reader:
            if filter_garmin and not GARMIN_RE.search(str(row.get("货品名称", ""))):
                continue
            out.append(row)
    return out


def is_strap_or_film(name: str) -> bool:
    return bool(re.search(r"表带|保护膜|钢化膜|表壳|保护壳|保护套|非原装|副厂", name))


def is_non_brand_accessory(name: str) -> bool:
    return bool(re.search(r"表带|保护膜|钢化膜|表壳|保护壳|保护套|数据线|充电线|收纳包|礼品袋|袖套|残次|样机|二手|非原装|副厂", name))


def classify_model(name: str) -> str:
    if is_strap_or_film(name):
        return "表带/保护膜(第三方)"
    if is_non_brand_accessory(name):
        return "配件/耗材"
    if "S72" in name:
        return "S72 主力新款"
    if "S70" in name:
        return "S70 老款"
    if "S50" in name:
        return "S50"
    if "R50" in name:
        return "R50 模拟器"
    if "G82" in name:
        return "G82 雷达"
    if "Z30" in name:
        return "Z30 激光"
    if "CT1" in name and "CT10" not in name:
        return "CT1 传感器"
    if "MARQ" in name:
        return "MARQ 高端"
    return "其他"


def auto_locate_vault_files(vault_root: pathlib.Path) -> tuple[pathlib.Path | None, pathlib.Path | None]:
    jky = vault_root / "03-公司/财务数据/吉客云销售"
    snap_dir = jky / "库存快照"
    raw_dir = jky / "原始明细"

    stock_file = None
    if snap_dir.exists():
        pkls = sorted(snap_dir.glob("*-仓库库存详情.pkl"))
        xlsxs = sorted(snap_dir.glob("*-仓库库存详情.xlsx"))
        stock_file = pkls[-1] if pkls else (xlsxs[-1] if xlsxs else None)

    sales_file = None
    if raw_dir.exists():
        gzs = sorted(raw_dir.glob("吉客云销售明细_全库含货品明细_*_脱敏.csv.gz"))
        if gzs:
            sales_file = gzs[-1]
    return stock_file, sales_file


def analyze(
    stock_path: pathlib.Path,
    sales_path: pathlib.Path,
    as_of_date: dt.date | None = None,
    lead_days: int = 8,
    target_days: int = 28,
) -> dict:
    stock_rows = read_table(stock_path, filter_garmin=True)
    sales_rows = read_table(sales_path, filter_garmin=True)

    # Determine cutoff from sales max date if not provided
    max_dt: dt.datetime | None = None
    parsed_sales = []
    placeholder_count = 0
    refund_count = 0

    for r in sales_rows:
        status = str(r.get("订单状态") or "")
        otype = str(r.get("订单类型") or "")
        if BAD_STATUS_RE.search(status):
            continue
        if REFUND_TYPE_RE.search(otype):
            refund_count += 1
            continue
        order_dt = _parse_date(r.get("下单时间"))
        if not order_dt:
            continue
        if max_dt is None or order_dt > max_dt:
            max_dt = order_dt
        qty = _to_float(r.get("数量"))
        amt = _to_float(r.get("金额"))
        code = str(r.get("货品编号") or "").strip()
        if code.lower() in {"nan", "none"}:
            code = ""
        name = str(r.get("货品名称") or "").strip()
        spec = str(r.get("规格") or "").strip()
        if spec.lower() in {"nan", "none"}:
            spec = ""
        is_gift = str(r.get("赠品") or "").strip() == "是"

        # Exclude placeholder/brushing/deposit rows without SKU code
        unit_amt = amt / qty if qty > 0 else amt
        is_placeholder = (not is_gift) and (
            (qty >= 10 and unit_amt < 50) or (code == "" and amt <= 200)
        )
        if is_placeholder:
            placeholder_count += 1
            continue

        # Normalize unmapped S72 stream gold 43mm if SKU title explicitly says it
        if code == "" and "S72" in name and "流光金" in spec and "43" in spec:
            code = "019942"
            spec = "流光金-43 mm"

        parsed_sales.append(
            {
                "dt": order_dt,
                "code": code or "UNMAPPED",
                "name": name,
                "spec": spec,
                "qty": qty,
                "amt": amt,
                "is_gift": is_gift,
                "is_dx": "代销" in otype,
                "order_id": str(r.get("订单编号") or ""),
            }
        )

    ref_date = as_of_date or (max_dt.date() if max_dt else dt.date.today())
    d30_start = ref_date - dt.timedelta(days=29)
    d90_start = ref_date - dt.timedelta(days=89)
    ytd_start = dt.date(ref_date.year, 1, 1)

    # Aggregate inventory by (code, spec)
    inv: dict[tuple[str, str], dict] = {}
    zombie_intransit = []

    for r in stock_rows:
        code = str(r.get("货品编号") or "").strip()
        if code.lower() in {"nan", "none"}:
            code = ""
        spec = str(r.get("规格") or "").strip()
        if spec.lower() in {"nan", "none"}:
            spec = ""
        name = str(r.get("货品名称") or "").strip()
        key = (code, spec)

        stock_q = _to_float(r.get("库存数量"))
        avail_q = _to_float(r.get("可用库存"))
        locked_q = _to_float(r.get("锁定待发"))
        intransit_q = _to_float(r.get("采购在途"))
        cost = _to_float(r.get("当前成本价"))
        val = _to_float(r.get("库存金额"))
        last_pur = _parse_date(r.get("最近采购时间"))

        if key not in inv:
            inv[key] = {
                "code": code,
                "spec": spec,
                "name": name,
                "stock": 0.0,
                "avail": 0.0,
                "locked": 0.0,
                "intransit_raw": 0.0,
                "intransit_eff": 0.0,
                "cost": 0.0,
                "stock_val": 0.0,
                "last_pur": None,
            }
        it = inv[key]
        it["stock"] += stock_q
        it["avail"] += avail_q
        it["locked"] += locked_q
        it["intransit_raw"] += intransit_q
        it["cost"] = max(it["cost"], cost)
        it["stock_val"] += val
        if last_pur and (it["last_pur"] is None or last_pur > it["last_pur"]):
            it["last_pur"] = last_pur

    # Aggregate sales by (code, spec)
    sales_agg: dict[tuple[str, str], dict] = defaultdict(
        lambda: {"name": "", "q30": 0.0, "dx30": 0.0, "gmv30": 0.0, "q90": 0.0, "ytd_q": 0.0, "ytd_gmv": 0.0, "gift30": 0.0}
    )
    for s in parsed_sales:
        key = (s["code"], s["spec"])
        sd = s["dt"].date()
        agg = sales_agg[key]
        if not agg["name"]:
            agg["name"] = s["name"]
        if s["is_gift"]:
            if sd >= d30_start:
                agg["gift30"] += s["qty"]
            continue
        if sd >= ytd_start:
            agg["ytd_q"] += s["qty"]
            agg["ytd_gmv"] += s["amt"]
        if sd >= d90_start:
            agg["q90"] += s["qty"]
        if sd >= d30_start:
            agg["q30"] += s["qty"]
            agg["gmv30"] += s["amt"]
            if s["is_dx"]:
                agg["dx30"] += s["qty"]

    # Merge & detect zombie in-transit
    all_keys = set(inv.keys()) | set(sales_agg.keys())
    brand_rows = []
    strap_rows = []

    for key in all_keys:
        i = inv.get(key, {})
        sa = sales_agg.get(key, {})
        name = i.get("name") or sa.get("name") or ""
        code, spec = key

        stock = i.get("stock", 0.0)
        avail = i.get("avail", 0.0)
        locked = i.get("locked", 0.0)
        intransit_raw = i.get("intransit_raw", 0.0)
        last_pur = i.get("last_pur")
        cost = i.get("cost", 0.0)
        stock_val = i.get("stock_val", 0.0)

        q30 = sa.get("q30", 0.0)
        dx30 = sa.get("dx30", 0.0)
        q90 = sa.get("q90", 0.0)
        ytd_q = sa.get("ytd_q", 0.0)
        ytd_gmv = sa.get("ytd_gmv", 0.0)
        gift30 = sa.get("gift30", 0.0)

        # Zombie in-transit: >0 intransit, 0 q90, last_pur older than 90 days, and (no stock or intransit wildly > stock)
        is_zombie = (
            intransit_raw > 0
            and q90 <= 0
            and (last_pur is None or (ref_date - last_pur.date()).days > 90)
            and (stock <= 1 or intransit_raw >= stock * 3)
        )
        intransit_eff = 0.0 if is_zombie else intransit_raw
        if is_zombie:
            zombie_intransit.append(
                {
                    "code": code,
                    "name": name,
                    "spec": spec,
                    "intransit": int(intransit_raw),
                    "last_pur": last_pur.strftime("%Y-%m-%d") if last_pur else "未知",
                    "est_val": round(intransit_raw * cost, 0),
                }
            )

        if stock == 0 and avail == 0 and intransit_eff == 0 and q90 == 0 and gift30 == 0:
            continue

        pos = avail + intransit_eff
        mu30 = q30 / 30.0
        cat = classify_model(name)

        # Separate straps/films/non-OEM accessories (3rd party) vs brand host/core items
        if is_strap_or_film(name) or "非原装" in spec or "副厂" in spec:
            if avail < 0 or stock > 0 or intransit_eff > 0 or gift30 > 0 or q30 > 0:
                strap_rows.append(
                    {
                        "code": code,
                        "name": name,
                        "spec": spec,
                        "stock": int(stock),
                        "avail": int(avail),
                        "locked": int(locked),
                        "intransit": int(intransit_eff),
                        "pos": int(pos),
                        "gift30": int(gift30 + q30),
                        "cost": cost,
                        "action": "🔴 立刻补卡单" if pos < 0 else ("🟡 备货观察" if pos < 10 else "🟢 充足"),
                    }
                )
            continue

        # Never reorder defective/sample/used/old-clearance SKUs
        if any(x in name for x in ("残次", "样机", "二手")) or any(x in spec for x in ("残次", "样机", "二手")):
            continue

        # Brand ordering logic
        is_old_watch = any(x in name for x in ("S70", "S50", "S40", "LILY", "Venu", "蛇年"))
        is_high_ticket = "R50" in name or "MARQ" in name

        if is_old_watch and q30 <= 1:
            grade = "⛔ 禁补清仓"
            sug = 0
        elif "R50" in name and "保护罩" not in name:
            # Cap position at 2 units
            sug = max(0, 2 - int(math.floor(pos)))
            grade = "🟡 轻补守2台" if sug > 0 else "🟢 滚动守2台"
        elif "MARQ" in name:
            grade = "⚪ 保留现货/代销" if pos >= 1 else "⚪ 按单代销"
            sug = 0
        elif mu30 > 0:
            rop = mu30 * (lead_days + 5)  # lead + 5d buffer
            target = mu30 * target_days
            need = max(0, math.ceil(target - pos))
            if pos <= rop or (dx30 >= 2 and pos < 15):
                grade = "🔴 立即补"
                sug = need
            elif pos <= rop * 1.4 or (stock <= 3 and ytd_q >= 20):
                grade = "🟡 轻补/拼单"
                sug = max(need, 3 if stock <= 3 else 0)
            else:
                grade = "🟢 够用"
                sug = 0
        else:
            grade = "🟢 无近期动销"
            sug = 0

        brand_rows.append(
            {
                "code": code,
                "name": name,
                "spec": spec,
                "cat": cat,
                "stock": int(stock),
                "avail": int(avail),
                "intransit": int(intransit_eff),
                "pos": int(pos),
                "q30": int(q30),
                "dx30": int(dx30),
                "q90": int(q90),
                "ytd_q": int(ytd_q),
                "cost": cost,
                "stock_val": stock_val,
                "grade": grade,
                "sug": int(sug),
                "est_cash": round(sug * cost, 0),
                "is_host": not is_non_brand_accessory(name),
            }
        )

    brand_rows.sort(key=lambda x: (-x["sug"] * (x["cost"] or 1), -x["q30"], -x["stock_val"]))
    strap_rows.sort(key=lambda x: (x["pos"], -x["gift30"]))

    host_order_units = sum(r["sug"] for r in brand_rows if r["is_host"])
    host_order_cash = sum(r["est_cash"] for r in brand_rows if r["is_host"] or r["sug"] > 0)

    return {
        "ref_date": ref_date.isoformat(),
        "stock_file": stock_path.name,
        "sales_file": sales_path.name,
        "placeholder_excluded": placeholder_count,
        "refund_rows": refund_count,
        "total_stock_val": sum(r["stock_val"] for r in brand_rows) + sum(_to_float(r.get("库存金额")) for r in stock_rows if is_strap_or_film(str(r.get("货品名称") or ""))),
        "host_order_units": host_order_units,
        "moq_ok": host_order_units >= 10,
        "est_order_cash": host_order_cash,
        "brand_rows": brand_rows,
        "strap_rows": strap_rows,
        "zombie_intransit": zombie_intransit,
    }


def render_markdown(res: dict) -> str:
    lines = [
        f"# Garmin 佳明每周订货分析（截至 {res['ref_date']}）",
        "",
        f"> **数据源**：库存 `{res['stock_file']}` ｜ 销售 `{res['sales_file']}`",
        f"> **数据清洗**：已剔除 {res['placeholder_excluded']} 笔无货品编码测试/占位待审核单，以及 {res['refund_rows']} 笔退款退货单；已按「货品编号 + 规格」拆色统计。",
        f"> **品牌硬规则校验**：拟向品牌方订主机合计 **{res['host_order_units']} 台**（{'✅ 满足 ≥10 台起订' if res['moq_ok'] else '⚠️ 未满 10 台起订，建议从畅销款凑单或延至下周'}），预计占款 **¥{res['est_order_cash']:,.0f}**（表带单独走第三方，不计入 10 台）。",
        "",
        "## 一、品牌方主机与原厂配件订货表（10 台起订 · 每周可订一次）",
        "",
        "| 等级 | 货品名称 | 规格 | 现货 | 在途 | 总头寸 | 30天销(代销) | 90天销 | 成本价 | 建议订货 | 预算 |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in res["brand_rows"]:
        dx_str = f"({r['dx30']})" if r["dx30"] > 0 else ""
        cost_str = f"¥{r['cost']:,.0f}" if r["cost"] > 0 else "待核"
        cash_str = f"¥{r['est_cash']:,.0f}" if r["est_cash"] > 0 else "¥0"
        lines.append(
            f"| {r['grade']} | {r['name']} | {r['spec'] or '-'} | {r['stock']} | {r['intransit']} | **{r['pos']}** | {r['q30']}{dx_str} | {r['q90']} | {cost_str} | **{r['sug']}** | {cash_str} |"
        )

    lines.extend([
        "",
        "## 二、第三方表带、保护膜与副厂配件（⚠️ 不向品牌方采购，不计入 10 台起订）",
        "",
        "| 状态 | 货品名称 | 规格 | 现货 | 可用 | 锁定 | 在途 | 头寸 | 30天消耗(含赠品) |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ])
    for r in res["strap_rows"]:
        lines.append(
            f"| {r['action']} | {r['name']} | {r['spec'] or '-'} | {r['stock']} | {r['avail']} | {r['locked']} | {r['intransit']} | **{r['pos']}** | {r['gift30']} |"
        )

    if res["zombie_intransit"]:
        lines.extend([
            "",
            "## 三、异常「僵尸在途」（已从头寸剔除，请库管核销关闭）",
            "",
            "| 货品编号 | 货品名称 | 规格 | 虚挂在途 | 最近采购时间 | 虚占成本 |",
            "|---|---|---|---:|---|---:|",
        ])
        for z in res["zombie_intransit"]:
            lines.append(
                f"| {z['code']} | {z['name']} | {z['spec'] or '-'} | {z['intransit']} | {z['last_pur']} | ¥{z['est_val']:,.0f} |"
            )

    lines.extend([
        "",
        "---",
        "> **审批门禁（Draft-Only）**：请采购核对今日实物、近期已审批未建单在途后，报祥书确认下单数量与打款金额。",
    ])
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Garmin 佳明每周订货分析")
    ap.add_argument("--stock", help="吉客云仓库库存详情/总库存查询路径 (.pkl/.xlsx)")
    ap.add_argument("--sales", help="吉客云销售明细路径 (.csv/.csv.gz/.xlsx)")
    ap.add_argument("--vault", default="/Users/mac/obsidian/祥子AI", help="知识库根目录（自动探测用）")
    ap.add_argument("--lead-days", type=int, default=8, help="采购提前期天数（默认 8 天，兼顾紧俏色）")
    ap.add_argument("--target-days", type=int, default=28, help="目标覆盖天数（默认 28 天）")
    ap.add_argument("--out", help="可选输出 Markdown 文件路径")
    args = ap.parse_args()

    stock_path = pathlib.Path(args.stock) if args.stock else None
    sales_path = pathlib.Path(args.sales) if args.sales else None
    if not stock_path or not sales_path:
        auto_st, auto_sa = auto_locate_vault_files(pathlib.Path(args.vault))
        stock_path = stock_path or auto_st
        sales_path = sales_path or auto_sa

    if not stock_path or not stock_path.exists():
        print("ERROR: 找不到库存快照文件，请通过 --stock 指定吉客云导出的仓库库存详情 .xlsx", file=sys.stderr)
        return 1
    if not sales_path or not sales_path.exists():
        print("ERROR: 找不到销售明细文件，请通过 --sales 指定吉客云导出的销售明细 .csv/.xlsx", file=sys.stderr)
        return 1

    res = analyze(stock_path, sales_path, lead_days=args.lead_days, target_days=args.target_days)
    md = render_markdown(res)
    if args.out:
        pathlib.Path(args.out).write_text(md, encoding="utf-8")
        print(f"Saved: {args.out}")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
