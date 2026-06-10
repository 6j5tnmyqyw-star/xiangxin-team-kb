---
name: chatgpt-image-maker
description: "用 AI（Claude）操作 ChatGPT 生成电商营销图：商品场景图 / 大促海报 / 详情页卖点图 / 社媒封面 / 公众号配图。Claude 帮你打开 ChatGPT、套用高尔夫电商作图模板、把图生出来并下载归档。当使用者（阿祥或运营）说『作图 / 生图 / 画张图 / 做张图 / 做个海报 / 做 banner / 做配图 / 出图 / 做主图背景 / 做详情图 / 做大促图 / 做社媒封面 / 公众号配图 / 用 ChatGPT 作图 / 用 GPT 画图 / 让 AI 画 X』时使用。替代旧的『豆包 AI 生图』，质量更高。"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - AskUserQuestion
metadata:
  trigger: 用 ChatGPT 生成电商营销图
  audience: 阿祥 + 运营组（小琴/娜娜/洪洪/嘉欣/庆弘）
  templates: references/prompt-templates.md
  onboarding: references/ops-onboarding.md
---

# chatgpt-image-maker：用 ChatGPT 生电商图

> **这是什么**：让 Claude 帮你在 ChatGPT 里又快又好地生成电商营销图——你说要什么图，Claude 套用现成的高尔夫电商作图模板，把 prompt 发进 ChatGPT，等图生成完，下载好、命名归档。
>
> **谁用**：阿祥（用 browser-harness 路径）+ 运营组（用 Claude Desktop + Claude in Chrome 扩展路径）。
>
> **作什么图**：商品场景/氛围图、大促海报、详情页卖点示意、社媒封面、公众号配图。**不是**真实商品实拍主图（见红线第 1 条）。

---

## 一、先认清楚：三条执行路径

同一套作图逻辑，区别只在"谁来操作 ChatGPT、把图生出来"。**先确认你是哪条**：

- **路径 A · 全自动（阿祥）**：Claude Code（命令行）+ browser-harness（CDP 直连 Chrome）。Claude 自己开 ChatGPT、发 prompt、等图、下载。适合批量、无人值守。
- **路径 B · 半自动（配了浏览器扩展的人）**：Claude.app 桌面端的 `</> Code` 标签 + Claude in Chrome 扩展。Claude 用扩展操作 ChatGPT 网页生图。适合边看边调。
- **路径 C · 给 prompt（运营默认 / 保底）**：Claude.app 的 `</> Code` 标签，**不需要任何浏览器工具**。Claude 帮你选模板、填好一段合规的作图 prompt，**你自己复制到 ChatGPT 网页生图、下载**。最简单，谁都能用。

> ⚠️ **运营注意**：browser-harness 是阿祥 Mac 上的私有工具，**你的电脑没有也装不了**——别走路径 A。没特意配过 Claude in Chrome 扩展，就走 **路径 C**（Claude 给你 prompt，你手动生图），照样又快又合规。装了扩展能升路径 B。怎么装、怎么用见 [references/ops-onboarding.md](references/ops-onboarding.md)。

三条路径**共用**：作图模板、合规红线、命名归档。差别只在"操作 ChatGPT"那一步。

---

## 二、何时触发

使用者说：作图 / 生图 / 画张图 / 做个海报 / 做 banner / 做配图 / 做主图背景 / 做详情图 / 做大促图 / 做社媒封面 / 公众号配图 / 用 ChatGPT（GPT）画 X……

触发后先问清三件事（一次问全，别一条条来）：
1. **作什么图**？（商品场景图 / 海报 / 详情卖点图 / 社媒封面 / 公众号配图）→ 决定套哪个模板
2. **哪个商品 / 什么主题**？（如 Bushnell V6S、618 大促、Garmin S70 续航卖点）
3. **用在哪 / 什么比例**？（公众号封面 16:9 / 正文 3:4 / 小红书 3:4 / 抖音封面 9:16 / 主图背景 1:1）

信息齐了进第三步。

---

## 三、通用作图流程（五步）

```
1. 选模板    →  按"作什么图"从 references/prompt-templates.md 取模板，填进商品/主题/比例
2. 开 ChatGPT →  路径 A：browser-harness 开；路径 B：Claude in Chrome 开 chatgpt.com
3. 发 prompt  →  把填好的作图 prompt 输入 ChatGPT 对话框，发送
4. 等生成    →  ChatGPT 生图 ~10-40 秒，等图出现在对话里
5. 下载归档   →  下载图片，按命名规范存好，回报使用者
```

> **路径 C（运营默认）只做第 1 步和第 5 步的命名规范**：选好模板、填好 prompt 后，**直接把 prompt 整段给运营**，告诉他"复制到 ChatGPT 发送，生成后下载，按下面规范命名"。中间第 2-4 步（开浏览器、自动发、自动下载）跳过，由人手动。Claude 的价值在"选对模板 + 填好 prompt + 红线全检查过"。

### 3.1 选模板 + 填 prompt

读 [references/prompt-templates.md](references/prompt-templates.md)，按"作什么图"选模板，把商品名、主题、比例、风格填进占位符。

**作 prompt 时套用公司视觉规范**（已内置在模板里，作图前再核对一遍）：
- 风格关键词：高尔夫球场 / 清晨光线 / 专业 / 克制（不浮夸、不花哨）
- 分辨率：不低于 1080×720
- 比例：公众号封面 16:9、正文嵌入 3:4，按用途调
- **图上文字**：GPT 生图的中文文字常出错（缺笔画 / 乱码）。**能不放文字就不放**，文案留到后期用 Canva/PS 加；非要放就放短英文或数字，且生成后逐字检查

### 3.2 开 ChatGPT

**路径 A（browser-harness）**：

```bash
browser-harness <<'PY'
ensure_real_tab()
new_tab("https://chatgpt.com/")
wait_for_load()
capture_screenshot()   # 看是否已登录；没登录就停，让阿祥登
PY
```

- 跳到登录页 → **停下来**告诉阿祥"ChatGPT 没登录，登一下我等"，**绝不**自己输账号密码
- 想用某个固定的作图 GPT/项目，就把 URL 换成那个

**路径 B（Claude in Chrome 扩展）**：
- 让 Claude 用扩展打开新标签 `https://chatgpt.com/`
- 没登录 → 提示使用者先在 Chrome 里登录 ChatGPT，登好再继续

### 3.3 发 prompt（路径 A 示例）

```bash
browser-harness <<'PY'
new_tab("https://chatgpt.com/c/<对话 id>")    # 进已有对话用 new_tab，别 goto——祥书常开几十个 tab，js() 容易漂到别的页
wait_for_load()
assert "chatgpt.com/c/" in (js("return location.href") or ""), "连错 tab 了，重开 new_tab"
js("document.querySelector('#prompt-textarea')?.focus()")   # 输入框 = #prompt-textarea（ProseMirror contenteditable）
type_text("""<填好的作图 prompt>""")
capture_screenshot()                          # 确认文字进去了
key("Enter")
capture_screenshot()
PY
```

> **多 tab 漂移坑**：祥书 Chrome 常开几十个 tab，`js()` / `switch_tab` 可能连错 tab（连到 `file://` 或别的页）。可靠做法：用 `new_tab` 打开目标对话 URL，**每次操作前**先 `js("return location.href")` 校验在 `chatgpt.com/c/`。路径 B 让 Claude 用扩展的填表/点击能力做同样的事。

> **坑：新进对话发的第一条图 prompt 有时不触发生成**——prompt 发出去了、显示成用户消息，但没有助手响应、不出现停止按钮。发出后等 ~6s 检测停止按钮，没出现就补发一句一行催促即可触发：

```bash
browser-harness <<'PY'
import time
def stopping():                               # 停止按钮在 = 正在生成
    return js("""return [...document.querySelectorAll('button')].some(b=>{
      const a=(b.getAttribute('aria-label')||'')+(b.innerText||'');
      return a.includes('停止')||a.includes('Stop');});""")
time.sleep(6)
if not stopping():                            # 没启动 → 补一句催促
    js("document.querySelector('#prompt-textarea')?.focus()")
    type_text("请基于我上一条消息里的图1，直接生成。")
    key("Enter")
PY
```

### 3.4 等生成完成

**判据用"停止按钮在不在"，不要用"正在生成 / 正在思考"文字**——生成中期文案会变，文字检测会给假阴性。停止按钮消失 = 出图完成。3.3 的 nudge 已确认生成启动，这里轮询它消失即可：

```bash
browser-harness <<'PY'
import time

def stopping():
    return js("""return [...document.querySelectorAll('button')].some(b=>{
      const a=(b.getAttribute('aria-label')||'')+(b.innerText||'');
      return a.includes('停止')||a.includes('Stop');});""")

for _ in range(120):                 # gpt-image 出图慢，给到 ~2 分钟
    if not stopping():
        break
    time.sleep(1)

# 成品和上传图都从 backend-api/estuary/content 加载，靠 naturalWidth 区分
img_url = js("""
  const imgs = [...document.querySelectorAll('img')]
    .filter(i => (i.src||'').includes('/backend-api/estuary/content'));
  for (let i = imgs.length-1; i>=0; i--) {
    const w = imgs[i].naturalWidth;            // 成品约 1086×1448；上传原图 1440×1920、红圈标注版更小
    if (w >= 900 && w <= 1300) return imgs[i].src;   // DOM 顺序最后一张、宽度落在成品区间 = 最新成品
  }
  return null;
""")
print(img_url or "没抓到成品图：截图看是不是没触发生成（回 3.3 补催促）或报错了")
PY
```

> ChatGPT 已没有 `data-message-author-role` 容器、也不是通用 `img.src`——生成图和上传图统一从 `https://chatgpt.com/backend-api/estuary/content?id=file_...` 加载。区分成品 vs 参考图只能靠 `naturalWidth`（gpt-image 成品 ~1086×1448，落在 900-1300），取 DOM 顺序最后一张即最新成品。

### 3.5 下载 + 命名归档

拿到 estuary 图片 URL 后下载（路径 A）。**必须走页面内 async fetch 拿字节转 base64，不能用 `http_get`**——estuary 直链要 ChatGPT 登录 cookie，`http_get` 没会话 cookie 会失败：

```bash
browser-harness <<'PY'
import base64, time

img_url = "<3.4 拿到的 estuary src>"
b64 = None
for _ in range(3):                 # 大图 fetch 偶尔超 IPC 超时，单独重试即可
    try:
        b64 = js(f"""
          return (async()=>{{                      // js() 不能用顶层 await，包成 async IIFE 返回 Promise
            const r = await fetch("{img_url}");     // 带页面登录 cookie
            const bytes = new Uint8Array(await r.arrayBuffer());
            let bin=''; for (let i=0;i<bytes.length;i++) bin+=String.fromCharCode(bytes[i]);
            return btoa(bin);
          }})();
        """)
        if b64:
            break
    except Exception:
        time.sleep(2)

open("/tmp/chatgpt-img.png","wb").write(base64.b64decode(b64))
print("saved /tmp/chatgpt-img.png")
PY
```

- 路径 B：让使用者直接在 ChatGPT 里点图片下载（运营手动点最省事），或用扩展触发下载

**命名规范**（沿用公司素材命名）：
```
YYYYMMDD_产品_场景_版本.png
例：20260521_BushnellV6S_球场场景图_v1.png
```
- 存哪：阿祥本机存 `99-附件/AI生成图/`；运营存自己电脑的"AI配图"文件夹，要上飞书的传到对应素材夹
- 生成多张备选就 `_v1 _v2 _v3`

下载完**回报使用者**：存哪了 + 图片预览（截图）+ 要不要改 / 再生几张。

---

## 四、作图模板库

按场景取，见 **[references/prompt-templates.md](references/prompt-templates.md)**：
1. 商品场景 / 氛围图（商品放球场、果岭、清晨光线背景）
2. 大促 / 节日海报（618、双11、节日主题）
3. 详情页卖点示意图（功能点图解、对比图）
4. 社媒封面（小红书 / 抖音 / 公众号）
5. 白底 / 纯色衬托图（商品突出、留白）
6. 节日 / 季节主题氛围图

每个模板含：用途、prompt 骨架（带占位符）、推荐比例、注意点。

---

## 五、红线（每次作图前过一遍，自包含、必须遵守）

1. **AI 图 ≠ 真实商品主图**。ChatGPT 生成的是氛围 / 背景 / 营销概念 / 配图，**不能替代真实商品实拍**。涉及商品具体外观、细节、参数展示的主图、详情实拍，**必须用真实拍摄的图**——AI 编出来的商品和实物不符 = 虚假宣传，平台会罚。AI 图只做：背景、场景氛围、海报底图、留白衬托、概念示意。

2. **违禁词（极限词）一个都不能上图**。营销图上的文案禁用：
   - 通用：极致、史上最低、第一、绝对、国家级、最、唯一、顶级、独家
   - 测距仪专属：军用级、百分百精准、激光武器级、超越同行
   - 生成的图里若 AI 自己加了这类字，**删掉重做**。

3. **品牌名必须拼对**。Bushnell（不是 Bushnel）、Garmin、Ping、Callaway、Bushnell V6/V6S/V7S/PRO XM、Garmin S70/R50/G82。图上出现品牌名 / 型号，生成后逐字核对，错了重做。

4. **不放客户隐私**。客户姓名、手机、地址、订单号、聊天截图，绝不作为作图素材或出现在图上。

5. **店铺后台截图、订单数据**不拿去喂 ChatGPT 作图。

---

## 六、给运营（默认走路径 C）

第一次用，先看 **[references/ops-onboarding.md](references/ops-onboarding.md)**：
- 怎么把这个 skill 装进 Claude.app 的 `</> Code` 标签
- 路径 C：Claude 给你 prompt → 你去 ChatGPT 生图 → 下载命名（最常用）
- 怎么开口让它作图（例句）
- 图存哪、怎么上飞书
- （进阶）装了 Claude in Chrome 扩展才升路径 B

**出问题找阿祥**。

---

## 七、与其他工具的边界

| 你要 | 用什么 |
|---|---|
| **生成营销图 / 配图 / 海报** | **本 skill** |
| 把内容做成可视化展示网页（数据图表、培训页、H5） | content-visualizer（那是 Claude 写网页，不是作图） |
| 用 ChatGPT 写口播文案稿 | xiangshu-write-flow |
| 真实商品主图 / 详情实拍 | 真实拍摄，不归 AI |

---

## 八、文件位置

- 主 SKILL：本文件
- 作图模板库：`references/prompt-templates.md`
- 运营上手指南：`references/ops-onboarding.md`
- 阿祥本机软链：`~/.claude/skills/chatgpt-image-maker → 本目录`
- 上游工具：[browser-harness](~/work/browser-harness/SKILL.md)（路径 A）
