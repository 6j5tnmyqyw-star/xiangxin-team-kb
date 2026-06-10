---
name: xiangxin-jiaoguan-review
description: 校官——跨模型质检。用与撰写者不同的模型(Codex)复核别的 agent/人的产出，专挑毛病：文案违禁词、调价数字、对账结果、SOP 正确性。当祥书说『校官查一下』『用 codex 复核』『这条文案/调价/对账/SOP 帮我审一遍』『跨模型校验』，或任何 agent 即将发布对外/对客户/动钱的产出需要二次把关时使用。
---

# 校官（xiangxin-jiaoguan-review）

祥新 AI 组织里的「质检」横向员工。核心原理来自那套 AI Agency 设计：
**Claude 写的让 Claude 验只会说"挺好"，必须换一个模型（Codex）才挑得出毛病。**

任何 agent 即将产出【对外 / 对客户 / 动钱 / 发团队】的东西——发布前先过校官。

## 跑法

```bash
cd 07-AI协作/skills/xiangxin-jiaoguan-review
python3 check.py --type 文案 --file draft.txt        # 文件
python3 check.py --type 调价 "Bushnell V6 京东价改 1299"  # 直接传
echo "内容" | python3 check.py --type SOP             # stdin
python3 check.py --type 对账 --file recon.md --json   # 只要原始 JSON
python3 check.py --type 通用 --file x.md --focus "重点看数字"
```

type：`文案`（违禁词/品牌名/夸大/隐私）｜`调价`（录错/亏本/天猫基准/SKU）｜`对账`（金额/绿黄红/错配）｜`SOP`（事实/矛盾/可读性）｜`通用`

## 输出

`✅ PASS`（没问题）｜`🟡 RISK`（有可疑点需人确认）｜`🔴 FAIL`（有硬伤必须改：违禁词/亏本/隐私/事实错误），附逐条问题 + 改法。

## 关键设计

- 引擎是 `codex exec --skip-git-repo-check -s read-only --ephemeral`（只读沙盒、不落盘、跨模型）。需 `codex login` 已登录。
- 校官只挑毛病、不改、不发布——把关权和拍板权留给人 / 调用方。
- 文案质检会自动带上 vault 里 `07-AI协作/规则/03-内容创作*` 的违禁词规则。
- 这是按需工具，不挂 launchd；可被其他 skill 或会话当"发布前一道关"调用。
- 配套：采集层 [[xiangxin-jiucuo-daily]]、决策层 [[xiangxin-zhanggui-review]]（掌柜复盘）。
