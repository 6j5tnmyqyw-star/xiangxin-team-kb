# 技能已迁到 `.workbuddy/skills/`（2026-11-20）

公司 30+ 个 AI 技能**不再放这里**，全部搬到了仓库根目录的 **`.workbuddy/skills/`**。

## 为什么搬

团队现在统一用 **WorkBuddy**。WorkBuddy 只认两个技能目录：

| 级别 | 路径 | 说明 |
|---|---|---|
| 项目级（本库用这个） | `{工作区}/.workbuddy/skills/` | 只在本库生效，同事同步库就自动带上 |
| 用户级 | `~/.workbuddy/skills/` | 所有项目都生效，同名时项目级优先 |

WorkBuddy **不读 `.claude/skills/`**。原来放这里，等于技能根本没生效——2026-11-20 之前所有同事都踩了这个坑。

## 现在怎么用

1. 用 WorkBuddy 打开本库（工作区选团队知识库根目录）
2. 直接说人话，比如「帮我对账」「把这条询单回一下」「列一下 V6S 的售后单」
3. 技能名对得上就自动加载，不用手动装

技能清单 / 版本 / 谁能用 → 飞书「📦 AI 技能更新台账」：https://xiangxingolf.feishu.cn/wiki/EAI1wrGl8izDAUkD9AtcMIADnMb

## 还留着这个目录做什么

给仍在使用 Claude Code 的人留个路标。如果你确实在用 Claude Code，把
`.workbuddy/skills/` 下的技能软链到 `~/.claude/skills/` 即可：

```bash
mkdir -p ~/.claude/skills
ln -s "$(pwd)/.workbuddy/skills/"* ~/.claude/skills/
```

新装机的同事**不用管这个目录**，按 WorkBuddy 那套走就行。
