# Claude 技能包（团队试用）

这里放阿祥这边验证过、给团队复用的 Claude 技能。装法统一：**把技能文件夹复制到你电脑的 `~/.claude/skills/` 下**，重开 Claude 即生效。

```bash
mkdir -p ~/.claude/skills
cp -R "<本库路径>/04-业务技能/Claude技能/"* ~/.claude/skills/   # 全装
# 或只装某一个：cp -R "<本库路径>/04-业务技能/Claude技能/content-visualizer" ~/.claude/skills/
```

## 1. content-visualizer — 内容做成可视化网页

把任意内容（培训材料、数据汇报、操作流程）做成一个**双击就能打开的单文件网页**，带图表和交互。

- 怎么用：装好后直接跟 Claude 说"把这个做成可视化页面"，它会自动走这个技能
- 产出是单个 `.html` 文件，发给谁都能直接打开
- 注意：`scripts/deploy-push.py`（发妙搭+推送）依赖阿祥电脑的配置，**试用阶段忽略它**，本地生成 HTML 看效果就够

## 2. lark-push-xiangshu — 飞书推送卡片消息

让 Claude 主动给人发飞书消息（自动把 Markdown 转成卡片，不会满屏星号；还能发带按钮的提问卡）。

- 前提 1：需要应用凭据，**找阿祥单独要 Secret**（绝不能写进任何文件/代码，放自己的 `~/.zshrc` 环境变量）：
  ```bash
  export LARK_XIANGSHU_PUSH_APP_ID="cli_a977681a7d389bc1"
  export LARK_XIANGSHU_PUSH_APP_SECRET="<找阿祥要>"
  ```
- 前提 2：脚本默认发给阿祥；想发给自己，传自己的 union_id 做第二个参数（不知道自己的 union_id 也找阿祥查）
- 用法见技能里的 `SKILL.md`

## 3. xiangxin-problem-delivery — 问题登记 → 处理 → 回写

把你日常碰到的流程问题登记进「纠错日志」Base，按七步处理，处理完自动回写结论。

- 前提：装 `lark-cli` 并登录飞书，且在你的 Base 权限内
- 用途：报错 / 卡点别只在群里喊，登记一次 AI 就能跟踪到底

## 4. xiangxin-shitu-teaching — 师徒制派学 / 验收

老带新的结构化工具：派学习任务、跟进度、验收。

- 前提：`lark-cli` + 任务清单权限
- 用途：新人入职、转岗学新模块时用，别再靠口头带

## 5. xiangxin-doc-task-sync — 文档待办 → 任务卡

把飞书文档里写的「待办 / 下周计划」自动拆成任务卡，挂到对应清单。

- 前提：`lark-cli` + 有文档读权限
- 用途：开会文档写完不用手工再建一遍任务

## 6. xiangxin-replenish-advisor — 补货建议（ABC + 安全库存 + 订货点）

读吉客云库存快照，算动销、ABC 分级、安全库存、再订货点，给出「该补哪些 / 补多少 / 找谁拿」。

- 前提：自己先把库存导出的 xlsx 放进库里，并 `export KB_VAULT=你的库路径`
- 输出：`_待整理/YYYY-MM-DD-补货建议.md`
- 注意：结论依赖快照质量，快照少于两份时只能做端点估算，别当精算用

## 7. 淘宝店铺图片下载器（不在本目录）

在 [[08-运营与工具/工具手册/淘宝店铺图片下载器/README]]。双击 `.command` 按菜单走即可，注意它**依赖 browser-harness**（阿祥电脑上的浏览器控制工具）——荔枝电脑上没装的话先在阿祥电脑上试，或找阿祥装一份。

## 暂未上库的技能（等改造或涉敏感）

| 技能 | 原因 |
|---|---|
| `qianniu-chat-extract` 千牛聊天提取 | 17 处硬编码阿祥本机路径，同事装了也跑不通；需改成可配置再上 |
| `xiangxin-yingke-kefu` 客服副驾 | 脚本内含「成本/拿货价对内部公开」的口径，公开库不适合放，需先删该段 |
| `xiangxin-supplier-finder` 供应商速查 | 含拿货价 / 账期，属报价类敏感，不上公开库 |
| `xiangxin-jingying-analysis` 经营复盘 | 依赖财务口径与毛利数据，不上公开库 |

## 问题反馈

试用中报错 / 用不顺，截图发工作群 @ 阿祥，别自己改这里的文件。
