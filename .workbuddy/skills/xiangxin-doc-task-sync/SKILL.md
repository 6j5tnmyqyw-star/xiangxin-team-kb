---
name: xiangxin-doc-task-sync
version: 1.0.0
description: "祥新公司专用：把任意飞书文档里的待办（勾选框 ☐ 或待办文字行）转成绑定飞书任务的【同步任务卡片】——文档里勾掉=任务中心完成，反之亦然（双向同步）。自动给每条待办建飞书任务（挂【祥新任务】清单、按文档归属/点名派人/识别优先级与截止），再把文档里对应的勾选框替换成 <task> 卡片。当祥书给一个飞书文档链接并说『把里面待办挂上飞书任务』『这些待办关联飞书任务』『待办转成同步任务卡片』『文档待办建成任务』『待办跟飞书任务关联起来』『把这文档的待办同步到任务』时使用。区别于 xiangxin-yunying-meeting（那个是妙记→提取→登记全流程，本 skill 只做"待办→同步卡片"这一段，可作用于任意文档）。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# 祥新·文档待办 → 飞书同步任务卡片

> **前置：** 先读 [`../lark-shared/SKILL.md`](../lark-shared/SKILL.md)。命令细节按需读 [`../lark-doc`](../lark-doc/SKILL.md)（**用 `--api-version v2`**）、[`../lark-task`](../lark-task/SKILL.md)。
> 运营组 open_id 见下表，其余人见 memory `reference_company_roster.md`。

## 一句话

祥书给**任意飞书文档**（wiki/docx）→ 我把里面**未完成的待办**逐条建成飞书任务（挂【祥新任务】、派对的人）→ 把文档里对应的**勾选框替换成 `<task>` 任务卡片**。卡片和任务**双向同步**：文档勾掉=任务完成，任务点完=卡片变完成。这就是祥书要的"那边点了这边就同步"。

## 默认行为（祥书 2026-05-26 定，最重要）

**祥书在文档里写待办，默认就要跟飞书详细任务同步，不用他开口说"挂任务"。**
- AI 主动往他飞书文档写待办（会议总结/日会跟进/工作安排）时，**默认直接落 `<task>` 同步卡片**，不要先写成普通勾选框再等他要求转。
- 本 skill 的触发词（"挂任务/关联飞书任务"）只是"对已有文档补转"的显式入口，**不是同步的前提**。
- **缝隙**：祥书自己手敲的勾选框 AI 实时看不到。要做到他敲了也"不用说一句"，需定时扫描固定文档清单自动补转（见 memory `feedback_doc_todo_default_sync`，扫哪些文档/频率待敲定）。

## 原理（务必理解，别搞错）

飞书文档里两种"待办"长得像但完全不同：
- **普通勾选框** `<checkbox done="false">文字</checkbox>`：勾没勾只活在文档里，**任务中心无感**，不同步。
- **任务卡片** `<task task-id="GUID"></task>`：和飞书任务中心**原生双向绑定**。必须先有一个真实飞书任务（拿到 GUID），才能插这个卡片。

所以转换 = ①建飞书任务拿 GUID → ②`block_replace` 把勾选框换成 `<task task-id="GUID">`。

## 固定资源

| 资源 | 值 |
|---|---|
| 【祥新任务】清单 tasklist | `a1b4297b-0a7a-4b0e-8748-e0b75ae15485`（**别**选成祥书私人清单 `a543155a-...`） |

### 运营组 open_id（派任务用，跨租户那条）

| 别名 | 真名 | open_id |
|---|---|---|
| 荔枝 | 何小琴 | `ou_14bf1279a6115f36cf5e98746e138f8a` |
| 娜娜 | 王娜 | `ou_f4d78367e15db6628b2a5ff71218bfc7` |
| 洪洪/红红 | 洪丽华 | `ou_655d3dd4590eb9baa9415596bba31ce3` |
| 嘉欣 | 于嘉欣 | `ou_ab49258dc68e351d1bf1cbdf24b0c622` |
| 老孙 | 孙庆弘 | `ou_047bb1745d4d61c3430023d8eb545e5c` |
| 鹤子 | 徐鹤 | `ou_f972473873fc9088193de4ed88eabfed` |
| 祥书本人 | 邹祥书 | `ou_ed1dba4721b4aae7f7f0a96ebf37b63c` |

> 点到运营之外的人，现查 `lark-cli contact +search-user` 确认（荔枝/洪洪有双账号，选**跨租户 + 部门=祥书（河北）国际贸易**那条）。

## 流程

### Step 1 · 读文档、抓待办

```bash
lark-cli docs +fetch --api-version v2 --doc "<文档URL或token>" --detail with-ids
```

抓取目标 = **未完成的待办**，按优先级：
1. `<checkbox done="false">...</checkbox>` 块（**主力**，记下每块 `id` 和文字）。
2. 看起来是待办的纯文本行（`<p>` 里写着动作项，如"拍摄素材""统一整理价格"）——仅当祥书明确说"连没打框的待办也转"时才纳入；默认只转勾选框。

**跳过**：`done="true"` 的历史项（已完成，转了没意义）；已经是 `<task>` 的块（已绑定）。
> 默认只处理祥书指定的小节 / 最近一次会议小节；他说"整篇都转"才全文扫。

### Step 2 · 逐条定三件事：派给谁 / 优先级 / 截止

**派给谁（assignee）— 决策树，从上往下命中即停：**
1. 祥书调用时显式说了"派给 X / 这是 X 的文档" → X。
2. 待办文字里点名（"娜娜：上架""@荔枝 调价") → 那个人。
3. 文档明确归属某人（标题如「老孙每日工作安排」、某人专属工作文档） → 该人。
4. 会议类文档（标题含"会议/晨会/日会"）→ 按行点名；点不到名的，进 Step 3 预览标 `❓待定`。
5. 都判不出 → **不瞎派**，预览里标 `❓待定`，让祥书一次性指定。

**优先级：** 待办已带 `🔴/🟡/🟢` 前缀就沿用；没有则 AI 自己判（重要×紧急），标 `🔴高/🟡中/🟢低`（依据见 memory `feedback_ai_judges_priority`）。

**截止：** 先 `date +%Y-%m-%d` 拿今天，把"今天/下班前/明天/本周"等换成绝对时间 `2026-MM-DDTHH:MM:00+08:00`（"下班前"按 18:00）。识别不到就留空，不硬编。

### Step 3 · 预览（有不确定才必须预览）

- **若每条 assignee 都明确**（决策树 1-3 命中，无 `❓`）→ 可**直接落地**（建任务直接发，见 memory `feedback_send_tasks_directly`）。
- **只要有任何一条标了 `❓待定`** → **必须先发清单给祥书指定派给谁**，再落地。别把判不准的任务瞎派出去通知到人。

预览格式：
```
【待办 → 任务】(派给谁 · 优先级 · 截止)
1. 老孙｜🔴高｜今天：今天下班前定要调的货
2. ❓待定｜🟡中｜—：整理店铺价格   ← 这条派给谁？
```

### Step 4 · 落地（每条两步，幂等）

**① 建飞书任务**（挂【祥新任务】）：
```bash
lark-cli task +create --as user \
  --summary "🔴高｜<负责人>：<标题>" \
  --description $'优先级：🔴高（重要✓ 紧急✓）— <理由>\n<详细要求>\n来源：<文档名/会议>\n完成后在任务里回复确认' \
  --assignee "ou_xxx" \
  --due "2026-MM-DDTHH:MM:00+08:00" \
  --tasklist-id "a1b4297b-0a7a-4b0e-8748-e0b75ae15485" \
  --idempotency-key "<doc短token>-<blockid>"   # 幂等：重复跑不会重建
# 从返回 JSON 取 data.guid
```
> `--description` 用 `$'...\n...'`（ANSI-C 引号）才能得到真实换行。截止留空就不传 `--due`。
> 多人**各自**都要做同一件事（会签）→ 别用 `+create`，改原生 `task tasks create --data` 加 `"mode":1` + `members`（见 `xiangxin-yunying-meeting` 3A 与 memory `reference_lark_task_huiqian`）。

**② 把勾选框替换成任务卡片**：
```bash
lark-cli docs +update --api-version v2 --doc "<doc>" --command block_replace \
  --block-id "<checkbox的blockid>" \
  --content "<task task-id=\"<上一步的guid>\"></task>"
```
> 纯文本待办行（Step 1 第2类）同理，把那个 `<p>` 的 block-id 替换成 `<task>`。

### Step 5 · 验证 + 汇报

```bash
# 抽查：对应小节现在应是 <task ... status="init"> 而不是 <checkbox>
lark-cli docs +fetch --api-version v2 --doc "<doc>" --scope section --start-block-id "<小节标题id>" --detail with-ids
```
汇报（简短）：建了 N 条任务（派给谁）、文档对应位置已换成同步卡片、文档链接。提示祥书：随手在文档勾一条 / 在任务 App 点一条，验证双向同步。**点明 assignee 是按哪条规则判的**，判错让他改。

## 铁律（违反要主动提醒）

1. **先有飞书任务（GUID）才能插 `<task>` 卡片**，顺序不能反。
2. 任务**必挂【祥新任务】** `a1b4297b-...`；多人各自做用会签 `mode:1`。
3. **派给谁判不准就标 `❓` 先问，不瞎派**（会直接通知到人）。
4. 用 `--idempotency-key`（doc+blockid）保证**重复跑不重建**；已是 `<task>` 的块跳过 → 天然可重跑。
5. 只转**未完成**待办（done=false），不动已完成历史项。
6. 顾客 PII（手机/地址/订单号）不进任务标题/描述；人名/品牌名写前核对花名册 + grep vault。
7. 改文档只动目标勾选框，**别碰图片、其他块**（block_replace 精确到 block-id）。

## 维护

- 运营人员/open_id 变动 → 更新本 skill 顶部表 + `reference_company_roster`。
- 衔接：会议全流程走 `xiangxin-yunying-meeting` / `xiangxin-xiaoshou-meeting`（它们的"待办→卡片"段就是本 skill 的逻辑）；纯派任务给运营组走 `lark-xiangxin-yunying-task`。
