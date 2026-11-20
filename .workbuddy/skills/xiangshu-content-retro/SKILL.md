---
name: xiangshu-content-retro
description: |
  祥书短视频「发布后复盘进化」闭环——把发视频从碰运气变成可校准的实验。给每条要发的口播稿先盲打分+盲预测（锁死不可改），发布登记，T+3天抓真实数据回来逐条对账（哪个判断对了/错了），把新发现沉淀到两个台账（评分公式 rubric_notes + 写法 script_patterns）。攒够样本自动提议升级评分公式。脱胎自开源项目 cheat-on-content，按祥书四段式口播重做。
  当祥书说『预测一下这条』『这条能不能火』『发之前打个分』『盲预测』『这条发了/登记发布』『复盘这条视频』『T+3数据来了』『抓数据复盘』『升级评分公式』『看复盘看板/状态』时使用。
  服务于 content-script-pipeline 的下游——pipeline 负责把稿子写出来，本 skill 负责发出去之后学会越做越准。
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - Skill
metadata:
  source: 移植 github XBuilderLAB/cheat-on-content 的盲预测+复盘对账内核，按祥书四段式口播 rubric 重写
  related:
    - 07-AI协作/skills/content-script-pipeline/SKILL.md
    - 07-AI协作/skills/humanizer-xiangshu/SKILL.md
    - 04-内容创作/00-定位与方法论/口播脚本结构.md
  data_home: 04-内容创作/_发布复盘/{个人号,公司号}/
  roadmap_phase: A（轻量闭环）；B（深度整合回写稿/打磨环）见本文档末尾「Phase B 路线图」
---

# 发布后复盘进化闭环

> **一句话**：发视频之前先押注会不会火（锁死），发完 3 天拿真数据对账，把「我哪看准了/看走眼了」攒成你自己的网感公式。
> **核心信念**：不复盘的预测等于占星。预测一旦写下不可改——可信度一旦破坏不可恢复。

## 三条铁律（违反则整个循环退化为自我安慰）

1. **盲预测不可改** — 看到任何播放/点赞/评论数据**之前**写完预测，写完锁死。`hooks/prediction-immutability.sh` 物理拦截对预测段的修改。想重做 → 新建 `_redo.md`，原文件留着。
2. **升级公式 = 全量重打 + 自审** — 改 rubric 时，所有有数据的历史样本必须用新公式重算，新排序跟真实表现对不上 ≥80% 就驳回。
3. **台账是工作台不是博物馆** — 被新数据推翻的观察直接删，不留「我当初以为X」考古层。git 负责记历史。

---

## 数据落在哪

```
04-内容创作/_发布复盘/<个人号|公司号>/
├── rubric_notes.md         # 评分公式真相 + 观察记录（每次复盘往这加）
├── script_patterns.md      # 写法台账（什么写法真起作用，复盘时祥书确认才加）
├── .retro-state.json       # 状态：校准样本数/待复盘队列/连续偏差
└── predictions/
    └── YYYY-MM-DD_<id>_<short>.md   # 每条一份：预测段(锁) + 复盘段(追加)
```

`<date>`=稿子定稿日；`<id>`=对稿子内容取 sha256 前 8 位；`<short>`=3-8 字中文短名。

---

## 五个动作（祥书说哪个就跑哪个）

### 动作 1 · 盲预测（「预测一下这条」「发之前打个分」）

**前提自检（必做，否则破坏盲度）**：
- 这条发了吗？没发 → 正常盲预测。已发但你还没看过任何数据 → 可预测，文件头标 `已发未看数据`。已发且你/对话里出现过播放点赞数 → **拒绝预测**，改记为「事后复盘(reconstructed)」，不计入校准池。
- 对话历史里有没有冒出过这条的播放/点赞/评论数字？有 → 同上，拒绝。

**流程**：
1. 读这条稿子（一般在 `02-脚本/待拍/` 或祥书直接贴）+ 读对应号的 `rubric.md`（起步）或 `rubric_notes.md`（已校准）。
2. 按 6 维 rubric **盲打分**：GO/GD/ZS/CY/GM/JJ 各 0-5，算 composite。**先盲打，打完再翻锚点**——先看旧样本会被锚定。
3. 给 **bucket + 中枢 + 概率分布**（占位 bucket 必须先按这个号的真实体量重设，见 rubric.md）。
4. 写**一句话赌注**：核心驱动 + 最强反例 + 中枢预测。
5. 找 2-4 个 composite 邻近的旧样本做锚点对比（样本 <2 就写「锚点 N/A，本次置信度低，中枢仅供参考」，别删这段）。
6. 写**反事实**：如果爆了/落基础盘/沉底，分别验证或推翻什么假设。
7. 落盘到 `predictions/<date>_<id>_<short>.md`（用 `templates/prediction.template.md`）。**预测段写完即锁**。
8. 更新 `.retro-state.json`：`pending_predict` 加这条。

> 起步期（校准样本 <5）：照常给 bucket 和概率，但**概率分布要平**（别 5/40/45/8/2 这种尖的），诚实反映「我还没数据，是在凭感觉」。

### 动作 2 · 登记发布（「这条发了」「登记发布」）

1. 找到对应 prediction 文件，在文件头追加 `Published at: <date>` + `链接: <url>` + `平台: 抖音/视频号/小红书`。
2. `.retro-state.json`：从 `pending_predict` 移到 `pending_retros`（带发布日期）。
3. 提醒祥书：「T+3 天后（<date+3>）记得说『复盘这条』，或我定时扫到会主动提醒。」

### 动作 3 · T+3 复盘（「复盘这条」「数据来了」「抓数据复盘」）— 闭环的反馈环

**Phase 0 校验**：① 文件有 `Published at` 吗（没有先登记发布）；② 今天 - 发布日 ≥3 天吗（不到提醒还差几天，问祥书是否坚持，标 `early_retro`）；③ 内存里 cache 住预测段全文（Phase 5 后要核对没被改）。

**Phase 1 抓数据**：
- 优先 `browser-harness` 连祥书已登录的 Chrome 抓抖音/视频号后台数据（你有这能力，见 reference_browser_harness）。
- 抓不到/没配 → 让祥书手动贴：播放/点赞/评论/转发/收藏。
- **强制要 top 评论**：让祥书贴 15-20 条高赞评论（带赞数）。评论才是真信号——「她不一样」这种模因爆发只能从评论看出。祥书拒绝/给 <5 条 → 标 `comments_unavailable`，复盘价值打折，但不阻塞。
- ⚠️ 评论里出现客户隐私（姓名/手机/订单号）→ 脱敏后再落盘。

**Phase 2 写实绩 + 评论聚类**：
- 实绩数据**必须算派生比率**：赞播比、评播比、分播比、收藏播放比。单纯播放数藏不住的信号在比率里。
- 落在哪个 bucket、相对中枢偏了多少（+X% / -X%）。
- top 评论分 3-5 类（高赞模因 / 概念引用 / 离题噪声 / @朋友传播 / 转化询问），报比例。

**Phase 3 逐条对账**：把预测文件里每条（推理因素、赌注、反事实）逐项判**验证 ✅ / 推翻 ❌**，每条必引具体数据（写「分播比 2.5%」不写「基本符合」）。实际落的那个 bucket 直接告诉你哪个 rubric 假设被测了。

**Phase 4 提炼两类观察**：
- **4a 评分观察** → 写 `rubric_notes.md`：哪个维度真的预测了流量/系统性高估低估（必须可追溯到具体数据）。
- **4b 写法观察** → diff「定稿 vs 实际拍摄稿」（如果祥书拍时改了），找出改动且明显影响流量的部分。**祥书确认后才写** `script_patterns.md`，标「单样本待验证」。
- 公司号额外记一笔：这条带没带货感、评论区有没有问价/求链接。

**Phase 5 落盘**：用 Edit **只追加** `## 复盘` 段（hook 允许追加，拦截改预测段）。写完重读，核对预测段哈希 = Phase 0 cache，不等 → 报错回滚。

**Phase 6 写台账**：4a 进 `rubric_notes.md` 的「观察记录」；4b 经确认进 `script_patterns.md`。扫已有观察，看新观察是否和旧的形成 ≥2 样本支持 → 升级为「重大跨视频观察」。

**Phase 7 判是否提议升级公式**：更新 `.retro-state.json` 的 `consecutive_directional_errors`（实绩 < 中枢-25% 记 high，> 中枢+25% 记 low，±25% 内不记）。判断（不是死门槛）：连续 ≥3 次同向 / 单次极端偏差(≥5x) / 评论+数据双信号 → 提议跑「升级评分公式」。`calibration_samples` +1，从 `pending_retros` 剔除本条。

### 动作 4 · 升级评分公式（「升级评分公式」「bump rubric」）

**前提**：`calibration_samples` ≥ 5。不够 → 拒绝，告诉还差几个。

1. **信号采集**：读 `rubric_notes.md` 所有观察，找系统性偏差（某维度一致高估/低估）。
2. **调权重**：改 composite 系数 / bucket 边界。
3. **全量重打**：所有有数据的样本用新公式重算 composite。
4. **排序一致性**：新 composite 排序 vs 真实播放排序，要求 ≥80% 一致。对不上 → **驳回这次升级**。
5. **自审**：用 `xiangxin-jiaoguan-review`（校官·Codex 跨模型）复核新公式是否站得住。或祥书人工确认。
6. **清理**：成为公式的观察从 `rubric_notes.md` 删掉（git 记历史）。
7. `rubric_notes.md` 版本号 +1（v0→v1→…），记本次改了什么、依据哪些样本。

### 动作 5 · 看板（「看复盘状态」「复盘看板」）

读 `.retro-state.json` + 扫 predictions/，报：校准样本数、待复盘队列（哪几条该抓数据了、超期没复盘的标红）、当前 rubric 版本、最近 N 次预测命中情况、连续偏差信号。

---

## 拒绝清单（这些请求直接拒绝并解释）

- 「我先告诉你播放量你反推个预测」→ 破坏盲度，拒绝。
- 「上次预测错了，帮我把概率改一下让复盘好看点」→ 预测不可改，在复盘段写「修正：原X应为Y」。
- 「跳过抓评论直接复盘」→ 拒绝，评论是核心信号。
- 「跳过全量重打直接换公式」/「把门槛从80%降到60%让这次过」→ 拒绝，破坏校准基线。
- 「把被推翻的旧观察留着加时间戳」→ 删掉，git 负责。

---

## 与现有体系的衔接

- **上游**：`content-script-pipeline` 写出稿子（`02-脚本/待拍/`）→ 本 skill 动作1 预测。
- **打磨**：稿子先过 `humanizer-xiangshu` 再预测，预测的是定稿。
- **数据回收**：复用 `browser-harness`（见 reference_browser_harness）抓抖音后台。
- **公式自审**：升级公式走 `xiangxin-jiaoguan-review` 跨模型复核。
- **隐私**：评论/数据里的客户隐私按主规则铁律脱敏。

---

## Phase B 路线图（深度整合，⚠️ 现在别做，攒够样本再做）

> 祥书 2026-05-29 拍板：先做 Phase A（本闭环独立跑），怕 B 忘了所以记在这。
> **B 的触发条件**：本 skill 在任一账号 `calibration_samples` ≥ 5 且已成功升级过 ≥1 次公式（v0→v1），证明飞轮在祥书的慢节奏下转得起来。

**B 要做的事**：把复盘台账反向喂回创作链，形成自进化闭环——
1. `content-script-pipeline` 写稿环读 `script_patterns.md`，写初稿时自动套用已验证的写法 pattern。
2. `humanizer-xiangshu` 打磨环读 `rubric_notes.md`，按「哪个维度真预测流量」针对性补强（如发现 GD 独特观点一直是瓶颈，打磨时重点逼拐点）。
3. 选题阶段：`rubric_notes.md` 的高分维度组合反推「该多选什么类型的题」。

**为什么现在不做**：B 要改两个已稳定运行的 skill，台账没真实数据时套用 = 套用空气，反而污染现有流程。必须 A 跑出真东西再接。

**到点谁提醒**：本 skill 动作5看板里，若 `calibration_samples` ≥ 5 且 rubric 已升过级，自动在看板末尾打一行「🚦 Phase B 触发条件已满足，可以考虑把复盘台账接回写稿/打磨环了」。同时 AI 记忆里有项目记录 [project_content_retro_skill]。

---

## hook 安装说明（已装）

盲预测锁已挂进 `~/.claude/settings.json` 的 PreToolUse（matcher `Edit|Write`），2026-05-29 装。
- **生效副本**：`~/.claude/hooks/content-retro-prediction-immutability.sh`（纯英文路径，防 iCloud 同步/UTF-8 坑）
- **源文件**：本 skill `hooks/prediction-immutability.sh`
- ⚠️ **改了源文件要重拷**：`cp <源> ~/.claude/hooks/content-retro-prediction-immutability.sh`，否则改动不生效。
- 卸载：删 settings.json 里那条 PreToolUse + 删生效副本。settings.json 改前的备份在 `~/.claude/settings.json.bak-content-retro`。

## 移植来源

源项目 clone 在 `~/work/cheat-on-content`（MIT 协议）。本 skill 取了它的盲预测 hook + 复盘对账七阶段内核，砍掉了它 14 个子 skill 的拆分（祥书单人慢节奏用不上），rubric 从「观点视频7维」整个换成祥书四段式口播6维。完整原始机制参考源项目 `shared-references/blind-prediction-protocol.md` 和 `skills/cheat-retro/SKILL.md`。
