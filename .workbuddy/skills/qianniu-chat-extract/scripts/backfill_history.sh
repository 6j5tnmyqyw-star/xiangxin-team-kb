#!/usr/bin/env bash
# 历史回溯 wrapper: 按日期范围逐天调 qianniu_extract.py,跳过已有,失败继续。
# 用法: bash backfill_history.sh <slug> <YYYY-MM-DD start> <YYYY-MM-DD end>
# 例:   bash backfill_history.sh bsn-tmall 2025-11-21 2026-05-18
#
# resumable: 重跑会跳过已有 ~/千牛产出/qianniu_chats_<date>_<slug>.json
# 验证产出: md 顶部日期不匹配 → 视为污染,自动删
set -uo pipefail

SLUG="${1:?用法: backfill_history.sh <slug> <start YYYY-MM-DD> <end YYYY-MM-DD>}"
START="${2:?需要 start date}"
END="${3:?需要 end date}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HOME/千牛产出"
KB_ROOT="/Users/mac/obsidian/祥子AI/08-公司知识库/客服话术/原始记录"
LOG_DIR="$OUT/logs"
mkdir -p "$LOG_DIR"
STAMP=$(date +%Y%m%d_%H%M%S)
LOG="$LOG_DIR/backfill_${SLUG}_${STAMP}.log"
STATE="$OUT/backfill_${SLUG}_state.jsonl"

# 列日期(macOS date)
DATES=()
CUR="$START"
while [[ "$CUR" < "$END" ]] || [[ "$CUR" == "$END" ]]; do
    DATES+=("$CUR")
    CUR=$(date -j -v+1d -f "%Y-%m-%d" "$CUR" +"%Y-%m-%d")
done
TOTAL=${#DATES[@]}

SKIP=0; DONE=0; FAIL=0; IDX=0
START_TS=$(date +%s)

log_state() {
    local d="$1" status="$2" detail="$3"
    printf '{"date":"%s","status":"%s","detail":"%s","ts":"%s"}\n' "$d" "$status" "$detail" "$(date -Iseconds)" >> "$STATE"
}

echo "===== backfill start slug=$SLUG range=$START..$END total=$TOTAL log=$LOG =====" | tee -a "$LOG"

for D in "${DATES[@]}"; do
    IDX=$((IDX+1))
    JSON="$OUT/qianniu_chats_${D}_${SLUG}.json"
    if [[ -s "$JSON" ]]; then
        echo "[$IDX/$TOTAL skip] $D (already exists)" | tee -a "$LOG"
        SKIP=$((SKIP+1))
        log_state "$D" "skip" "already-exists"
        continue
    fi
    ELAPSED=$(( $(date +%s) - START_TS ))
    echo "[$IDX/$TOTAL run ] $D ... (elapsed ${ELAPSED}s)" | tee -a "$LOG"
    /usr/local/bin/python3 "$SCRIPT_DIR/qianniu_extract.py" --shop "$SLUG" --auto-date --date "$D" >> "$LOG" 2>&1
    RC=$?

    MD="$OUT/qianniu_chats_${D}_${SLUG}.md"
    # 验证 md 顶部日期匹配
    if [[ ! -s "$MD" ]]; then
        echo "[$IDX/$TOTAL fail] $D (md missing rc=$RC)" | tee -a "$LOG"
        FAIL=$((FAIL+1))
        log_state "$D" "fail" "md-missing rc=$RC"
        continue
    fi
    if ! head -3 "$MD" 2>/dev/null | grep -q "$D"; then
        echo "[$IDX/$TOTAL fail] $D (date mismatch — md was for other date, removing)" | tee -a "$LOG"
        rm -f "$OUT/qianniu_chats_${D}_${SLUG}.json" "$OUT/qianniu_chats_${D}_${SLUG}.md" "$OUT/qianniu_chats_${D}_${SLUG}_raw.json"
        rm -f "$KB_ROOT/${D:0:7}/qianniu_chats_${D}_${SLUG}.md" 2>/dev/null
        FAIL=$((FAIL+1))
        log_state "$D" "fail" "date-mismatch"
        continue
    fi
    SESSIONS=$(grep -c '^## 会话' "$MD" 2>/dev/null || echo "?")
    echo "[$IDX/$TOTAL ok  ] $D ($SESSIONS sessions)" | tee -a "$LOG"
    DONE=$((DONE+1))
    log_state "$D" "ok" "sessions=$SESSIONS"
done

TOTAL_ELAPSED=$(( $(date +%s) - START_TS ))
H=$((TOTAL_ELAPSED/3600))
M=$(( (TOTAL_ELAPSED%3600) / 60 ))
echo "===== summary total=$TOTAL skip=$SKIP done=$DONE fail=$FAIL elapsed=${H}h${M}m =====" | tee -a "$LOG"
