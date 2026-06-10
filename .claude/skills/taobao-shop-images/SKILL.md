---
name: taobao-shop-images
version: 1.0.0
description: "祥新公司标准方法：下载自家淘宝/天猫店铺商品的全部图片（主图/3:4长主图/SKU颜色图/详情长图/主图视频），走卖家后台发布页、零反爬。当同事说『下载店铺图片』『下载淘宝图』『把XX商品的图扒下来』『一键下载全店图片』时使用。⚠️ 这是公司标准版（踩过反爬坑），凡下载自家店铺图片一律用它，不要自创爬买家页的方法。"
metadata:
  requires:
    bins: ["python3"]
    pip: ["websocket-client"]
---

# 淘宝店铺图片下载（公司标准方法 · 可移植版）

下载**自家**店铺商品的全部图片，按 `商品名_ID/{01-主图,02-3比4长主图,03-SKU颜色图,04-详情长图,05-主图视频}/` 归类，全是原图，默认存 `~/Downloads/淘宝店铺图片/`。

## 为什么必须用这个方法（不要自创）

打开自己商品的**后台发布页** `item.upload.taobao.com/sell/v2/publish.htm?itemId=<ID>`，服务端把整份商品数据直出在 `window.Json`，所有图片 URL 分门别类都在里面；图片本体在 `img.alicdn.com` 公共 CDN，直接下载不设防。**全程只碰自己卖家后台，不开买家详情页**——买家页是 baxia/滑块反爬的高发区，自制脚本爬买家页下多了会触发平台风控，影响店铺。

## 三个前提

1. **Chrome 带调试端口启动 + 在里面登录目标店铺的千牛**（启动命令见下；想下哪个店就登哪个店，不存账密）
2. **不挂代理/VPN**（淘宝必须走国内网络，挂代理反而触发风控）
3. 装过依赖：`pip install websocket-client`（只装一次）

## 第一次配置：启动带调试端口的 Chrome

新版 Chrome 不允许在默认配置上开调试端口，所以用一个**专门的下载用 Chrome**（独立配置目录，第一次要在里面登一次千牛，以后记住）：

**Windows**（保存成 `启动下图Chrome.bat` 双击即可）：
```bat
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\chrome-taobao-images"
```

**Mac**：
```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --remote-debugging-port=9222 --user-data-dir="$HOME/chrome-taobao-images" &
```

启动后在这个 Chrome 窗口里打开 `myseller.taobao.com` 登录千牛（扫码即可）。**这一步只有第一次需要做。**

## 怎么跑

脚本：本目录 `scripts/shop_images_portable.py`。三种模式：

```bash
# 下指定商品（ID 从商品链接里的 id= 参数拿，可多个）
MODE=ids ITEM_IDS=1046638400847,1045007898948 python3 scripts/shop_images_portable.py

# 下全店所有在售商品
MODE=all python3 scripts/shop_images_portable.py

# 只下上次跑之后新上架的商品（适合定期跑）
MODE=scan python3 scripts/shop_images_portable.py
```

Windows 下环境变量写法：`set MODE=all` 后再 `python scripts\shop_images_portable.py`（或让 AI 直接用 PowerShell：`$env:MODE="all"; python ...`）。

可选环境变量：`CDP_PORT`（Chrome 调试端口，默认 9222）、`OUT_DIR`（输出目录）、`MAX_PAGES`（全店翻页上限，默认 80）。

## AI 执行要点

- 用户给的是商品**链接**时，自己从中抽出 `id=` 后面的数字串当 ITEM_IDS，别让用户手动抠
- 跑之前先 `curl http://127.0.0.1:9222/json/version` 探一下端口：不通 → 引导用户按上面命令启动 Chrome 并登录千牛，**别擅自换成爬买家页的方案**
- 输出里出现「提取失败（可能千牛没登录）」→ 让用户在那个 Chrome 窗口里重新登录千牛后重跑，失败的商品重跑会自动补
- 全店模式商品多时（几十上百个）耗时较长，告知用户预估后台跑，跑完汇报成功/失败数
- 脚本自带拟人随机间隔，**不要为了快改小 sleep**

## 排错

| 现象 | 原因 | 解法 |
|---|---|---|
| 连不上调试端口 | Chrome 没带参数启动 | 按上面命令重启 Chrome（先完全退出） |
| no window.Json / 提取失败 | 千牛没登录 / 不是本店商品 | 在那个 Chrome 里登录千牛；确认商品属于当前登录的店 |
| 图片下载 0 字节/失败几张 | CDN 偶发 | 重跑该商品（MODE=ids）即可补齐 |
| 列表页收集不到 ID | 商品管理页改版/加载慢 | 提高等待后重试；仍不行群里反馈阿祥 |

## 维护

源头版本在阿祥本机（browser-harness 版，`~/work/taobao-shop-images/`），本可移植版与其同源同逻辑。发现失效（页面改版等）在群里 @ 阿祥，统一修。
