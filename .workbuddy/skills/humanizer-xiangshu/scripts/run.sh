#!/bin/bash
# 手动跑文风指纹补料的便捷封装。
# launchd 不走这里——plist 直接用 /usr/local/bin/python3 跑 .py。
# 用法:./run.sh [--dry-run] [--force] [--batch N]
# 日志:~/.claude/logs/fingerprint-updater.log
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$HOME/.npm-global/bin:$PATH"
# 代理:仅当本地 7890 真在监听才走;没起就直连(Clash TUN/关 都直连可达,relay 是公网US-IP不需代理) — 2026-06-14 统一修 ConnectionRefused
if nc -z -G1 127.0.0.1 7890 2>/dev/null; then
  export HTTP_PROXY="http://127.0.0.1:7890"
  export HTTPS_PROXY="http://127.0.0.1:7890"
  export NO_PROXY="localhost,127.0.0.1,::1,.local,149.28.77.181"
else
  unset HTTP_PROXY HTTPS_PROXY ALL_PROXY
fi
export LANG=zh_CN.UTF-8
export LC_ALL=zh_CN.UTF-8
cd "$(dirname "$0")"
exec /usr/local/bin/python3 fingerprint_updater.py "$@"
