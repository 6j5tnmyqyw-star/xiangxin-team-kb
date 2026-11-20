#!/usr/local/bin/python3
"""校官 —— 跨模型质检

用【与撰写者不同的模型 Codex】复核别的 agent / 人的产出，专挑毛病。
原理：Claude 写的让 Claude 验只会说"挺好"，换 Codex 才挑得出问题。

用法：
  python3 check.py --type 文案 --file draft.txt
  python3 check.py --type 调价 "Bushnell V6 京东价改 1299"
  python3 check.py --type 对账 --file recon.md --json
  echo "内容" | python3 check.py --type SOP

type: 文案 / 调价 / 对账 / SOP / 通用
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys
import tempfile

VAULT_DIR = "/Users/mac/obsidian/祥子AI"
PROXY = "http://127.0.0.1:7890"

# 各类型的质检清单（注入给 Codex；越具体越能挑出真问题）
CHECKLISTS = {
    "文案": """1. 违禁词：绝对化用语(最/第一/顶级/国家级/唯一)、极限词、虚假或夸大功效、医疗暗示、贬低同行、诱导性承诺
2. 品牌/产品名拼写是否正确（如 Bushnell / Garmin / Ping / Callaway / VESSEL / 泰勒梅），可疑的逐个标出让人核对
3. 数字 / 参数 / 价格 是否有依据、有没有夸大
4. 客户隐私（姓名 / 手机 / 地址 / 订单号）是否泄露""",
    "调价": """1. 价格是否疑似录错（多一位 / 少一位 / 小数点错位）
2. 是否低于成本 / 亏本卖
3. 比价是否以【天猫】为基准（不是京东）
4. SKU / 商品型号 是否对得上
5. 大促(如618)期间若涉及改主图 / 大幅改价，是否该先告知祥书""",
    "对账": """1. 金额加总、各行小计是否算对
2. 绿 / 黄 / 红 判定是否合理（如：完全对得上=绿，仅差运费=黄，对不上=红）
3. 有没有把不同订单 / 不同供应商错配
4. 有无漏对、重复对的行""",
    "SOP": """1. 事实 / 数字 / 流程步骤是否准确、有没有自相矛盾
2. 有没有遗漏的边界情况或异常分支
3. 团队同事能否直接读懂、有没有错别字 / 病句
4. 品牌名 / 人名 / 店铺名是否正确""",
    "通用": """请以最挑剔的眼光通读，找出事实错误、逻辑漏洞、自相矛盾、遗漏、拼写 / 数字错误、以及任何会让人误解或踩坑的地方。""",
}


def _env():
    env = os.environ.copy()
    env["HTTPS_PROXY"] = PROXY
    env["HTTP_PROXY"] = PROXY
    env.pop("CLAUDECODE", None)
    env.pop("CLAUDE_CODE_ENTRYPOINT", None)
    return env


def load_banned_words():
    """文案质检时尽量带上 vault 里的违禁词规则"""
    for pat in ["07-AI协作/规则/03-内容创作*", "07-AI协作/规则/*内容创作*", "07-AI协作/规则/*违禁*"]:
        for f in glob.glob(os.path.join(VAULT_DIR, pat)):
            try:
                with open(f, encoding="utf-8") as fh:
                    return fh.read()[:3000]
            except OSError:
                continue
    return ""


def build_prompt(ctype, content, focus):
    checklist = CHECKLISTS.get(ctype, CHECKLISTS["通用"])
    extra = ""
    if ctype == "文案":
        bw = load_banned_words()
        if bw:
            extra = f"\n\n【公司内容创作规范节选，违禁词以此为准】\n{bw}\n"
    focus_line = f"\n额外重点关注：{focus}\n" if focus else ""
    return (
        "你是一名独立质检员（用的是和撰写者不同的模型）。你的唯一任务是【挑毛病】——"
        "宁可多疑、宁可误报，也不要放过问题。不要夸奖，不要复述原文。\n\n"
        f"内容类型：{ctype}\n"
        f"按以下清单逐项检查：\n{checklist}{extra}{focus_line}\n"
        f"=== 待检内容开始 ===\n{content}\n=== 待检内容结束 ===\n\n"
        "只返回 JSON（不要别的文字）：\n"
        '{"verdict":"PASS 或 RISK 或 FAIL","summary":"一句话总评",'
        '"issues":[{"item":"命中的检查项","problem":"具体问题","fix":"怎么改"}]}\n'
        "verdict 规则：FAIL=有必须改的硬伤(违禁词/亏本/隐私泄露/事实错误)；"
        "RISK=有需人确认的可疑点；PASS=没发现问题。没问题时 issues 给空数组。"
    )


def run_codex(prompt, timeout=300):
    out_path = tempfile.mktemp(suffix=".txt")
    try:
        subprocess.run(
            ["codex", "exec", "--skip-git-repo-check", "-s", "read-only",
             "--ephemeral", "-o", out_path, prompt],
            env=_env(), capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return ""
    try:
        with open(out_path, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""
    finally:
        try:
            os.remove(out_path)
        except OSError:
            pass


def parse_verdict(text):
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", required=True, choices=list(CHECKLISTS.keys()))
    ap.add_argument("--file", help="待检内容文件路径")
    ap.add_argument("--focus", help="额外重点关注的点")
    ap.add_argument("--json", action="store_true", help="只输出原始 JSON")
    ap.add_argument("content", nargs="*", help="待检内容（也可走 --file 或 stdin）")
    args = ap.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            content = f.read()
    elif args.content:
        content = " ".join(args.content)
    elif not sys.stdin.isatty():
        content = sys.stdin.read()
    else:
        print("✗ 没有待检内容（用 --file / 直接传参 / stdin）", file=sys.stderr)
        sys.exit(2)

    content = content.strip()
    if not content:
        print("✗ 待检内容为空", file=sys.stderr)
        sys.exit(2)

    raw = run_codex(build_prompt(args.type, content, args.focus))
    verdict = parse_verdict(raw)

    if args.json:
        print(raw or "{}")
        return

    if not verdict:
        print("⚠️ 校官没返回有效结果（codex 超时或解析失败）。原始输出：")
        print(raw[:500] if raw else "(空)")
        sys.exit(1)

    icon = {"PASS": "✅", "RISK": "🟡", "FAIL": "🔴"}.get(verdict.get("verdict", ""), "❓")
    print(f"{icon} 校官判定：{verdict.get('verdict', '?')}　—　{verdict.get('summary', '')}")
    issues = verdict.get("issues") or []
    if issues:
        print(f"\n发现 {len(issues)} 处：")
        for i, it in enumerate(issues, 1):
            print(f"  {i}. [{it.get('item', '')}] {it.get('problem', '')}")
            if it.get("fix"):
                print(f"     → 改：{it['fix']}")
    else:
        print("  （没挑出问题）")


if __name__ == "__main__":
    main()
