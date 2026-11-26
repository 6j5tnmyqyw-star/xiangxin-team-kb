#!/usr/local/bin/python3
"""销售每日微信 + 飞书消息雷达预处理脚本（同步校验 + 本地脱敏降噪 + 飞书采集）。

设计目标：
1. 跨平台（Windows / macOS），仅依赖 Python 标准库（3.9+），方便 4 位销售在各自电脑 WorkBuddy 直接跑。
2. 先校验“同步前提”：
   - 微信：扫描工作区内微信导出目录，检查最新消息时间戳；若缺失或早于昨天，标出 missing/stale，
     绝不让 AI 把“没同步”当成“零遗漏”。
   - 飞书：调用 `lark-cli auth status` + `lark-cli im +messages-search`（--as user）拉取自己可见的
     群聊与私聊消息（保留 message_app_link 可点击直达链接）以及本人待办。
3. 强制本地脱敏降噪：
   - 绝不读取 `本人自查原版-勿喂AI` 目录。
   - 正则剥离 11 位手机号、微信号、精确地址、15 位以上订单号，并尝试匹配 `AI可读脱敏版` 已有代号；
     匹配不到则编为 `WX-001`、`WX-002`……
   - 写入脱敏产物后执行二次正则自检，确认 `0 手机号 / 0 长单号` 残留。

用法：
  python3 prepare_radar.py --workspace . --days 2 --followup-days 14
  python3 prepare_radar.py --workspace . --wechat-dir "./微信聊天原件" --no-feishu
  python3 prepare_radar.py --self-test
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import html
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from typing import Any

# ===================== 正则与配置 =====================
PHONE_RE = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")
LONG_ORDER_RE = re.compile(r"(?<!\d)(\d{15,})(?!\d)")
WECHAT_ID_RE = re.compile(r"(微信号|vx|wxid)[：:\s]*([A-Za-z][A-Za-z0-9_-]{4,})", re.I)
ADDR_RE = re.compile(
    r"([^\s，。,；;]{2,8}(?:省|自治区)[^\s，。,；;]{0,12}(?:市|区|县)[^\n，。,；;]{4,40}(?:路|街|道|巷|弄|号|栋|单元|室|楼)[^\n，。,；;]{0,20})"
)
CITY_STREET_RE = re.compile(
    r"([^\s，。,；;]{2,6}(?:市|区|县)[^\n，。,；;]{2,25}(?:路|街|道|大道|小区|花园|大厦|广场|栋|单元|室)[^\n，。,；;]{1,20})"
)

DATE_LINE_RE = re.compile(
    r"(?<!\d)(?P<date>20\d{2}[-/年.](?:1[0-2]|0?[1-9])[-/月.](?:3[01]|[12]\d|0?[1-9]))(?:日)?(?!\d)(?:\s+(?P<time>\d{1,2}:\d{2}(?::\d{2})?))?"
)
CODE_PREFIX_RE = re.compile(r"\b((?:SS|LC|YY|MY)-\d{3,5})\b", re.I)

NOISE_EXACT = {
    "收到", "好的", "好", "ok", "嗯", "嗯嗯", "行", "明白", "谢谢", "感谢",
    "辛苦了", "哈哈", "哈哈哈", "1", "666", "[表情]", "[动画表情]",
    "[图片]", "[语音]", "[视频]", "[文件]", "[链接]", "[sticker]",
}

BUSINESS_KEYWORDS = (
    "价", "多少钱", "优惠", "折扣", "现货", "有货", "没货", "缺货", "断码",
    "发货", "单号", "物流", "快递", "顺丰", "退", "换", "售后", "发票", "开票",
    "保修", "刻字", "定制", "测距仪", "手表", "球杆", "手套", "球包", "球",
    "倍视能", "bushnell", "佳明", "garmin", "ping", "callaway", "卡拉威",
    "taylormade", "泰勒梅", "titleist", "xxio", "honma", "fit39", "footjoy",
    "s70", "s72", "v6", "v6s", "v7s", "r50", "trackman", "下单", "拍", "付款",
    "转账", "留货", "储值", "回访", "尺码", "左右手", "差点", "预算", "送礼",
    "比价", "便宜", "考虑", "几号", "什么时候", "?", "？",
)

FORBIDDEN_DIR_KEYWORDS = ("本人自查原版", "勿喂ai", "ai可读脱敏版", "微信聊天脱敏版", "飞书消息缓存", "每日消息雷达")
WECHAT_DIR_HINTS = (
    "_私密-客户档案/微信聊天原件-勿直接喂AI",
    "_私密-客户档案/微信聊天原件",
    "微信聊天原件-勿直接喂AI",
    "微信聊天原件",
    "微信聊天记录",
    "微信记录",
    "微信聊天",
    "wechat",
    "WeChat",
)
SUPPORTED_EXTS = {".md", ".txt", ".csv", ".json", ".jsonl", ".html", ".htm", ".tsv"}


def now_local() -> dt.datetime:
    return dt.datetime.now().astimezone()


def parse_dt_from_text(text: str) -> dt.datetime | None:
    m = DATE_LINE_RE.search(text)
    if not m:
        return None
    d_raw = m.group("date").replace("年", "-").replace("月", "-").replace("日", "").replace("/", "-").replace(".", "-")
    parts = [int(p) for p in d_raw.split("-") if p]
    if len(parts) != 3:
        return None
    t_raw = m.group("time") or "00:00:00"
    t_parts = [int(p) for p in t_raw.split(":")]
    while len(t_parts) < 3:
        t_parts.append(0)
    try:
        parsed = dt.datetime(parts[0], parts[1], parts[2], t_parts[0], t_parts[1], t_parts[2])
        return parsed.replace(tzinfo=now_local().tzinfo)
    except ValueError:
        return None


def parse_any_timestamp(val: Any) -> dt.datetime | None:
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)):
        ts = float(val)
        if ts > 1e12:
            ts /= 1000.0
        try:
            return dt.datetime.fromtimestamp(ts, tz=now_local().tzinfo)
        except (ValueError, OSError):
            return None
    s = str(val).strip()
    if s.isdigit():
        return parse_any_timestamp(int(s))
    try:
        iso = s.replace("Z", "+00:00")
        d = dt.datetime.fromisoformat(iso)
        if d.tzinfo is None:
            d = d.replace(tzinfo=now_local().tzinfo)
        return d.astimezone(now_local().tzinfo)
    except ValueError:
        pass
    return parse_dt_from_text(s)


def desensitize_text(text: str, extra_names: set[str] | None = None) -> str:
    if not text:
        return ""
    out = PHONE_RE.sub("[手机已脱敏]", text)
    out = LONG_ORDER_RE.sub("[单号已脱敏]", out)
    out = WECHAT_ID_RE.sub(r"\1:[微信号已脱敏]", out)
    out = ADDR_RE.sub("[地址已脱敏]", out)
    out = CITY_STREET_RE.sub("[地址已脱敏]", out)
    if extra_names:
        for nm in sorted(extra_names, key=len, reverse=True):
            if len(nm) >= 2:
                out = out.replace(nm, "[客户]")
    return out


def verify_no_pii(text: str) -> dict[str, int]:
    return {
        "phones": len(PHONE_RE.findall(text)),
        "long_orders": len(LONG_ORDER_RE.findall(text)),
    }


def is_noise_message(content: str) -> bool:
    s = content.strip()
    if not s:
        return True
    if s.lower() in NOISE_EXACT:
        return True
    if len(s) <= 2 and not any(k in s for k in ("?", "？", "货", "价", "单", "买", "退")):
        return True
    return False


def has_business_signal(content: str) -> bool:
    low = content.lower()
    return any(kw in low for kw in BUSINESS_KEYWORDS)


def load_known_codes(workspace: pathlib.Path) -> dict[str, str]:
    """只读 AI可读脱敏版 里的客户编号索引（绝不碰 本人自查原版-勿喂AI）。"""
    code_map: dict[str, str] = {}
    safe_dir = workspace / "_私密-客户档案" / "AI可读脱敏版"
    if not safe_dir.exists():
        return code_map
    for p in safe_dir.glob("*.md"):
        m = CODE_PREFIX_RE.search(p.stem)
        if m:
            code = m.group(1).upper()
            code_map[code] = code
    return code_map


def find_wechat_dirs(workspace: pathlib.Path, explicit_dir: str | None) -> list[pathlib.Path]:
    if explicit_dir:
        p = pathlib.Path(explicit_dir).expanduser()
        if not p.is_absolute():
            p = (workspace / p).resolve()
        return [p] if p.exists() else []
    found: list[pathlib.Path] = []
    for rel in WECHAT_DIR_HINTS:
        cand = workspace / rel
        if cand.exists() and cand.is_dir():
            found.append(cand)
    # 兼容个人 Obsidian 库里含「微信」字样的子目录（排除禁止目录和自身输出目录）
    for p in workspace.iterdir():
        if not p.is_dir():
            continue
        low = p.name.lower()
        if any(bad in low for bad in FORBIDDEN_DIR_KEYWORDS) or p.name in ("团队知识库", ".git", ".workbuddy"):
            continue
        if ("微信" in p.name or "wechat" in low) and p not in found:
            found.append(p)
    return found


def safe_conv_code(raw_name: str, known_codes: dict[str, str], seen_aliases: dict[str, str]) -> str:
    m = CODE_PREFIX_RE.search(raw_name)
    if m:
        code = m.group(1).upper()
        return code
    if raw_name in seen_aliases:
        return seen_aliases[raw_name]
    idx = len(seen_aliases) + 1
    alias = f"WX-{idx:03d}"
    seen_aliases[raw_name] = alias
    return alias


def parse_wechat_file(path: pathlib.Path) -> list[dict[str, Any]]:
    """支持 .md/.txt/.csv/.tsv/.json/.jsonl/.html 常见微信导出格式，返回统一消息字典列表。"""
    ext = path.suffix.lower()
    conv_guess = path.stem
    msgs: list[dict[str, Any]] = []
    fallback_dt = dt.datetime.fromtimestamp(path.stat().st_mtime, tz=now_local().tzinfo)

    if ext in {".json", ".jsonl"}:
        try:
            raw = path.read_text(encoding="utf-8", errors="ignore").strip()
            items: list[Any] = []
            if ext == ".jsonl" or (raw.startswith("{") and "\n{" in raw):
                for line in raw.splitlines():
                    line = line.strip()
                    if line:
                        items.append(json.loads(line))
            else:
                obj = json.loads(raw)
                if isinstance(obj, list):
                    items = obj
                elif isinstance(obj, dict):
                    for key in ("messages", "data", "list", "chats", "records"):
                        if isinstance(obj.get(key), list):
                            items = obj[key]
                            break
                    if not items:
                        items = [obj]
            for it in items:
                if not isinstance(it, dict):
                    continue
                t = (
                    parse_any_timestamp(it.get("createTime") or it.get("timestamp") or it.get("StrTime") or it.get("time") or it.get("date"))
                    or fallback_dt
                )
                sender = str(it.get("sender") or it.get("senderName") or it.get("talkerName") or it.get("role") or "?")
                is_self = bool(it.get("isSender") or it.get("isSelf") or it.get("is_mine"))
                conv = str(it.get("conversation") or it.get("talker") or it.get("remark") or it.get("nickName") or conv_guess)
                body = str(it.get("content") or it.get("StrContent") or it.get("text") or it.get("msg") or "").strip()
                if body:
                    msgs.append({"conv": conv, "time": t, "sender": "我" if is_self else sender, "is_self": is_self, "content": body})
        except Exception:
            pass
        return msgs

    if ext in {".csv", ".tsv"}:
        delim = "\t" if ext == ".tsv" else ","
        try:
            with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as f:
                reader = csv.DictReader(f, delimiter=delim)
                for row in reader:
                    t = (
                        parse_any_timestamp(row.get("StrTime") or row.get("CreateTime") or row.get("time") or row.get("时间") or row.get("日期"))
                        or fallback_dt
                    )
                    is_self = str(row.get("IsSender") or row.get("is_sender") or row.get("是否本人") or "").strip() in {"1", "true", "True", "是", "我"}
                    sender = str(row.get("Sender") or row.get("NickName") or row.get("发送人") or ("我" if is_self else "客户")).strip()
                    conv = str(row.get("Remark") or row.get("Talker") or row.get("NickName") or row.get("会话") or row.get("客户") or conv_guess).strip()
                    body = str(row.get("StrContent") or row.get("Content") or row.get("内容") or row.get("消息") or "").strip()
                    if body:
                        msgs.append({"conv": conv, "time": t, "sender": "我" if is_self else sender, "is_self": is_self, "content": body})
        except Exception:
            pass
        return msgs

    raw_text = path.read_text(encoding="utf-8", errors="ignore")
    if ext in {".html", ".htm"}:
        raw_text = re.sub(r"<br\s*/?>", "\n", raw_text, flags=re.I)
        raw_text = re.sub(r"<[^>]+>", " ", raw_text)
        raw_text = html.unescape(raw_text)

    # 跳过 markdown frontmatter
    lines = raw_text.splitlines()
    if lines and lines[0].strip() == "---":
        for i in range(1, min(len(lines), 40)):
            if lines[i].strip() == "---":
                lines = lines[i + 1 :]
                break

    current_dt: dt.datetime | None = None
    for line in lines:
        s = line.strip()
        if not s:
            continue
        parsed_dt = parse_dt_from_text(s)
        if parsed_dt:
            current_dt = parsed_dt
            # 支持 "2026-11-25 14:20 张三: 内容" 单行格式
            rest = DATE_LINE_RE.sub("", s, count=1).strip(" []:|-")
            if rest:
                sender, body = split_sender_body(rest)
                is_self = sender in {"我", "自己", "客服", "销售", "me", "Me"}
                msgs.append({"conv": conv_guess, "time": current_dt, "sender": "我" if is_self else sender, "is_self": is_self, "content": body})
            continue
        if current_dt is not None:
            sender, body = split_sender_body(s)
            is_self = sender in {"我", "自己", "客服", "销售", "me", "Me"}
            msgs.append({"conv": conv_guess, "time": current_dt, "sender": "我" if is_self else sender, "is_self": is_self, "content": body})

    # 若文本里没有任何日期行，至少保留一条占位供上层判断为“缺时间戳/仅文件名mtime”
    if not msgs and lines:
        joined = " ".join(lines[:30]).strip()
        if joined:
            msgs.append({"conv": conv_guess, "time": fallback_dt, "sender": "未知", "is_self": False, "content": joined[:300], "mtime_only": True})
    return msgs


def split_sender_body(text: str) -> tuple[str, str]:
    for sep in ("：", ":"):
        if sep in text:
            left, right = text.split(sep, 1)
            if 1 <= len(left.strip()) <= 20 and right.strip():
                return left.strip(), right.strip()
    return "客户", text.strip()


def process_wechat(workspace: pathlib.Path, explicit_dir: str | None, days: int, followup_days: int) -> dict[str, Any]:
    now = now_local()
    yesterday_start = (now - dt.timedelta(days=max(days - 1, 0))).replace(hour=0, minute=0, second=0, microsecond=0)
    followup_start = (now - dt.timedelta(days=followup_days)).replace(hour=0, minute=0, second=0, microsecond=0)

    dirs = find_wechat_dirs(workspace, explicit_dir)
    if not dirs:
        return {
            "status": "missing",
            "reason": "未在工作区找到微信聊天记录导出目录",
            "dirs_checked": [str(workspace / rel) for rel in WECHAT_DIR_HINTS[:4]],
            "latest_dt": None,
            "recent_convs": [],
            "followup_convs": [],
            "output_md": "",
        }

    known_codes = load_known_codes(workspace)
    seen_aliases: dict[str, str] = {}
    all_msgs: list[dict[str, Any]] = []
    file_count = 0

    for d in dirs:
        for p in sorted(d.rglob("*")):
            if not p.is_file() or p.suffix.lower() not in SUPPORTED_EXTS:
                continue
            low_path = str(p).lower()
            if any(bad in low_path for bad in FORBIDDEN_DIR_KEYWORDS):
                continue
            file_count += 1
            all_msgs.extend(parse_wechat_file(p))

    if file_count == 0 or not all_msgs:
        return {
            "status": "missing",
            "reason": f"扫描了 {len(dirs)} 个目录但未读到有效微信聊天记录（支持 md/txt/csv/json/html）",
            "dirs_checked": [str(d) for d in dirs],
            "latest_dt": None,
            "recent_convs": [],
            "followup_convs": [],
            "output_md": "",
        }

    # 只信真实消息里解析出的非 mtime 兜底时间；若全无显式日期则退回 mtime 并标注
    explicit_times = [m["time"] for m in all_msgs if not m.get("mtime_only")]
    latest_dt = max(explicit_times) if explicit_times else max(m["time"] for m in all_msgs)
    yesterday_date = (now - dt.timedelta(days=1)).date()
    status = "ok" if latest_dt.date() >= yesterday_date else "stale"

    # 按会话分组并脱敏降噪
    by_conv: dict[str, list[dict[str, Any]]] = {}
    for m in all_msgs:
        if m["time"] < followup_start:
            continue
        if is_noise_message(m["content"]):
            continue
        code = safe_conv_code(m["conv"], known_codes, seen_aliases)
        raw_sender = m["sender"]
        extra_names = {m["conv"]} if not CODE_PREFIX_RE.search(m["conv"]) else set()
        if raw_sender not in {"我", "客户", "未知"}:
            extra_names.add(raw_sender)
        safe_body = desensitize_text(m["content"], extra_names=extra_names)
        by_conv.setdefault(code, []).append({
            "time": m["time"],
            "sender": "我" if m["is_self"] else code,
            "is_self": m["is_self"],
            "content": safe_body[:300],
        })

    recent_lines: list[str] = []
    followup_lines: list[str] = []
    recent_count = 0
    followup_count = 0

    for code, cmsgs in sorted(by_conv.items()):
        cmsgs.sort(key=lambda x: x["time"])
        last_msg = cmsgs[-1]
        in_recent = last_msg["time"] >= yesterday_start
        has_biz = any(has_business_signal(x["content"]) for x in cmsgs)
        if not in_recent and not has_biz:
            continue

        tail = cmsgs[-8:]
        unreplied_hint = "⚠️ 客户最后发言未接" if not last_msg["is_self"] else "我方已收口/待对方回复"
        block = [f"### {code}（最新：{last_msg['time']:%Y-%m-%d %H:%M}｜{unreplied_hint}）"]
        for x in tail:
            block.append(f"- `{x['time']:%m-%d %H:%M}` {x['sender']}：{x['content']}")
        block_text = "\n".join(block)

        if in_recent:
            recent_count += 1
            recent_lines.append(block_text)
        elif has_biz:
            followup_count += 1
            followup_lines.append(block_text)

    md_parts = [
        f"# 微信聊天脱敏降噪摘要（{now:%Y-%m-%d %H:%M}）",
        "",
        f"- **同步状态**：`{status}`（扫描目录 {len(dirs)} 个 / 文件 {file_count} 份 / 最新消息时间 `{latest_dt:%Y-%m-%d %H:%M}`）",
        f"- **近 {days} 天活跃会话**：{recent_count} 个｜**近 {followup_days} 天业务待跟进会话**：{followup_count} 个",
        "",
    ]
    if status == "stale":
        md_parts.append(f"> ⚠️ **警告**：最新微信记录停在 `{latest_dt:%Y-%m-%d}`，请先在手机微信「设置 → 通用 → 聊天记录管理 → 导入与导出 → 导出到电脑」同步后再重扫！\n")

    md_parts.append("## 一、近 2 天会话（防漏回重点）\n")
    md_parts.append("\n\n".join(recent_lines) if recent_lines else "（近 2 天无有效脱敏会话）")
    md_parts.append(f"\n\n## 二、近 {followup_days} 天带业务关键词的历史会话（抓跟进商机）\n")
    md_parts.append("\n\n".join(followup_lines[:40]) if followup_lines else "（无额外历史业务会话）")
    md_text = "\n".join(md_parts) + "\n"

    pii_check = verify_no_pii(md_text)
    if pii_check["phones"] > 0 or pii_check["long_orders"] > 0:
        md_text = desensitize_text(md_text)
        pii_check = verify_no_pii(md_text)

    return {
        "status": status,
        "dirs_checked": [str(d) for d in dirs],
        "file_count": file_count,
        "latest_dt": latest_dt.strftime("%Y-%m-%d %H:%M"),
        "recent_count": recent_count,
        "followup_count": followup_count,
        "pii_check": pii_check,
        "output_md": md_text,
    }


# ===================== 飞书采集 =====================
def lark_env() -> dict[str, str]:
    env = os.environ.copy()
    env["LARK_CLI_NO_PROXY"] = "1"
    return env


def run_lark_json(args: list[str]) -> dict[str, Any] | None:
    try:
        r = subprocess.run(["lark-cli"] + args, capture_output=True, text=True, env=lark_env(), timeout=90)
    except FileNotFoundError:
        return {"_error": "未安装 lark-cli"}
    except subprocess.TimeoutExpired:
        return {"_error": "lark-cli 超时"}
    raw = (r.stdout or "").strip()
    if not raw:
        return {"_error": (r.stderr or "空返回")[:200]}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"_error": f"非 JSON 返回: {raw[:200]}"}


def process_feishu(days: int) -> dict[str, Any]:
    auth = run_lark_json(["auth", "status"])
    if not auth or auth.get("_error"):
        return {"status": "missing", "reason": auth.get("_error", "lark-cli 异常") if auth else "lark-cli 异常", "output_md": ""}

    user_info = (auth.get("identities") or {}).get("user") or {}
    if not user_info.get("available") or user_info.get("tokenStatus") == "expired":
        return {
            "status": "unauthenticated",
            "reason": "飞书 user 登录态不可用，请先运行 `lark-cli auth login` 用本人飞书账号扫码登录",
            "output_md": "",
        }

    my_open_id = user_info.get("openId", "")
    my_name = user_info.get("userName", "当前用户")

    now = now_local()
    start_dt = (now - dt.timedelta(days=max(days - 1, 0))).replace(hour=0, minute=0, second=0, microsecond=0)
    start_iso = start_dt.isoformat(timespec="seconds")
    end_iso = now.isoformat(timespec="seconds")

    all_msgs: list[dict[str, Any]] = []
    errors: list[str] = []
    counts = {"group": 0, "p2p": 0}
    for ctype in ("group", "p2p"):
        res = run_lark_json([
            "im", "+messages-search",
            "--query", "",
            "--chat-type", ctype,
            "--exclude-sender-type", "bot",
            "--start", start_iso,
            "--end", end_iso,
            "--page-size", "50",
            "--page-all",
            "--format", "json",
            "--as", "user",
        ])
        if not res or res.get("_error") or not res.get("ok"):
            err = (res or {}).get("_error") or (res or {}).get("error") or str(res)[:150]
            errors.append(f"{ctype}: {err}")
            continue
        items = (res.get("data") or {}).get("messages") or []
        counts[ctype] = len(items)
        all_msgs.extend(items)

    # 拉取本人未完待办
    tasks_res = run_lark_json(["task", "+get-my-tasks", "--format", "json", "--as", "user"])
    open_tasks: list[str] = []
    if tasks_res and tasks_res.get("ok"):
        for t in ((tasks_res.get("data") or {}).get("items") or (tasks_res.get("data") or {}).get("tasks") or []):
            if not isinstance(t, dict) or t.get("completed_at"):
                continue
            summary = desensitize_text(str(t.get("summary") or ""))
            due = (t.get("due") or {}).get("timestamp") or ""
            url = t.get("url") or ""
            link_part = f" — [任务]({url})" if url else ""
            open_tasks.append(f"- {summary}" + (f"（截止 {due[:10]}）" if due else "") + link_part)

    grouped: dict[str, list[dict[str, Any]]] = {}
    at_me_count = 0
    for m in all_msgs:
        sender = (m.get("sender") or {}).get("name") or "?"
        sender_id = (m.get("sender") or {}).get("id") or ""
        mentions = m.get("mentions") or []
        at_me = any(x.get("id") == my_open_id for x in mentions)
        if at_me:
            at_me_count += 1
        is_mine = bool(my_open_id and sender_id == my_open_id)
        ctype = m.get("chat_type") or ""
        cname = m.get("chat_name") or ""
        if not cname:
            partner = (m.get("chat_partner") or {}).get("name")
            cname = f"私聊·{partner}" if partner else (f"私聊·{sender}" if ctype == "p2p" else m.get("chat_id", "未知群"))
        body = desensitize_text((m.get("content") or "").strip().replace("\n", " "))[:280]
        if is_noise_message(body) and not at_me:
            continue
        grouped.setdefault(cname, []).append({
            "time": str(m.get("create_time") or "")[-8:],
            "sender": sender,
            "is_mine": is_mine,
            "at_me": at_me,
            "body": body,
            "link": m.get("message_app_link") or "",
        })

    lines = [
        f"# 飞书聊天与待办缓存（{my_name}｜{now:%Y-%m-%d %H:%M}）",
        "",
        f"- **时间窗**：`{start_iso}` → `{end_iso}`",
        f"- **原始采集**：群聊 `{counts['group']}` 条 / 私聊 `{counts['p2p']}` 条 / `@我` `{at_me_count}` 条 / 活跃会话 `{len(grouped)}` 个",
    ]
    if errors:
        lines.append(f"- **⚠️ 采集告警**：{'; '.join(errors)}")
    lines.append("\n## 一、待办清单（未完成前 25 条）\n")
    lines.append("\n".join(open_tasks[:25]) if open_tasks else "（无未完成待办或无读取权限）")
    lines.append("\n\n## 二、飞书群聊与私聊消息流（带直达链接）\n")

    for cname, msgs in sorted(grouped.items(), key=lambda kv: (-any(x["at_me"] for x in kv[1]), -len(kv[1]))):
        lines.append(f"### {cname}（{len(msgs)} 条）")
        for x in msgs[-30:]:
            tags = []
            if x["at_me"]:
                tags.append("@了我")
            if x["is_mine"]:
                tags.append("我发的")
            tag_str = f" [{' '.join(tags)}]" if tags else ""
            link_str = f" — [打开]({x['link']})" if x["link"] else ""
            lines.append(f"- `{x['time']}` {x['sender']}: {x['body']}{tag_str}{link_str}")
        lines.append("")

    md_text = "\n".join(lines) + "\n"
    return {
        "status": "ok" if not errors else "partial",
        "user": my_name,
        "group_count": counts["group"],
        "p2p_count": counts["p2p"],
        "at_me_count": at_me_count,
        "chats_count": len(grouped),
        "open_tasks_count": len(open_tasks),
        "errors": errors,
        "output_md": md_text,
    }


def write_outputs(workspace: pathlib.Path, wechat_res: dict[str, Any], feishu_res: dict[str, Any]) -> dict[str, str]:
    today = now_local().strftime("%Y-%m-%d")
    saved: dict[str, str] = {}
    if wechat_res.get("output_md"):
        dst = workspace / "_私密-客户档案" / "微信聊天脱敏版" / f"daily_scan_{today}.md"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(wechat_res["output_md"], encoding="utf-8")
        saved["wechat_md"] = str(dst)
    if feishu_res.get("output_md"):
        dst = workspace / "_私密-客户档案" / "飞书消息缓存" / f"feishu_scan_{today}.md"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(feishu_res["output_md"], encoding="utf-8")
        saved["feishu_md"] = str(dst)
    return saved


def self_test() -> int:
    """用模拟微信聊天数据自检脱敏、新鲜度判断、噪声过滤与文件输出。"""
    with tempfile.TemporaryDirectory() as tmp:
        ws = pathlib.Path(tmp)
        raw_dir = ws / "_私密-客户档案" / "微信聊天原件-勿直接喂AI"
        raw_dir.mkdir(parents=True)
        (ws / "_私密-客户档案" / "AI可读脱敏版").mkdir(parents=True)
        (ws / "_私密-客户档案" / "AI可读脱敏版" / "SS-0088-老客户.md").write_text("# SS-0088\n", encoding="utf-8")

        today = now_local().strftime("%Y-%m-%d")
        fake_phone = "138" + "1234" + "5678"
        fake_order = "123456789" * 2
        sample_chat = (
            f"{today} 10:15 李总: 你好，我手机{fake_phone}，地址广东省深圳市南山区科技园路88号3栋502室，帮我查下倍视能V6S现货多少钱？\n"
            f"{today} 10:16 我: 收到\n"
            f"{today} 10:18 李总: 还有我上次那个订单{fake_order}到哪了？微信号wxid_abc12345\n"
        )
        (raw_dir / "SS-0088-李总.md").write_text(sample_chat, encoding="utf-8")

        res = process_wechat(ws, None, days=2, followup_days=14)
        assert res["status"] == "ok", f"期望 status=ok，实际 {res}"
        assert res["pii_check"]["phones"] == 0, "手机号未完全脱敏"
        assert res["pii_check"]["long_orders"] == 0, "长订单号未完全脱敏"
        assert fake_phone not in res["output_md"]
        assert fake_order not in res["output_md"]
        assert "wxid_abc12345" not in res["output_md"]
        assert "SS-0088" in res["output_md"]
        assert "倍视能V6S" in res["output_md"]

        # 测试过期数据检测
        old_dir = ws / "old_wechat"
        old_dir.mkdir()
        (old_dir / "old.txt").write_text("2026-10-01 09:00 张哥: 问一下S72价格\n", encoding="utf-8")
        stale_res = process_wechat(ws, str(old_dir), days=2, followup_days=60)
        assert stale_res["status"] == "stale", f"期望 stale，实际 {stale_res['status']}"

        print("SELF-TEST PASSED:", json.dumps({
            "ok_status": res["status"],
            "pii_check": res["pii_check"],
            "stale_status": stale_res["status"],
        }, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="销售每日微信+飞书消息雷达预处理")
    parser.add_argument("--workspace", default=".", help="销售个人工作区根目录（默认当前目录）")
    parser.add_argument("--wechat-dir", default=None, help="显式指定微信导出目录（可选）")
    parser.add_argument("--days", type=int, default=2, help="防漏回窗口天数（默认 2=昨天+今天）")
    parser.add_argument("--followup-days", type=int, default=14, help="跟进商机窗口天数（默认 14）")
    parser.add_argument("--no-wechat", action="store_true", help="跳过微信扫描")
    parser.add_argument("--no-feishu", action="store_true", help="跳过飞书采集")
    parser.add_argument("--dry-run", action="store_true", help="只输出检查摘要，不写缓存文件")
    parser.add_argument("--self-test", action="store_true", help="运行内置自检")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    ws = pathlib.Path(args.workspace).expanduser().resolve()
    wechat_res = {"status": "skipped"} if args.no_wechat else process_wechat(ws, args.wechat_dir, args.days, args.followup_days)
    feishu_res = {"status": "skipped"} if args.no_feishu else process_feishu(args.days)

    saved = {} if args.dry_run else write_outputs(ws, wechat_res, feishu_res)
    summary = {
        "workspace": str(ws),
        "team_kb_exists": (ws / "团队知识库").exists(),
        "wechat": {k: v for k, v in wechat_res.items() if k != "output_md"},
        "feishu": {k: v for k, v in feishu_res.items() if k != "output_md"},
        "saved_files": saved,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
