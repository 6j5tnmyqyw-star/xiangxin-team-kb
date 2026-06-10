---
name: xiangxin-problem-delivery
version: 1.0.0
description: "祥新公司专用：祥书把【问题日志 Base】里的一条问题/事项直接发给 AI 处理。AI 完成后必须自动把交付（规则正文、文档链接、附件、群消息截图等）登记回 Base 对应记录，并把『是否处理』勾上。当祥书发来一段问题描述、贴 Base 链接/record_id、转飞书消息说『这个你处理一下』『把这个搞定登记下』『去 Base 找 XXX 那条处理完登记上』时使用。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# 祥新问题交付登记

> **前置条件：** 先读 [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md)、[[07-AI协作/规则/11-问题记录与处理流程]]。Base 元信息见 memory `reference_problem_log_base.md`。

## 适用场景

祥书把【问题日志 Base / Claude纠错日志】里某条**已存在**的问题派给 AI 处理。形式可能是：

- 直接贴 record_id 或 Base 行链接
- 复述一段问题描述（"那个绩效核对不查祥新任务清单的"）
- 转一段录音/会议/聊天里抽出的事，并说"处理一下"

> ⚠️ **不适用**：祥书让记**新问题**到 Base —— 那走 [[07-AI协作/规则/11-问题记录与处理流程]]，不走本 skill。本 skill 处理的是"已有记录 → 落地交付 → 登记回 Base"。

## Base 元信息（写死）

| 项 | 值 |
|---|---|
| base_token | `CWuIblgzqaW7lUsivCBccKSmnqf` |
| table_id | `tblfZ9iO2sqYEWTy` |
| URL | https://xiangxingolf.feishu.cn/base/CWuIblgzqaW7lUsivCBccKSmnqf |

字段 ID 速查：`截图附件`=`fldCUzhQM2`，`附件交付`=`fldJGEEUox`，`分类`=`fldWy7fuE3`

## 工作流（五步）

### Step 1：定位 Base 记录

- 祥书给了 record_id：直接用。
- 只给描述：用 `+record-search` 按关键词搜（搜 `错误场景` / `正确做法` / `文本交付` / `备注`）。

```bash
lark-cli base +record-search \
  --base-token CWuIblgzqaW7lUsivCBccKSmnqf \
  --table-id tblfZ9iO2sqYEWTy --as user \
  --json '{"keyword":"<关键词>","search_fields":["错误场景","正确做法","文本交付","备注"],"limit":20}'
```

搜到多条 → 列出来让祥书选；搜不到 → 反问"是不是要新建一条？"（若是，转到 [[07-AI协作/规则/11-问题记录与处理流程]]）。

### Step 2：完成实际工作

按问题性质处理。常见交付物：

| 问题类型 | 交付物 |
|---|---|
| 流程规则 / SOP | 在对应规则文档（如《海英工作流程与规则手册》《电商运营规则》）里补/改条款 |
| 价格 / 库存 | 调价、改库存，截图保留 |
| 客服 / 售后 | 起草客服话术或客户答复 |
| 内容创作 | 给庆弘的修改建议 / 重写文案 |
| AI 工具 | 改 prompt / 改脚本 / 改 skill |
| 团队管理 | 起草通知文案 |

> 💡 涉及 **流程规则** 类的交付，写法必须符合 [[07-AI协作/规则/11-问题记录与处理流程#61-流程类问题的特殊要求]]（公司正式规则风格，不口语化），文档里建议用 callout 块标注。

### Step 3：登记交付回 Base（核心）

完成后**必须**回写 Base，不要漏。最小字段集：

```bash
lark-cli base +record-upsert \
  --base-token CWuIblgzqaW7lUsivCBccKSmnqf \
  --table-id tblfZ9iO2sqYEWTy --as user \
  --record-id <record_id> \
  --json '{
    "是否处理": true,
    "正确做法": "<一段话总结今后应该怎么做，正式风格>",
    "文本交付": "<对应文档/规则的标题 + 飞书链接；多条用换行分隔>",
    "分类": "<若原记录分类为空，按 11-规则第四节补一个>"
  }'
```

有附件（截图、文件）单独走附件命令，不要塞进 json：

```bash
lark-cli base +record-upload-attachment \
  --base-token CWuIblgzqaW7lUsivCBccKSmnqf \
  --table-id tblfZ9iO2sqYEWTy \
  --record-id <record_id> \
  --field-id fldJGEEUox \
  --file <本地文件路径>
```

**不要做**：
- 不要勾「已入规则」（周五祥书自己勾）
- 不要修改「发现人」「发现日期」「评分」「优先级」
- 不要在「Claude错答」里乱填（仅原本就是 AI 错答场景才有值）

### Step 4：起草并发推送（强制 · 不可跳过）

⚠️ **任何流程规则 / SOP 类的更新都必须发推送给对应群/人，不只是"问一下"——是默认动作。** 团队不知道新规则等于规则不存在。

起草推送文案的要点：
- 标题写清楚是「新规」或「规则更新」 + 部门/范围
- 用书面口吻（公司正式规则风格，不要"通知大家""收到回 ✅"这种口语）
- 三段式：**为什么发**（背景/原因，1 句）→ **规则核心**（条款，2-4 条）→ **谁负责什么**（执行职责，精确到人）
- 附飞书规则原文链接
- 落款：阿祥 + 生效日期

发推送前先问祥书两件事（一次问完，不要分多次）：
1. **推给谁？** 群（哪个群？常见：电商运营工作群 / 客服售后群 / 库房群 / 财务对接群 / 仓库发货群 / 内容创作群）/ 人（指定 open_id）
2. **草稿你审一下** —— 把推送原文摆出来，他改/认可后再发

祥书认可后**真的发出去**，用：
- 发群：`lark-im` skill
- 发给祥书本人确认收到：`lark-push-xiangshu` skill（仅他本人确认场景用，不替代发群）

发完留证：截图或回执贴回 Base 记录的「附件交付」字段（用 `+record-upload-attachment`）。

❌ **不要做**：
- ❌ 不要登记完 Base 就完事——没发推送等于规则没落地
- ❌ 不要不问祥书就发——他要审文案、定推送对象
- ❌ 不要在群里口语化（"大家注意一下"、"收到回 1"）——按公司正式规则风格

### Step 5：汇报祥书

简短回复，包含：
1. 处理了什么（一句话）
2. 交付链接（文档 URL）
3. 已回写的 Base 字段（说出"是否处理已勾、文本交付已填"）
4. 推送已发到哪个群/人 + 回执截图（如有）

## 触发关键词

- "这个你处理一下" / "搞定后登记下"
- "去 Base 找 XXX 那条" / 贴出 Base record 链接
- "把这个问题处理掉" / "完成后填到表里"
- 任何形式的"已有 Base 记录 → 派活给 AI"

## 与其它 skill 的衔接

| 场景 | 配合 skill |
|---|---|
| 改飞书云文档 | lark-doc |
| 发飞书任务给运营 | lark-xiangxin-yunying-task |
| 发群消息 | lark-im（祥书明确指令"发"才动手） |
| 上传附件文件 | lark-base / lark-drive |
| 新建一条问题记录（非本 skill 场景） | 走 [[07-AI协作/规则/11-问题记录与处理流程]] |
