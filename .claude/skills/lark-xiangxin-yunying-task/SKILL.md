---
name: lark-xiangxin-yunying-task
version: 1.1.0
description: "祥新公司专用：给运营组（何小琴/王娜/洪丽华/于嘉欣/孙庆弘）批量派发飞书任务。当祥书说『给运营/给所有运营发个任务』『让运营调价/下架/上架/拍摄/整理 ...』『派任务给运营组』『让大家把 X 调价到 Y』时使用。自动会签所有 5 个运营 + 自动挂【祥新任务】清单。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# 祥新运营任务派发

> **前置条件：** 先阅读 [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md) 和 [`../lark-task/SKILL.md`](../lark-task/SKILL.md)。

## 适用场景

祥书要"给运营发任务"，比如：
- 调价 / 改价（"把 X 调价到 199"）
- 商品下架 / 上架
- 整理货品 / 拍摄 / 入库
- 朋友圈内容、清仓任务
- 其它需要 5 个运营都执行一次的工作

不适用：只发给一个具体人（直接用 lark-task）；视频/直播单人任务；跨部门任务。

## 运营组成员（写死，不用现查）

| 姓名 | open_id |
|------|---------|
| 何小琴（荔枝） | `ou_14bf1279a6115f36cf5e98746e138f8a` |
| 王娜（娜娜） | `ou_f4d78367e15db6628b2a5ff71218bfc7` |
| 洪丽华（洪洪） | `ou_655d3dd4590eb9baa9415596bba31ce3` |
| 于嘉欣（嘉欣） | `ou_ab49258dc68e351d1bf1cbdf24b0c622` |
| 孙庆弘（内容运营） | `ou_047bb1745d4d61c3430023d8eb545e5c` |

如果祥书指明"只发给其中几个"，按名字裁剪即可，不要现查通讯录。

## 默认配置（不要漏）

- **清单**：【祥新任务】tasklist guid `a1b4297b-0a7a-4b0e-8748-e0b75ae15485`
  - 别选成【祥新任务（祥书账号）】(`a543155a-c25c-44f2-aa1e-c553b97697b4`)，那是祥书私人清单
- **模式**：`mode=1` 会签（每人都要单独标记完成）
- **截止时间格式**：祥书常说"明天下班前 6 点" → `2026-MM-DDT18:00:00+08:00`
- **身份**：`--as user`（任务要挂在祥书名下，让运营看到是老板发的）
- **优先级写进清单字段**（不止标题前缀）：【祥新任务】清单有个单选自定义字段「优先级」，要写进去让同事按字段筛选/排序。
  - 字段 guid：`e9b77aba-6cc3-40b1-aa23-f448ddbcdd59`
  - 选项 guid：高 `d7aff674-0ef8-6397-9108-fb260e21bde9`｜中 `6238286f-b2e2-5ab8-e902-a3bb9dc242b0`｜低 `9de7ca79-281c-0b3b-75d6-847a8c69a330`
  - ⚠️ 同清单还有个独立字段「风险级」(guid `e9b77aba…` 之外的 `72cfcfe9…`/`74ba9133…`)，别写错。
  - 映射：标题前缀 `🔴高`→高、`🟡中`→中、`🟢低`→低。标题前缀**保留**（一眼可见），字段**也写**（可筛选）。
  - 需要 `task:custom_field:write` scope（已在 app `cli_aa8af48fd1785bb4` 授权）。

## 优先级（每条任务都要判 + 标，不要问祥书）

按 **重要 × 紧急** 双维自己判，标在**任务标题前缀**，方便运营按重要的先做：

| 重要 | 紧急 | 标题前缀 | due 倾向 |
|---|---|---|---|
| ✓ | ✓ | `🔴高｜` | 今天 / 明天 |
| ✓ | ✗ | `🟡中｜` | 本周 |
| ✗ | ✓ | `🟡中｜`（能委托就委托）| 1–3 天 |
| ✗ | ✗ | `🟢低｜` | 长 due / 无硬期限 |

- **重要** = 影响营收/客户/合规或老板在盯；**紧急** = 有近 deadline 或不做会扩大损失。
- 口诀：**重要的事最低也是中，只有又不重要又不急才落 🟢 低**。
- description 首行写「优先级：🔴高（重要✓ 紧急✓）— <一句理由>」，让判断透明、祥书可改。
- 判出的优先级还要写进清单「优先级」字段（见 Step 4），同事好筛选/排序。
- 详见记忆 `feedback_ai_judges_priority`。

## 完成是否需要交付物（每条自己判，不要问祥书）

派任务时判断这条「做完了应该留下可验证的东西吗」：

- **需要交付物**：上架 / 调价 / 改主图 / 拍摄 / 做图 / 数据分析 / 对账 / 整理表格 / 优化方案 / 写文档 / 谈判结果……凡是「做完应该有个东西能看」的。
- **不需要**：纯知会 / 收悉 / 检查确认 / 开会提醒 / 转发到群 / 「看一下」这类无产出物的。

**需要交付物时，把这句话写进任务 `--description` 末尾**（不要再用 `custom_complete`，原因见下）：

> ✅ 完成前请先在本任务评论区贴上交付结果（截图/链接/一句话说明做了什么），没有交付物视为未完成。

> 🚫 **绝对不要再用 `custom_complete`（自定义完成）卡完成。**
> 实测（2026-05-27 荔枝/阳阳）：只配 `tip`、不配 `href` 的 `custom_complete`，在手机端点「完成」只弹提示、**没有"仍然完成"按钮，任务被硬卡死、永远点不了完成**——不是软提醒。这跟早期记忆里写的"确认后还能完成"相反，已被真人实测推翻。
> 当时全板 177 条未完成里有 104 条被这么卡死，已批量清除。
> **硬闭环改靠 AI 定期抽查**已完成任务有没有交付痕迹（评论 / `attachments` / `text_deliveries`），没有的打回 + 提醒——背景见记忆 `project_tasklist_default`。

## 命令编排（4 步）

### Step 1：创建任务并挂到清单（带第一个 assignee）

```bash
lark-cli task +create \
  --as user \
  --summary "<任务标题>" \
  --description "<详细描述，含完成确认要求>" \
  --assignee "ou_14bf1279a6115f36cf5e98746e138f8a" \
  --due "2026-MM-DDTHH:MM:00+08:00" \
  --tasklist-id "a1b4297b-0a7a-4b0e-8748-e0b75ae15485"
```

**记下返回的 `data.guid`**，下两步要用。

### Step 2：批量加上其他 4 个 assignee

```bash
lark-cli task members add \
  --as user \
  --params '{"task_guid":"<Step1 返回的 guid>"}' \
  --data '{"members":[
    {"id":"ou_f4d78367e15db6628b2a5ff71218bfc7","role":"assignee","type":"user"},
    {"id":"ou_655d3dd4590eb9baa9415596bba31ce3","role":"assignee","type":"user"},
    {"id":"ou_ab49258dc68e351d1bf1cbdf24b0c622","role":"assignee","type":"user"},
    {"id":"ou_047bb1745d4d61c3430023d8eb545e5c","role":"assignee","type":"user"}
  ]}'
```

### Step 3：改成会签模式

```bash
lark-cli task tasks patch \
  --as user \
  --params '{"task_guid":"<Step1 返回的 guid>"}' \
  --data '{"task":{"mode":1},"update_fields":["mode"]}'
```

> 「需要交付物」不再走 `custom_complete`（会把任务在手机端卡死、点不了完成，见上一节）。交付要求直接写在 Step 1 的 `--description` 末尾那句话即可。

### Step 4：写「优先级」清单字段

把第 47 行判出的优先级写进字段（`<option_guid>` 按 高/中/低 取上面的选项 guid）：

```bash
lark-cli task tasks patch \
  --as user \
  --params '{"task_guid":"<Step1 返回的 guid>"}' \
  --data '{"task":{"custom_fields":[{"guid":"e9b77aba-6cc3-40b1-aa23-f448ddbcdd59","type":"single_select","single_select_value":"<option_guid>"}]},"update_fields":["custom_fields"]}'
```

## 完成后给祥书的汇报模板

```
✅ 任务已派发
- 标题：<标题>
- 清单：【祥新任务】
- 负责人：<列出的 5 个姓名>（会签）
- 截止：YYYY-MM-DD HH:MM
- 链接：<task url>
```

## 注意事项

- **不要现查 open_id**。表格里已经写死，直接用。如果祥书提到新员工，再查并提示要更新本 skill。
- **不要再问"哪个清单"**。默认【祥新任务】(`a1b4297b-...`)。
- **不要默认或签**。或签 = 任一人完成全任务关闭，不符合"每人各做一次"的意图。
- **跨租户 assignee 警告可忽略**：5 人都是 `is_cross_tenant=true`，但 user 身份下可以正常分配，bot 身份才不行——所以本 skill 强制 `--as user`。
- **截止日期换算**："明天" = 今天 +1 天；"下班前" = 18:00；不知道日期就先 `date +%Y-%m-%d` 拿今天。
- **描述里加确认要求**：建议在 description 末尾写"完成后在任务里回复确认"，方便祥书跟进。

## 权限

| 操作 | 所需 scope |
|------|-----------|
| 创建任务 | `task:task:write` |
| 添加成员 | `task:personnel:writeonly` + `task:task:write` |
| 修改任务 | `task:task:write` |
| 挂清单 | `task:tasklist:write` |

如缺权限，按 [`lark-shared`](../lark-shared/SKILL.md) 的 `auth login --scope` 流程补授权。

## 维护

- 运营组人员变动 → 更新本 skill 顶部 open_id 表
- 默认清单换了 → 更新 `a1b4297b-...` 这个 guid
- 来源参考：祥子AI 知识库 `CLAUDE.md` 的"团队/运营组"段
