# cinematic-showcase · cookbook（配方与踩坑）

配合 `assets/template.html` 用。模板已把组件和坑都配好，这里是「怎么调参 / 怎么扩展 / 出问题怎么查」。

## 一、炫酷组件配方

### 滚动进场 data-anim
模板的 `useCinematic()` 扫描所有 `[data-anim]`，统一用 **`gsap.set` 初始态 + `ScrollTrigger.create` 的 onEnter** 播放（不用 `gsap.from(...,{scrollTrigger})`，原因见踩坑 2）。内置四型：

| 值 | 效果 | 加在哪 |
|---|---|---|
| `fade-up` | 从下方上移淡入 | 任意元素 |
| `zoom` | 从 0.84 缩放淡入 | 图片 / 大卡 |
| `blur` | 从模糊到清晰 | 标题 / 引言 |
| `stagger` | **子元素**依次浮现 | **父容器**（grid / flex 列表） |

**加新类型**：在 `useCinematic` 的 `initial` 三元表达式里加一支初始态即可，onEnter 的 `to` 统一归位（opacity:1, y:0, scale:1, filter:blur(0)）。例：加 `data-anim="flip"` → `initial = {opacity:0, rotateY:90}`。

### 逐字标题 SplitText
```jsx
<SplitText text="标题文字" />          {/* 默认进场即播 */}
<SplitText text="第二行" delay={0.3} /> {/* 错开 0.3s */}
```
把字符拆成 `.ch` span，`gsap.set` 翻起来再 `to` 翻入。**只适合短标题**（每字一个节点，长段落会很多 DOM）。

### 3D 卡片 / 磁吸按钮
- `<TiltCard className="glass ...">内容</TiltCard>`：`max` 控制最大倾斜角（默认 9°）。
- `<MagneticButton href="#next" className="...渐变...">文字</MagneticButton>`：按钮吸鼠标；要触发函数用 `onClick`。

### ★ 自动巡演 useAutoplay（录屏核心）
- **收录哪些屏**：section 加 `data-scene` 就会被巡演依次走到；不想停的屏去掉 `data-scene`。
- **每屏停留时长**：`useAutoplay` 里 `wait(2700)` 的毫秒数——讲得多就加大（如 4000），留足口播时间。
- **滚动速度**：`smoothTo(..., 1100)` 的毫秒数，越大滚得越慢越稳。
- **想匀速滚到底而非分段停**：把 for 循环换成一次 `smoothTo(document.body.scrollHeight, 总秒数*1000)`。

### 粒子 ParticleField
- **数量**：`init()` 里 `Math.min(72, innerWidth/20)`，想密集调大 72 / 调小分母。
- **连线距离**：`link = 124*DPR`，调大连线更多。
- **颜色**：自动读 `--c1`（青）。想用多色，把 fillStyle 在 c1/c2 间随机。
- **关掉**：删 Hero 里的 `<ParticleField/>`（浅色页或想干净时）。
- **性能**：录屏卡顿就减粒子数 / 降 link 阈值；移动端粒子已按 innerWidth 自适应。

## 二、图片（让页面更高级的关键）

### 单图 + Ken Burns（缓缓推近）
```js
const SHOWCASE = { img: "https://图床/xxx.jpg" };  // 或 "file:///绝对路径.jpg"
```
模板 Showcase 区填了 `img` 就用真图 + `.ken-burns`（18s 从 scale1 推到 1.14）+ 底部渐变压暗。留空用渐变占位。

### 多图画廊（粘贴即用，配 stagger 进场）
```jsx
const GALLERY = ["url1","url2","url3","url4"];
function Gallery(){
  return <div data-anim="stagger" className="grid grid-cols-2 gap-4 md:grid-cols-4">
    {GALLERY.map((src,i)=><div key={i} className="group aspect-square overflow-hidden rounded-2xl border border-line neon">
      <img src={src} alt="" className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-110" /></div>)}
  </div>;
}
```

### 全屏背景图 + 文字叠加（电影海报感）
section 加 `relative`，内放 `<img className="absolute inset-0 -z-10 h-full w-full object-cover" />` + 一层 `bg-bg/70` 压暗，文字浮在上面。

> ⚠️ **内联陷阱**：`file://` 本地图在内联打包后**会失效**（inline-build 不一定抓本地图）。要发妙搭 / 手机，图片用**图床 http URL** 或转 **base64 data URI** 内嵌。

## 三、配色主题

默认深色电影（`--c1` cyan `#22d3ee` / `--c2` violet `#a78bfa` / `--c3` pink `#f472b6`）。**改主题只改 `:root` 和 `html[data-theme="light"]` 的三个霓虹色 + PALETTE，组件类名不动**。

几组好看的霓虹（深色底）：
| 风格 | --c1 | --c2 | --c3 |
|---|---|---|---|
| 默认（青紫粉） | `34 211 238` | `167 139 250` | `244 114 182` |
| 赛博朋克 | `34 211 238`(青) | `232 121 249`(品红) | `250 204 21`(黄) |
| 极光 | `52 211 153`(绿) | `34 211 238`(青) | `129 140 248`(靛) |
| 暖金奢华 | `251 191 36`(金) | `251 146 60`(橙) | `248 113 113`(红) |

改了 `:root`/`[data-theme=light]` 的 `--c1/2/3` 后，**记得同步改 JS 的 `PALETTE`**（图表色 SVG 不便用 CSS 变量，靠 `usePalette()` 切换）。

**浅色模式**：glass 卡 = 半透明白，在浅底对比低。浅色页建议：把卡片边框加重（`border-line` 已适配，必要时加 `shadow`），或浅色下关掉粒子（粒子在浅底几乎不可见）。深色才是主场。

## 四、分镜叙事建议（内容侧）

- **5–7 屏**，一屏一个信息，别堆。
- **弧线**：Hook（钩子，制造好奇）→ 问题 / 痛点 → 方案 / 卖点 → 证据 / 数据 → 升华 / 金句 → CTA（行动）。
- **大标题短**（≤10 字），用 `SplitText` 逐字翻入最抓眼；副文案一句话。
- **录屏**：让祥书用底部「自动巡演」，按口播节奏调 `wait()` 停留时长。
- **每屏留白充足**（全屏 `min-h-screen` + 居中），别塞满——电影感来自呼吸感。

## 五、踩坑清单

1. **整页 blank** → GSAP / Recharts CDN 没加载。GSAP 用 cdnjs `gsap@3.12.5`，Recharts 用 jsdelivr `recharts@2.12.7/umd`。`curl -sIL <url>` 看 200。
2. **首屏元素永久不显示（卡 opacity:0）** → 用了 `gsap.from(el,{scrollTrigger})`，首屏已在视口的元素 onEnter 不触发。**改用 `gsap.set` + `ScrollTrigger.create({onEnter})`**（模板已这么做）。
3. **stagger 卡片整组消失**（子 opacity 明明 1 却看不见）→ 父容器 `[data-anim]` 被 CSS `opacity:0` 卡住。在 setup 里对每个 `[data-anim]` 先 `gsap.set(el,{opacity:1})` 恢复自身（模板已加这行）。
4. **scrollIntoView 滚过头** → 全屏 section 上 `scrollIntoView()` 行为不稳，会滚到下一屏甚至更远。**测试和锚点都用 `scrollTo(offsetTop)`**。
5. **自动巡演不动 / 抖** → `html{scroll-behavior}` 别设 `smooth`（和 JS 滚动打架，模板设 auto）；测巡演要等够（前几秒在第一屏 dwell）。
6. **主题切换图表不变色** → 图表用了硬编码色。改用 `usePalette()` 取 `P.c1/P.c2`。
7. **lucide 图标不显示** → 用 `lucide@latest` UMD，`Icon` 读 `lucide.icons[PascalCase]`（如 `PlayCircle`、`Clapperboard`、`Wand2`），找不到降级空格。
8. **粒子卡顿 / 录屏掉帧** → 减粒子数、降连线阈值；或干脆只在 Hero 放粒子（模板如此）。
9. **内联后图片 / 字体丢失** → 本地 `file://` 资源内联不一定抓得到，用图床 URL 或 base64。

## 六、实开验证片段（browser-harness）

```python
import urllib.parse, time, shutil
url = "file://" + urllib.parse.quote("<HTML 绝对路径>")
new_tab(url); wait_for_load(); time.sleep(5)             # 等 GSAP + Babel + CDN
print("GSAP:", js("typeof gsap"), "ST:", js("typeof ScrollTrigger"))   # object / function
print("NOGSAP:", js("document.documentElement.classList.contains('no-gsap')"))  # False
print("CANVAS:", js("!!document.querySelector('canvas')"))             # True（粒子）
print("SURFACE:", js("document.querySelectorAll('.recharts-surface').length"))  # 用图表则 >0
# ★ 滚动用 scrollTo(offsetTop)，别用 scrollIntoView（全屏 section 会滚过头）
ftop = int(js("document.getElementById('<scene-id>').offsetTop"))
js("window.scrollTo(0,%d)" % ftop); time.sleep(2.5)
# stagger 区：检查父容器 opacity（必须 1，否则子卡整组隐形）
print("PARENT_OP:", js("(function(){var p=document.querySelector(\"[data-anim='stagger']\");return p?getComputedStyle(p).opacity:'NONE'})()"))  # 1
capture_screenshot(); shutil.copy("/tmp/shot.png","/tmp/scene.png")    # Read 看动效
# 切浅色再验一张
js("document.querySelector('[aria-label=\"切换深浅色\"]').click()"); time.sleep(1.2)
capture_screenshot(); shutil.copy("/tmp/shot.png","/tmp/scene_light.png")
# 验自动巡演
js("window.scrollTo(0,0)"); time.sleep(0.6)
js("document.querySelector('.fixed.bottom-6 button').click()"); time.sleep(7)
print("AUTOPLAY_Y:", js("window.scrollY"))   # 应 > 0（已滚到后续分镜）
```
跑完关掉自己开的标签（`cdp("Target.getTargets")` 找 url 含本页文件名的 `Target.closeTarget`）。

## 七、内联 + 发飞书妙搭

复用 content-visualizer 的 `assets/inline-build.js`：
```bash
node <content-visualizer>/assets/inline-build.js <你的页面.html>   # 输出 <页面>.inline.html
```
**注意**：本 skill 比 content-visualizer 多了 **GSAP / ScrollTrigger** 两个 CDN，确保 inline-build 把它们也下载内联（检查输出里有 gsap 代码）。打完用 browser-harness 验 `performance.getEntriesByType('resource').length === 0`（零外部请求）。图片记得用图床 URL / base64（见二）。完整链路见 content-visualizer 的 `references/deploy-inline.md`。
