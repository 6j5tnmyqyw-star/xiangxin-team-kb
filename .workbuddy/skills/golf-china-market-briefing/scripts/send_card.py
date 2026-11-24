#!/usr/bin/env python3
"""跨平台飞书 CardKit 2.0 简报推送脚本（供 WorkBuddy 技能直接调用）。

零第三方依赖，仅用 Python 3 标准库 + 本机 lark-cli。
支持 --dry-run 先预览卡片 JSON，确认后再去掉 --dry-run 正式发群。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def build_card(md: str, title: str | None = None, template: str = "blue", buttons: list[tuple[str, str]] | None = None) -> dict:
    elements: list[dict] = [{"tag": "markdown", "content": md}]
    for label, url in buttons or []:
        elements.append({
            "tag": "button",
            "text": {"tag": "plain_text", "content": label},
            "type": "primary",
            "width": "fill",
            "behaviors": [{"type": "open_url", "default_url": url}],
        })
    card: dict = {
        "schema": "2.0",
        "config": {"update_multi": True},
        "body": {"elements": elements},
    }
    if title:
        card["header"] = {
            "title": {"tag": "plain_text", "content": title},
            "template": template,
        }
    return card


def main() -> int:
    ap = argparse.ArgumentParser(description="将中国区高尔夫市场简报以 CardKit 2.0 卡片发送到飞书群")
    ap.add_argument("--title", required=True, help="卡片标题")
    ap.add_argument("--template", default="blue", help="卡片颜色：blue/green/yellow/orange/red，默认 blue")
    ap.add_argument("--file", required=True, help="简报 Markdown 文件路径")
    ap.add_argument("--chat-id", default=None, help="目标飞书群 chat_id（与 --user-id 二选一）")
    ap.add_argument("--user-id", default=None, help="目标飞书用户 open_id（与 --chat-id 二选一）")
    ap.add_argument("--as", dest="identity", default="user", choices=["user", "bot"], help="lark-cli 身份，同事本机默认 user")
    ap.add_argument("--button", action="append", default=[], metavar="文字=URL", help="底部按钮，可多次传入")
    ap.add_argument("--dry-run", action="store_true", help="仅打印卡片 JSON 与发送参数，不真正发送")
    args = ap.parse_args()

    md_path = Path(args.file)
    if not md_path.exists():
        print(f"ERROR: 找不到简报文件: {md_path}", file=sys.stderr)
        return 2

    if not args.dry_run and not (args.chat_id or args.user_id):
        print("ERROR: 正式发送必须指定 --chat-id 或 --user-id", file=sys.stderr)
        return 2

    md_text = md_path.read_text(encoding="utf-8").strip()
    btns = [tuple(b.split("=", 1)) for b in args.button if "=" in b]
    card_json = json.dumps(build_card(md_text, args.title, args.template, btns or None), ensure_ascii=False)

    cmd = [
        "lark-cli", "im", "+messages-send",
        "--as", args.identity,
        "--msg-type", "interactive",
        "--content", card_json,
    ]
    if args.chat_id:
        cmd += ["--chat-id", args.chat_id]
    elif args.user_id:
        cmd += ["--user-id", args.user_id]

    if args.dry_run:
        print("=== DRY RUN (未实际发送) ===")
        print(f"Target: chat_id={args.chat_id} user_id={args.user_id} identity={args.identity}")
        print(card_json)
        return 0

    env = {**os.environ, "LARK_CLI_NO_PROXY": "1"}
    try:
        proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=60)
    except FileNotFoundError:
        print("ERROR: 未找到 lark-cli 命令。请先完成飞书 CLI 安装与登录，或直接复制简报正文手动发群。", file=sys.stderr)
        return 127
    except subprocess.TimeoutExpired:
        print("ERROR: lark-cli 发送超时（60s），请检查网络后重试。", file=sys.stderr)
        return 124

    if proc.returncode != 0:
        print("ERROR: 飞书发送失败，原始返回如下：", file=sys.stderr)
        if proc.stdout:
            print(proc.stdout, file=sys.stderr)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        return proc.returncode

    print(proc.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
