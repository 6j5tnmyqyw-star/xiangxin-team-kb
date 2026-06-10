---
name: video-script-extract
description: 视频提取文案。祥书贴主流短视频链接(v.douyin.com / 抖音口令 / 小红书 xhslink / 快手 v.kuaishou / B 站 b23.tv / TikTok vt.tiktok 等)或说『扒这条 / 扒一下文案 / 视频文字稿 / 这条视频什么内容 / 提取文案 / 转文字 / 抽视频文字』时,用 browser-harness 接他本机 Chrome 走轻抖(已开通终身会员,镜像站 abmhz.top,账号 xiangxingolf)粘链接→提取→抓完整文案+AI摘要→落 _待整理/ → 走 Inbox 流程。目标位置默认 04-内容创作/参考文案/,可由祥书指定。
---

# 视频提取文案

## 何时启动

满足任一条件即触发:
- 消息里出现主流短视频链接或分享口令:
  - 抖音: `v.douyin.com/...` / `www.douyin.com/video/...` / 抖音口令(『7.61 复制打开抖音...』整段)
  - 小红书: `xhslink.com/...` / `www.xiaohongshu.com/...`
  - 快手: `v.kuaishou.com/...`
  - B 站: `b23.tv/...` / `www.bilibili.com/...`
  - TikTok: `vt.tiktok.com/...` / `www.tiktok.com/...`
- 祥书说『扒这条 / 扒一下文案 / 视频文字稿 / 这条视频什么内容 / 提取文案 / 转文字 / 抽视频文字』并附了链接

**轻抖支持全网主流短视频平台**,单次最多 100 条批量。

## 关键事实

- **必须用镜像站 https://www.abmhz.top**,正主 qingdou.vip 在祥书 Chrome 里没登录态
- 终身会员账号已开通(账号密码在飞书密码本"账号密码"表的"轻抖软件终身会员"行)
- 工具入口: https://www.abmhz.top/pctool/path-new-online/text-extract
- 输入区 CSS: `div[class*="editorContent___"]`(富文本编辑器,需要 click + type_text)
- 提取按钮 CSS: `div[class*="submitBtn___"]`
- 提交后 URL 加 `?batchId=<id>&isReload=1`,batchId 可作回查锚点

## 标准流程

### 1. 打开提文案页

```python
new_tab("https://www.abmhz.top/pctool/path-new-online/text-extract")
wait_for_load()
capture_screenshot("/tmp/qd-1.png")
```

如果跳出"忘词救星"或类似广告弹窗,找 `img[class*="close_icon"]` 关掉。

### 2. 验证登录态

截图看右上角:
- 显示头像 → 已登录,继续
- 显示"登录/注册" → 状态可能滞后,先尝试粘链接 + 点提取;真的没登录会弹登录窗,届时走第 5 步

### 3. 粘贴链接

```python
import json, time
rect = js("""
  const el = document.querySelector('div[class*="editorContent___"]');
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return JSON.stringify({x: Math.round(r.x+r.width/2), y: Math.round(r.y+r.height/2)});
""")
xy = json.loads(rect)
click_at_xy(xy['x'], xy['y'])
time.sleep(0.3)
# 整段口令直接贴(轻抖会自己解析出链接),多条用换行分隔
type_text(消息原文片段)  # 抖音口令『7.61 复制打开抖音...』整段也 OK
```

### 4. 点"提取文案"

```python
btn = js("""
  const el = document.querySelector('div[class*="submitBtn___"]');
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return JSON.stringify({x: Math.round(r.x+r.width/2), y: Math.round(r.y+r.height/2)});
""")
b = json.loads(btn)
click_at_xy(b['x'], b['y'])
time.sleep(2)
```

点击后 URL 会变成 `...text-extract?batchId=<id>&isReload=1`。记下 batchId。

### 5. 处理登录窗(只在弹出时)

弹窗默认显示"微信扫码登录"。两条路:

- **首选**:让祥书自己扫码(他手机微信常开,3 秒搞定)
- **备选**:点弹窗右下角"用户名登录"小图标 → 填账号密码 → 登录

如果备选:从飞书密码本"轻抖软件终身会员"行读账号密码,绝对**不要硬编码到 skill**。

### 6. 轮询等结果

每 5 秒抓一次表格行,最长 120 秒:

```python
import time
for i in range(24):
    time.sleep(5)
    rows_json = js("""
      const out = [];
      document.querySelectorAll('tr').forEach(tr => {
        const cells = [];
        tr.querySelectorAll('td').forEach(td => cells.push((td.innerText||'').trim()));
        if (cells.length > 0) out.push(cells);
      });
      return JSON.stringify(out);
    """)
    if '排队中' not in rows_json and '正在处理' not in rows_json and len(rows_json) > 100:
        rows = json.loads(rows_json)
        break
```

每行结构: `[checkbox, 视频信息(标题\n来源\n时长), 完整文案, AI摘要, 操作按钮]`

**注意**:AI 摘要列比文案列晚出几秒。如果摘要还是"正在处理",可再等 1-2 轮;实在拿不到摘要也别卡住,只用逐字稿写 md。

### 7. 写 Inbox md

文件名: `_待整理/视频文案-<标题前20字>-YYYY-MM-DD.md`

```markdown
---
类型: 视频文案
来源URL: <祥书贴的原链接,或从口令里抽出来的 v.douyin.com 短链>
平台: 抖音 | 小红书 | 快手 | B站 | TikTok
标题: <轻抖返回的标题>
时长: <轻抖返回的时长,例 1分18秒>
作者: <如果链接或口令里能看出作者,否则留空>
轻抖batchId: <URL 里的 batchId>
抓取日期: YYYY-MM-DD
目标位置: 04-内容创作/参考文案/
---

# <视频标题>

## 逐字稿
<轻抖完整文案,原文不改,口误错字都留>

## AI 摘要
<轻抖 AI 摘要;如果还没出来写"(轻抖摘要未生成,可去云盘 batchId=xxx 回查)">

## 我的笔记
<留空给祥书补>
```

`目标位置` 给 Vault 自动归档进程([project_inbox_auto_archiver])看,祥书过一遍后自动搬。

### 8. 回报告

```
✅ 文案抓好了
标题: <title>
平台: <平台> · 时长: <duration> · 作者: <uploader 或空>
batchId: <id>(轻抖云盘可回查)
md: _待整理/视频文案-<标题>-YYYY-MM-DD.md
目标位置: <frontmatter 里的目标>

逐字稿(前 200 字):
<text[:200]>...

AI 摘要:
<summary>
```

## 不要做的事

- **不要总结/改写/翻译逐字稿**——原文保留,口误错字都留(轻抖已给 AI 摘要,逐字稿不要再动)
- **不要直接落 `04-内容创作/`**——Inbox-first 铁律
- **不要发到群**——这是个人素材库
- **不要存到 Anki/任务/Base**——纯素材沉淀,不是待办
- **不要硬编码坐标**——用 CSS 选择器 + `getBoundingClientRect()` 拿位置;轻抖 UI 改版坐标会失效
- **不要硬编码账号密码**——从飞书密码本现读

## 失败兜底

| 现象 | 处理 |
|---|---|
| 弹微信扫码登录 | 让祥书扫;扫不了用账号密码(密码本现读) |
| 输入区 `editorContent___` 类名变了 | 截图汇报,DOM 可能改版,先回退到 yt-dlp + 妙记 |
| 提取卡 >120 秒 | 截图汇报,可能轻抖后台拥堵或视频被删 |
| 链接"不支持平台" | 改走 yt-dlp + 妙记 fallback(见下) |
| 抖音口令解析失败 | 单独抽 `https://v.douyin.com/...` 那段再粘 |
| 轻抖会员到期 | 提醒祥书续费,本月用 yt-dlp + 妙记顶上 |

## 视频原文件归档(可选,非默认)

**轻抖路径默认不下载视频**。如果祥书说『也存视频 / 原片留下』,并行用 `scripts/extract.sh`(yt-dlp 路径):

```bash
"<skill 目录>/scripts/extract.sh" "<douyin_url>"
# 输出 JSON 含 video_path,把视频移到:
# 99-附件/抖音素材/YYYY-MM/<title-前30字>-<video_id>.mp4
```

`scripts/extract.sh` 保留作 yt-dlp + 元数据 JSON 路径的 fallback,默认走轻抖。

## 调整目标位置

祥书说『这条存到 X』,把 frontmatter `目标位置` 改成他指定的。常见去处:

- `04-内容创作/参考文案/` — **默认**,竞品口播 / 选题灵感 / 痛点表达
- `02-人物/明宇/` — 明宇出镜的家庭视频
- `02-人物/<家人名>/` — 其他家人视频
- `04-内容创作/个人号/02-脚本/参考素材/` — 个人号选题素材
- `04-内容创作/高尔夫公司号/参考文案/` — 公司号选题素材

判断不准就问一句,别瞎归。
