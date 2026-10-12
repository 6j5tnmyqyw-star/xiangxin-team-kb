---
类型: 团队文档
目标位置: 08-公司知识库/AI协作规则/13-完整AI系统装机手册（Claude Code版）.md
来源: 祥书要求（5/18 周会 Z1 任务，老孙首批内测）
创建时间: 2026-05-18 17:30
关联人物: 邹祥书、孙庆弘、何小琴、王娜、洪丽华、于嘉欣
关联项目: AI 转型推进、Claude Max 实战、全员 Claude Code 内测
配套文件: _配套-空白CLAUDE.md模板-给同事.md
状态: 归档（2026-10 起不再作为团队主路径）
---

> **不要按本文装机。** 阿祥 2026-10 起，团队主路径是飞书机器人 + Obsidian，见 [[07-AI协作/团队AI装机手册]]。本文只留作以前 Claude Code 方案的记录。飞书文档 https://xiangxingolf.feishu.cn/docx/XKcRdIyU9ovE5rxuOMxc09Wyntg 已改为五步新手册，不要按下面的 Claude / 官网下载 Obsidian 步骤操作。

# 📘 完整 AI 系统装机手册（Claude Code 版）

> **历史说明**：下面正文写于 2026-05，当时飞书链还指向 Claude 版。该链接现已换成新手册。

> 这套是**祥书自己每天在用的「深度版」AI 工作系统**。装完之后，你就有了一个能读你电脑文件、能改你飞书文档、能自动整理资料、能长期记得你偏好的私人 AI 助手。
>
> **适合**：愿意花一晚上跟着教程走完、之后每天用 1 小时以上 AI 的同事。
> **不适合**：偶尔写写文案、查查规则——直接看 [[12-团队AI助手(Claude桌面版)使用指南]]，那个 5 分钟装完。

**最后修订**：2026-05-18　**修订人**：邹祥书　**面向**：老孙（首批内测）→ 后续有意愿的同事

---

## 0. 总览（先看这块再开干）

### 0.1 装完之后你能干啥

- 一句话让 AI 读你电脑里的 Excel/Word/PPT，跨文件分析
- 一句话让 AI **去你飞书里改文档/Base/表格**（不用切窗口、不用打开浏览器）
- 让 AI 整理会议录音、提取待办、登记问题
- AI 长期记得你的偏好和工作风格，越用越懂你
- 自己造"机器秘书"：定时跑、自动推、自动整理

### 0.2 整套要装的东西

| 组件 | 作用 | 难度 | 啥时候装 |
|---|---|---|---|
| **Claude.app 桌面端** | AI 主程序（**里面有「Code」标签，就在这干活**） | ⭐ | ✅ 核心启动 |
| Claude 账号 | 闲鱼买 Pro / Max 会员 | ⭐ | ✅ 核心启动 |
| Obsidian | 知识库 GUI（看文档/做笔记） | ⭐ | ✅ 核心启动 |
| 知识库目录结构 | 复制祥书 vault 简化模板 | ⭐ | ✅ 核心启动 |
| 核心 Skills（refresh-memory 等） | 让 AI 记住你 | ⭐⭐ | ⭐ 强烈推荐 |
| **browser-harness** | **让 AI 操控 Chrome 浏览器**（吉客云、抖店、京麦、千牛、生意参谋等公司核心系统） | ⭐⭐ | ⭐⭐⭐ **核心增强**（阿祥强调，详见 §4.5） |
| Node.js | lark-cli 的前置（装飞书机器人才需要） | ⭐ | 🔚 最后装（§4.0） |
| lark-cli | 「飞书机器人」：让 AI 操作飞书文档/Base/IM | ⭐⭐ | 🔚 最后装·可选（§4） |

> 🌟 **重要：日常工作就在 Claude.app 桌面端的「Code」标签里干**（左侧栏，</> Code 那个按钮）。不用开终端、不用敲命令。打开 → 点 Code → 选你 vault 路径 → 开始对话。

### 0.3 预计耗时

- **Mac**：核心启动（装软件 + 买号 + 搭知识库）约 1-1.5 小时；之后要加飞书机器人再 +0.5 小时
- **Windows**：核心启动约 1.5-2 小时；加飞书机器人再 +0.5-1 小时（Claude 桌面端 Win 直接装，不需要 WSL）

### 0.4 开始之前先确认

- [ ] **必须有翻墙工具**，且是 **TUN 模式**或**全局模式**（普通"系统代理"不行）
- [ ] **有一个空邮箱**（注册 Claude 用，或者闲鱼直接买现成账号）
- [ ] **Mac 用户**：macOS 12 (Monterey) 或更新
- [ ] **Win 用户**：Win 10/11，能装 Claude 桌面端（基本都能，公司电脑也行）

---

## 1. 装 Claude 桌面端

> 🌟 我们**不用**命令行那个 `claude`——直接装 **Claude.app 桌面端**，桌面端里就有「Code」标签（左侧栏，</> Code 按钮），点进去就是完整 Claude Code 体验。
>
> 这一节只装 Claude.app 一个东西，**不碰命令行**。（Node.js 等到要装飞书机器人时再说，见 §4。）

---

### 1.1 装 Claude.app 桌面端（Mac / Win 都一样）

#### Step 1：下载
浏览器（**先确认翻墙开了 TUN 模式或全局**）打开：

**https://claude.com/download**

挑你系统：
- **Mac**：点 "Download for Mac" → 拿到 `Claude.dmg`
- **Win**：点 "Download for Windows" → 拿到 `Claude-Setup.exe`

#### Step 2：装
- **Mac**：双击 `.dmg`，把 Claude 图标拖到「应用程序」文件夹
- **Win**：双击 `.exe`，下一步下一步

#### Step 3：先打开看一眼
- **Mac**：启动台搜 "Claude" 打开
- **Win**：开始菜单搜 "Claude" 打开

打开后**左上角侧边栏**会看到 3 个图标：💬 对话 / ☑ Tasks / **</> Code**——**Code 就是我们日常工作的地方**。

但先别急着在 Code 里开干——它现在还**不能直接对话**，得先：
1. 买账号 + 登录（第 2 节）
2. 首次激活 Code：下载一个组件，装完**彻底退出再开**（见 §2.4）

#### ⚠️ Step 4：记住怎么「彻底退出」Claude（装机全程都要用）

> **同事第一次装最容易栽在这一步**：点窗口右上角的 ✕ **只是关掉窗口，软件还在后台（托盘 / 菜单栏）跑着**。这时候你新装的组件、改的设置、登录状态都**不会生效**——表现就是「软件用不了 / 没反应 / 不对劲」，其实是没真正重启。
>
> 凡是装完东西、改完设置后软件不对劲，先**彻底退出再重开**：
>
> - **Mac**：屏幕**最顶上菜单栏**左边的 `Claude` → `Quit Claude`（或按 **⌘Q**）。再瞄一眼右上角菜单栏还有没有 Claude 小图标，有就右键 → 退出。
> - **Win**：右下角**托盘区**（时间左边，点 `^` 小箭头展开）找到 Claude 图标 → **右键 → Quit / 退出**。光点窗口的 ✕ 没用。
>
> 退干净了再重新打开，新装 / 改的东西才会生效。**这份手册后面凡是说「重启 Claude.app」，都是指这个「彻底退出再开」，不是关窗口。**

> 💡 **Node.js 不用现在装。** 它只是后面装"飞书机器人"（lark-cli）时才需要——挪到了 §4。核心启动这一段先不碰命令行。

---

### 1.2 这一节装完应该长这样

| 检查项 | 怎么验证 |
|---|---|
| Claude 桌面端装了 | 启动台 / 开始菜单能搜到 "Claude"，能打开 |
| 左侧能看到 Code 标签 | 打开 Claude，左侧栏有 `</> Code` |

2 个都打勾再去第 2 节。

---

## 2. 买 Claude 账号（闲鱼）

> 🌟 **祥书亲测过的卖家（推荐先去这家）**
>
> 两个渠道都能买，挑一个顺手的：
>
> - **闲鱼**：HU006「克劳德 Claude Pro 独享代充｜官网正规订阅｜成品账」
>   链接：https://m.tb.cn/h.RcoTd3l?tk=JXa85tYZYup
> - **微信**：加 **A克克代充**（这是老板本人微信，直接发需求就行，Pro / Max 都能开）
>
> 适合：第一次买不想踩坑、不想自己挑卖家的同事，直接走这家
>
> 想自己挑别的卖家、想了解怎么辨别靠谱卖家，看下面 2.2 / 2.3。

### 2.1 买啥版本

| 版本 | 月费 | 适合谁 | 祥书评价 |
|---|---|---|---|
| Claude **Pro** | ~200 元/月 | 一天用 1-2 小时 | "用得少 100 多就够" |
| Claude **Max（5x）** | ~800 元/月 | 一天用 3-5 小时 | "用个 800 都挺好" |
| Claude **Max（20x）** | ~1600 元/月 | 高强度，全天跑 | 祥书在用 |
| ❌ Team / Enterprise | - | - | 别买，贵且 Computer Use 没有 |

**第一次推荐买 Pro**，用一周看看强度再决定升不升级。

### 2.2 闲鱼搜啥关键词

- "Claude Pro 独享"（首选独享，**别买拼车/共享**）
- "Claude Code Max"
- "Claude 200刀"（Max 的美元定价对应这个）

### 2.3 怎么辨别靠谱卖家

- ✅ 选**独立账号**（一人一号），别选共享/拼车——5 个人共享，封号率 80%
- ✅ 卖家有 **100+ 成交记录** + 好评率 95%+
- ✅ 明确写"含 Claude Code 用量"——有些只能用网页 chat，不能用 Code
- ✅ 价格区间：Pro 150-250/月，Max 5x 600-900/月，Max 20x 1400-1800/月——离谱便宜的多半是骗子
- ❌ 不要选"账号密码自己登录然后改密"——大概率封号
- ❌ 不要选要你"先付款再发账号 + 不走闲鱼担保"

### 2.4 拿到账号之后：登录 + 激活 Code

卖家一般会给你：**邮箱 + 密码** 或 **一个登录链接**。

**① 登录**：打开 Claude.app 桌面端 → 主界面会让你登录 → 用卖家给的方式登（邮箱密码 或 Google）。

> 🛑 登录报 "network error / 无法连接" → 翻墙没开 TUN/全局模式，调好再试。

**② 激活 Code（第一次必做）**：登录后点左侧 `</> Code` 标签。**第一次点它不能马上对话**——Claude.app 会提示你下载安装一个组件（Claude Code 运行环境），点同意，等它装完。

**③ 装完彻底退出再重开**：组件装完后**别急着用**——先按 §1.1 Step 4 **彻底退出 Claude.app（不是关窗口），再重新打开**，这时候 Code 才能正常对话。

到这步 Claude.app + Code 就能用了 ✅（但它还不认识你、也没有你的资料——下一节装 Obsidian 把知识库搭起来）。

### 2.5 被封号了怎么办

1. 闲鱼上联系卖家换号（一般售后保 30 天）
2. 想根治：找祥书帮你接入 Vultr VPS（祥书有 [[claude-us-ip-setup]] skill，能给你配一台美国固定 IP 走流量，不容易封）

---

## 3. 装 Obsidian + 搭你自己的知识库

> Code 现在能对话了，但它还不知道你是谁、东西该往哪放——这一节装 Obsidian 建一个你自己的知识库（vault），再把 AI 的工作目录指过去。

> 🌟 **2026-06 更新·更省事的路线**：如果你已经按引导页 clone 了「祥新团队知识库」（GitHub 仓库 xiangxin-team-kb），**直接把它当工作目录**——公司规则（CLAUDE.md）和 25 个公司技能（.claude/skills/）自动生效，啥都不用配。你自己的笔记放库里的 `_我的笔记/` 文件夹（不会被同步覆盖、也不会上传）。再在 Obsidian 装 **Git 插件**：社区插件搜「Git」→ 启用 → 设置里把「自动拉取间隔」设 60 分钟，以后公司规则更新自动到你电脑。下面 3.2~3.4 的「自建 vault」路线适合想完全自己折腾的人，二选一即可。

### 3.1 装 Obsidian

- 官网下载：https://obsidian.md/download
- Mac / Win 都有，挑对应系统装，一路下一步
- 中文界面：设置（左下齿轮）→ Language → 切换"简体中文"

### 3.2 新建你自己的 vault（知识库）

打开 Obsidian → "创建新库" → 给个名字（建议 `<你名字>AI`，比如 `庆弘AI`、`荔枝AI`）→ 选位置：

**🌟 强烈推荐放在 iCloud Drive 里**（Mac 用户）：
```
~/Library/Mobile Documents/iCloud~md~obsidian/Documents/<你名字>AI/
```
好处：iPhone 装 Obsidian app，同一个库手机能看，开会路上随时翻。

**Win 用户**：放 OneDrive 里同理（手机端 Obsidian 也支持）。

### 3.3 复制祥书的目录结构（简化版）

打开你的 vault 文件夹（Finder 或 资源管理器），手动建下面这些子文件夹：

```
_待整理/        ⭐ Inbox：AI 第一次写新文件默认放这里
00-入口/        知识地图（先留空）
01-每日/        日记 / 复盘 / 想法
02-人物/        家人、重要同事档案（可选，看你愿不愿意记）
03-工作/        你工作相关全部
  ├── 会议/
  ├── 项目/
  └── SOP/
04-内容创作/    你做的视频 / 文案（庆弘必备，运营组可选）
05-知识/        长期收集的知识
06-读书/        读书笔记
07-AI协作/      AI 用的规则和模板（这块祥书会给模板）
99-附件/        图片 / 截图 / AI 生成图
```

> 💡 这是简化版，不用照搬祥书完整的 11 个目录。少了不要紧，用得到再加。

### 3.4 写你自己的 CLAUDE.md 主规则

vault **根目录**新建一个文件 `CLAUDE.md`（注意大小写，必须全大写）。

这是 Claude Code 默认会读的"项目说明书"——AI 一进你的 vault 先读它，知道你是谁、想让它干啥。

**用配套的空白模板**：见 [[_配套-空白CLAUDE.md模板-给同事]]，复制进去填几个空就行。

> 💡 第一版别搞得太复杂，先抄空白模板填 5 个字段。用熟了之后会 AI 主动建议你怎么改它。

### 3.5 在 Claude.app 里把 Code 指向你的 vault

> 🌟 **这是全套最关键的一步**——选对了路径，AI 之后写的所有文档都进你 vault；选错了就到处乱跑。

#### Step 1：记住你 vault 叫啥名字

打开 Obsidian → 看**左下角**显示的 vault 名字（比如「庆弘AI」「荔枝AI」「祥子AI」）。这一步只是看一眼，下一步要认它。

#### Step 2：打开 Claude.app → 点 Code 标签

左侧栏 `</> Code` → 点 **+ New session**（新建会话）

#### Step 3：选 working directory（**点跟 Obsidian 同名那个按钮**）

新建 session 时它会弹"选哪个文件夹工作 / Select working directory"。

输入框下方会列出几个按钮，**其中有一个跟你 Obsidian 左下角同名**（比如 vault 叫「庆弘AI」，按钮就显示「庆弘AI」）—— **点这个就行，最简单**。

- ❌ 不要点 `Local`（那是你电脑根目录，AI 看不到你 vault）
- ❌ 不要选 Desktop、Documents 或别的位置
- ❌ 不要每次选不同位置
- ✅ **每次新建 session 都点跟 Obsidian 同名的那个**

> 💡 这一步是同事最容易翻车的地方。AI 在哪个目录工作就只能看到那个目录里的东西，选错位置 AI 就找不到你的 CLAUDE.md，也写不到你 vault 里。

**万一弹窗里没出现 vault 同名按钮**（少数情况，比如 Claude.app 还没记住你的 vault 路径）——走老办法手动复制：

- **Mac**：Obsidian 左下角 vault 名字上**右键 → 复制路径 → 绝对路径** → 在 Claude.app 弹窗里粘贴
- **Win**：资源管理器打开你的 vault 文件夹 → 点上方地址栏空白处 → 显示完整路径 → Ctrl+C 复制 → 粘贴到 Claude.app

绝对路径长这样（认一眼，别选错）：
```
Mac: /Users/yourname/Library/Mobile Documents/iCloud~md~obsidian/Documents/庆弘AI
Win: C:\Users\yourname\OneDrive\Documents\庆弘AI
```

#### Step 4：第一次对话

进去之后第一句：

```
看一下我的 CLAUDE.md，告诉我你认识我了吗、能干啥。
```

AI 应该能复述你 CLAUDE.md 里的姓名、岗位、铁律 → 通了 ✅

如果 AI 说"找不到 CLAUDE.md"——你选错 working directory 了，关掉 session 重新建，重新选路径。

---

### 3.6 切到「自动模式（Auto mode）」⭐ 必做

> 🌟 **进 Code session 第一件事就切 Auto mode。** 不切的话每一步都会弹窗问你同意，效率掉一半。

**怎么切**：

输入框右下角能看到一个模式按钮（默认显示 `Accept edits`）→ 点一下 → 弹出 Mode 面板 → 选 **Auto mode**。

或者直接按快捷键 **⇧⌘M**（Mac）/ **Ctrl+Shift+M**（Win），按几下能在 4 个模式之间切。

**4 个模式啥区别**：

| 模式 | 快捷键 | 啥意思 | 啥时候用 |
|---|---|---|---|
| Ask permissions | 1 | 每个动作都问你 | 第一天试，想盯着 AI 干啥 |
| Accept edits | 2 | 改文件不问，跑命令/调 MCP 还问 | 想稳一点 |
| Plan mode | 3 | 只出方案，不动手 | 让 AI 先给大方案再批量执行 |
| **Auto mode** | **4** | **AI 自己判断，常规操作不打扰，危险动作（删文件、动钱、动飞书别人的东西）还是会停下来问** | **日常默认用这个** ⭐ |

**为啥默认用 Auto mode**：

- 写文档、读 Excel、跑 lark-cli 查飞书、整理 vault——这些都是常规操作，没必要每步问
- 真有风险的动作（rm、删飞书文档、群发消息、改数据库）AI 还是会弹窗等你点 yes
- 切到 Auto 之后效率至少翻倍，**祥书自己每天就是开 Auto mode 干活**

> ⚠️ **不要碰 Bypass permissions**（截图里灰色那个）。那是"AI 想干啥就干啥不再问"，灾难按钮，企业版才能开，我们也别开。

---

## 4. （核心装好后再来）飞书机器人 + 浏览器操控

> 🔚 **这一节是装好前 3 节（核心启动）之后才需要的增强，第一天可以先不碰。** 分两块：
>
> - **飞书机器人（Node.js + lark-cli）**：让 AI 去飞书改文档、查 Base、发消息——从"AI 助手"升级到"AI 同事"。**可选**，等你确实要 AI 操作飞书时再装（§4.0–§4.4）。
> - **browser-harness（浏览器操控）**：⭐⭐⭐ 阿祥强调的核心增强，让 AI 跑公司 ERP / 后台 / 客服系统（吉客云、抖店、京麦、千牛 …），§4.5。

### 4.0 前置：装 Node.js（只有装 lark-cli 才需要）

> 装飞书机器人（lark-cli）需要 Node.js；如果你只想用 browser-harness（§4.5），这步可跳过。

#### Mac 路线

打开**终端**（应用 → 实用工具 → 终端，或 Spotlight 搜 "终端"），一行一行粘进去回车：

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
（装 Homebrew，会问开机密码——输入时屏幕不动是正常的，输完回车；要等 10-15 分钟）

装完照提示再敲 2 行（把 brew 加进 PATH），它会告诉你具体怎么敲。

然后：

```bash
brew install node
node --version
```

输出 `v20.x.x` 就 OK。

#### Win 路线

浏览器打开：**https://nodejs.org/zh-cn/download**

下 "LTS" 那个 Windows Installer (.msi)，双击装，全部下一步。

装完打开「命令提示符」（开始菜单搜 cmd）：

```cmd
node --version
```

输出 `v20.x.x` 就 OK。

> ⚠️ 报错 "node 不是内部或外部命令"——重启电脑再试；还不行找祥书。

### 4.1 装 lark-cli

打开**终端（Mac）** 或 **命令提示符 cmd（Win）**，敲：

```bash
npm install -g @larksuiteoapi/lark-cli
```

> ⚠️ Win 上如果报"权限不足"——以**管理员身份**重开 cmd 再装。

### 4.2 登录公司飞书账号

```bash
lark-cli auth login
```

输出一个授权链接，浏览器打开，**用你公司飞书账号扫码授权**。

> 第一次授权可能要祥书在飞书后台批一下，先告诉祥书你要登。

### 4.3 验证

```bash
lark-cli im chat list
```

应该列出你的飞书群清单。看到群名 = 成功。

### 4.4 在 CLAUDE.md 里告诉 AI 你装了 lark-cli

打开你的 `CLAUDE.md`，加一段：

```markdown
## 飞书操作
本机已经装好 lark-cli，登录的是我（XX）的公司飞书账号。
需要操作飞书文档 / Base / IM / 日历时，直接用 lark-cli 命令。
不会的命令现学：lark-cli --help 或 lark-cli <子命令> --help。
```

之后你跟 Claude Code 说：
- "帮我把飞书 wiki «XX文档» 的 §3 改成 YY"
- "今天我的飞书日历列一下"
- "帮我去 «Claude 纠错日志 Base» 看下昨天有多少条未处理"

AI 会自己用 lark-cli 去读、改、写回。

---

### 4.5 装 browser-harness（**浏览器操控核心**）⭐⭐⭐

> 🔥 **这一步阿祥强调：日常工作流核心靠这个**。装上之后 AI 才能真的帮你跑公司 ERP / 后台 / 客服系统（吉客云、抖店、京麦、千牛 …），不只是聊天写文案。
>
> 跟 lark-cli 是俩独立工具：lark-cli 让 AI 控**飞书**（可选），browser-harness 让 AI 控**Chrome 浏览器里的网页**（⭐⭐⭐ 更该优先装）。互不依赖——browser-harness **不需要** Node.js，想跳过 §4.0–§4.4 直接装它也行。

#### 4.5.1 怎么装（让 AI 自己装）

回到 Claude.app vault Code session，复制下面整段粘进去回车：

```
帮我装 browser-harness：https://github.com/browser-use/browser-harness

要求：
1. 把仓库克隆到 ~/work/browser-harness/（跟阿祥保持一致路径）
2. 读仓库里的 install.md，按它的步骤装
3. 用 uv tool install -e . 装成全局命令
4. 装完跑 browser-harness --doctor 验证

我用 Mac / 我用 Win（选一个告诉它）。哪一步要我操作浏览器或点权限弹窗，告诉我我去点。
```

AI 会一步一步告诉你怎么装——你不用记命令，跟着做就行。

> 📌 **Win 用户**：装之前先在 cmd 跑 `winget install Git.Git` 装 git，不然 AI 拉不了仓库。

#### 4.5.2 Chrome 端再配一次

装完命令之后，打开 Chrome → 地址栏访问：

```
chrome://inspect/#remote-debugging
```

勾选 "Allow remote debugging for this browser instance"（勾一次永久有效）。

之后第一次让 AI 操作浏览器，Chrome 会弹一个 "Allow remote debugging?" 对话框 → **点 Allow**。

#### 4.5.3 验证

回到 Code session 说：

```
帮我用 browser-harness 打开 https://github.com/browser-use/browser-harness
告诉我页面标题。
```

你 Chrome 里看到新 tab 打开 = 装好了 ✅

#### 4.5.4 详细用法 + 公司核心场景

完整指南见 [[14-浏览器操控(browser-harness)使用指南]]——里面写清楚了吉客云、抖店、京麦、千牛、生意参谋这些**公司核心系统**怎么让 AI 跑，跟 Claude for Chrome 扩展啥区别，翻车了怎么自救。

---

## 5. 装核心 Skills（让 AI 更懂你）

**Skill** = 把"常用工作流"打包成一句话能触发的模块。

> 🌟 **2026-06 更新**：如果你的工作目录是「祥新团队知识库」，**25 个公司技能已经随库自带**（在 `.claude/skills/`），不用下载不用装，同步（pull）即更新——本节的云盘 zip 路线只给没走 git 的人兜底。下面要单独装的只剩 refresh-memory / mac-reminder 这类**个人**技能。

### 5.1 第一版必装：refresh-memory

让 AI **长期记住你**——你叫啥、岗位、家人姓名、工作偏好、协作风格。下次重新打开 Claude Code，它接着记得。没有这个 skill，每次都从零开始，废。

### 5.2 第一版推荐：mac-reminder（仅 Mac 用户）

跟 Mac/iPhone 「提醒事项」App 联动。你说"明天 9 点提醒我给厂家打款"，AI 直接给你 iPhone 上加提醒。

### 5.3 怎么装

**方式 A：从公司飞书云盘下载（推荐）**

云盘地址：让祥书在飞书发你「Claude Skills 共享」云盘链接 → 找到「📦 正式发布」文件夹 → 下载对应 zip。

**方式 B：让祥书帮你拷**

祥书电脑上有现成的，让他用 AirDrop / 飞书发文件给你。

### 5.4 装到本地（最省事的方式：让 AI 帮你装）

把下载的 zip 解压，得到一个文件夹（比如 `refresh-memory/`，里面有 `SKILL.md`）。

**直接拖文件给 Claude.app 不行**——它要放到一个特定位置（Mac 是 `~/.claude/skills/`，Win 是 `%USERPROFILE%\.claude\skills\`）。

**最省事**：在你 vault 的 Code session 里跟 AI 说：

```
我下载文件夹里有 refresh-memory.zip 和 mac-reminder.zip，
帮我解压并装到 ~/.claude/skills/ 下面，装完告诉我结果。
```

AI 会自己解压 + 移动 + 验证。

#### 装完之后目录结构应该是

**Mac**：
```
~/.claude/skills/
  ├── refresh-memory/
  │   └── SKILL.md
  └── mac-reminder/
      └── SKILL.md
```

**Win**：
```
C:\Users\yourname\.claude\skills\
  ├── refresh-memory\
  │   └── SKILL.md
  └── mac-reminder\
      └── SKILL.md
```

### 5.5 验证

**重启 Claude.app**（彻底退出再开，不是关窗口——见 §1.1 Step 4），打开 Code session，问：

```
我现在装了哪些 skill？列一下。
```

AI 应该列出 `refresh-memory` 和 `mac-reminder`。看不到 = 没装对，让它再帮你查一遍路径。

> ⚠️ 暂时**不要**装这些祥书私人 skill：`doubao`、`xiaoai`、`lark-bot-daemon`、`lark-push-xiangshu`、`jackyun-*`、`taobao-*`、`qianniu-*`、`xiangxin-*`。这些写死了祥书的名字 / 飞书账号 / 公司 Base / 本地路径，你装上跑不了。

---

## 6. 第一天怎么用：3 个开箱示例

> 装完了别冷启动，立刻跑这 3 个示例，把手感建起来。

### 示例 1：让 AI 认识你

```
我叫 XX，岗位 XX，今天第一次用 Claude Code。
我的 CLAUDE.md 你刚才读过了。
现在问我 5 个问题（不要超过 5 个），把答案写进 memory 系统，
让你下次重新打开还能记得我。
```

AI 应该问你：作息、口头禅、专业领域、汇报偏好、家人关系。回答完毕检查 `~/.claude/projects/.../memory/` 里有没有新增 .md 文件。

### 示例 2：让 AI 操作飞书

```
帮我把今天的飞书日历列出来，再告诉我有没有冲突。
```

```
帮我去飞书 wiki «XX 文档»（贴链接），抓内容总结成 3 句话。
```

```
帮我新建一条飞书任务，挂在「祥新任务」清单，
内容："明天下午 3 点跟祥书过短视频脚本"，截止明天 3 点。
```

### 示例 3：让 AI 读你电脑文件

```
我桌面上 0518销售明细.xlsx，帮我看看有哪些异常订单
（金额低于成本的、退款率超过 30% 的）。
```

```
我下载文件夹里那个 PDF，帮我读完总结一下要点，输出到 vault 里
05-知识/ 目录下。
```

---

## 7. 翻车了怎么办

| 情况 | 解决 |
|---|---|
| Claude.app 报 "network error / 无法连接" | 翻墙没开 / 不是 TUN 模式 / 没全局——开了 TUN 重启 Claude.app |
| Claude.app 报 "401 / 登录失效" | 账号过期或被封——找闲鱼卖家换号 / 找祥书 |
| 新建 Code session 后 AI 找不到 CLAUDE.md | 你选的 working directory **不是 vault 路径**——关掉 session 重建，重新选 vault 绝对路径 |
| `npm install` 卡死或 timeout | 切国内源：`npm config set registry https://registry.npmmirror.com` 再重试 |
| `lark-cli auth login` 报权限不够 | 找祥书在飞书自建应用后台给你加 scope |
| `lark-cli` 命令找不到 | 装 lark-cli 那步没成功，重跑 `npm install -g @larksuiteoapi/lark-cli`（Win 用管理员 cmd） |
| AI 答非所问 / 瞎编 | 提问太短。告诉它**上下文 + 目标 + 约束**，AI 答得越准 |
| AI 改坏了你的文件 | Obsidian 有自动版本历史（设置 → 核心插件 → 启用"文件恢复"），iCloud / OneDrive 也有版本回滚 |
| Claude Code 卡住 / 反应慢 | 界面里点中断按钮，重新提问 |
| **装完 / 改了设置后软件用不了、没反应、新东西不生效** | **多半是没真正重启**——只关了窗口，软件还在托盘 / 菜单栏跑着。彻底退出再开（见 §1.1 Step 4） |
| AI 看不到你装的 skill | 彻底退出 Claude.app 再开（让它重新扫 skill 目录，见 §1.1 Step 4） |
| 每一步都弹窗问"同意吗" | 没切 Auto mode——按 ⇧⌘M（Mac）/ Ctrl+Shift+M（Win）切到 Auto mode，参考 3.6 |

---

## 8. 安全规则（⚠️ 必读）

1. **闲鱼账号别外泄**：不发群、不截图含账号、密码本地存好
2. **客户隐私不进 AI**：手机号、地址、身份证、订单号、人名（顾客的）——这些都不能粘到 AI 对话框
3. **公司内部财务/成本数据**：✅ 可以跟 AI 聊，祥书已确认这不算敏感（详见 [[feedback_privacy_scope_is_hr_only]]）
4. **HR 相关信息严格保密**：员工工资、绩效、矛盾——不进 AI
5. **大动作让 AI 先给方案再动**：批量删文件、批量改飞书文档、群发消息——先看方案审批，再让它执行
6. **lark-cli 是用你的飞书身份**：AI 发出去的消息署你的名，别让它乱发；@ 别人前先让它给你看一眼

---

## 9. 完成度自检清单

装到这里你应该能打勾的项：

- [ ] Claude.app 桌面端能打开，左侧有 `</> Code` 标签
- [ ] 闲鱼账号在 Claude.app 里登录成功
- [ ] 你的 vault 在 Obsidian 里能打开，目录都建好了
- [ ] vault 根目录有填好的 `CLAUDE.md`
- [ ] 在 Code → New session 时**点了跟 Obsidian 同名的那个按钮**作为 working directory（不是 Local）
- [ ] **模式已切到 Auto mode**（右下角显示 `Auto mode`，或按 ⇧⌘M / Ctrl+Shift+M 切）
- [ ] 第一次对话 AI 能复述你 CLAUDE.md 的内容
- [ ] `lark-cli im chat list` 能列群清单
- [ ] ⭐⭐⭐ **browser-harness 装好**——让 AI "打开 https://github.com/browser-use/browser-harness 告诉我标题"，Chrome 能弹出新 tab（详见 §4.5）
- [ ] 装了至少 1 个 skill（`refresh-memory` 必装），AI 能列出来
- [ ] 已经让 AI 帮你**真改了一次**飞书文档（哪怕只是个测试文档）

**10 个全打勾 = 你跟祥书在同一条 AI 轨道上了**。截图发祥书报到。

---

## 10. 进阶（用熟之后再看）

- **自建 skill**：把你日常重复的工作流打包成一句话能调（祥书会单独教）
- **launchd / 定时任务**：让 AI 每天定时自动跑（早报、周报、数据抓取）
- **飞书机器人 daemon**：让 AI 主动在飞书私聊里跟你对话（不用开终端）——技术复杂，二期统一推
- **Vultr VPS + relay**：给闲鱼账号上一层固定美国 IP，几乎不封号（见 [[claude-us-ip-setup]]）
- **MCP / Plugin**：接公司 ERP、千牛、生意参谋等内部系统

---

## 11. 谁负责啥

| 事 | 谁 |
|---|---|
| 闲鱼买账号 | 自己买（祥书帮辨别） |
| **第一次装到跑通** | **祥书 / 庆弘 远程协助**（视频屏幕共享） |
| 日常使用、提问 | 自己 + 直接问 Claude |
| 装新 skill / lark-cli 报权限 | 找祥书 |
| vault 结构疑问 | 找祥书或庆弘 |
| 账号被封 | 找闲鱼卖家换 / 找祥书帮你上 VPS |
| 提建议 / 报错 | 加到 [Claude 纠错日志 Base](https://xiangxingolf.feishu.cn/base/CWuIblgzqaW7lUsivCBccKSmnqf)，分类选「Claude Code 装机问题」 |

---

## 12. 推进节奏

| 阶段 | 谁 | 时间 |
|---|---|---|
| 第一批内测 | **老孙** | 即刻起，1 周内跑通 |
| 反馈收集 + 文档迭代 | 老孙 + 祥书 | 内测后第 2 周 |
| 第二批 | 有意愿的运营（看老孙试用结果） | 5 月底 / 6 月初 |
| 全员推广 | 全部上 | 文档稳定后 |

---

> "你装上这个软件之后就解脱了——只要跟它讲一下，不用你做了。"
> "现在我是驾驶员，它是机器——我告诉我的想法，它就帮我去实践。"
> —— 祥书，2026-05-18 销售周会
