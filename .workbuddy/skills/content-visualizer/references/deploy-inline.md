# 部署：发妙搭 / 发手机前先内联（防白屏）

> **铁律**：content-visualizer 产物默认走 6 个国际 CDN（unpkg / jsdelivr / cdn.tailwindcss.com）。**自己电脑双击看没问题，但部署飞书妙搭 / 发祥书手机飞书打开会整页白屏**——手机无代理加载不出国际 CDN → React/Babel 跑不起来 → `#root` 空 → 白屏。（2026-05-23 身体数据全景页踩到：本地全正常、祥书手机全白。）
>
> 所以 **凡是要发出去（妙搭 / 手机 / 分享给别人）的页面，先用 `assets/inline-build.js` 打成零外部依赖的内联版再发。** 只给自己电脑看可以跳过。

## 1. 一步打包：CDN 版 → 内联自包含版

```bash
node <本skill>/assets/inline-build.js <你的页面.html> [输出.html]
# 不给输出路径 → 默认写 <页面>.inline.html；想原地覆盖就把输出填成和源一样
```

脚本自动：① 下载 6 个库到 `~/.cache/content-visualizer-libs/`（首次下载后复用）；② 提取 `type="text/babel"` 的 JSX，用 esbuild 预编译成纯 JS（去掉 3MB Babel，手机秒开、无浏览器转译延迟/失败风险）；③ 把 6 个 CDN `<script src>` + 编译后 JS 全部内联 → 输出 ~1.6MB 单文件。

末尾打印 `剩余外部 <script src>: 0 ✓ 零外部依赖` 才算成功（脚本里 ext≠0 会 exit 1）。

依赖：node + `npx esbuild`（脚本自动调，首次现下）。库版本与 template.html 的 CDN 标签逐字对应——**改 template 的 CDN 行就要同步改脚本里的 `LIBS[].tag`**。

## 2. 验证（发出去前必做）

browser-harness 实开内联版，铁证是 **零网络请求**：

```python
import time, urllib.parse
new_tab("file://"+urllib.parse.quote("<内联HTML绝对路径>")); wait_for_load(); time.sleep(5)
print(js("performance.getEntriesByType('resource').length"))         # 必须 0
print(js("document.querySelectorAll('.recharts-surface').length"))   # = 图表数，>0
print(js("typeof React"), js("typeof Recharts"), js("typeof tailwind"))  # 都 'object'
```

`resource length == 0` 就证明手机离线也能开。再点 `header button[aria-label]` 切深色截图核对双主题。

## 3. 部署飞书妙搭（lark-apps）

妙搭单文件部署两个硬约束：**文件名必须是 `index.html`**、`--path` 必须是 **cwd 内相对路径**（绝对路径/`../` 会被拒）。固定套路：

```bash
mkdir -p ~/work/miaoda-deploy
cp <内联HTML> ~/work/miaoda-deploy/index.html
# 首次：新建应用（复用旧应用直接拿 app_id，跳过这步）
lark-cli apps +create --name "<应用名>" --app-type HTML --as user      # 返回 data.app.app_id
# 发布（cd 进去用相对路径）
cd ~/work/miaoda-deploy && lark-cli apps +html-publish --app-id <app_id> --path ./index.html
```

返回 `data.url` 即访问链接（祥书本人 user 身份建的，他自己能开）。**更新内容**：同 app_id 重新 `+html-publish`，链接不变，重开即新版。

> 妙搭线上访问要飞书 OAuth 登录，browser-harness 那个 Chrome 没登录态会跳授权页、抓不到真实页面——线上只能靠祥书手机实开；自动化验证就验本地 file:// 内联版。

## 4. 推送给祥书

部署拿到链接后，用 `lark-push-xiangshu` 发祥书飞书（手机能点）：

```bash
source ~/.zshrc >/dev/null 2>&1; ~/.claude/skills/lark-push-xiangshu/scripts/send.py "链接 + 一句话摘要"
```

（send.py 的 App ID/Secret 在 `~/.zshrc`，Claude Code 的 Bash 是非交互 shell 不自动读，必须先 `source`。）
