---
name: content-visualizer
version: 1.4.0
description: "祥书专属：把任意内容/文章/资料/数据升维成高级可视化单页网页。**先按内容自动选范式**——原理/机制/操作/流程→可动手的交互演示（零依赖原生 HTML+SVG+JS）；概念/科普/故事/汇报/培训→动画叙事+配图；数据/复盘/经营→图表看板（React+Recharts）。尽量多上可视化、动画、配图，别干巴巴堆字。**默认做完自动内联→部署飞书妙搭→推祥书手机**（他常用手机看、常要分享）。当祥书发来一段内容/文章/链接/资料/笔记并说『做个可视化页面』『可视化展示一下』『把这个/这篇做成网页/做成一页』『做个讲解页/展示页/培训页/H5』『把这篇做成可视化』『visualize 一下』『搞成一个页面』『做个落地页』『把信息可视化』，或要给客户/品牌方/合作方做对外提案/方案/产品介绍（自动套对方 logo + 品牌配色、可输出 PDF）时使用。"
metadata:
  requires:
    bins: ["browser-harness", "lark-cli"]
---

# 内容可视化展示页

> **用途：** 祥书丢来一坨内容（文章 / 资料 / 培训材料 / 数据 / 想法），**直接产出一个能双击打开就讲、就看的高级可视化网页**。不是讲给他听，是替他把页面做出来。
> **起点资产：** `assets/template.html`（已验证可跑的骨架，CDN 版本和核心组件都配好了，**基于它改最快、最不踩坑**）。
> **配方细节：** `references/cookbook.md`（图表选型 / 交互组件 / 配色色值 / 踩坑）。

## 零、先按内容选范式（动手前先定，别一个模板套到底）

| 内容类型 | 范式 | 技术栈 | 典型 |
|---|---|---|---|
| 原理 / 机制 / 操作 / 流程 / 算法 | **交互演示**：能点/拖/拨的小实验，动手看结果 | **轻量原生 HTML+SVG+JS（零依赖）** | 香农开关点亮、设备配对分步 |
| 概念 / 科普 / 故事 / 汇报 / 培训 | **动画叙事 + 配图**：滚动逐步动画、示意图、配图 | 原生 或 React 均可 | 趋势解读、方法论长页 |
| 数据 / 复盘 / 经营 / 对比 | **数据看板**：图表为主 + 计数/对比/进度 | **React+Recharts（`assets/template.html`）** | 经营月报、销售复盘 |

- **混合内容就组合**（一页里既有原理演示又有数据图表完全可以）。
- **尽量多上可视化**：能画图/动画/示意/可交互的，别用纯文字平铺（祥书明确要"尽量去可视化"）。
- ⚠️ **选栈关键**：**交互演示 / 纯动画讲解优先「轻量原生」**（`assets/template-demo.html` 起步）——零外部依赖、手机直接开不白屏、不用内联打包；**带统计图表的数据型才用 React `template.html`**（功能强但发手机要先内联）。判断不准就一句话：**要不要 Recharts 画的统计图？要→React；不要→原生。**

## 一、什么时候用 / 不适用

**用**：祥书要把信息变成一个**可视化展示页面**——培训页、讲解页、落地页、数据看板、产品介绍、知识梳理、复盘汇报。

**不适用**：
- 只要文字答案 / 总结 → 直接回答，别套页面
- 要飞书文档 / 多维表格 / 幻灯片 → 走对应 `lark-*` skill
- 改的是已有网页项目（有构建环境）→ 直接改那个项目，别套本骨架

## 二、产物

**一个单文件 HTML**，双击即在浏览器打开、可全屏讲，**不需要 npm / 构建 / 任何环境**。
- 输出到 `99-附件/AI生成/<主题>.html`
- 技术栈**按 §零 选**：数据型 = React 18 + Tailwind + Recharts + Lucide（CDN，需联网，发手机前内联）；交互演示型 = 零依赖原生 HTML+SVG+JS（直接开、免内联）。
- ⚠️ **CDN 版只够自己电脑双击看。要发飞书妙搭 / 发祥书手机 / 分享给别人，必须先内联**（手机无代理加载不出 CDN 会白屏）→ 见第六节 + [`references/deploy-inline.md`](references/deploy-inline.md)

## 三、执行流程（5 步；前 3 步先用简短文字把规划发给祥书看，再写代码）

### 1. 解构（信息架构）
- **MECE 拆 4–6 个递进区块**（Sections）
- **数据锚点**：内容里的数字 / 趋势 / 对比 → 规划用什么图（柱状 / 折线 / 雷达，选型见 cookbook）
- **交互锚点**：并列分类→Tab；FAQ/多条详情→手风琴；流程→步骤条；前后/方案对比→对比滑块；单一占比/完成度→环形进度；关键数字→CountUp 滚动。**能点能切能拖 > 纯文字平铺。**

### 2. 视觉规范
- **配色（默认 Anthropic 暖调）**：cream `#F0EEE6` 底 + 赤陶橙 `#D97757` + 暖炭灰 `#1F1E1D` 文字。**祥书没指定就用暖调**（他偏爱）。模板自带明暗一键切换、两套主题都调好了，配色走 CSS 变量（改色/换深色科技风见 cookbook 三）。
- **留白充足**（`py-20`+）；**可扫视**：关键结论提成大字 stat 看板或左侧彩条 blockquote，别埋进段落。
- 图表**单色系或邻近色**，禁高饱和刺眼色。
- **配图策略（v1.3）**：能用 **SVG / 图标（lucide）/ CSS 画的示意图**优先（零依赖、手机稳）；要真实感图片/插画 → 走 `chatgpt-image-maker` skill 生成，**再 base64 内联**进页面；产品图先搜 vault。🔴 **任何图片都不准走外链**——外链图手机无代理一样裂/白，跟 CDN 同一个坑。

- **对外品牌物料（给客户 / 品牌方 / 合作方看的提案 / 方案 / 介绍）：套对方品牌视觉，别用默认暖调，整页一眼要是"对方家的"（v1.4）**：
  1. **先扒对方品牌**（动手前必做、别凭印象）：browser-harness 开对方官网抓官方 logo（透明 PNG/SVG）+ PIL 取真实品牌色（或官网截图取色）。⚠️ 认准**子品牌**——Bushnell Golf（橙 `#F05223` + 炭黑）≠ Bushnell 主站（黑/灰/白），别张冠李戴；高清 logo 改 CDN 尺寸段拉大。
  2. **logo base64 内联**：封面放大 logo（白字版 logo 配深色封面最稳）；内页用文字标识或深色版；图片一律不走外链。
  3. **配色全对齐**对方品牌色（主色 / 强调 / 深色块），别套自己习惯的调。
  4. **抬头 / 落款写全**（呈送对象 · 提案人 · 日期），落款身份要对；对外提案**先给祥书审再发**。
  5. 对外正式提案优先出 **PDF**（飞书可在线预览、好转发）：HTML→headless Chrome（`--headless --no-pdf-header-footer --print-to-pdf`，logo base64 内联保证自包含），章节标题块加 `break-inside/after:avoid` 防跨页孤儿。

### 3. 动效 + 讲解动画 + 交互演示（v1.3 强化）
**基础动效**（每页标配）：
- 滚动**淡入 + 上移**（IntersectionObserver + CSS，**不用 Framer Motion**，单文件更稳）
- 卡片 / 按钮 hover：`hover:-translate-y-1 hover:shadow-lg transition-all duration-200 ease-out`
- 图表开 `isAnimationActive` + `<Tooltip/>` + `<ResponsiveContainer/>`；图表色用 `usePalette()`（跟随主题），别硬编码

**讲解动画**（让人"看懂过程"，配方见 cookbook）：
- **SVG 分步动画**：高亮当前步、连线流动、状态点亮（像香农电路通电）、数字逐位推演
- 触发：滚动进视口自动播 或「下一步」按钮手动推进；流程/时间线/因果链分段渐次出现，别一次全甩

**交互演示**（讲原理/操作最有效，配方见 cookbook）：
- 可**点 / 拖 / 拨**的微实验：开关、滑杆、切换 → 结果实时变（香农"拨开关看灯"即范本）
- 每个交互旁给一句"这说明了什么"，别让他自己猜
- ⚠️ 交互逻辑**必须 browser-harness 实测**（拨一下验证输出对，不能花架子）

### 4. 产出
- **复制 `assets/template.html` 作起点**，替换 §数据区 与区块即可。模板已内置：明暗主题切换 / 数字滚动 CountUp / Tab 切换 / 滚动淡入 / 顶部进度条 / 回到顶部 / 柱状·雷达图。
- **更多交互组件**（手风琴 Accordion / 前后对比滑块 / 环形进度 Gauge / 步骤条 / 对比卡）见 `references/cookbook.md`，复制粘贴即用。
- 技术铁律见第四节，**别自己换 CDN 版本**。

### 5. 实测验证（必做，不可跳）
- 用 **browser-harness** 实开生成的 HTML（`file://` + `urllib.parse.quote` 编码路径，路径含空格和中文）
- `wait_for_load()` 后 `time.sleep(4)` 等 Babel 转译；检查：
  - `js("document.getElementById('root').children.length")` > 0
  - `js("typeof Recharts")` === `"object"`、`.recharts-surface` 计数 > 0
  - `capture_screenshot()` 截图肉眼看视觉、看图表/Tab
  - **切深色再验**：点 `[aria-label=切换深浅色]` 后截图，看深色视觉 + 图表色是否跟随；`bg-clay/10` 的 computed alpha 正常（透明度类生效）
- 有错先修再交付 —— **给客户/团队看的东西不能现场翻车**。

## 四、技术栈铁律（踩过的坑，别再踩）

1. **Recharts 必须用 `https://cdn.jsdelivr.net/npm/recharts@2.12.7/umd/Recharts.min.js`** —— 2.15.x 删了 UMD 构建会 404，导致顶层解构抛错、**整页 blank**。
2. CDN 加载顺序：React → ReactDOM → prop-types → Recharts → lucide → Babel。
3. JSX 用 `<script type="text/babel" data-presets="react">`（经典 runtime，React 全局在作用域内）。
4. Recharts 解构加兜底（`RECHARTS_OK`），图表区单独降级，不让整页 blank。
5. lucide 用 UMD + 自建 `Icon` 组件读 `lucide.icons[name]`，找不到降级为空格。
6. 动画用 IntersectionObserver + CSS（Framer Motion UMD 不可靠，已弃用）。
7. **配色走 CSS 变量（RGB 通道）+ `rgb(var(--x) / <alpha-value>)`**：改主题只改 `:root` / `html[data-theme=dark]` 变量，组件类名不动；卡片底色用 `bg-card`（别写 `bg-white`），否则深色模式不跟随。已实测 cdn Tailwind 支持 `<alpha-value>`。
8. **图表色用 `usePalette()`**（JS 调色板按主题切换），别硬编码色值，否则深色下不跟随。

> 以上 template.html 已全部配好，照用即可；细节解释见 `references/cookbook.md`。

## 五、内容铁律

- **涉及公司业务**（产品 / SOP / 售后 / 数据）：先 grep / 搜 vault 拿真实资料，再结合网络，别凭空编。
- **经验值 / 示意数据**必须在页面标注「经验估算 / 主观评分」，祥书不接受模糊。
- 客户隐私、违禁词、品牌名（VESSEL 等易错）按主规则核对。
- 不确定内容真伪 → 标注或问，别假装权威。

## 六、交付（v1.3：默认全自动发妙搭 + 推手机）

🔴 **默认动作（祥书定的，不用他开口）**：每个可视化做完 → 部署飞书妙搭 → 推祥书飞书手机。他常用手机看、常要分享，本地文件他打不开也发不出去。

**一键完成**（封装内联 / 建妙搭 / 发布 / 推送）：
```bash
python3 <本skill>/scripts/deploy-push.py <页面.html> "<标题>"
```
脚本依次：① React 版先跑 `inline-build.js` 内联（原生零依赖版自动跳过）；② browser-harness 验零外部请求；③ 建独立妙搭 app（命名「可视化·<标题>·<日期>」）+ 发布拿链接（底层走 `lark-cli apps`，详见 `lark-apps` skill）；④ `lark-push-xiangshu` 把链接 + 一句话摘要推祥书手机。

- **每页独立妙搭 app**（链接永久、互不覆盖）；更新同一页就复用其 app_id 重发，链接不变。
- 同时给祥书**本地文件路径**（预览面板可看）作副本。
- 例外：明显是临时草稿 / 他说"先别发"的可只本地；其余一律默认发。

### 🔴 为什么 React 版必须先内联
CDN 版只够自己电脑双击看：手机无代理加载不出国际 CDN（unpkg/jsdelivr/cdn.tailwindcss.com）→ React/Babel 跑不起来 → 整页白屏（2026-05-23 实测踩过，本地全正常、手机全白）。所以 React 版发出去前必内联，验证 `performance.getEntriesByType('resource').length === 0`。**轻量原生演示版本就零依赖，直接发、免内联。** 手动细节见 [`references/deploy-inline.md`](references/deploy-inline.md)。

## 资产
- `assets/template.html` —— **数据看板/报告型**起点（React+Recharts），数据型每次从它开始。
- `assets/template-demo.html` —— **交互演示/原理讲解型**起点（零依赖原生 HTML+SVG+JS，手机直接开、免内联）。
- `assets/inline-build.js` —— 把 React CDN 版打成零依赖内联版（发妙搭/手机前；原生版免）。
- `scripts/deploy-push.py` —— 🔴 一键：内联→建妙搭→发布→推祥书手机（默认交付走它）。
- `references/cookbook.md` —— 图表选型 / 交互组件 / 讲解动画 / 配图 / 踩坑。
- `references/deploy-inline.md` —— 内联 + 部署妙搭 + 推送的手动流程。
