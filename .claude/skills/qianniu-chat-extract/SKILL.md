---
name: qianniu-chat-extract
description: 抓取千牛/生意参谋「旺旺咨询明细」的客服聊天记录。当祥书说『拉一下千牛聊天』『导出旺旺咨询明细』『看看昨天客服跟买家聊了啥』『抓千牛聊天记录』『把某店的客服对话导出来』『复盘客服聊天』时使用。脚本连已登录的 Chrome，逐行点开聊天弹窗抓全量消息，按「同一天同一买家」合并会话（能看出客服交接接力链），并关联跨天历史标出老客户，每店输出一份 JSON + Markdown。
---

# 千牛聊天明细抓取技能（macOS）

连上已登录千牛/生意参谋的 Chrome，把「旺旺咨询明细」里的客服-买家聊天逐条抓下来，合并、关联历史后输出结构化结果。

> **⚠️ AI 调用本 skill 前先读 [OPTIMIZATION_BACKLOG.md](OPTIMIZATION_BACKLOG.md)**：已知问题 + 待开发的分析方向都在那里。挑当下场景最相关的 1-2 条主动提给祥书（他明确说过"怕忘了，让 AI 主动提"），不要每次倒整张清单。

## 它做什么

1. 通过 CDP 连接一个已登录的 Chrome 实例（每店一个独立端口）
2. 切到生意参谋「客服 → 旺旺咨询明细」**全量 tab**（不是「有效接待明细」，避免漏抓真实买家咨询）
3. 从第 1 页开始翻页，逐行点「聊天明细」弹窗，滚动加载抓出**全部消息**（时间/发送方/内容）
4. **合并会话**：同一天同一买家的多行记录合并成一条按时间排序的会话——跨客服交接（上下班换人）会体现在「客服接力链」里
5. **关联历史**：扫描 `~/千牛产出/` 下的历史 JSON，把同一买家过去和本店的会话摘要附上，标出老客户
6. 每店输出三份文件到 `~/千牛产出/`：`..._<slug>.json`（合并后，主）、`..._<slug>.md`（人读版）、`..._<slug>_raw.json`（原始备份）

## 隐私铁律（重要）

聊天记录天然含买家旺旺 ID、可能含手机号/地址/订单号。产出文件落在本地 `~/千牛产出/`，**不要**把原始聊天内容贴进飞书、外发或写进知识库正文。复盘时只引用脱敏后的结论。

## 前置依赖

```bash
pip3 install playwright
python3 -m playwright install chromium
```

需要本机装有 Google Chrome（`/Applications/Google Chrome.app`）。

## 配置：shops.json

第一次用，照 `shops.json.example` 在 `~/千牛产出/shops.json` 建店铺清单：

```json
{
  "shops": [
    {"name": "祥新网商", "slug": "xinshui", "port": 9222},
    {"name": "Taylormade北京精品店", "slug": "taylormade-bj", "port": 9223}
  ]
}
```

- `name` 用于和页面顶部店铺名做一致性校验
- `slug` 命令行 `--shop` 参数 + 输出文件名
- `port` 每店一个独立 CDP 调试端口，多店可同时登录互不干扰

## 操作步骤

### 第一步：启动并登录 Chrome（每个要抓的店都要做一次）

```bash
bash scripts/start_chrome.sh xinshui
```

会弹出一个 Chrome 窗口并打开生意参谋。**在这个窗口里手动登录该店账号**，登录后窗口保持开着。
要抓多店就对每个 slug 各跑一次（端口不同，互不冲突）。

> Chrome 登录态保存在 `~/千牛产出/chrome-profiles/<slug>/`，下次一般不用重新登录。

### 第二步：跑抓取脚本

```bash
# 跑所有店，默认抓昨天
python3 scripts/qianniu_extract.py

# 只跑某一个店
python3 scripts/qianniu_extract.py --shop xinshui

# 指定日期
python3 scripts/qianniu_extract.py --shop xinshui --date 2026-05-10

# 自动切页面日期到 --date（best-effort，不需要先在 Chrome 里点日期）
python3 scripts/qianniu_extract.py --shop xinshui-tm --auto-date

# 跳过知识库归档（默认会归档脱敏版到 08-公司知识库/客服话术/原始记录/）
python3 scripts/qianniu_extract.py --shop xinshui --no-archive
```

脚本会自己切「旺旺咨询明细」全量 tab、重置到第 1 页、翻页逐行抓。终端会打印每行进度和最终汇总（原始行数 → 合并会话数，含几个客服交接、几个老客户）。

> 关于日期：默认情况下 `--date` 只影响输出文件名和历史关联，**实际抓的是页面上当前筛选的日期**——跑之前要在 Chrome 里手动把日期选到目标日。
> 加 `--auto-date` 后脚本会尝试自动切页面日期（best-effort，依赖生意参谋当前的日期选择器 DOM 结构，可能失败）。

## 归档到知识库

默认每次抓取完，会把**脱敏版** md 拷一份到：

```
08-公司知识库/客服话术/原始记录/YYYY-MM/qianniu_chats_<日期>_<slug>.md
```

脱敏规则：
- 买家旺旺 ID → 客户A/B/C（按 hash 稳定映射，同一买家跨天还是同一别名）
- 手机号 → `138****1234`
- 订单号（12+ 位数字）→ 全 `*`
- 含地址关键词（路/街/号/楼/室 等）的句子 → 截断成 `***[地址脱敏]`
- 客服名保留（运营内部交接需要）

幂等：目标文件已存在就跳过，不覆盖。要重跑必须先手动删。

原始未脱敏 JSON + md 仍只落本地 `~/千牛产出/`，**不会**进知识库。

## 定时任务（launchd）

每天 06:00 自动跑天猫祥新运动专营店（slug `xinshui-tm`）：

```bash
# 启用
launchctl load ~/Library/LaunchAgents/com.xiangshu.qianniu-chat-extract.plist

# 立刻跑一次（不等到 6 点）
launchctl start com.xiangshu.qianniu-chat-extract

# 看日志
tail -50 ~/.claude/logs/qianniu-chat-extract.stdout.log
tail -50 ~/千牛产出/logs/run_$(date +%F).log

# 停用
launchctl unload ~/Library/LaunchAgents/com.xiangshu.qianniu-chat-extract.plist
```

成功/失败都会用 `lark-push-xiangshu` 推送通知给祥书本人。

**重要前提**：定时任务靠 CDP 连本地 Chrome，Chrome 必须**前一晚保持开着且登录态有效**。睡前 Cmd+Q 关掉就抓不到了。失败会推飞书告警，看到告警手动跑一次 `start_chrome.sh xinshui-tm` 重登即可。

### 第三步：呈现结果给祥书

读 `~/千牛产出/qianniu_chats_<日期>_<slug>.md` 给祥书看，重点提示：

- **客服交接会话**：MD 顶部会标 `⚠ N 个会话存在客服交接`，这些会话可能有交接遗漏、重复回答的问题
- **老客户**：标了 `🔁 老客户` 的会话，看历史是不是反复问同一问题（说明上次没解决）
- 如果要做客服质检/问题复盘，结合 lark-helpdesk-xiangshu 的纠错日志一起看

## 边界情况

- **连不上端口**：脚本会提示先跑 `start_chrome.sh`——大概率是 Chrome 没启动或那个窗口被关了
- **页面店铺名对不上**：脚本会打 `⚠ 配置店铺名 与 页面 不一致`，说明那个 Chrome 窗口登录的不是预期账号
- **表格未加载**：可能日期筛选下当天没有咨询记录，或生意参谋页面没刷出来——手动刷一下页面再跑
- **某行弹窗抓不到消息**：脚本会打 `! modal wait failed` 但继续往下跑，不会整体中断；raw.json 里能看到哪行是空的
