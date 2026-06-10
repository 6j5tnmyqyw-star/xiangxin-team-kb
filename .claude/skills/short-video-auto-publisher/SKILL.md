---
name: short-video-auto-publisher
employee: xs
description: 短视频一键多平台发布：把祥书做好的一条视频自动发到抖音、微信视频号、小红书（小红书发视频笔记），全程准备好封面、各平台差异化标题、话题标签、简介。封面用 ChatGPT 出干净视觉底图 + 本地叠正确中文标题字；文案过违禁词红线；发布走 browser-harness 连已登录 Chrome 截图驱动，默认全自动直发、首测用 --dry-run 停在发布前校准。当祥书说『发个视频』『把这条发抖音/视频号/小红书』『一键发布』『三平台分发』『发布短视频』『给视频配封面标题话题』『自动发视频』『把视频发出去』时使用。
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - AskUserQuestion
metadata:
  trigger: 短视频一键发抖音/视频号/小红书
  audience: 祥书（browser-harness 路径）
  requires:
    bins: ["browser-harness", "python3"]
  references:
    platforms: references/platform-flows.md
    copywriting: references/copywriting.md
    cover: references/cover-generation.md
---

# short-video-auto-publisher：短视频一键多平台发布

> **这是什么**：祥书拍/剪好一条短视频后，让 Claude 一条龙把它发到**抖音 + 微信视频号 + 小红书**三个平台。每个平台自动备好封面、差异化标题、话题标签、简介，然后用 browser-harness 操作已登录的 Chrome 完成发布。
>
> **谁用**：祥书本人（走 browser-harness 路径，连他自己已登录的 Chrome）。
>
> **三平台都发同一条视频**；小红书发**视频笔记**（不是图文）。

---

## 一、何时触发

祥书说出以下意图之一：

- 「这条视频发一下 / 把这个发出去 / 发抖音视频号小红书」
- 「一键发布 / 三平台分发 / 自动发视频」
- 「给这条视频配好封面标题话题再发」

**先确认 3 件事**（一次问全，缺了能从草稿/视频推就别问）：
1. **视频文件在哪**？（mp4 绝对路径）
2. **哪个号**？公司号（倍视能/测距仪测评软广）还是个人号（邹祥书个人 IP）→ 决定文案口吻 + 归档位置
3. **配套文案草稿**有没有？有就读它（`04-内容创作/{公司号,个人号-邹祥书}/02-脚本/`），没有就看视频/听祥书口述提炼

---

## 二、能做到哪一步（发布边界）

祥书定的是**全自动直接发布**。但发布到全网不可逆，所以内置一道安全闸：

- **默认全自动**：填好封面+标题+话题+简介，自动点「发布」，等到「发布成功」确认态才报成功。
- **`--dry-run`（首测必用）**：一切照做，但**停在「发布」按钮前截图**，不点发布。用于第一次实测、或平台改版后校准选择器。
- **铁律**：绝不在没到达「已发布/发布成功」可见确认态时谎报已发。选择器找不到、卡住、登录失效 → **停下截图报告是哪一步断的**，不瞎猜不硬点。（沿用 [[browser-harness]] 的诚实发布原则）

> 第一次跑这个 skill，或任一平台改版后，**先 `--dry-run` 把三平台各走一遍**，我盯着截图确认每步都对，再放开直发。

---

## 三、整体流程（五步）

```
1. 读素材   →  视频路径 + 选号 + 读配套草稿（标题/正文/软广点/来源）
2. 生成文案 →  各平台差异化标题 + 话题标签 + 简介 + @建议，过违禁词红线
3. 生成封面 →  ChatGPT 出干净竖版视觉底图(不放中文) → 本地叠正确标题大字
4. 发布     →  browser-harness 连已登录 Chrome，逐平台上传视频+封面+填文案+发布
5. 归档通知 →  发布记录写 03-已发布/，飞书私信回报（发了哪几个平台+链接/截图）
```

各步细节分别看：
- 第 2 步文案 → **[references/copywriting.md](references/copywriting.md)**（各平台标题/话题/简介风格 + 违禁词清单 + @规则）
- 第 3 步封面 → **[references/cover-generation.md](references/cover-generation.md)**（ChatGPT 底图 prompt + `make_cover.py` 叠字）
- 第 4 步发布 → **[references/platform-flows.md](references/platform-flows.md)**（三平台 URL + 上传流程 + 选择器候选 + 坑 + 实测校准清单）

---

## 四、前置：连已登录的 Chrome + 三平台登录态

发布走 browser-harness（CDP 直连祥书自己的 Chrome），**不自己开浏览器、不输账号密码**。开跑前先探端口、确认三平台登录态：

```bash
# 1) 看哪些 Chrome 开着调试端口
ps aux | grep -o "remote-debugging-port=[0-9]*" | grep -v grep | sort -u

# 2) 逐个探，看登录了哪些平台
for p in 9222 9223 9224 9225 9226 9227 9228; do
  res=$(curl -s --max-time 2 "http://127.0.0.1:$p/json/list" 2>/dev/null)
  [ -n "$res" ] && echo "[$p]" && echo "$res" | python3 -c "import sys,json;[print('  ',t.get('url','')[:70]) for t in json.load(sys.stdin) if t.get('type')=='page' and any(k in t.get('url','') for k in ['douyin','channels.weixin','xiaohongshu'])]" 2>/dev/null
done
```

三平台创作者后台：

| 平台 | 发布页 URL | 登录方式 |
|---|---|---|
| 抖音 | `https://creator.douyin.com/creator-micro/content/upload` | 抖音/手机号，登录态较久 |
| 视频号 | `https://channels.weixin.qq.com/platform/post/create` | **微信扫码，登录态短易掉**，常要重扫 |
| 小红书 | `https://creator.xiaohongshu.com/publish/publish` | 小红书/手机号 |

- 哪个平台没登录 → **停下来**让祥书在那个 Chrome 里登一下，登好再继续。**绝不**自己输账号密码。
- 没有任何 Chrome 开调试端口 → 让祥书启动一个（或复用 qianniu/价格监控那类抓取 Chrome 的 `start_chrome.sh`）。

---

## 五、执行要点（按流程走，细节进 references）

1. **读素材**：拿到视频路径 + 号；有草稿就 Read 草稿，提取 H1 标题、`[钩子]/[落点]` 段落、软广点、来源。无草稿则据视频内容/祥书口述写一句话核心 + 卖点。

2. **生成文案**：照 [references/copywriting.md](references/copywriting.md) 为**每个平台**分别产出 标题 / 话题标签 / 简介 / @建议。**发布前必须过违禁词红线**（见第六节）。把三平台文案先给祥书过一眼（除非他说直接发）。

3. **生成封面**：照 [references/cover-generation.md](references/cover-generation.md)——调 [[chatgpt-image-maker]] 路径 A 出一张**干净竖版视觉底图（不放中文字）**，再用 `scripts/make_cover.py` 把标题大字叠上去。封面落 `99-附件/AI生成图/`。

4. **发布**：照 [references/platform-flows.md](references/platform-flows.md) 逐平台执行。每个平台：开发布页 → 截图确认登录 → CDP 上传视频 → 等转码完 → 填标题/简介/话题 → 传封面 → `--dry-run` 截图停 / 否则点发布等确认。**每个关键动作后必 `capture_screenshot()` 验证**。

5. **归档 + 通知**：发布记录追加到对应 `03-已发布/`（视频文件名、三平台标题/话题/封面、发布时间、链接或截图）；用 [[lark-push-xiangshu]] 给祥书发飞书私信汇报。发完别忘按 browser-harness 习惯**关掉自己 new_tab 开的发布页**，不碰他原有标签。

---

## 六、红线（每次发布前过一遍，自包含、必须遵守）

1. **违禁词（极限词）一个都不能进文案**。通用禁用：极致、史上最低、第一、绝对、国家级、最、唯一、顶级、独家；测距仪专属：军用级、百分百精准、激光武器级、超越同行。生成的标题/简介/话题里出现 → 改写后再发。
2. **品牌名/型号必须拼对**：Bushnell（不是 Bushnel）、Garmin、Ping、Callaway；型号 V6/V6S/V7S/PRO XM、S70/R50/G82。
3. **客户隐私零出现**：客户姓名、手机、地址、订单号、聊天截图，绝不进文案/封面/任何输入输出。
4. **比价以天猫为基准**，文案不引用京东价做对比。
5. **不谎报发布**：只有到达平台「发布成功/已发布」可见态才说发了；否则说「已停在发布前」或「第 X 步断了」。
6. **不自己登录**：登录态缺失就停下让祥书登，绝不输账号密码。
7. **只发祥书指定的这一条视频**；不批量翻历史视频（沿用 [[剪辑默认只剪当天上传]] 的克制原则）。

---

## 七、发布后（提示祥书，不自动做）

- 投流：发布后看自然流量，互动率（赞+评+藏+转/播放）≥5% 可追投、≥10% 必须追投（公司号规则，庆弘判断）。
- 数据回收：哪条爆了值得复盘，归档进 `04-复盘/`。

---

## 八、文件位置

- 主 SKILL：本文件
- 各平台发布流程：`references/platform-flows.md`
- 文案规范：`references/copywriting.md`
- 封面规范：`references/cover-generation.md`
- 封面叠字脚本：`scripts/make_cover.py`
- 软链：`~/.claude/skills/short-video-auto-publisher → 本目录`
- 上游工具：[[browser-harness]]（发布）、[[chatgpt-image-maker]]（封面底图）、[[lark-push-xiangshu]]（回报）

---

## 九、与其他工具的边界

| 你要 | 用什么 |
|---|---|
| **把做好的视频发到三平台** | **本 skill** |
| 写口播文案稿（从话题/录音） | [[content-script-pipeline]] / [[xiangshu-write-flow]] |
| 文案去 AI 味、加钩子、改口吻 | [[humanizer-xiangshu]] |
| 剪视频（转写/切/字幕/调色） | video-use |
| 单独作一张电商营销图 | [[chatgpt-image-maker]] |
