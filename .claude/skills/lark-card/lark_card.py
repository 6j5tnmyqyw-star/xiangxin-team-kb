#!/usr/bin/env python3
"""飞书卡片构造（CardKit 2.0）——团队消息统一可视化格式。

给同事 / 群发结构化内容（催办、通知、周报、话术）用卡片，别发纯文本糊一团。
markdown 里 ``` 代码块自带一键复制按钮，要对方复制粘贴的内容（话术 / prompt / 命令）放代码块里。

header template 色卡约定：
  red / orange  催办、告警        yellow  温和提醒
  blue          常规通知、周报    green   完成 / 好消息
"""
import json


def build_card(md, title=None, template="blue", buttons=None):
    """buttons: [(按钮文字, url)] → 卡片底部跳转按钮。返回 card dict。"""
    elements = [{"tag": "markdown", "content": md}]
    for label, url in buttons or []:
        elements.append({
            "tag": "button",
            "text": {"tag": "plain_text", "content": label},
            "type": "primary",
            "width": "fill",
            "behaviors": [{"type": "open_url", "default_url": url}],
        })
    card = {"schema": "2.0", "config": {"update_multi": True},
            "body": {"elements": elements}}
    if title:
        card["header"] = {"title": {"tag": "plain_text", "content": title},
                          "template": template}
    return card


if __name__ == "__main__":
    # 用法：正文走 stdin，输出卡片 JSON（喂给 lark-cli im +messages-send --msg-type interactive --content）
    #   CARD=$(python3 lark_card.py --title "📊 标题" --template blue \
    #          --button "📄 打开文档=https://..." <<< "$MD")
    import argparse
    import sys
    ap = argparse.ArgumentParser(description="构造飞书 CardKit 2.0 卡片 JSON")
    ap.add_argument("--title", default=None)
    ap.add_argument("--template", default="blue",
                    help="red/orange=催办告警 yellow=提醒 blue=通知/周报 green=完成")
    ap.add_argument("--button", action="append", default=[],
                    metavar="文字=URL", help="底部跳转按钮，可多次")
    ap.add_argument("md", nargs="?", default=None, help="正文 markdown；缺省读 stdin")
    a = ap.parse_args()
    body = a.md if a.md is not None else sys.stdin.read()
    btns = [tuple(b.split("=", 1)) for b in a.button if "=" in b]
    print(json.dumps(build_card(body, a.title, a.template, btns or None),
                     ensure_ascii=False))
