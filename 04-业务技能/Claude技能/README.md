# Claude 技能包（团队试用）

这里放阿祥这边验证过、给团队复用的 Claude 技能。装法统一：**把技能文件夹复制（或软链）到你电脑的 `~/.claude/skills/` 下**，重开 Claude 即生效。

```bash
mkdir -p ~/.claude/skills
cp -R "<本库路径>/04-业务技能/Claude技能/content-visualizer" ~/.claude/skills/
cp -R "<本库路径>/04-业务技能/Claude技能/lark-push-xiangshu" ~/.claude/skills/
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

## 3. 淘宝店铺图片下载器（不在本目录）

在 [[08-运营与工具/工具手册/淘宝店铺图片下载器/README]]。双击 `.command` 按菜单走即可，注意它**依赖 browser-harness**（阿祥电脑上的浏览器控制工具）——荔枝电脑上没装的话先在阿祥电脑上试，或找阿祥装一份。

## 问题反馈

试用中报错/用不顺，截图发工作群 @ 阿祥，别自己改这里的文件。
