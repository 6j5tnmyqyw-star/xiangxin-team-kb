#!/bin/bash
# 淘宝店铺图片下载器 —— 双击启动
# 双击本文件即可打开菜单：下全店 / 下指定商品 / 设置定时 / 取消定时
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
OUT_DIR="${OUT_DIR:-$HOME/Downloads/淘宝店铺图片}"
PLIST="$HOME/Library/LaunchAgents/com.xiangxin.taobao-shop-images.plist"
LOG="$DIR/state/cron.log"
mkdir -p "$DIR/state"

run() {  # run <MODE> [ITEM_IDS]
  local mode="$1"; local ids="${2:-}"
  echo "──────────────────────────────────────────"
  echo "  模式: $mode   输出目录: $OUT_DIR"
  echo "  （跑的时候请保持 Chrome 开着、并已登录目标店铺的千牛）"
  echo "──────────────────────────────────────────"
  MODE="$mode" ITEM_IDS="$ids" OUT_DIR="$OUT_DIR" STATE_DIR="$DIR/state" browser-harness < "$DIR/shop_images.py"
  echo
  echo "✅ 跑完了。图片在： $OUT_DIR"
  open "$OUT_DIR" 2>/dev/null || true
}

install_cron() {
  local hour="$1"
  chmod +x "$DIR/run_scan.sh"
  cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.xiangxin.taobao-shop-images</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$DIR/run_scan.sh</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict><key>OUT_DIR</key><string>$OUT_DIR</string></dict>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>$hour</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>$LOG</string>
  <key>StandardErrorPath</key><string>$LOG</string>
</dict></plist>
PL
  plutil -lint "$PLIST" >/dev/null || { echo "✖ plist 格式有误，放弃。"; return 1; }
  launchctl unload "$PLIST" 2>/dev/null || true
  launchctl load "$PLIST"
  echo "✅ 已设置每天 ${hour}:00 自动扫描新上架商品并下图。"
  echo "   日志: $LOG"
  echo "   注意: 到点时 Chrome 必须开着且登录千牛，否则当次跳过。"
}

remove_cron() {
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "✅ 已取消定时任务。"
}

while true; do
  clear
  echo "╔══════════════════════════════════════╗"
  echo "║      淘宝店铺图片下载器                ║"
  echo "╚══════════════════════════════════════╝"
  echo "  输出目录: $OUT_DIR"
  [ -f "$PLIST" ] && echo "  定时: ✅ 已开启（每天自动扫新品）" || echo "  定时: ✖ 未开启"
  echo
  echo "  1) 下载全店所有在售商品的图"
  echo "  2) 下载指定商品（粘贴商品ID或链接，可多个）"
  echo "  3) 设置定时：每天自动扫新上架商品下图"
  echo "  4) 取消定时"
  echo "  5) 退出"
  echo
  read -p "  请输入数字回车: " choice
  case "$choice" in
    1) run all; read -p "回车返回菜单…" _ ;;
    2)
       echo "粘贴商品ID或商品链接（多个用空格/逗号分隔），回车："
       read -r raw
       ids="$(echo "$raw" | grep -oE '[0-9]{10,}' | tr '\n' ',' )"
       if [ -z "$ids" ]; then echo "没识别到商品ID。"; else run ids "$ids"; fi
       read -p "回车返回菜单…" _ ;;
    3)
       read -p "每天几点跑？输入 0-23 的整点（建议白天电脑开着的时段，如 9）: " hr
       [[ "$hr" =~ ^[0-9]+$ ]] && [ "$hr" -ge 0 ] && [ "$hr" -le 23 ] && install_cron "$hr" || echo "时间无效。"
       read -p "回车返回菜单…" _ ;;
    4) remove_cron; read -p "回车返回菜单…" _ ;;
    5) echo "再见 👋"; exit 0 ;;
    *) ;;
  esac
done
