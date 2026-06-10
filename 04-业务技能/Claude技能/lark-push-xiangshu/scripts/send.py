#!/usr/bin/env python3
"""Send a Feishu DM to 祥书 via the 祥子AI 推送 self-built app.

Uses curl subprocess instead of urllib so it works regardless of which
python3 picks it up (system 3.9 has no CA bundle issues; curl uses the
macOS keychain).

Modes:
  send.py "文本"  [target]                     默认发 markdown 卡片（祥书要求 2026-06-10）
  send.py --ask "问题" "选项A,选项B" [target]   提问卡片，按钮回调走桥(__claude_cb)
  send.py --card '<card json>' [target]        原样发 CardKit 2.0 卡片 JSON

Env:
  LARK_PUSH_TARGET  目标 oc_/ou_/on_（优先级低于位置参数 target）
  LARK_PUSH_FORMAT  card|text  默认 card：一律发卡片；显式设 text 才发纯文本
  LARK_PUSH_TITLE   卡片标题（可选，加蓝色 header）
"""
import json
import os
import re
import subprocess
import sys

UNION_ID = "on_6cd4ed98397599f3bf0c1ff341a2eaf6"
TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
SEND_BASE = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type="

MD_PATTERN = re.compile(
    r"\*\*.+?\*\*"          # bold
    r"|^#{1,6} "            # heading
    r"|^[-*] "              # bullet list
    r"|^\d+\. "             # ordered list
    r"|\[.+?\]\(.+?\)"      # link
    r"|```"                 # code block
    r"|^> ",                # quote
    re.MULTILINE,
)


def resolve_target(argv_target=""):
    """目标可由位置参数或 env LARK_PUSH_TARGET 指定；默认发给祥书本人(union_id)。
    oc_ → 群(chat_id)，on_ → union_id，ou_ → open_id。"""
    t = (argv_target or os.environ.get("LARK_PUSH_TARGET") or "").strip()
    if t.startswith("oc_"):
        return t, "chat_id"
    if t.startswith("ou_"):
        return t, "open_id"
    if t.startswith("on_"):
        return t, "union_id"
    return UNION_ID, "union_id"


def curl_post(url, body, extra_headers=None):
    headers = ["-H", "Content-Type: application/json"]
    for h in extra_headers or []:
        headers += ["-H", h]
    cmd = [
        "curl", "-sS", "--max-time", "20",
        "--noproxy", "*",
        "-X", "POST", url,
        *headers,
        "--data-binary", json.dumps(body, ensure_ascii=False),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"curl failed (exit {result.returncode}): {result.stderr}", file=sys.stderr)
        sys.exit(5)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Bad JSON response: {result.stdout}", file=sys.stderr)
        sys.exit(5)


def build_markdown_card(text, title=None):
    card = {
        "schema": "2.0",
        "config": {"update_multi": True},
        "body": {"elements": [{"tag": "markdown", "content": text}]},
    }
    if title:
        card["header"] = {
            "title": {"tag": "plain_text", "content": title},
            "template": "blue",
        }
    return card


def build_ask_card(question, options):
    """提问卡片：每个选项一个按钮。__claude_cb 让桥把点击作为 [card-click]
    回灌到该 chat 的 claude 会话（推送 app 与桥同为 cli_a977681a）。"""
    elements = [{"tag": "markdown", "content": question}]
    for opt in options:
        elements.append({
            "tag": "button",
            "text": {"tag": "plain_text", "content": opt},
            "type": "primary",
            "width": "fill",
            "behaviors": [{
                "type": "callback",
                "value": {"__claude_cb": True, "choice": opt, "question": question},
            }],
        })
    return {
        "schema": "2.0",
        "config": {"update_multi": True},
        "body": {"elements": elements},
    }


def main() -> int:
    argv = sys.argv[1:]
    if not argv or not argv[0]:
        print(__doc__, file=sys.stderr)
        return 1

    if argv[0] == "--ask":
        if len(argv) < 3:
            print('Usage: send.py --ask "问题" "选项A,选项B,选项C" [target]', file=sys.stderr)
            return 1
        options = [o.strip() for o in argv[2].split(",") if o.strip()]
        if not options:
            print("Error: no options given", file=sys.stderr)
            return 1
        payload = build_ask_card(argv[1], options)
        msg_type = "interactive"
        target_arg = argv[3] if len(argv) > 3 else ""
    elif argv[0] == "--card":
        if len(argv) < 2:
            print("Usage: send.py --card '<card json>' [target]", file=sys.stderr)
            return 1
        try:
            payload = json.loads(argv[1])
        except json.JSONDecodeError as e:
            print(f"Error: --card payload is not valid JSON: {e}", file=sys.stderr)
            return 1
        msg_type = "interactive"
        target_arg = argv[2] if len(argv) > 2 else ""
    else:
        text = argv[0]
        target_arg = argv[1] if len(argv) > 1 else ""
        # 2026-06-10 祥书：推送默认卡片格式（清晰）。只有显式 LARK_PUSH_FORMAT=text 才发纯文本。
        fmt = os.environ.get("LARK_PUSH_FORMAT", "card")
        if fmt == "text":
            payload = {"text": text}
            msg_type = "text"
        else:
            payload = build_markdown_card(text, os.environ.get("LARK_PUSH_TITLE"))
            msg_type = "interactive"

    app_id = os.environ.get("LARK_XIANGSHU_PUSH_APP_ID")
    app_secret = os.environ.get("LARK_XIANGSHU_PUSH_APP_SECRET")
    if not app_id or not app_secret:
        print(
            "Error: LARK_XIANGSHU_PUSH_APP_ID and LARK_XIANGSHU_PUSH_APP_SECRET must be set",
            file=sys.stderr,
        )
        return 2

    token_resp = curl_post(TOKEN_URL, {"app_id": app_id, "app_secret": app_secret})
    if token_resp.get("code") != 0:
        print(f"Token fetch failed: {token_resp}", file=sys.stderr)
        return 3
    token = token_resp["tenant_access_token"]

    receive_id, id_type = resolve_target(target_arg)
    send_resp = curl_post(
        SEND_BASE + id_type,
        {
            "receive_id": receive_id,
            "msg_type": msg_type,
            "content": json.dumps(payload, ensure_ascii=False),
        },
        extra_headers=[f"Authorization: Bearer {token}"],
    )
    if send_resp.get("code") != 0:
        print(f"Send failed: {send_resp}", file=sys.stderr)
        return 4

    msg_id = send_resp.get("data", {}).get("message_id", "")
    print(f"OK message_id={msg_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
