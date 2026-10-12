#!/bin/bash
# 定时任务入口：扫描全店、只下新出现的商品。由 launchd 调用，也可手动跑。
# 把复杂管道/重定向放在这里，避免写进 plist 的 XML（< > & 会破坏 plist）。
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="${OUT_DIR:-$HOME/Downloads/淘宝店铺图片}"
LOG="$DIR/state/cron.log"
mkdir -p "$DIR/state"
echo "==== $(date '+%Y-%m-%d %H:%M:%S') 定时扫新品开始 ====" >> "$LOG"
MODE=scan OUT_DIR="$OUT" STATE_DIR="$DIR/state" browser-harness < "$DIR/shop_images.py" >> "$LOG" 2>&1
echo "==== $(date '+%Y-%m-%d %H:%M:%S') 结束 ====" >> "$LOG"
