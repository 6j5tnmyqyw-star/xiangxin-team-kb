---
name: shop-new-items
description: 天猫店铺新品采集：抓某个天猫店铺最新上架的商品列表（按"新品"排序，默认过滤清仓/福利款）。当祥书说『看看 XX 店上新了什么』『抓一下 XX 竞品店的新品』『XX 店最近上了哪些款』『查下 XX 店铺新品』『竞品上新』『XX 店铺新品列表』时使用。靠 browser-harness 连已登录淘宝的 Chrome 抓 mtop 接口，输出店铺名/粉丝数/全店数 + 商品列表（标题/主图/年销量/优惠点）。
metadata:
  requires:
    bins: ["browser-harness", "python3"]
---

# 天猫店铺新品采集

> **用途：** 抓**单个天猫店铺**最新上架的商品（按店铺"新品 newOn_desc"排序），主要用来盯竞品店上新动态。脚本走 browser-harness 连一个已登录淘宝的 Chrome，hook XHR 抓 `mtop.taobao.shop.simple.fetch` 接口，输出结构化 JSON。

脚本：`scripts/shop_new_items.py`

## 一、什么时候用

祥书说出以下意图之一就触发：
- 「看看 XX 店上新了什么 / 最近上了哪些款」
- 「抓一下 XX 竞品店的新品 / 竞品上新」
- 「查下 XX 店铺新品列表」

**不适用 / 区分**：
- 跨店比同一型号的价格、找异常低价/串货 → 用 [[taobao-price-monitor]]（那个是按搜索词跨店抓价格，这个是盯单店上新）
- 单条商品看详情 → 直接开淘宝
- 非天猫（C 店 taobao.com）店铺：接口结构可能不同，没测过

## 二、前置：找一个已登录淘宝的 Chrome 调试端口

脚本不自己开浏览器，要连一个**已登录淘宝、开了 CDP 调试端口**的 Chrome（和 [[qianniu-chat-extract]] / [[taobao-price-monitor]] 复用同一类抓取 Chrome）。调用前先确认端口：

```bash
# 1) 看哪些 Chrome 开着调试端口
ps aux | grep -o "remote-debugging-port=[0-9]*" | grep -v grep | sort -u

# 2) 逐个探，看哪个登录了淘宝（有 taobao/tmall/sycm 标签 = 已登录）
for p in 9222 9223 9224 9225 9227; do
  echo "[$p]"; curl -s --max-time 2 http://127.0.0.1:$p/json/list 2>/dev/null \
    | python3 -c "import sys,json; [print('  ',t.get('url','')[:50]) for t in json.load(sys.stdin) if t.get('type')=='page']" 2>/dev/null
done
```

- 实测祥书机器上淘宝登录态常在 **9224**（生意参谋那个 Chrome）。
- 都没有 → 让祥书启动一个登录淘宝的 Chrome（或复用 qianniu 的 `start_chrome.sh`），脚本默认端口是 9227。

## 三、跑脚本

```bash
python3 scripts/shop_new_items.py "<店铺主页URL>" --port <端口> [--limit N]
```

例（实测可跑）：

```bash
python3 scripts/shop_new_items.py "https://kingloy.tmall.com" --port 9224 --limit 10
```

参数：

| 参数 | 默认 | 说明 |
|---|---|---|
| `shop_url` | 必填 | 店铺主页 URL（`https://xxx.tmall.com`，带不带 `/index.htm` 都行，脚本会规范化成新品排序页） |
| `--port` | 9227 | 已登录淘宝的 Chrome 调试端口；也可用环境变量 `BH_TB_PORT` |
| `--limit` | 10 | 取前 N 个（按上架时间倒序） |
| `--include-clearance` | 关 | 默认会过滤掉福利款/清仓款，加这个开关则不过滤 |

脚本行为：开**隔离新标签**抓取、抓完即关，不动那个 Chrome 的其他标签（安全，不会覆盖正在用的页面）。

## 四、输出

stdout 是 JSON，stderr 是进度日志。JSON 结构：

```json
{
  "shopName": "KINGLOY旗舰店",
  "fansNum": "3111",
  "totalCnt": 153,
  "items": [
    {
      "itemId": 1043775778191,
      "title": "【冰丝凉感】KINGLOY高尔夫女装2026夏季...",
      "image": "https://gw.alicdn.com/...jpg",
      "sold365": "6",
      "benefits": ["官方立减15%", "已降124元"]
    }
  ]
}
```

- `items` 按 `itemId` 倒序 = **上架时间倒序**（最新上架的在最前）。
- `sold365` 是淘宝展示的近 365 天销量（模糊值，字符串）。
- `benefits` 是页面上的优惠点文案。

呈现给祥书时：把前 N 个商品列成清单（标题 + 年销量 + 优惠），点出"最新上架的是哪几款、有没有在主推某个新方向"。要落地（建任务/存档）再走对应流程。

## 五、注意事项

- **接口易变**：核心靠 `mtop.taobao.shop.simple.fetch` + 字段 `signInfoDTO.shopName` / `itemInfoDTO.data[]`。淘宝改版后若抓不到，先在浏览器里看该接口名/字段是否变了，再改 `BH_SNIPPET` 里的 hook 和读取 JS。
- **单页 30 条**：接口一页约返回 30 个商品（`totalCnt` 是全店总数）。要更多得翻页（改 `pageNo`），目前脚本只抓第 1 页（新品看最新一页足够）。
- **风控/未登录**：抓不到数据多半是那个 Chrome 没登录淘宝或被风控。脚本会报错提示，换一个登录态好的端口即可。
- **频次**：盯竞品上新一天看一两次就够，别高频跑。
- **隐私**：竞品店铺商品是公开信息，不涉隐私；但产出别和客户/订单数据混在一起外发。

## 六、来源

脚本由祥书 2026-05-22 提供（`shop_new_items.zip`），封装时做了两处修正：① 加 `--port`（原脚本写死 9227，但机器上淘宝登录态在 9224）；② 把 `goto_url` 改成"开隔离新标签抓完即关"，避免覆盖 Chrome 当前标签（遵守 browser-harness 铁律）。已用 KINGLOY旗舰店实测通过。
