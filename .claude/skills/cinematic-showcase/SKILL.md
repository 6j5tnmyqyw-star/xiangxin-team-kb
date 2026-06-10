---
name: cinematic-showcase
description: 把一段内容做成「会动、会炫、能直接录屏播放」的电影感 / 发布会级炫酷展示页——满屏粒子光网、GSAP 滚动叙事、逐字翻入大标题、3D 倾斜卡片、流光渐变文字、一键自动巡演。专为录屏、视频演示、产品发布、营销造势、视频号 / 抖音封面页。当祥书说「做个炫酷的展示页」「做个会动的 / 带特效的页面」「视频演示用的」「发布会那种页面」「把这个做炫酷一点 / 酷一点 / 加高级动效」「做个 H5 大片 / 落地页大片」时，必须用本 skill。它和 content-visualizer 的分工：content-visualizer 做克制专业的培训 / 讲解 / 汇报页；本 skill 做炫、动、视觉冲击强、给镜头看的页。即使没明说「炫酷」，只要目标是录屏播放、视觉要抓眼球、像发布会 / 广告片，就优先用本 skill。
---

# 电影感展示页 · cinematic-showcase

> 把一段内容做成「会动、会炫、能录屏播放」的电影感展示页：粒子光网 + GSAP 滚动叙事 + 逐字标题 + 3D 卡片 + 一键自动巡演。
> **起点资产：** `assets/template.html`（已 browser-harness 验证能跑的炫酷骨架，基于它改最快、最不踩坑）。
> **配方细节：** `references/cookbook.md`（动画 / 巡演 / 粒子 / 图片 / 配色 / 踩坑）。

## 一、什么时候用 · 和 content-visualizer 怎么分

祥书有两个做展示页的 skill，**按气质和场景分工，别用错**：

| | content-visualizer | **cinematic-showcase（本 skill）** |
|---|---|---|
| 气质 | 克制、专业、高级、耐看 | 炫、动、视觉冲击、抓眼球 |
| 场景 | 培训 / 讲解 / 汇报 / 数据看板 / 客服话术 | 录屏 / 视频演示 / 产品发布 / 营销造势 / 封面页 |
| 动效 | 轻微滚动淡入 | 满屏粒子 + GSAP 叙事 + 3D + 逐字 + 自动巡演 |
| 默认配色 | Anthropic 暖调 | 深色电影科技感（霓虹渐变） |

- 祥书说「炫酷 / 会动 / 视频演示 / 发布会 / 带特效 / 酷一点 / 大片」→ **本 skill**。
- 祥书说「培训 / 讲解 / 汇报 / 正经一点 / 给团队看的资料」→ **content-visualizer**。
- 拿不准但提到「录屏 / 对着镜头讲 / 发视频号」→ 本 skill（它有自动巡演，专为录屏）。

**不适用**：要飞书文档 / 表格 / 幻灯片 → 走 `lark-*`；只要一段文字答案 → 直接答，别套页面。

## 二、产物

**单文件 HTML**，双击即在浏览器打开、可全屏录屏，无需构建（依赖全走 CDN：React + Tailwind + GSAP + ScrollTrigger + Recharts + Lucide，需联网）。
- 输出到 `99-附件/AI生成/<主题>.html`
- ⚠️ **CDN 版只够自己电脑双击看。要发飞书妙搭 / 发祥书手机 / 分享给别人，必须先内联**（手机无代理加载不出 CDN 会白屏）→ 复用 content-visualizer 的 `assets/inline-build.js`，注意把 GSAP 也内联进去（见 cookbook 七）。

## 三、执行流程（前 3 步先用简短文字把规划发给祥书，再写代码）

### 1. 拆分镜（Scene）
- 把内容拆成 **5–7 个分镜**，**一屏一个核心信息**（适合录屏节奏：滚一屏、讲一段）。
- 每个分镜 = 一个 `<section data-scene>`，全屏 `min-h-screen`。

### 2. 编叙事弧
- 给内容排一条电影般的弧线：**钩子 → 抛问题 → 给方案 → 上证据 → 升华 → 行动号召（CTA）**。
- 每屏一句**大标题**（≤10 字最佳，逐字翻入最抓眼），配一句副文案。

### 3. 选炫酷手法 + 配图
- 给每屏挑进场动效和组件（见第四节），规划哪屏用图、用什么图。

### 4. 产出
- **复制 `assets/template.html` 作起点**，替换 §数据区、按分镜增删 Scene。
- 技术铁律见第七节，**别自己换 CDN 版本、别改动画触发方式**。

### 5. 实测验证（必做，不可跳）
- 用 **browser-harness** 实开（`file://` + `urllib.parse.quote`，路径含空格中文）。
- `wait_for_load()` 后 `time.sleep(5)` 等 GSAP + Babel + CDN，然后检查：
  - `typeof gsap` → `"object"`、`typeof ScrollTrigger` → `"function"`、`document.documentElement.classList.contains('no-gsap')` → `false`
  - `document.querySelector('canvas')` 存在（粒子）；`.recharts-surface` > 0（若用图表）
  - **滚动测试用 `window.scrollTo(0, el.offsetTop)` 或锚点 `#id`，绝不要用 `scrollIntoView()`**——它在全屏 section 上会滚过头，让你误判。
  - 滚到每屏 `capture_screenshot()` 肉眼看动效是否到位；**深色、浅色各验一张**。
  - 验自动巡演：点底部播放按钮，等 ~7s 看 `window.scrollY` 是否增大。
- 给镜头看的东西不能现场翻车，有问题先修再交付。

## 四、炫酷组件（template 已内置，改数据即用；扩展见 cookbook）

- **逐字翻入大标题** `<SplitText text="让每一次展示" />`：每屏主标题用，字符依次翻入。
- **流光渐变文字** class `grad-text`：重点词高亮，渐变随时间流动。
- **滚动进场** `data-anim="fade-up | zoom | blur | stagger"`：元素滚进视口戏剧性出现。`stagger` 加在**父容器**上，子元素依次浮现。
- **3D 倾斜卡片** `<TiltCard>`：鼠标悬停立体倾斜，玻璃拟态。
- **磁吸按钮** `<MagneticButton>`：按钮吸住鼠标，配渐变 + 发光。
- **数字滚动** `<CountUp value="60fps" />`：进视口从 0 滚到目标。
- **★ 自动巡演**：section 加 `data-scene` 即被收录；底部「自动巡演」按钮一点，页面自动匀速滚 + 每屏停留让动画播完。停留时长 / 滚动速度在 `useAutoplay` 调（见 cookbook 一）。**这是录屏杀手锏**——祥书点一下，只管对着镜头讲。
- **粒子光网背景** `<ParticleField />`：放 Hero（深色下最炫）。
- **图片**：`SHOWCASE.img` 填 URL 即用真图 + Ken Burns 缓缓推近；留空则用渐变占位。多图画廊见 cookbook 二。

## 五、配色

默认 **深色电影科技感**：深蓝黑底 + cyan→violet→pink 霓虹渐变 + 光晕。**深色是本 skill 的主场**（粒子、发光、渐变在深色最炫）。
- 走 CSS 变量，改主题只改 `<style>` 的 `:root` / `html[data-theme="light"]` 三个霓虹色 `--c1/--c2/--c3`，组件类名不动。
- 换风格（赛博朋克 / 极光 / 暖金）见 cookbook 三。
- 祥书要浅色也支持（顶栏可一键切），但浅色下 glass 卡对比偏低，需加重边框（cookbook 三）。

## 六、内容铁律

- **涉及公司业务**（产品 / 数据 / SOP）：先 grep / 搜 vault 拿真实资料，再结合网络，别凭空编。
- **经验值 / 示意数据**必须在页面标注「主观示意 / 非实测」，祥书不接受模糊。
- 客户隐私、违禁词、品牌名（VESSEL ≠ visa、LAB ≠ Labo 等易错）按主规则核对。

## 七、技术铁律（踩过的坑，别再踩）

1. **GSAP 用 cdnjs `3.12.5` UMD**（`gsap.min.js` + `ScrollTrigger.min.js`，按序加载后 `gsap.registerPlugin(ScrollTrigger)`）；**Recharts 只能 `2.12.7` UMD**（新版无 UMD 会 404 整页 blank）。
2. **进场动画用「`gsap.set` 设初始态 + `ScrollTrigger.create` 的 `onEnter` 回调」**，**不要**用 `gsap.from(el,{scrollTrigger})`——首屏「加载时就已在视口」的元素，`from` 的 onEnter 事件不触发，会**永久卡在 `opacity:0`**（首屏全黑的元凶）。
3. **`[data-anim]{opacity:0}` 占位 + stagger 父容器**：`stagger` 动画目标是子元素，但父容器自己也带 `data-anim` 被 CSS 设成 `opacity:0`——必须在 setup 里 `gsap.set(el,{opacity:1})` 把每个 `[data-anim]` 自身恢复，否则父 `opacity:0` 会把子卡片**整组乘没**（血泪坑：子元素 opacity 明明是 1 却看不见）。
4. 配色走 CSS 变量；卡片用 `glass` / `bg-surface`，别写死 `bg-white`/具体色，否则切主题不跟随。图表色用 `usePalette()`。
5. **滚动用 `scrollTo(offsetTop)` 或锚点 `#id`，别用 `scrollIntoView()`**（全屏 section 上会滚过头）。`html{scroll-behavior:auto}` 别开 smooth，免得和自动巡演打架。
6. 发妙搭 / 手机**先内联**（含 GSAP），否则白屏。

> template.html 已把以上全部配好，照用即可；逐条解释见 cookbook。

## 八、交付

- 给祥书**可点击的文件链接** + 一句话：双击开；顶栏右上切深 / 浅色；**底部「自动巡演」按钮一点，页面自动播放，适合直接录屏**。
- 主动提供：**推飞书** / **内联发手机** / 录屏导出建议。
- 涉及团队复用时按需沉淀成运营可读文档。

## 资产
- `assets/template.html` —— 验证过的炫酷骨架，**每次从它开始**。
- `references/cookbook.md` —— 动画 / 巡演 / 粒子 / 图片 / 配色配方 + 踩坑清单 + 实开验证片段。
