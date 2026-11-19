---
title: AI 四件套打通（WorkBuddy 执行版）
version: v1
date: 2026-11-19
owner: 阿祥
applies: 全公司
purpose: 知识库 / 浏览器 / 网页后台 / 飞书，四件事串成一条链，同事装完就能用
---

# AI 四件套打通（WorkBuddy 执行版）

> **给同事的一句话**：把这份文件丢给你的 WorkBuddy，说「照这个把我这四件事打通」。它会自己装、自己验，你只在 Chrome 弹窗的时候点一下「允许」。
>
> **给 AI**：按阶段推进，**每个阶段有验收，验收不过不许往下走**。这份文件没写的报错，停下来问人，不要自己编一个绕法混过去。

---

## 〇、先看懂：四件事其实是一条链

不是四个功能，是**一个闭环**：

```
你在飞书说一句「把今天抖店数据拉一下」
        ↓
   WorkBuddy（大脑，跑在你电脑上）
        ├── 记忆：知识库（你的文件夹）      → 知道你是谁、上次做到哪
        ├── 手：  浏览器（你已登录的 Chrome）→ 点后台、抓数据、填表
        └── 嘴：  飞书（lark-cli，你的账号） → 读消息、发消息、改文档
        ↓
   结果回到你的飞书 / 屏幕
```

缺任何一块会怎样：

| 缺 | 症状 |
|---|---|
| 没有知识库 | 每次都从零教你，问三遍公司有几家店 |
| 没有浏览器 | 只能说不能做，数据得你自己复制粘贴给它 |
| 没有飞书 | 只能坐在电脑前守着，人在外面就断线 |
| 没串起来 | 三样都装了，但 AI 不知道「我可以用这些」——等于白装 |

**第四块（串联）是最容易被漏的**：装完不告诉 AI 它有什么工具，它就不会用。第五阶段专门解决这个。

---

## 一、开工前自检（30 秒，别跳）

```bash
# 1. 系统
uname -s          # Darwin=macOS；MINGW/MSYS=Windows；Linux=Linux

# 2. 有没有 uv（装浏览器工具要用）
command -v uv

# 3. 有没有 node / lark-cli（飞书要用）
command -v node; command -v lark-cli

# 4. 你的库在哪
ls -d ~/obsidian/* ~/Documents/*库* 2>/dev/null
```

把结果记下来，后面分阶段走。Windows 用户先看第八节末尾的说明再动手。

---

## 二、第一件事：知识库（30 分钟）

**不在这份文件里重写。** 公司团队库有一份专门的安装文件，比这里细：

> 共享云盘 → `📚 团队知识库镜像` → `00-新人必读` → **`00B-把这个库装好-交给AI执行版.md`**

把 00B 丢给你的 AI，让它装。装完再做个人库（你自己的、含敏感数据的那个）。

### 验收（三条问答，AI 必须全答对）

问你的 WorkBuddy：

1. 「公司的团队库在哪？我自己的库在哪？」
2. 「我的库有几个一级目录？分别放什么？」
3. 「我上次在这个库里干的最后一件活是什么？」

第 3 问答不出来是正常的（新库没历史），但前两问必须张口就来。**答不出来 = 库没装好，别往下走。**

---

## 三、第二件事：浏览器 + 网页后台（20 分钟）

> 你说的「操作电脑」，指的就是这个：让 AI 点你**已经登录**的后台页面——吉客云、抖店罗盘、京麦、千牛、天猫商家后台。
> 关键不是「能开网页」，是**带着你的登录态**开。所以 AI 连的是你正在用的那个 Chrome，不是另开一个干净的浏览器。

### 3.1 装 uv（Python 工具管家，一次就够）

```bash
# macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
# 装完关掉终端重开，或者
source $HOME/.local/bin/env

# 验证
uv --version
```

### 3.2 装 browser-harness

```bash
uv tool install --python 3.12 --upgrade --force browser-harness
browser-harness --version
```

装完 `browser-harness` 就在 PATH 里（通常在 `~/.local/bin/`）。

### 3.3 给 Chrome 开一个开关（**这一步需要你自己点，AI 点不了**）

1. Chrome 地址栏输入：`chrome://inspect/#remote-debugging`
2. 勾上 **"Allow remote debugging for this browser instance"**
3. 如果 Chrome 弹窗问「要允许远程调试吗？」，点**允许**

这一步做一次就够，之后 Chrome 重启也记得住（同一个 profile）。

> **这一步做完，AI 连的就是你现在这个 Chrome**——所有登录态（吉客云、抖店、京麦）它都能用，不需要重新登录。

### 3.4 验收

```bash
browser-harness <<'PY'
print(page_info())
PY
```

打印出**你当前标签页的标题和网址** = 通了。

再验一步（证明能读页面内容）：

```bash
browser-harness <<'PY'
print(js("document.title"))
PY
```

### 3.5 常用命令（记住这 4 条就够）

| 想干什么 | 怎么写 |
|---|---|
| 看当前页面 | `print(page_info())` |
| 开新标签 | `new_tab("https://...")` |
| 读页面内容 | `print(js("document.body.innerText.slice(0,500)"))` |
| 点某个位置 | `capture_screenshot()` → 看图 → `click_at_xy(x, y)` |

**多标签/多窗口的情况**：如果 AI 连不上或连错，先跑 `browser-harness --doctor` 看连接列表，再用 `BU_NAME=<连接名>` 指定。

### 3.6 这一阶段最常见的两个坑

1. **Chrome 弹窗没点「允许」** → `page_info()` 报 CDP 超时。回到 3.3 重做。
2. **不要关那个 Chrome 窗口**。登录态在窗口里，关了就得重新登。**AI 用完不要替你关浏览器**——这条写进第五阶段的规矩里。

---

## 四、第三件事：飞书（20 分钟）

### 4.1 装 node（已有可跳过）

```bash
# macOS
brew install node
node --version      # 出 v20 以上就行

# Windows：https://nodejs.org/zh-cn/download 下 LTS 的 .msi 装
```

### 4.2 装 lark-cli

```bash
npm install -g @larksuiteoapi/lark-cli
lark-cli --version
```

> Windows 报「权限不足」→ 用管理员身份重开命令提示符再装。

### 4.3 登录你自己的飞书账号

```bash
lark-cli auth login
```

会给你一个授权链接，浏览器打开，用**你自己的**公司飞书账号扫码。

> ⚠️ 第一次可能要找阿祥在飞书后台批一下权限。批完重跑 `lark-cli auth login`。

### 4.4 验收（两条）

```bash
# 1. 能列出你加入的群 = 读通了
lark-cli im +chat-list --as user

# 2. 发一条消息到你自己的私聊 = 写通了
lark-cli im +messages-send --chat-id <你的chat_id> --text "测试" --as user
```

`chat_id` 怎么拿：`lark-cli im +chat-list --as user` 的输出里，每条都有 `chat_id`（`oc_` 开头）。

### 4.5 能干什么（举几个真事）

- 「把我飞书日历今天的事列出来」
- 「读一下 XX 那份文档，总结三条」
- 「把这周的报表传到共享云盘 05-财务行政」
- 「在三方发货群发一句：今天截单 17:00」

---

## 五、第四件事：串起来（5 分钟，最关键）

前三件事装完，AI 还是不知道「我手上有这些东西」。**必须在它每次开工都会读的文件里写清楚。**

### 5.1 把这段加进你库根目录的 `AGENTS.md`（没有就新建）

````markdown
## 本机能力（已装好，直接用，不用再问我）

### 浏览器：browser-harness
- 连的是**我正在用的 Chrome**，所有后台都是登录态（吉客云、抖店、京麦、千牛、天猫）。
- 用法：
  ```bash
  browser-harness <<'PY'
  print(page_info())                       # 看当前页
  print(js("document.body.innerText"))     # 读内容
  new_tab("https://...")                   # 开新页
  PY
  ```
- 多连接时用 `BU_NAME=<name>` 指定；先 `browser-harness --doctor` 看有哪些。
- **绝对不许关我的浏览器窗口、不许清 profile/Cookies**。用完就放着。

### 飞书：lark-cli
- 登录的是**我自己的**飞书账号，能读消息、发消息、读写文档、传云盘。
- 常用：`lark-cli im +chat-list --as user` / `lark-cli im +messages-send --chat-id oc_xxx --text "..." --as user`
- 不会的命令现查：`lark-cli <子命令> --help`

### 知识库
- 就是当前这个目录。开工先读 `00-入口/00-首页.md`，再按需翻目录。
- 新写的东西先落 `_待整理/`，等我确认再归档。

### 规矩
1. 客户姓名/手机号/地址/订单号：不进库、不进任何 AI 输入输出。
2. 密钥、AppSecret、密码：不进库、不写代码、不贴聊天。
3. 对外发消息（群、客户）之前，先给我看草稿。
4. 动钱（>¥1000）、改价、改主图、发对外文案：必须我确认。
5. 浏览器里的登录态是我的，不许退出登录、不许换账号。
````

### 5.2 联调：三条指令验证「真的串起来了」

依次跟 AI 说：

| # | 说什么 | 通过标准 |
|---|---|---|
| 1 | 「打开抖店罗盘，告诉我现在页面上第一行数据是什么」 | 它自己连浏览器、读页面、把数字说出来 |
| 2 | 「把刚才这个结论记进库里，写清日期」 | 它在 `_待整理/` 建了一个 md，内容对 |
| 3 | 「把这条结论发到我飞书私聊」 | 你飞书收到消息，内容一致 |

三条全过 = 四件套通了。**任何一条不过，回到对应阶段重做验收。**

---

## 六、我这台机器上的实测记录（2026-11-19，阿祥机器）

| 项目 | 命令 | 结果 |
|---|---|---|
| Chrome 调试端口 | `curl 127.0.0.1:9226/json/version` | ✅ Chrome/157.0.8103.78 |
| browser-harness 诊断 | `browser-harness --doctor` | ✅ daemon alive，**6 个已登录连接**（抖店/吉客云×2/千牛/京东客服/默认） |
| 读页面 | `BU_NAME=doudian` + `page_info()` | ✅ `核心数据-抖音电商罗盘` |
| 读 DOM | `js("...innerText...")` | ✅ 取到导航文本 |
| 飞书读 | `lark-cli im +chat-messages-list` | ✅ 读到最新一条消息 |
| 飞书写 | `lark-cli im +messages-send` | ✅ 消息已送达 |
| 飞书文档 | `lark-cli docs +fetch / +update` | ✅ 读全文、原地覆盖 |
| 云盘 | `lark-cli drive +upload / +member-add` | ✅ 上传、给同事授权 |

**结论**：这四条链在 macOS + Chrome 上全部跑通，单次调用都在 1-3 秒内。

**没验证的**：Windows 同事的完整路径（browser-harness 在 Windows 上装 uv 的方式不同）。Windows 的同事先做知识库 + 飞书两件事，浏览器这块找阿祥单独装。

---

## 七、卡住对照表（照着对，别自己猜）

| 现象 | 原因 | 解法 |
|---|---|---|
| `page_info()` 超时 / CDP 握手失败 | Chrome 没允许远程调试，或连的是 9222 空端口 | 回 3.3 勾选；`browser-harness --doctor` 看实际连接 |
| `browser-harness: command not found` | 装完没重开终端 | 关掉终端重开，或 `source ~/.local/bin/env` |
| `uv: command not found` | uv 没装或没进 PATH | 重跑 3.1，装完重开终端 |
| 连上了，但页面是「未登录」 | 连到了另一个 Chrome 实例 | 只保留一个 Chrome 窗口；别用 --user-data-dir 另起 |
| 登录态突然没了 | Chrome 被关了 / 清了 Cookie | 重新登录一次。**以后别关窗口** |
| `lark-cli` 报权限错 | 首次授权没批 | 找阿祥在飞书后台批；或重跑 `lark-cli auth login` |
| `npm install -g` 报 EACCES | 权限 | macOS 别加 sudo，改用 `npm config set prefix ~/.npm-global`；Win 用管理员 |
| AI 说「我没有浏览器权限」 | 没写进 AGENTS.md | 回第五阶段，把那段贴进去 |
| AI 读库读错文件 | 库太大、没有索引 | 每个目录补 `00-索引.md` |
| 发消息发错人 | chat_id 拿错 | 先 `+chat-list` 确认群名再发 |

---

## 八、红线（违反一次就停用）

1. **客户隐私**：姓名、手机号、地址、订单号，不进库、不进 AI 输入输出。
2. **账号密码 / 密钥**：不进库、不写代码、不贴聊天。
3. **浏览器登录态是你的身份**：AI 不许退出登录、不许换账号、不许关窗口。
4. **对外动作先给人看**：群消息、客户回复、对外文案，AI 出草稿，你点头再发。
5. **动钱动价必须确认**：单笔 > ¥1000、改价、改主图、报名活动，一律先问。

---

## 九、谁能用、卡住找谁

| 事项 | 找谁 |
|---|---|
| 知识库装不上 | 阿祥（或看 00B 第七节报错表） |
| 浏览器连不上 | 阿祥 |
| 飞书权限批不下来 | 阿祥 |
| 想加新场景（某后台自动抓数） | 报阿祥，评估后排进流水线 |

**一句总结**：库是记忆，浏览器是手，飞书是嘴，WorkBuddy 是大脑——四样接上，你才真的有个「AI 同事」，而不是一个更聪明的搜索框。

---

*最后更新 2026-11-19 · 阿祥 · 实测环境 macOS + Chrome 157 + WorkBuddy*
