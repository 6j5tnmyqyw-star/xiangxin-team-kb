---
name: taobao-price-monitor
version: 2.0.0
description: "祥新公司专用：跑淘宝竞品监控脚本，把异常价格写入飞书多维表格。当祥书说『跑一下淘宝比价』『监控一下竞品价格』『查 Garmin 价格』『跑竞品监控』『今日比价』时使用。脚本连已登录淘宝的真 Chrome（browser-harness，防反爬），按型号取销量榜 Top N，只把偏离中位数 ≥ 3% 的异常价写入飞书。"
metadata:
  requires:
    bins: ["lark-cli", "python3", "browser-harness"]
  python: "/usr/local/bin/python3"
---

# 淘宝竞品价格监控（v2.0 · browser-harness 版）

> **用途：** 连一个**已登录淘宝的真 Chrome**（端口 9224，与 `xiangxin-jingpin-shangxin` 共用同一监控 profile），抓淘宝按销量 Top N 的商品价格，按型号分组后**只把异常价**写入飞书多维表格。

> ⚠️ **v2.0 变更（去反爬）**：已弃用 selenium-stealth（弱指纹，天天吃 rgv587 风控）。现在走 browser-harness 连真 Chrome，指纹是真浏览器。老脚本 `~/garmin_monitor.py` 已挪到 `~/garmin_monitor.py.selenium-deprecated.bak`，不再使用。

## 一、什么时候用

祥书说出以下意图之一就触发：
- 「跑一下淘宝比价 / 今日比价」
- 「监控一下竞品 / Garmin 价格」「跑竞品监控脚本」
- 「看看今天有没有人乱报价 / 串货价」

不适用：
- 单条商品价格查询 → 直接打开淘宝
- 非 Garmin 型号（先在 `scripts/monitor.py` 的 `KEYWORDS` 里加配置）

## 二、前置：9224 Chrome 登录淘宝（与 jingpin-shangxin 共用）

脚本走 browser-harness 连**端口 9224** 的监控专用 Chrome（profile = `~/千牛产出/chrome-profiles/bsn-tmall`）。一个登录态喂两个监控技能。

```bash
# 1) 看 9224 是否在跑
curl -s --max-time 3 http://127.0.0.1:9224/json/version >/dev/null && echo "9224 ALIVE" || echo "需启动"

# 2) 没在跑 → 启动它（独立 profile，不动祥书主 Chrome）
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9224 \
  --user-data-dir="$HOME/千牛产出/chrome-profiles/bsn-tmall" "https://www.taobao.com" &
```

**登录态会过期**：脚本报「登录墙(需重登淘宝)」时 = 让祥书在 9224 那个 Chrome 窗口里**扫码重新登录淘宝**，登录态留 profile 里复用。**不要替祥书输账号密码。**

## 三、监控对象

| 型号 | 搜索词 |
|---|---|
| S70 | Garmin S70 高尔夫 |
| G82 | Garmin G82 高尔夫 |
| R50 | Garmin R50 高尔夫 |
| Z30 | Garmin Z30 高尔夫 |

每个型号取销量排序 Top 15。

## 四、运行流程（标准操作）

1. 确认 9224 Chrome 在跑且登录淘宝（见上）。**不需要再 Cmd+Q 关 Chrome**（v1 的 selenium 才要复制 profile，v2 不用）。
2. 跑脚本：
   ```bash
   cd 07-AI协作/skills/taobao-price-monitor/scripts
   /usr/local/bin/python3 monitor.py --port 9224
   ```
   常用参数：
   - `--only S70`：只跑一个型号
   - `--dry-run`：抓+过滤但**不写飞书**（先验证再正式跑）
3. 脚本逐型号搜索 → 按型号做异常价过滤 → 异常价写入飞书。
4. 报给祥书：`今天 X 条异常价已记录，Y 条正常价已忽略`，附飞书表格链接。若有型号报「登录墙/风控」，提示祥书去 9224 Chrome 手动过一次。

## 五、异常价过滤规则（铁律）

> **大家价格都一样的就是正常价，不写入飞书。只记录偏离的。**

- **分组**：按型号（S70 / G82 / R50 / Z30）。
- **基准**：每组到手价的**中位数** = 「市场正常价」。
- **过滤**：偏离 ≤ `NORMAL_PRICE_TOLERANCE`（默认 **3%**）→ 正常价丢弃；偏离 > 3% → 异常价写入飞书。
- **样本量**：该型号有效样本 < `MIN_RECORDS_FOR_FILTER`（默认 **3**）→ 不过滤，全部写入。

调整阈值：编辑 `scripts/monitor.py` 顶部配置区。

## 六、脚本结构

| 文件 | 作用 |
|---|---|
| `scripts/scrape_search.py` | 单关键词抓取：browser-harness 连真 Chrome → 淘宝销量榜 → DOM 抽取（`doubleCard--`）→ 返回 JSON。可单独调试：`python3 scrape_search.py "Garmin S70 高尔夫" --port 9224` |
| `scripts/monitor.py` | 编排：逐型号抓 → 异常价过滤 → 写飞书 |

## 七、飞书配置（写死在 monitor.py）

| 项目 | 值 |
|---|---|
| App ID | `cli_a977681a7d389bc1` |
| Bitable Token | `KkWWbX5goaoMKrsDcOvcb2Emn2d` |
| 数据表 ID | `tbl5JSiMcOVd2eMa`（Garmin竞品） |
| 飞书表格 | https://xiangxingolf.feishu.cn/base/KkWWbX5goaoMKrsDcOvcb2Emn2d |

## 八、可调参数（monitor.py 配置区）

| 参数 | 默认值 | 说明 |
|---|---|---|
| `KEYWORDS` | 4 个型号 | 增删监控关键词 |
| `TOP_N` | 15 | 每个型号抓前 N 条 |
| `NORMAL_PRICE_TOLERANCE` | 0.03 | 偏离中位数 ≤ 3% 视为正常价 |
| `MIN_RECORDS_FOR_FILTER` | 3 | 样本少于这个数不过滤 |

## 九、注意事项

- **频次**：每天 1 次，不要小时级频跑。
- **别和 jingpin-shangxin 同时跑**：两者抢同一个 9224 Chrome，浏览器任务要串行（参见协作铁律）。
- **选择器失效**：淘宝改版后更新 `scrape_search.py` 里的 `doubleCard--` / 各 class 选择器。
- **风控/登录墙**：browser-harness 真 Chrome 指纹强，rgv587 概率远低于 v1；万一弹滑块/登录墙，**别刷新**，让祥书在 9224 Chrome 手动过一次再重跑。规避总纲见 [[reference_taobao_antibot]]。

## 十、查看历史

每次运行追加，按「采集时间」列区分批次。建议视图：按「采集时间」分组 / 按「型号」筛选 / 按「价格」升序找异常低价。

## 十一、维护

- **新增型号**：编辑 `monitor.py` 的 `KEYWORDS`。
- **过滤太严/太松**：调 `NORMAL_PRICE_TOLERANCE`。
- **文档同步**：本 SKILL.md 是单一权威源；`祥子AI/03-公司/工具与需求/Garmin竞品监控.md` 是团队简版，改这里记得同步那边。
