# 三平台发布流程（抖音 / 视频号 / 小红书）

发布走 [[browser-harness]]：**截图驱动**为主，CDP 文件上传为确定性骨架，选择器只是提示——**一切以实测截图为准**。第一次跑务必 `--dry-run`，把每个平台的真实选择器/坐标/坑回填到本文件对应小节，让它越用越准。

> **诚实原则**：任一步骤找不到元素、卡转码、登录失效 → `capture_screenshot()` 后**停下报告是哪一步断的**，不硬点、不谎报已发。

---

## 通用子流程（三平台共用骨架）

```bash
browser-harness <<'PY'
# ---- 0. 连已登录 Chrome + 开发布页 ----
ensure_real_tab()
new_tab("<平台发布页 URL>")          # 见各平台小节；用 new_tab 不用 goto，别动祥书其他标签
wait_for_load()
capture_screenshot()                  # 看登录态：没登录就停，让祥书登，绝不自己输密码
PY
```

```bash
browser-harness <<'PY'
# ---- 1. 上传视频：CDP setFileInputFiles（不弹系统文件框，最稳）----
VIDEO = "/abs/path/to/video.mp4"
doc = cdp("DOM.getDocument", {"depth": -1})
root = doc["root"]["nodeId"]
node = cdp("DOM.querySelector", {"nodeId": root, "selector": "input[type=file]"})  # 多个 file input 时见各平台小节
nid = node.get("nodeId")
assert nid, "没找到 file input：截图看上传区，可能在 iframe 或要先点'上传视频'按钮唤出 input"
cdp("DOM.setFileInputFiles", {"files": [VIDEO], "nodeId": nid})
capture_screenshot()                  # 确认进度条/预览出现 = 上传开始
PY
```

```bash
browser-harness <<'PY'
# ---- 2. 等转码完成（轮询，别假设瞬间好）----
import time
for _ in range(180):                  # 给到 ~3 分钟，长视频更久
    capture_screenshot()              # 看进度；平台一般转码完才允许填封面/发布
    # 判据：进度文案消失 / 出现"重新上传"+封面编辑入口 / 发布按钮变可点
    txt = js("return document.body.innerText") or ""
    if any(k in txt for k in ["上传成功","发表","发布"]) and "上传中" not in txt and "%" not in txt[:2000]:
        break
    time.sleep(2)
PY
```

```bash
browser-harness <<'PY'
# ---- 3. 填标题/描述/话题（平台差异见各小节）----
# 富文本/contenteditable：focus 后 type_text（仿 chatgpt-image-maker 对 ProseMirror 的处理）
js("<标题框选择器>.focus?.() || document.querySelector('<标题框选择器>')?.focus()")
type_text("<标题>")
# 描述框同理；话题在描述里打 #关键词 触发下拉，需选中（见各平台坑）
capture_screenshot()
PY
```

```bash
browser-harness <<'PY'
# ---- 4. 设封面：点封面编辑入口 → 上传本地封面 ----
# 先点"选择封面/编辑封面"唤出面板，再 setFileInputFiles 到封面的 file input
# 封面 input 常与视频 input 不同，唤出面板后重新 querySelector
capture_screenshot()
PY
```

```bash
browser-harness <<'PY'
# ---- 5. 发布 ----
import os
DRY_RUN = True                        # 首测 True：截图停在发布前；放开直发改 False
capture_screenshot()                  # 发布前全局截图存档
if DRY_RUN:
    print("DRY-RUN：已停在发布按钮前，未点发布。检查截图无误后再放开。")
else:
    # 找"发布"按钮点击（见各平台选择器），点完轮询"发布成功"确认态
    # 到达确认态才算成功；否则报告卡在哪
    pass
PY
```

---

## 抖音

- **URL**：`https://creator.douyin.com/creator-micro/content/upload`
- **流程**：上传视频 → 跳到编辑页 → 填「作品描述」(标题+话题合一，第一行最关键) → 选封面 → 选合集/位置(可选) → 发布。
- **话题**：在描述框打 `#关键词`，弹下拉，**要点选下拉项**才成话题（直接打 `#xx ` 有时不生效）。3-5 个。
- **封面**：上传后点「选择封面」→ 可「上传封面」用本地图 → 裁切确认。
- **发布按钮**：编辑页底部「发布」。点后等跳转到内容管理 + "发布成功"提示。
- **选择器（实测回填）**：
  - file input：`____`
  - 描述框：`____`（contenteditable）
  - 封面入口：`____`
  - 发布按钮：`____`
- **坑（实测回填）**：`____`

---

## 微信视频号

- **URL**：`https://channels.weixin.qq.com/platform/post/create`
- **登录**：微信扫码，**登录态短、易掉**，发之前先截图确认，掉了让祥书重扫。
- **流程**：上传视频 → 填「描述」(短标题在前) → 话题/活动(可选) → 封面 → 位置/合集(可选) → 发表。
- **标题**：视频号短标题建议 ≤20 字，描述清晰可信。
- **封面**：上传后「编辑封面」→ 上传本地图。
- **发布按钮**：「发表」。点后等"发表成功"。
- **选择器（实测回填）**：file input `____`／描述框 `____`／封面入口 `____`／发表按钮 `____`
- **坑（实测回填）**：`____`（视频号部分控件可能在 iframe，坐标点击穿透 iframe，必要时 click_at_xy）

---

## 小红书（视频笔记）

- **URL**：`https://creator.xiaohongshu.com/publish/publish`
- **流程**：默认有「上传视频 / 上传图文」Tab——**选「上传视频」** → 上传 → 填标题(≤20字) → 正文(含话题) → 封面 → 添加话题/地点(可选) → 发布。
- **话题**：正文里打 `#关键词` 弹下拉点选；小红书话题 5-10 个，覆盖品类+人群+场景+痛点。
- **标题/正文**：标题框 + 正文框分开；正文口语种草、分行、适度 emoji。
- **封面**：「编辑封面」→ 上传本地竖版封面（3:4 友好）。
- **发布按钮**：「发布」。点后等"发布成功"跳转。
- **选择器（实测回填）**：上传视频Tab `____`／file input `____`／标题框 `____`／正文框 `____`／封面入口 `____`／发布按钮 `____`
- **坑（实测回填）**：`____`

---

## 实测校准清单（第一次跑 --dry-run 时逐平台填）

每个平台 dry-run 跑通后，把上面 `____` 处替换成真实选择器/坐标，并记录遇到的坑（iframe、受控组件要触发 input 事件、转码等待时长、话题下拉交互、封面裁切弹窗等）。这份文件填实后，后续发布才能顺。

- [ ] 抖音：file input / 描述框 / 话题下拉 / 封面 / 发布按钮 全部实测
- [ ] 视频号：登录态确认 / file input / 描述框 / 封面 / 发表按钮 全部实测
- [ ] 小红书：上传视频Tab / file input / 标题 / 正文 / 话题 / 封面 / 发布按钮 全部实测
