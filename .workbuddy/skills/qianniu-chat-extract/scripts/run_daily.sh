#!/usr/bin/env bash
# 每日定时抓取 wrapper（被 launchd 调用，也可手动跑）。
# - 抓取昨天的天猫祥新运动专营店聊天
# - 自动归档脱敏 md 到 08-公司知识库/客服话术/原始记录/
# - 失败/无数据时用 lark-push-xiangshu 推送告警

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PUSH="$HOME/.claude/skills/lark-push-xiangshu/scripts/send.py"
LOG_DIR="$HOME/千牛产出/logs"
mkdir -p "$LOG_DIR"

DATE=$(date +%Y-%m-%d)
YESTERDAY=$(date -v-1d +%Y-%m-%d)
LOG="$LOG_DIR/run_${DATE}.log"
SHOP_SLUG="${SHOP_SLUG:-xinshui-tm}"

{
    echo "===== $(date '+%Y-%m-%d %H:%M:%S') start (shop=$SHOP_SLUG, target=$YESTERDAY) ====="
    cd "$SCRIPT_DIR"
    /usr/local/bin/python3 qianniu_extract.py --shop "$SHOP_SLUG" --auto-date --date "$YESTERDAY"
    RC=$?
    if [ $RC -eq 0 ]; then
        echo "----- service metrics snapshot (6 dashboards) -----"
        /usr/local/bin/python3 extract_service_metrics.py --shop "$SHOP_SLUG" || echo "  ! service metrics failed (non-fatal)"

        echo "----- post-process: analyze + phrase library -----"
        /usr/local/bin/python3 analyze_chats.py --date "$YESTERDAY" --shop "$SHOP_SLUG" || echo "  ! analyze failed (non-fatal)"
        /usr/local/bin/python3 update_phrase_library.py --date "$YESTERDAY" || echo "  ! phrase update failed (non-fatal)"

        # 把短语库同步到飞书云文档（覆盖式更新）
        echo "----- sync phrase library to Feishu -----"
        PHRASE_MD="/Users/mac/obsidian/祥子AI/08-公司知识库/客服话术/快捷短语库.md"
        DOC_TOKEN=$(/usr/local/bin/python3 -c "import json; print(json.load(open('$HOME/千牛产出/lark_docs.json'))['phrase_library']['doc_token'])" 2>/dev/null || echo "")
        if [ -n "$DOC_TOKEN" ] && [ -s "$PHRASE_MD" ]; then
            CONTENT=$(cat "$PHRASE_MD")
            /usr/local/bin/lark-cli docs +update --api-version v2 --doc "$DOC_TOKEN" \
                --command overwrite --doc-format markdown --content "$CONTENT" \
                >/dev/null 2>&1 \
                && echo "  ✓ Feishu doc updated" \
                || echo "  ! Feishu sync failed (non-fatal)"
        else
            echo "  ↷ skip Feishu sync (no doc_token or empty md)"
        fi
    fi
    echo "===== rc=$RC end ====="
    exit $RC
} >> "$LOG" 2>&1
RC=$?

# 检查产出文件是否存在（rc=0 也可能因为 Chrome 没数据导致没产出）
KB_FILE="/Users/mac/obsidian/祥子AI/08-公司知识库/客服话术/原始记录/${YESTERDAY:0:7}/qianniu_chats_${YESTERDAY}_${SHOP_SLUG}.md"
LOCAL_MD="$HOME/千牛产出/qianniu_chats_${YESTERDAY}_${SHOP_SLUG}.md"

if [ $RC -ne 0 ]; then
    MSG="❌ 千牛聊天抓取失败 (${YESTERDAY} ${SHOP_SLUG})
rc=${RC}
日志: ${LOG}
排查: 多半是 Chrome 没开/没登录。手动跑 bash ${SCRIPT_DIR}/start_chrome.sh ${SHOP_SLUG} 重登。"
    "$PUSH" "$MSG" >> "$LOG" 2>&1 || echo "[wrapper] push failed too" >> "$LOG"
    exit $RC
fi

if [ ! -s "$LOCAL_MD" ]; then
    MSG="⚠️ 千牛聊天抓取跑完但没产出 (${YESTERDAY} ${SHOP_SLUG})
日志: ${LOG}
可能原因: 当天无咨询 / 页面日期没切对 / 表格未加载。"
    "$PUSH" "$MSG" >> "$LOG" 2>&1
    exit 0
fi

# 成功：发个简短的成功通知（含归档路径）
SESSIONS=$(grep -c "^## 会话" "$LOCAL_MD" 2>/dev/null || echo "?")
MSG="✅ 千牛聊天抓取完成 (${YESTERDAY} ${SHOP_SLUG})
合并后 ${SESSIONS} 个买家会话
本地: ${LOCAL_MD}
知识库: ${KB_FILE}"
"$PUSH" "$MSG" >> "$LOG" 2>&1

exit 0
