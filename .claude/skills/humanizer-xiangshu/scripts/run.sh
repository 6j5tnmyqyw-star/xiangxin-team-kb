#!/bin/bash
# 手动跑文风指纹补料的便捷封装。
# launchd 不走这里——plist 直接用 /usr/local/bin/python3 跑 .py。
# 用法:./run.sh [--dry-run] [--force] [--batch N]
# 日志:~/.claude/logs/fingerprint-updater.log
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$HOME/.npm-global/bin:$PATH"
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
export NO_PROXY=localhost,127.0.0.1,::1,.local
export LANG=zh_CN.UTF-8
export LC_ALL=zh_CN.UTF-8
cd "$(dirname "$0")"
exec /usr/local/bin/python3 fingerprint_updater.py "$@"
