#!/usr/bin/env bash
# 启动一个带远程调试端口的 Chrome 实例，供 qianniu_extract.py 通过 CDP 连接。
# 每个店铺用独立 user-data-dir + 独立端口，可以多店同时登录互不干扰。
#
# 用法: bash start_chrome.sh <shop-slug>
#   slug 与端口在 ~/千牛产出/shops.json 里维护
set -euo pipefail

SLUG="${1:?用法: start_chrome.sh <shop-slug>}"
OUT="$HOME/千牛产出"
CONFIG="$OUT/shops.json"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SYCM_URL="https://sycm.taobao.com/qos/service/frame/performance/detail/new#/detail"

[ -f "$CONFIG" ] || { echo "✗ 找不到配置 $CONFIG —— 先照 shops.json.example 建一份"; exit 1; }
[ -x "$CHROME" ] || { echo "✗ 找不到 Chrome：$CHROME"; exit 1; }

PORT=$(python3 -c "
import json
shops = json.load(open('$CONFIG'))['shops']
m = [s for s in shops if s['slug'] == '$SLUG']
print(m[0]['port'] if m else '')
")
[ -n "$PORT" ] || { echo "✗ 未在 $CONFIG 找到 slug=$SLUG"; exit 1; }

PROFILE="$OUT/chrome-profiles/$SLUG"
mkdir -p "$PROFILE"
echo "启动 Chrome  slug=$SLUG  port=$PORT  profile=$PROFILE"
"$CHROME" --remote-debugging-port="$PORT" --user-data-dir="$PROFILE" "$SYCM_URL" &
echo "✓ Chrome 已启动。请在该窗口登录【$SLUG】对应的千牛/淘宝账号，登录后再跑 qianniu_extract.py。"
