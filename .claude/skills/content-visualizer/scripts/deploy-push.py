#!/usr/bin/env python3
"""content-visualizer 一键交付：内联(按需) → 部署飞书妙搭 → 推送祥书手机。

用法:
  python3 deploy-push.py <页面.html> "<标题>" [选项]

选项:
  --scope {tenant,public,specific}  妙搭访问范围，默认 public(需登录飞书)。
                                    ⚠️ 同事(运营/张桐等)全是跨租户账号，tenant 对他们打不开；
                                    财务/敏感数据页必须显式 --scope tenant 锁回公司内。
  --no-push                         只部署，不推送祥书
  --dry-run                         只打印 lark-cli 请求不真执行(首测用)
  --app-id <id>                     复用已有妙搭 app(更新同一页，链接不变；跳过 +create)
  --skip-inline                     强制跳过内联(你确定是零依赖原生版)

流程:
  1. 检测页面是否含外部 CDN(React 版) → 跑 inline-build.js 内联；原生版自动跳过
  2. cp 成 index.html 到 ~/work/miaoda-deploy/<slug>/
  3. lark-cli apps +create(除非 --app-id 复用) → app_id
  4. lark-cli apps +html-publish → 拿访问 URL
  5. lark-cli apps +access-scope-set --scope <scope>
  6. lark-push-xiangshu 把「标题 + URL」推祥书飞书(除非 --no-push)
"""
import argparse
import datetime
import json
import re
import shlex
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent          # content-visualizer/
INLINE_BUILD = SKILL / "assets" / "inline-build.js"
SEND_PY = Path.home() / ".claude" / "skills" / "lark-push-xiangshu" / "scripts" / "send.py"
DEPLOY_ROOT = Path.home() / "work" / "miaoda-deploy"
CDN_MARKERS = ("cdn.tailwindcss.com", "unpkg.com", "jsdelivr.net", "cdnjs.", "esm.sh", "//cdn.")


def run(cmd, **kw):
    shown = " ".join(cmd) if isinstance(cmd, list) else cmd
    print("» " + shown)
    return subprocess.run(cmd, text=True, capture_output=True, **kw)


def find_key(obj, key):
    """递归在 dict/list 里找第一个名为 key 的标量值。"""
    if isinstance(obj, dict):
        if key in obj and isinstance(obj[key], (str, int)) and obj[key] != "":
            return obj[key]
        for v in obj.values():
            r = find_key(v, key)
            if r is not None:
                return r
    elif isinstance(obj, list):
        for v in obj:
            r = find_key(v, key)
            if r is not None:
                return r
    return None


def lark(args, dry, cwd=None, identity="user", fatal=True):
    full = ["lark-cli", "apps", *args, "--as", identity, "--format", "json"]
    if dry:
        full.append("--dry-run")
    r = run(full, cwd=cwd)
    if r.returncode != 0:
        if fatal:
            sys.stderr.write(r.stdout + "\n" + r.stderr + "\n")
            blob = (r.stdout + r.stderr).lower()
            if "permission" in blob or "scope" in blob or "denied" in blob:
                sys.stderr.write(
                    "\n⚠️ 像是 lark-cli user 身份没授权妙搭(apps) scope。"
                    "需重新授权一次(同一 app 加 scope，非换机器人)：见 lark-shared skill。\n"
                )
            sys.exit(2)
        return None   # 非致命失败：返回 None 让调用方自己处理
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"_raw": r.stdout}


def set_scope(app_id, scope, dry):
    """设置妙搭访问范围：先试 bot，再试 user，都失败就警告（不中止）。"""
    scope_args = ["+access-scope-set", "--app-id", str(app_id), "--scope", scope]
    if scope == "public":
        scope_args.append("--require-login")
    # 1. 先试 bot 身份（bot 通常有 spark:app.access_scope:write）
    res = lark(scope_args, dry, identity="bot", fatal=False)
    if res is not None:
        print(f"访问范围 = {scope} (bot 身份设置成功)")
        return
    print("bot 身份设置 scope 失败，尝试 user 身份…")
    # 2. 再试 user 身份
    res = lark(scope_args, dry, identity="user", fatal=False)
    if res is not None:
        print(f"访问范围 = {scope} (user 身份设置成功)")
        return
    # 3. 都失败：警告，但不中止部署
    print(
        f"⚠️ 无法自动设置访问范围（缺 spark:app.access_scope:write scope）。\n"
        f"   页面已部署成功，但默认只有创建者本人可见。\n"
        f"   手动修复：飞书妙搭后台 → 应用 {app_id} → 访问权限 → 设为「企业内可见」。"
    )


def slugify(s):
    s = re.sub(r"[^\w一-鿿-]+", "-", s).strip("-")
    return s[:40] or "viz"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("title")
    ap.add_argument("--scope", default="public", choices=["tenant", "public", "specific"])
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--app-id", default=None)
    ap.add_argument("--skip-inline", action="store_true")
    a = ap.parse_args()

    src = Path(a.html).expanduser().resolve()
    if not src.exists():
        sys.exit(f"找不到文件: {src}")
    html = src.read_text(encoding="utf-8", errors="ignore")

    # 1. 内联判断
    needs_inline = (not a.skip_inline) and any(m in html for m in CDN_MARKERS)
    deploy_src = src
    if needs_inline:
        out = src.with_suffix(".inline.html")
        print("检测到外部 CDN → 内联打包 (inline-build.js)…")
        r = run(["node", str(INLINE_BUILD), str(src), str(out)])
        sys.stdout.write(r.stdout)
        if r.returncode != 0:
            sys.stderr.write(r.stderr + "\n")
            sys.exit("内联失败")
        deploy_src = out
    else:
        print("零依赖原生版 → 跳过内联，直接部署。")

    # 2. cp 成 index.html
    ddir = DEPLOY_ROOT / slugify(a.title)
    ddir.mkdir(parents=True, exist_ok=True)
    (ddir / "index.html").write_bytes(deploy_src.read_bytes())
    print(f"已复制 → {ddir/'index.html'}")

    # 3. create / 复用
    app_id = a.app_id
    if not app_id:
        name = f"可视化·{a.title}·{datetime.date.today().isoformat()}"
        res = lark(["+create", "--name", name, "--app-type", "html",
                    "--description", "content-visualizer 自动部署"], a.dry_run)
        if a.dry_run:
            print("(dry-run) 跳过解析 app_id；后续步骤用占位 DRYRUN")
            app_id = "DRYRUN"
        else:
            app_id = find_key(res, "app_id")
            if not app_id:
                print(json.dumps(res, ensure_ascii=False))
                sys.exit("没解析到 app_id —— 看上面返回，按需调整 find_key")
        print(f"妙搭 app_id = {app_id}")

    # 4. publish(cd 进目录用相对路径)
    pub = lark(["+html-publish", "--app-id", str(app_id), "--path", "./index.html"],
               a.dry_run, cwd=str(ddir))
    url = None
    if not a.dry_run:
        url = find_key(pub, "url")
        if not url:
            m = re.search(r'https?://[^\s"\\]+', json.dumps(pub, ensure_ascii=False))
            url = m.group(0) if m else None
    print(f"访问链接 = {url}")

    # 5. scope
    set_scope(app_id, a.scope, a.dry_run)

    # 6. push
    if not a.no_push and not a.dry_run and url:
        msg = f"📊 {a.title}（可视化页，手机可直接打开）\n{url}"
        push = run(["zsh", "-c",
                    f"source ~/.zshrc >/dev/null 2>&1; python3 {shlex.quote(str(SEND_PY))} {shlex.quote(msg)}"])
        sys.stdout.write(push.stdout or push.stderr)

    print("\n✅ 完成。")
    if url and not a.dry_run:
        print(f"URL: {url}\napp_id: {app_id}  (更新这页就 --app-id {app_id} 重跑，链接不变)")


if __name__ == "__main__":
    main()
