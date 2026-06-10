#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
祥书口播文风指纹 · 自动增量补料

每周扫 01-每日/想法/ 里【未经 AI 重写的口述原文】(frontmatter「来源: 苹果备忘录/语音口述/祥书口述」),
挑出 state 里还没处理过的,喂 claude -p 提炼【指纹里还没有的】新口头禅/句式/对仗/打比方/原话锚点,
append 到指纹文件的 <!-- AUTO-FINGERPRINT-APPEND --> 锚点后(只动候选区,永不改 §A-§G 主体)。

设计:
- 幂等可恢复:state.json 记已处理文件,每次最多处理 BATCH 篇,跑不完下周继续。
- claude 零工具调用:纯文本进->markdown 片段出,保守模式即可,不需 skip-permissions。
- 录音逐字稿暂不纳入(混同事/家人发言,易误采);想法是纯祥书第一人称,最干净。

用法:
  python3 fingerprint_updater.py [--dry-run] [--force] [--batch N]
  --dry-run  只打印提炼结果,不写指纹文件/不更新 state
  --force    忽略 state,重新扫全部(调试用)
  --batch N  本次最多处理 N 篇(默认 40)

launchd:周日 21:20 com.xiangshu.fingerprint-updater-weekly
日志:~/.claude/logs/fingerprint-updater.log
"""
import os
import sys
import re
import json
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

VAULT = Path("/Users/mac/obsidian/祥子AI")
IDEAS_DIR = VAULT / "01-每日" / "想法"
FINGERPRINT = VAULT / "07-AI协作/skills/humanizer-xiangshu/references/祥书口播文风指纹.md"
STATE = Path(__file__).resolve().parent / "state.json"
LOG = Path.home() / ".claude/logs/fingerprint-updater.log"
ANCHOR = "<!-- AUTO-FINGERPRINT-APPEND -->"

# 口述原文标志(frontmatter「来源:」命中这些 = 祥书原话,非 AI 整理)
ORAL_SOURCE_HINTS = ("苹果备忘录", "语音口述", "祥书口述")
BATCH_DEFAULT = 40
MIN_CHARS = 60          # 太短的碎片跳过(没提炼价值)
MAX_FEED_CHARS = 60000  # 喂 claude 的正文软上限,超了截断


def log(msg: str):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def claude(instruction: str, stdin_data: str = "", timeout: int = 600) -> str:
    """调 claude -p;大段数据走 stdin。失败返回空串。零工具调用、保守模式。
    cwd 设在 /tmp:claude -p 会自动加载工作目录 CLAUDE.md,在 vault 内跑会串入主规则。"""
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)  # 防 claude -p 在 claude 环境里嵌套
    try:
        r = subprocess.run(
            ["claude", "--strict-mcp-config", "--disable-slash-commands", "-p", instruction],
            input=stdin_data, capture_output=True, text=True, timeout=timeout,
            cwd="/tmp", env=env,
        )
    except subprocess.TimeoutExpired:
        log("⚠️  claude 超时")
        return ""
    except FileNotFoundError:
        log("⚠️  找不到 claude 命令(PATH?)")
        return ""
    if r.returncode != 0:
        log(f"⚠️  claude 异常退出: {r.stderr[:300]}")
        return ""
    return (r.stdout or "").strip()


def load_state() -> dict:
    if STATE.exists():
        try:
            return json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            log("⚠️  state.json 解析失败,按空处理")
    return {"processed_files": [], "runs": []}


def save_state(state: dict):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def strip_frontmatter(text: str) -> tuple[dict, str]:
    """返回 (frontmatter字段dict, 正文)。简单解析,只取「来源」等行。"""
    fields = {}
    body = text
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            fm = text[3:end]
            body = text[end + 4:].lstrip("\n")
            for line in fm.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    fields[k.strip()] = v.strip()
    return fields, body


def is_oral_original(fields: dict) -> bool:
    src = fields.get("来源", "")
    return any(h in src for h in ORAL_SOURCE_HINTS)


def collect_new(state: dict, force: bool, batch: int) -> list[tuple[str, str]]:
    """返回 [(文件名, 正文), ...],最多 batch 篇,优先最新(按文件名日期倒序)。"""
    done = set(state.get("processed_files", []))
    candidates = []
    for p in sorted(IDEAS_DIR.glob("*.md"), reverse=True):
        if not force and p.name in done:
            continue
        try:
            raw = p.read_text(encoding="utf-8")
        except Exception:
            continue
        fields, body = strip_frontmatter(raw)
        if not is_oral_original(fields):
            continue
        body = body.strip()
        if len(body) < MIN_CHARS:
            # 太短的也标记为已处理,免得每周重扫
            done.add(p.name)
            continue
        candidates.append((p.name, body))
        if len(candidates) >= batch:
            break
    return candidates


def read_fingerprint_main() -> str:
    """读指纹文件锚点【之前】的主体(§A-§F + 原话锚点),作为去重基准喂给 claude。"""
    text = FINGERPRINT.read_text(encoding="utf-8")
    idx = text.find(ANCHOR)
    return text[:idx] if idx != -1 else text


def build_corpus(items: list[tuple[str, str]]) -> str:
    parts, total = [], 0
    for name, body in items:
        chunk = f"\n【{name}】\n{body}\n"
        if total + len(chunk) > MAX_FEED_CHARS:
            break
        parts.append(chunk)
        total += len(chunk)
    return "".join(parts)


def append_to_fingerprint(snippet: str, n_files: int, dry: bool) -> bool:
    today = f"{datetime.now():%Y-%m-%d}"
    block = f"\n### 🗓 {today} 自动补料(扫 {n_files} 篇新口述)\n\n{snippet.strip()}\n"
    if dry:
        log("---- DRY-RUN 将追加 ----\n" + block)
        return True
    text = FINGERPRINT.read_text(encoding="utf-8")
    idx = text.find(ANCHOR)
    if idx == -1:
        log("⚠️  指纹文件找不到锚点,放弃追加")
        return False
    insert_at = idx + len(ANCHOR)
    new_text = text[:insert_at] + "\n" + block + text[insert_at:]
    FINGERPRINT.write_text(new_text, encoding="utf-8")
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--batch", type=int, default=BATCH_DEFAULT)
    args = ap.parse_args()

    log(f"=== 文风指纹补料开始 (dry={args.dry_run} force={args.force} batch={args.batch}) ===")

    if not FINGERPRINT.exists():
        log(f"⚠️  指纹文件不存在: {FINGERPRINT}")
        sys.exit(1)

    state = load_state()
    items = collect_new(state, args.force, args.batch)
    log(f"挑到 {len(items)} 篇新口述原文待提炼")
    if not items:
        log("没有新原文,收工。")
        return

    corpus = build_corpus(items)
    main_text = read_fingerprint_main()
    # 把"已有指纹"(去重基准)和"新原文"都放 stdin,instruction 里引用
    stdin_data = f"<已有指纹>\n{main_text}\n\n<新原文corpus>\n{corpus}"
    instruction = (
        "你在维护『祥书口播文风指纹』。stdin 里 <已有指纹> 是已提炼好的文风(去重基准),"
        "<新原文corpus> 是祥书最近的口述原文(苹果备忘录,纯第一人称)。\n"
        "任务:从新原文里挑【已有指纹还没有的】、能体现祥书说话味道的新增样本,输出 markdown 直接 append 到候选区。\n"
        "优先:新的对仗短句/打比方/类比 > 标志性句式 > 1-2段代表性原话锚点(50-150字)。\n"
        "硬性:①每条括号标出处文件名 ②跟已有指纹重复/雷同的一律去掉 ③规避客户隐私(姓名/手机/订单/金额)和敏感人事,涉及就跳过 "
        "④只输出 markdown 本身,不解释不调用任何工具;无可新增就只输出一行 NONE "
        "⑤用三级标题分类(### 对仗/打比方  ### 句式  ### 原话锚点),每条一个 - 列表项。"
    )

    out = claude(instruction, stdin_data=stdin_data, timeout=600)
    if not out:
        log("⚠️ claude 没产出,不更新 state(下周重试这批)。")
        return

    processed_names = [name for name, _ in items]

    if out.strip().upper() == "NONE" or len(out.strip()) < 10:
        log("claude 判定无值得新增的样本(NONE)。仍标记这批已处理。")
        appended = True
    else:
        appended = append_to_fingerprint(out, len(items), args.dry_run)
        if appended and not args.dry_run:
            log(f"✅ 已追加补料,提炼 {len(out)} 字。")

    if args.dry_run:
        log("DRY-RUN 不更新 state。")
        return

    if appended:
        done = set(state.get("processed_files", []))
        done.update(processed_names)
        state["processed_files"] = sorted(done)
        state.setdefault("runs", []).append({
            "at": f"{datetime.now():%Y-%m-%d %H:%M}",
            "processed": len(processed_names),
            "appended": out.strip().upper() != "NONE",
        })
        state["runs"] = state["runs"][-20:]
        save_state(state)
        log(f"state 更新:累计已处理 {len(state['processed_files'])} 篇。")

    log("=== 收工 ===")


if __name__ == "__main__":
    main()
