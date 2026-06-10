---
name: lark-push-xiangshu
description: 用专属飞书自建应用给祥书（邹祥书）本人发私信，绕开 lark-cli 的 user 身份。当需要让 AI 主动推送内容到祥书飞书（早报、定时提醒、长任务完成通知、异常告警等）时使用。本 skill 用专门的「祥子AI 推送」应用作为发送方，跟 lark-cli +send 走 user 身份发自己消息不一样——这个是机器人主动推。不要用来发别人，只发祥书本人。
---

# lark-push-xiangshu

让任何 AI 任务把内容**主动推到祥书的飞书**。底层是飞书 IM API 的 `send_messages`，用一个专门的自建应用（不是 lark-cli 自带 app）作为发送方，祥书会看到一条机器人私信。

## 什么时候用

- 定时任务的输出（早报、库存日报、价格监控告警等）
- 长任务完成通知（"导出跑完了，附件在 X 处"）
- 异常告警（"昨晚的 cron 失败了，原因是 ..."）
- AI 主动想到要告诉祥书的事

## 什么时候不用

- 发给**别人**（运营组、客户等）—— 用 `lark-im` skill 或 `lark-cli im +send`
- 发到群里 —— 用 `lark-im` skill
- 祥书自己回复别人 —— 用 `lark-cli im +send --as user`，那是他本人身份

## 调用方法

```bash
# 普通推送：默认发 Markdown 卡片（祥书要求 2026-06-10，卡片清晰）。正文直接写 markdown，推荐带标题。
LARK_PUSH_TITLE="📖 标题" ~/.claude/skills/lark-push-xiangshu/scripts/send.py "消息文本" [target]

# 提问卡片：每个选项一个按钮，祥书点击后桥(__claude_cb)把选择回灌到该 chat 的 claude 会话
~/.claude/skills/lark-push-xiangshu/scripts/send.py --ask "问题" "选项A,选项B,选项C" [target]

# 原样发 CardKit 2.0 卡片 JSON（复杂表单/布局自己拼）
~/.claude/skills/lark-push-xiangshu/scripts/send.py --card '<card json>' [target]
```

- `target` 可选：`oc_` 群 / `ou_` open_id / `on_` union_id，缺省发祥书本人
- env：`LARK_PUSH_FORMAT=card|text`（**默认 card，一律发卡片**）、`LARK_PUSH_TITLE`（卡片蓝色标题）、`LARK_PUSH_TARGET`
- ⚠️ 2026-06-10 祥书两次反馈：**推送必须卡片格式**。默认已是 card；只有一两句话的短通知可显式 `LARK_PUSH_FORMAT=text` 降级，成段内容禁止 text
- 交互回调原理：推送 app 与 lark-channel-bridge 同为 `cli_a977681a`，按钮 value 带 `__claude_cb: true` 时桥收到点击 → 以 `[card-click] {...}` 灌回该 chat 的 claude 会话继续处理

成功打印：`OK message_id=om_xxxxx`
失败会输出错误信息到 stderr 并 exit 非 0。

### 例子

```bash
# 简单一行
~/.claude/skills/lark-push-xiangshu/scripts/send.py "天猫库存周报跑完了，附件已传到飞书云空间。"

# 多行（用 $'...' 或真换行）
~/.claude/skills/lark-push-xiangshu/scripts/send.py "$(cat <<'EOF'
【高尔夫早报 2026-05-13】

1. Bushnell 发布 V8 新品，激光测距 1500 码
   https://example.com/news/1

2. PGA 巡回赛美国公开赛预选名单公布
   https://example.com/news/2

来源：高尔夫文摘 / Golf.com
EOF
)"
```

## 凭据存放

App ID 和 Secret 走环境变量，在 `~/.zshrc` 里：

```bash
export LARK_XIANGSHU_PUSH_APP_ID="cli_a977681a7d389bc1"
export LARK_XIANGSHU_PUSH_APP_SECRET="..."  # 实际值在 ~/.zshrc
```

⚠️ Secret 一旦泄漏（误推到 git、贴到聊天等），立刻去 [开发后台](https://open.feishu.cn/app/cli_a977681a7d389bc1/credential) 重置，然后更新 `~/.zshrc`。

接收方（祥书）的 union_id `on_6cd4ed98397599f3bf0c1ff341a2eaf6` 写死在脚本里，不是密钥不用环境变量。

## 出错怎么办

- `code 99991663` token 失效 → 脚本每次都重新拿 token，不会出现这个；如果出现，检查 secret 是否被重置过
- `code 230001` invalid receive_id → union_id 写错了或者祥书离职/被冻结（哈哈不太可能）
- `code 99992361` cross app → 用错 ID 类型，必须是 union_id 不是 open_id
- `Error fetching token` → 网络问题，或者 secret 被重置但 `~/.zshrc` 没更新

## 不要做的事

- 不要把 secret 写进 SKILL.md、写进代码、贴到聊天、传到 git
- 不要用 open_id（每个 app 独立，会 cross app）
- 不要把这个 skill 用来发别人
- 不要在脚本里把 token 缓存到磁盘——飞书 token 2 小时有效，每次重新拿成本极低，缓存增加泄漏面
