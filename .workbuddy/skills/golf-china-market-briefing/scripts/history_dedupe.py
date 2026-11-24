#!/usr/bin/env python3
"""跨平台（Win/Mac/Linux）中国区高尔夫市场日报去重与归档工具。

零第三方依赖，仅使用 Python 3 标准库。
默认数据存放在当前工作空间的 `_我的笔记/高尔夫中国区市场日报/`，避免污染只读的 `团队知识库/`。

用法示例：
  # 1. 查看近 14 天已推送过的条目（写简报前先跑）
  python3 history_dedupe.py list --days 14

  # 2. 记录今日已推条目并归档简报正文
  python3 history_dedupe.py record \
    --date 2026-11-25 \
    --items-json '[{"key":"Callaway-2026世界杯限量一号木","brand":"Callaway","title":"2026世界杯限量一号木中国区发售","url":"https://..."}]' \
    --briefing-file /tmp/today.md
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
from pathlib import Path


def default_archive_dir() -> Path:
    return Path.cwd() / "_我的笔记" / "高尔夫中国区市场日报"


def history_file(archive_dir: Path) -> Path:
    return archive_dir / "_pushed_history.jsonl"


def load_entries(hfile: Path) -> list[dict]:
    if not hfile.exists():
        return []
    entries: list[dict] = []
    for line in hfile.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def cmd_list(args: argparse.Namespace) -> int:
    archive_dir = Path(args.archive_dir) if args.archive_dir else default_archive_dir()
    hfile = history_file(archive_dir)
    entries = load_entries(hfile)
    cutoff = (dt.date.today() - dt.timedelta(days=args.days)).isoformat()
    recent = [e for e in entries if str(e.get("date", "")) >= cutoff]

    if args.json:
        print(json.dumps({"archive_dir": str(archive_dir), "days": args.days, "count": len(recent), "items": recent}, ensure_ascii=False, indent=2))
        return 0

    if not recent:
        print(f"[去重库] 近 {args.days} 天暂无已推送记录（目录：{archive_dir}）。")
        return 0

    print(f"[去重库] 近 {args.days} 天已推送 {len(recent)} 条（以下内容如无实质新进展请勿重复）：")
    for e in recent:
        date_s = e.get("date", "?")
        brand = e.get("brand", "")
        title = e.get("title", "")
        key = e.get("key", "")
        print(f"- [{date_s}] ({brand}) {title}  [key: {key}]")
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    archive_dir = Path(args.archive_dir) if args.archive_dir else default_archive_dir()
    archive_dir.mkdir(parents=True, exist_ok=True)
    hfile = history_file(archive_dir)

    date_str = args.date or dt.date.today().isoformat()
    try:
        items = json.loads(args.items_json)
        if not isinstance(items, list):
            raise ValueError("items-json 必须是 JSON 数组")
    except Exception as exc:
        print(f"ERROR: 解析 --items-json 失败: {exc}", file=sys.stderr)
        return 2

    existing = load_entries(hfile)
    existing_keys = {(e.get("date"), e.get("key")) for e in existing}

    added = 0
    with hfile.open("a", encoding="utf-8") as fh:
        for item in items:
            if not isinstance(item, dict):
                continue
            key = str(item.get("key") or item.get("title") or "").strip()
            if not key or (date_str, key) in existing_keys:
                continue
            rec = {
                "date": date_str,
                "key": key,
                "brand": str(item.get("brand", "")).strip(),
                "title": str(item.get("title", key)).strip(),
                "url": str(item.get("url", "")).strip(),
                "recorded_at": dt.datetime.now().isoformat(timespec="seconds"),
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            existing_keys.add((date_str, key))
            added += 1

    archived_path = None
    if args.briefing_file:
        src = Path(args.briefing_file)
        if not src.exists():
            print(f"ERROR: 简报文件不存在: {src}", file=sys.stderr)
            return 2
        dst = archive_dir / f"{date_str}.md"
        if src.resolve() != dst.resolve():
            shutil.copyfile(src, dst)
        archived_path = str(dst)

    print(json.dumps({
        "ok": True,
        "date": date_str,
        "added": added,
        "history_file": str(hfile),
        "archived_briefing": archived_path,
    }, ensure_ascii=False))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="中国区高尔夫市场日报去重与归档工具")
    parser.add_argument("--archive-dir", default=None, help="自定义归档目录（默认 ./_我的笔记/高尔夫中国区市场日报）")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="列出近 N 天已推送条目")
    p_list.add_argument("--days", type=int, default=14, help="回看天数，默认 14")
    p_list.add_argument("--json", action="store_true", help="输出 JSON 格式")
    p_list.set_defaults(func=cmd_list)

    p_rec = sub.add_parser("record", help="写入今日推送记录并归档简报 md")
    p_rec.add_argument("--date", default=None, help="日期 YYYY-MM-DD，默认今天")
    p_rec.add_argument("--items-json", required=True, help="JSON 数组，每项含 key/brand/title/url")
    p_rec.add_argument("--briefing-file", default=None, help="要归档保存的当日简报 markdown 文件路径")
    p_rec.set_defaults(func=cmd_record)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
