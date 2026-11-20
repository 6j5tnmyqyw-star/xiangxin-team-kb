#!/usr/bin/env bash
# 抖音视频下载 + 元数据提取
# 用法: extract.sh <抖音URL>
# 输出: JSON 到 stdout,字段 video_path/title/uploader/duration/upload_date/source_url/video_id
# 视频文件落到 $TMPDIR/douyin-extract/<video_id>.mp4

set -euo pipefail

URL="${1:-}"
if [[ -z "$URL" ]]; then
  echo '{"ok":false,"error":"missing url argument"}' >&2
  exit 1
fi

# 规范化短链 v.douyin.com → 跟随重定向到完整 URL (yt-dlp 自己也能处理,但提前展开更稳)
if [[ "$URL" =~ v\.douyin\.com ]]; then
  URL="$(curl -sILo /dev/null -w '%{url_effective}' --max-redirs 5 "$URL" 2>/dev/null || echo "$URL")"
fi

WORKDIR="${TMPDIR:-/tmp}/douyin-extract"
mkdir -p "$WORKDIR"

# 优先用 Chrome cookies(抖音必须有 cookies 才能解析)
COOKIE_ARGS=(--cookies-from-browser chrome)

# 拿元数据 + 下载,一次完成。-o 模板用 id 防中文文件名问题
OUTPUT_TEMPLATE="$WORKDIR/%(id)s.%(ext)s"
META_JSON=$(yt-dlp \
  "${COOKIE_ARGS[@]}" \
  --no-warnings \
  --no-playlist \
  --format "bv*+ba/best" \
  --merge-output-format mp4 \
  -o "$OUTPUT_TEMPLATE" \
  --print-json \
  --no-simulate \
  "$URL" 2>/tmp/yt-dlp-err.log) || {
    ERR=$(tail -3 /tmp/yt-dlp-err.log | tr '\n' ' ' | sed 's/"/\\"/g')
    echo "{\"ok\":false,\"error\":\"yt-dlp failed: ${ERR}\",\"hint\":\"检查 Chrome 是否登录了抖音网页版,或视频是否被删\"}"
    exit 2
  }

# 抽关键字段
echo "$META_JSON" | jq --arg workdir "$WORKDIR" '{
  ok: true,
  video_id: .id,
  title: .title,
  uploader: .uploader,
  uploader_id: .uploader_id,
  description: .description,
  duration: .duration,
  upload_date: .upload_date,
  view_count: .view_count,
  like_count: .like_count,
  source_url: .webpage_url,
  video_path: ($workdir + "/" + .id + ".mp4"),
  thumbnail: .thumbnail
}'
