#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""客服知识库同步 —— 从飞书「高尔夫知识库 > 三、销售与客服」重新拉取，
保持本地 03-公司/SOP与流程/销售客服/ 与飞书最新内容一致。

做法：遍历本地每个带「来源链接」的 .md，用 lark-cli docs +fetch 按该 wiki URL
重新拉 markdown，内容有变化才覆盖正文（frontmatter 原样保留）。幂等、可重跑。
还在飞书填充的空壳/新写的内容，下次同步自动学到。

为什么按本地文件的 URL 拉、不直接遍历 wiki 树：飞书 wiki 节点 token 有新旧两种格式，
node-list 对老格式(wikcn/短token)报 131005，树遍历不可靠；而每个文档的 URL 用
docs +fetch 都能拉到。代价：5-12 之后【全新】建的节点（本地还没文件）这条路覆盖不到，
那种少量增量后续补。

用法：
  python3 sync_kb.py            # 全量同步
  python3 sync_kb.py --limit 3  # 只同步前3个（测试用）
  python3 sync_kb.py --dry-run  # 只看会更新哪些，不写
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time

VAULT = "/Users/mac/obsidian/祥子AI"
KB_DIR = os.path.join(VAULT, "03-公司/SOP与流程/销售客服")
PROXY = "http://127.0.0.1:7890"
MARKER = "<!-- SYNC-CONTENT -->"
URL_RE = re.compile(r"^来源链接:\s*(\S+)", re.M)


def fetch_doc(url):
    """用 lark-cli 拉 wiki/docx 的 markdown 正文。
    返回 (content, status)：status ∈ {ok, unsupported(非docx如思维导图/表格/PDF/视频), error}"""
    # 飞书是国内服务，直连即可，不走 Clash 代理（强制走代理 Clash 一挂就断）
    env = os.environ.copy()
    for k in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy", "ALL_PROXY", "all_proxy"):
        env.pop(k, None)
    cmd = ["lark-cli", "docs", "+fetch", "--api-version", "v2",
           "--doc", url, "--doc-format", "markdown", "--as", "user"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60, env=env)
    except Exception:
        return None, "error"
    blob = (r.stdout or "") + "\n" + (r.stderr or "")
    if "Unsupported document type" in blob:  # 思维导图/表格/PDF/视频，错误可能在 stderr
        return None, "unsupported"
    try:
        d = json.loads(r.stdout)
    except Exception:
        return None, "error"
    if not d.get("ok"):
        msg = (d.get("error", {}) or {}).get("message", "")
        return None, ("unsupported" if "Unsupported document type" in msg else "error")
    return (d.get("data", {}).get("document", {}) or {}).get("content"), "ok"


def split_frontmatter(text):
    """返回 (frontmatter含分隔线, 正文)。无 frontmatter 时 fm=''。"""
    if text.startswith("---"):
        m = re.match(r"^(---.*?\n---\n)(.*)$", text, re.S)
        if m:
            return m.group(1), m.group(2)
    return "", text


def existing_synced_content(body):
    """取上次同步写进去的内容（MARKER 之后）；没有 MARKER 返回 None。"""
    i = body.find(MARKER)
    return body[i + len(MARKER):].strip() if i != -1 else None


def is_shell(content, title_guess):
    """判断拉回来的还是不是空壳（只有标题、几乎没正文）。"""
    c = content.strip()
    # 去掉首个 H1 标题行后看剩多少
    rest = re.sub(r"^#\s+.*\n?", "", c, count=1).strip()
    return len(rest) < 15


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(KB_DIR, "*.md")))
    todo = []
    for f in files:
        if os.path.islink(f):  # 跳过软链进来的（如728真实问答库，单独维护）
            continue
        try:
            text = open(f, encoding="utf-8").read()
        except OSError:
            continue
        m = URL_RE.search(text)
        if m:
            todo.append((f, text, m.group(1)))
    if args.limit:
        todo = todo[:args.limit]

    print(f"待同步文档：{len(todo)} 篇（来源链接）")
    updated = unchanged = shell = nondocx = failed = 0
    changed_files = []

    for i, (f, text, url) in enumerate(todo, 1):
        name = os.path.basename(f)
        content, status = fetch_doc(url)
        if status == "unsupported":
            nondocx += 1  # 思维导图/表格/PDF/视频，非docx拉不成md，保留本地原文
            continue
        if content is None:
            failed += 1
            print(f"  [{i}/{len(todo)}] ✗拉取失败 {name}")
            continue
        content = content.strip()
        if is_shell(content, name):
            shell += 1
            continue  # 还是空壳，不动本地
        fm, body = split_frontmatter(text)
        prev = existing_synced_content(body)
        if prev is not None and prev == content:
            unchanged += 1
            continue
        # 内容有变化（或首次纳入同步格式）→ 重写
        updated += 1
        changed_files.append(name)
        if not args.dry_run:
            header = (f"\n> 📥 飞书知识库自动同步 | 最近同步 {time.strftime('%Y-%m-%d')}\n"
                      f"> 🔗 {url}\n\n{MARKER}\n")
            new_text = (fm + header + content + "\n") if fm else (header + content + "\n")
            with open(f, "w", encoding="utf-8") as fh:
                fh.write(new_text)
        if i % 20 == 0:
            print(f"  …进度 {i}/{len(todo)}")

    print("─" * 40)
    print(f"✅ 同步完成：更新 {updated} | 无变化 {unchanged} | 仍空壳 {shell} | 非docx跳过 {nondocx} | 失败 {failed}")
    if changed_files:
        print("有更新的文档：")
        for n in changed_files[:40]:
            print("  •", n)
    if args.dry_run:
        print("(dry-run，未写文件)")


if __name__ == "__main__":
    main()
