# cookbook · 配方与踩坑

配合 `assets/template.html` 用。模板已把组件和坑都配好，这里是选型决策 + 扩展配方 + 出问题时的排查。

## 一、图表选型（数据形态 → 图表）

| 数据形态 | 用什么 | 说明 |
|---|---|---|
| 占比 / 排名 / 类别对比 | **柱状图**（横向条更适合中文长标签） | `layout="vertical"`，单色赤陶橙渐变 |
| 两组对象多维对比 | **分组柱状** | 两个 `<Bar>`，邻近色（clay + gold） |
| 多维能力 / 画像对比 | **雷达图** | 2–3 个系列，邻近暖色 + `fillOpacity 0.18` |
| 随时间变化的趋势 | **折线图** `LineChart` | 有时间序列才用；没有别硬塞 |
| 单一进度 / 完成度 / 占有率 | **环形进度 Gauge**（见配方三） | 比柱状直观，中间叠大字数字 |
| 构成占比（单一整体） | 柱状优先，少用饼图 | 饼图扇区多了难读 |

**配色铁律**：单色系（同一色不同透明度）或邻近色（橙→棕→金 / 蓝→靛→紫）。禁高饱和杂色。`isAnimationActive` + `<Tooltip>` + `<ResponsiveContainer>` 三件套必开。
**诚实铁律**：经验值 / 主观评分必须在图表副标题或页脚标注，别冒充官方统计。
**主题铁律**：图表颜色走 `usePalette()`（见配方四），别硬编码色值，否则深色模式不跟随。

## 二、交互组件配方

**模板（v1.1）已内置，开箱即用、不用抄**：
明暗主题切换（`ThemeToggle`）、数字滚动（`CountUp`）、Tab 切换（`Tabs`）、stat 看板、金句 blockquote、卡片网格、柱状 / 雷达图、滚动淡入（`Reveal`）、顶部进度条、回到顶部（`BackToTop`）。

下面是模板没放、按需粘贴的组件（**均已实测可跑**）：

### 手风琴 Accordion（FAQ / 多条详情，省空间）
平滑展开用 `grid-template-rows 0fr↔1fr`（比 max-height 准）。默认开第一项；`defaultOpen={-1}` 则全收起。
```jsx
function Accordion({ items, defaultOpen=0 }){      // items:[{q, a}]
  const [open,setOpen]=useState(defaultOpen);
  return <div className="mx-auto max-w-3xl divide-y divide-line overflow-hidden rounded-3xl border border-line bg-card shadow-sm">
    {items.map((it,i)=>{ const on=open===i; return <div key={i}>
      <button onClick={()=>setOpen(on?-1:i)} className="flex w-full items-center justify-between gap-4 px-6 py-5 text-left transition-colors hover:bg-clay/5 sm:px-8">
        <span className="text-base font-semibold text-ink sm:text-lg">{it.q}</span>
        <Icon name="ChevronDown" size={20} className={`shrink-0 text-clay transition-transform duration-300 ${on?"rotate-180":""}`} /></button>
      <div className="grid transition-[grid-template-rows] duration-300 ease-out" style={{gridTemplateRows:on?"1fr":"0fr"}}>
        <div className="overflow-hidden"><p className="px-6 pb-6 text-sm leading-relaxed text-muted sm:px-8">{it.a}</p></div></div>
    </div>; })}
  </div>;
}
```

### 前后对比滑块 Compare（拖动对比，改图 / 改前后 / 效果对比超直观）
传两张图（URL 或本地 `file://`）。**对齐关键**：被裁的 before 图宽度必须 = 容器宽（用 `ResizeObserver` 测量后写死 px），否则会被压缩错位。支持鼠标 + 触摸拖动。
```jsx
function Compare({ before, after, beforeLabel="改前", afterLabel="改后", height=380 }){
  const box=useRef(null), drag=useRef(false), [pos,setPos]=useState(50), [w,setW]=useState(0);
  const move=x=>{ const r=box.current.getBoundingClientRect(); setPos(Math.max(0,Math.min(100,((x-r.left)/r.width)*100))); };
  useEffect(()=>{ const ob=new ResizeObserver(es=>setW(es[0].contentRect.width)); if(box.current)ob.observe(box.current);
    const mm=e=>{ if(drag.current){ if(e.cancelable&&e.touches)e.preventDefault(); move(e.touches?e.touches[0].clientX:e.clientX);} };
    const mu=()=>drag.current=false;
    window.addEventListener("mousemove",mm); window.addEventListener("mouseup",mu);
    window.addEventListener("touchmove",mm,{passive:false}); window.addEventListener("touchend",mu);
    return ()=>{ ob.disconnect(); window.removeEventListener("mousemove",mm); window.removeEventListener("mouseup",mu); window.removeEventListener("touchmove",mm); window.removeEventListener("touchend",mu); }; },[]);
  return <div ref={box} className="relative mx-auto max-w-3xl cursor-ew-resize select-none overflow-hidden rounded-3xl border border-line shadow-lg" style={{height}}
      onMouseDown={e=>{drag.current=true;move(e.clientX)}} onTouchStart={e=>{drag.current=true;move(e.touches[0].clientX)}}>
    <img src={after} alt={afterLabel} className="absolute inset-0 h-full w-full object-cover" draggable="false" />
    <span className="absolute right-4 top-4 z-10 rounded-full bg-black/55 px-3 py-1 text-xs font-medium text-white backdrop-blur">{afterLabel}</span>
    <div className="absolute inset-y-0 left-0 overflow-hidden" style={{width:`${pos}%`}}>
      <img src={before} alt={beforeLabel} className="absolute inset-0 h-full object-cover" style={{width:w||"100%",maxWidth:"none"}} draggable="false" />
      <span className="absolute left-4 top-4 rounded-full bg-black/55 px-3 py-1 text-xs font-medium text-white backdrop-blur">{beforeLabel}</span></div>
    <div className="absolute inset-y-0 z-10 w-0.5 bg-white" style={{left:`${pos}%`}}>
      <span className="absolute left-1/2 top-1/2 flex h-10 w-10 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border-2 border-white bg-clay text-white shadow-lg"><Icon name="ChevronsLeftRight" size={18} /></span></div>
  </div>;
}
```

### 环形进度 Gauge（单一占比 / 完成度，中间叠大字）
`RadialBarChart` + `PolarAngleAxis domain=[0,100]` 把单值映射成弧度。**记得在顶部 RC 解构里加** `RadialBarChart, RadialBar`（`PolarAngleAxis` 模板已解构）。
```jsx
// 顶部解构补：const { RadialBarChart, RadialBar } = RC;
function Gauge({ value, label, suffix="%", color }){
  const P=usePalette(); const data=[{name:label,value}];
  return <div className="relative">
    <ResponsiveContainer width="100%" height={220}>
      <RadialBarChart innerRadius="76%" outerRadius="100%" data={data} startAngle={90} endAngle={-270}>
        <PolarAngleAxis type="number" domain={[0,100]} angleAxisId={0} tick={false} />
        <RadialBar background={{fill:P.grid}} dataKey="value" cornerRadius={20} fill={color||P.clay} angleAxisId={0} isAnimationActive animationDuration={1100} /></RadialBarChart>
    </ResponsiveContainer>
    <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
      <span className="text-4xl font-bold text-ink">{value}{suffix}</span><span className="mt-1 text-xs text-muted">{label}</span></div>
  </div>;
}
```

### 步骤条（流程 / SOP，左列点击、右列详情）
- 左：`<ol>` 每步一个 `<button onClick={()=>setActive(i)}>`，active 加 `border-clay/45 bg-clay/8`
- 右：`bg-card` 卡显示 `STEPS[active]` 详情；详情 div 加 `key={active}` + `reveal is-visible` 触发淡入
- 底部圆点指示器：`i===active ? "w-6 bg-clay" : "w-1.5 bg-line"`
（完整写法参考佳明培训页 `99-附件/AI生成/佳明手表配对培训.html` 的 `Steps` 组件）

### 正确/错误对比卡（语义色，深浅主题都安全）
用半透明叠加而非硬底色，深色下也协调：
- 错误：`border-bad/30 bg-bad/8 text-bad`，icon `XCircle`
- 正确：`border-good/30 bg-good/8 text-good`，icon `CheckCircle2`
（`good`/`bad` 已在 template 的 tailwind.config + 变量里定义）

## 三、配色与主题切换

模板配色走 **CSS 变量（RGB 通道）**：`<style>` 的 `:root` 是亮色（暖调），`html[data-theme="dark"]` 覆盖成深色；Tailwind colors 指向 `rgb(var(--x) / <alpha-value>)`，所以 `bg-clay/10`、`text-ink/70` 这类**透明度类照常用**（已实测 cdn Tailwind 支持 `<alpha-value>`）。明暗一键切换、`localStorage` 记忆、防闪烁脚本都内置好了。

- **改 / 换主题色**：只改 `:root` 和 `html[data-theme="dark"]` 里的变量值（空格分隔的 RGB 三通道），**组件类名一律不动**。
- **新增一个色**：① `:root` 和 dark 各加一行 `--xxx: R G B;` ② tailwind.config.colors 加 `xxx:'rgb(var(--xxx) / <alpha-value>)'`。
- **卡片底色必须用 `bg-card`**（别写 `bg-white`），否则深色模式不跟随。
- **图表色跟随主题**：SVG 不便用 CSS 变量，图表用 JS 调色板 + `usePalette()`，主题切换时 React 重渲染自动换色。改图表色改 `PALETTE`：

```js
const PALETTE = {
  light:{ clay:"#D97757", brown:"#B07D62", gold:"#C99A5B", grid:"#E3E0D6", axis:"#9B978E", axis2:"#46443F", cursor:"rgba(217,119,87,0.07)" },
  dark: { clay:"#E8956F", brown:"#C99A7A", gold:"#D9B074", grid:"#2A2F38", axis:"#6B7280", axis2:"#9CA3AF", cursor:"rgba(232,149,111,0.10)" },
};
function usePalette(){ return PALETTE[useContext(ThemeCtx).theme] || PALETTE.light; }
```

### 色值表（变量名 → 亮色 / 暗色 RGB）
| 变量 | 用途 | 亮色 | 暗色 |
|---|---|---|---|
| `--cream` | 主背景 | 240 238 230 | 15 17 21 |
| `--paper` | 次背景 | 250 249 245 | 23 26 32 |
| `--card` | 卡片 | 255 255 255 | 27 31 38 |
| `--line` | 边框 | 227 224 214 | 42 47 56 |
| `--ink` | 主文字 | 31 30 29 | 240 242 245 |
| `--ink2` / `--muted` / `--faint` | 次/弱/更弱 | 70 68 63 / 115 112 106 / 155 151 142 | 201 207 216 / 148 158 173 / 107 115 128 |
| `--clay` | 主强调 | 217 119 87 | 232 149 111 |
| `--clay-600` | 深强调 | 194 97 63 | 217 119 87 |
| `--good` / `--bad` | 语义绿 / 红 | 92 122 63 / 179 80 60 | 124 158 92 / 214 122 102 |
| `--grid` | 网格线基色 | 31 30 29 | 255 255 255 |

> **要纯深色科技风**（indigo 系，非暖调）：把上面 dark 那套变量换成 slate + indigo（`--clay` 换 `99 102 241`/`129 140 248`），并把 PALETTE.dark 的 clay/gold 换 indigo/violet 即可。

## 四、踩坑清单

1. **Recharts 整页 blank** → 必用 `recharts@2.12.7/umd/Recharts.min.js`（jsdelivr）。`recharts@2`/2.15.x 无 UMD，404。验证：`curl -sIL <url>` 看是否 200。
2. **顶层 `const {...} = Recharts` 抛错连累整页** → 用 `RC = (typeof Recharts!=="undefined"&&Recharts)?Recharts:{}` 兜底 + `RECHARTS_OK` 守卫图表区。
3. **lucide 图标不显示** → 用 `lucide@latest` UMD，`Icon` 组件读 `lucide.icons[PascalCaseName]`（如 `BatteryCharging`、`ChevronsLeftRight`）；找不到时降级空格，不抛错。
4. **JSX 不转译** → script 必须 `type="text/babel" data-presets="react"`；保持经典 script（非 module），UMD 全局才在作用域里。
5. **Framer Motion** → UMD 全局名 / 构建不稳，**弃用**；滚动动画用 `Reveal`（IntersectionObserver + `.reveal/.is-visible`），微交互用 Tailwind `hover:` 类。
6. **CDN 顺序** → React → ReactDOM → prop-types → Recharts → lucide → Babel（prop-types 是 Recharts UMD 的外部依赖）。
7. **挂载前白屏闪烁** → `<style>` 给 `body` 设 `background-color:rgb(var(--cream))`；主题防闪烁靠 `<head>` 顶部那段读 localStorage 设 `data-theme` 的内联脚本。
8. **分组柱状 barGap 太挤** → `<BarChart barGap={2}>`；中文长标签用 `layout="vertical"` 横向条 + 加大 `YAxis width`。
9. **主题切换图表不变色** → 图表用了硬编码色值。改用 `usePalette()` 取色（`stroke={P.grid}`、`fill={P.clay}`），主题切换才会重渲染换色。
10. **深色模式卡片还是白的** → 写了 `bg-white`。全部换成 `bg-card`。
11. **透明度类失效（`bg-clay/10` 变透明）** → tailwind.config 的颜色没用 `rgb(var(--x) / <alpha-value>)` 格式；变量值也必须是「空格分隔的 RGB 通道」（`217 119 87`）不能是 hex。

## 五、实开验证片段（browser-harness）

```python
import urllib.parse, time, shutil
url = "file://" + urllib.parse.quote("<HTML 绝对路径>")
new_tab(url); wait_for_load(); time.sleep(4)            # 等 Babel + CDN
print("ROOT:", js("document.getElementById('root').children.length"))   # 应 >0
print("RECHARTS:", js("typeof Recharts"))                               # 应 'object'
print("SURFACE:", js("document.querySelectorAll('.recharts-surface').length"))  # 应 >0
# 透明度类是否生效（变量化主题成立的关键）
print("CLAY10:", js("(function(){var e=[].slice.call(document.querySelectorAll('*')).filter(function(x){return x.className&&(''+x.className).indexOf('bg-clay/10')>-1})[0];return e?getComputedStyle(e).backgroundColor:'NONE'})()"))  # 应 rgba(...,0.1)
capture_screenshot(); shutil.copy("/tmp/shot.png","/tmp/v_light.png")
# 切深色再验一次
js("document.querySelector('[aria-label=\"切换深浅色\"]').click()"); time.sleep(1.2)
print("THEME:", js("document.documentElement.dataset.theme"))           # 应 'dark'
print("BODYBG:", js("getComputedStyle(document.body).backgroundColor"))  # 应深色
capture_screenshot(); shutil.copy("/tmp/shot.png","/tmp/v_dark.png")     # 再 Read 两张肉眼看
```
ROOT=0 或 SURFACE=0 → 查 `typeof Recharts/React/Babel`、看控制台报错，多半是坑 1/2/4。
`CLAY10` 返回 transparent → 坑 11。切深色后 BODYBG 不变 → 检查 `html[data-theme]` 选择器与变量。

## 六、导出 PDF（团队材料常用）

祥书的团队材料偏好 PDF（飞书可在线预览免下载）。用 browser-harness 的 CDP `Page.printToPDF` 把单文件 HTML 转 PDF。**导 PDF 前先强制亮色**（深色背景打印费墨、预览发灰）：`js("document.documentElement.dataset.theme='light'")`。

### 转 PDF 前必做「平铺展开」（不做会缺内容/发虚）

页面是给屏幕设计的（动画、交互、装饰），直接打印会丢东西。在 `<style>` 的 `@media print {}` 里一次性处理：

1. **淡入元素**：`.reveal` 初始 `opacity:0`，视口外的不会被 IntersectionObserver 触发 → `.reveal{opacity:1!important;transform:none!important;transition:none!important}`
2. **悬浮导航 + 回到顶部按钮**：fixed 元素打印会重叠 → 给 `<header>`、`BackToTop` 加 `no-print` 类 + `.no-print{display:none!important}`
3. **交互组件摊平**：步骤条 / Tab / 手风琴只渲染 active 项，PDF 里看不到其余项 → 额外渲染一个 `print-only`（Tailwind `hidden` + `.print-only{display:block!important}`）的静态完整列表，把原交互区设 `no-print`
4. **bg-grid 遮罩坑（template.html 特有）**：Hero 的 `.bg-grid` 用了 `mask-image` 径向渐变，**mask 会连同子元素一起按渐变擦淡**，导致 Hero 下半部分（stat 卡）发虚 → `.bg-grid{-webkit-mask-image:none!important;mask-image:none!important;background-image:none!important}`
5. **卡片防跨页切断**：`.rounded-3xl,.rounded-2xl{break-inside:avoid}`；`body` 加 `-webkit-print-color-adjust:exact` 保背景色

`@media print` 由 `printToPDF`（或 `Emulation.setEmulatedMedia media=print`）自动激活，无需 JS 改 DOM。

### 生成脚本（browser-harness）

两个会卡住的坑：
- **`cdp()` 签名是 `cdp(method, session_id=None, **params)`** —— 参数必须 kwargs 展开，**不能**把 params dict 当第二个位置参数传（会塞进 session_id，报 `Message may have string 'sessionId' property`）。
- **`printToPDF` 生成慢**，`_send` 的 IPC recv 硬超时 5s 不够 → 用作用域里的 `ipc.connect(NAME, timeout=90)` 直发这一条命令绕开。

```python
import base64, time, urllib.parse
url = "file://" + urllib.parse.quote("<HTML 绝对路径>")
new_tab(url); wait_for_load(); time.sleep(4)
js("document.documentElement.dataset.theme='light'")     # 导 PDF 用亮色
cdp("Emulation.setDeviceMetricsOverride", width=1056, height=1400, deviceScaleFactor=1, mobile=False)  # 1056>1024 触发 lg 多列布局
time.sleep(1)
req = {"method":"Page.printToPDF", "session_id":None,
       "params":{"printBackground":True, "preferCSSPageSize":False,
                 "paperWidth":11.0, "paperHeight":17.0,           # 长页，减少分页与切断
                 "marginTop":0.4,"marginBottom":0.4,"marginLeft":0.45,"marginRight":0.45}}
c, token = ipc.connect(NAME, timeout=90.0)        # 绕开 _send 的 5s 硬超时
try: r = ipc.request(c, token, req)
finally: c.close()
cdp("Emulation.clearDeviceMetricsOverride")
open("<输出.pdf>","wb").write(base64.b64decode(r["result"]["data"]))
```

验证：`Read` 那个 PDF（不带 `pages` 参数时走内置渲染、显示每页图像；带 `pages=` 才需 poppler）。逐页核对：淡入元素是否都显示、交互组件是否摊平成完整列表、对比卡颜色、图表是否渲染。

## 七、轻量原生「交互演示」配方（v1.3：讲解动画 / 可交互 / 配图）

讲**原理 / 机制 / 流程 / 操作** → 用零依赖原生（HTML+SVG+JS），从 `assets/template-demo.html` 起步；完整范例见 `99-附件/AI生成/香农1937-0和1如何计算-交互可视化.html`。零外部依赖 = 手机直接开、免内联、可直接 `deploy-push.py` 发妙搭。

### 7.1 可点拨交互单元（动手 > 你讲给他听）
状态变量 → 点击翻转 → 重渲染：
```js
let a=0;
function render(){
  const out = a;                       // 👈 换成你的逻辑：!a / a&&b / 加法…
  swA.textContent=a; swA.classList.toggle('hi',!!a);
  bulb.classList.toggle('on',!!out); document.getElementById('out').textContent=out;
}
swA.onclick=()=>{ a^=1; render(); };  render();
```
- 开关 = 按钮 + `.hi` 高亮；灯 = 圆 div + `.on`（`box-shadow` 发光）。
- 多输入(A/B) + 真值表：每次 render 给当前组合那行加 `.hit` 高亮（香农 AND/OR/NOT 即此模式）。
- 连续量：`<input type=range>` 的 `oninput` 里更新数字/图形。

### 7.2 SVG 分步动画 / 连线点亮 / 状态高亮
导线、元件给 class，JS 切 `.live`：
```css
.wire{stroke:var(--wire);stroke-width:5;transition:.3s}
.wire.live{stroke:var(--accent);filter:drop-shadow(0 0 5px var(--accent))}
.lamp.live{fill:var(--on);filter:drop-shadow(0 0 9px var(--on))}
```
- **通断可视化**：按"电流走到哪断了"逐段上色（香农串联：起段恒亮、A 后 = a、B 后 = a&&b）——让人看见为什么断。
- **分步推进**：`step` 0→N，`seg{i}.classList.toggle('live',step>=i)` + 步骤条 `.step.active`；「下一步」按钮 或 IntersectionObserver 滚动自动播。
- 开关两态：画两条线（闭合连接线 / 断开斜线闸刀），按状态切 `display`。

### 7.3 配图策略（任何范式通用）
🔴 **图片绝不走外链**（手机无代理一样裂/白，跟 CDN 同坑）。优先级：
1. **SVG / CSS 画的示意图**（电路、流程、几何）——零依赖、随主题变色，首选。
2. **图标**：内嵌 SVG `<path>` 或表情符号。
3. **真实图 / 插画**：走 `chatgpt-image-maker` skill 生成 → **base64 内联**：
   ```bash
   python3 -c "import base64,sys;print('data:image/png;base64,'+base64.b64encode(open(sys.argv[1],'rb').read()).decode())" 图.png
   ```
   输出塞进 `<img src="data:image/png;base64,…">`。产品图先搜 vault。
- 深色页：透明 PNG / SVG 最稳，白底图在暗色下突兀。

### 7.4 原生版交付与验证
零依赖原生版**免内联**，直接 `python3 scripts/deploy-push.py <页> "<标题>"` 发妙搭+推送（脚本检测无 CDN 自动跳过内联）。验证 = browser-harness 实开**逐个交互实拨**看输出对（香农就是 AND/OR/NOT + 半加器逐一拨验过），别只截图看静态。
