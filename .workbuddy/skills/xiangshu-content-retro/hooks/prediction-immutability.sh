#!/usr/bin/env bash
#
# xiangshu-content-retro / 盲预测不可改 hook
#
# 移植自 cheat-on-content。PreToolUse(Edit|Write) → 拦截任何对
# predictions/ 下文件「## 预测」段的修改。
#
# 放行：新建预测文件、改文件头(第一个 ## 之前)、追加「## 复盘」段、predictions/ 之外的文件。
# 拦截：「## 预测」到下一个 ## 之间的任何改动。
#
# 单次绕过(仅纯排版修复)：CHEAT_BYPASS_IMMUTABILITY=1 —— 会在 stderr 留警告 + git 留痕。
#
# 退出码：0=放行；1=拦截(Claude Code 把 stderr 给模型看)。

set -uo pipefail

if [[ "${CHEAT_BYPASS_IMMUTABILITY:-0}" == "1" ]]; then
  echo "[content-retro] ⚠️  盲预测锁已被单次绕过 (CHEAT_BYPASS_IMMUTABILITY=1)" >&2
  echo "[content-retro] ⚠️  只应用于纯 markdown 排版修复，不可改语义。git 会留痕。" >&2
  exit 0
fi

input=$(cat)
[[ -z "$input" ]] && exit 0

tool_name=$(printf '%s' "$input" | jq -r '.tool_name // empty' 2>/dev/null || echo "")
file_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null || echo "")

[[ "$tool_name" != "Edit" && "$tool_name" != "Write" ]] && exit 0
[[ -z "$file_path" ]] && exit 0

# 只管 _发布复盘 下的 predictions/*.md
case "$file_path" in
  */_发布复盘/*/predictions/*.md) : ;;
  */predictions/*.md) : ;;
  *) exit 0 ;;
esac

# 新建预测文件(Write 到不存在的路径) → 放行
if [[ "$tool_name" == "Write" && ! -f "$file_path" ]]; then
  exit 0
fi

if [[ "$tool_name" == "Edit" ]]; then
  old_string=$(printf '%s' "$input" | jq -r '.tool_input.old_string // empty' 2>/dev/null || echo "")
  [[ -z "$old_string" ]] && exit 0

  # 切出「## 预测」(含 ## 预测 v1/v2)到下一个非预测 ## 之间
  prediction_section=$(awk '
    /^## / {
      if ($0 ~ /^## (预测|Prediction)([^a-zA-Z]|$)/) { in_pred=1; print; next }
      else if (in_pred) { exit }
    }
    in_pred { print }
  ' "$file_path" 2>/dev/null || echo "")

  [[ -z "$prediction_section" ]] && exit 0

  pred_tmp=$(mktemp)
  printf '%s' "$prediction_section" > "$pred_tmp"

  if grep -qF -- "$old_string" "$pred_tmp" 2>/dev/null; then
    rm -f "$pred_tmp"
    cat >&2 <<EOF

[content-retro] 🚫 拦截：这次 Edit 动到了预测段：
  $file_path

违反铁律 #1：盲预测写完不可改。只能往「## 复盘」段追加，预测段一个字都不能改。

正确做法：
  • 想用新信息重做预测 → 新建 ${file_path%.md}_redo.md，原文件保留。
  • 发现写错了(已看到数据后) → 在复盘段写「修正：原X应为Y，<date>发现」。
  • 纯排版修复(无语义改动) → 单次绕过 CHEAT_BYPASS_IMMUTABILITY=1。
EOF
    exit 1
  fi
  rm -f "$pred_tmp"
  exit 0
fi

# Write 覆盖已存在的预测文件 → 拦截
if [[ "$tool_name" == "Write" && -f "$file_path" ]]; then
  cat >&2 <<EOF

[content-retro] 🚫 拦截：Write 会覆盖已存在的预测文件：
  $file_path

用 Edit 往「## 复盘」段追加；要重做用 _redo.md 新路径。原预测文件必须原样保留。
EOF
  exit 1
fi

exit 0
