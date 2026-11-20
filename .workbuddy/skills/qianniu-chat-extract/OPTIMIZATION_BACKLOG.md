# qianniu-chat-extract 优化清单（AI 主动维护）

> **AI 使用本 skill 时必读**：调用本 skill 任何命令前，先 cat 这份文件。如果有匹配当下场景的项（最近触发的问题、攒够数据可以跑的分析），主动向祥书提一次"要不要现在做"。不要每次倒整张清单，挑最相关的 1-2 条。

## 一、已知问题（待修复 bug / 小坑）

| 优先级 | 问题 | 触发条件 | 影响 | 建议修复方式 |
|---|---|---|---|---|
| ✅已复核 | ~~"旺旺咨询明细"全量 tab 切换失败 `tab-not-found`~~ | — | **2026-05-22 实测复核：tab 返回 `already-active`，切换/翻页都正常，非 bug。每天数据少（如 5-21 全量 tab 仅"共 9 条"）是真实业务量——倍视能测距仪是细分高客单品类，日咨询本就个位数到十几，不是漏抓。`已端到端跑通 5-21：9 行→9 会话全抓到。`历史 `tab-not-found` 疑为页面未加载完时的时序误报。** | 若再现 tab-not-found：在 `switch_to_all_tab` 前加 `wait_for_selector('.ant-tabs-tab-btn')` 等 tab 渲染再点 |
| ~~中~~ ✅ | ~~auto-date 日期切换失败 `no-date-picker-found`~~ | 已修复（2026-05-18）：生意参谋用淘宝自家 OUI 组件（`.oui-date-picker` + `.oui-dt-calendar-content.day`），脚本已支持点"日"按钮→翻月→点日期格 | — | — |
| 低 | 部分消息 sender 显示空 | 客服连续发多条消息时 | 阅读时要从上下文推断发送人；分析时统计客服话术会偏低 | 后处理：把空 sender 填成同一买家会话里上一条非空 sender |
| 低 | 店铺名匹配 warning | 启动时（"倍视能旗舰店\n主店" vs 配置"天猫倍视能旗舰店"） | 仅 warning，不阻塞 | 把 shops.json 里 name 改成页面实际显示的字符串（或脚本里做模糊匹配） |

## 二、待开发的分析方向（按祥书 2026-05-16 确认的优先级）

| # | 方向 | 输出 | 最小数据量 | 跑多久 | 状态 |
|---|---|---|---|---|---|
| 1 | 高频问题 TOP 10 + SOP 缺口 | 问题清单 md → 派任务给采购/运营 | ≥ 30 个会话（约 1 周） | 周 | demo 已跑，需 ≥ 30 会话再正式分析 |
| 2 | 优秀话术对照库 | 按场景分类（开场/对比/逼单/异议）的话术段落 | ≥ 30 个会话 | 周 | 未开发 |
| 3 | 运营决策周报 | 产品/价格/竞品 mention 汇总 + 决策建议 | ≥ 30 个会话 | 周 | 未开发 |
| 4 | 快捷短语提取 | 自动累积到 `08-公司知识库/客服话术/快捷短语库.md` + 同步飞书 docx | 持续累积 | 每次抓取后自动 | ✅ 已上线，挂在 run_daily.sh 后置流程 |
| 5 | 客服质检评分卡 | 每客服周评分卡 → 飞书私信 + 汇总群 | ≥ 50 会话/客服（约 1-2 周） | 周 | 未开发 |

### 触发条件
- 方向 1：本店本周累计抓到 ≥ 30 会话 → 提议跑一次
- 方向 2：方向 1 跑通后启动
- 方向 3：方向 1 跑通后启动
- 方向 4：已上线持续累积；累计 ≥ 50 会话/店时提议运营组评审一轮、把"待审核"标为"已采用"/"待优化"
- 方向 5：单个客服累计 ≥ 50 会话 → 提议给那个客服出一份评分卡

### 方向 4 飞书短语库
- 飞书 docx：[客服快捷短语库](https://xiangxingolf.feishu.cn/docx/NrOld9BQOooWW1xE7Y2cSgQ7n1c)（doc_token 存 `~/千牛产出/lark_docs.json`）
- 同步机制：本地 md 是 source of truth，每次抓取后用 lark-cli overwrite 模式覆盖飞书 docx
- 后续要做：① ≥ 50 短语时提议升级到飞书多维表格（可勾选"已采用"） ② 客服可以在飞书评论里建议改话术

## 三、运维 backlog（基础设施层面）

| 项 | 说明 | 触发提议时机 |
|---|---|---|
| 其它店登录 | 已配 slug 但未登录：xinshui-tm(9225) / xinshui(9222) / bsn-jd(9226) / xinshui-jd(9227) | 任何时候祥书说"再抓 X 店" |
| launchd 启用 | plist 已写但未 load | 测试跑通 1-2 次后提议启用 |
| 多店并行 wrapper | 现在 `run_daily.sh` 只跑 bsn-tmall，要支持 `--all` 跑所有已登录的店 | 第 2 家店登录后 |
| Chrome 心跳监控 | 凌晨 5:30 检测各端口 Chrome 还活着否，挂了就提前推飞书让祥书早起重登 | 第一次 6 点跑失败后 |
| 服务模块快照"已渲染"判断 | 真实体验分/物流洞察 2 个页面 wait_for_function 超时（但截图 OK，数据在 canvas/SVG 里）| 不影响功能，等做"结构化数据抽取"时再调 |
| 服务模块结构化抽取 | 现在只截图 + 文本，没解析具体数字。未来从 PNG/SVG 里抽体验分、退款率等指标，存 JSON 画趋势曲线 | 攒到 ≥ 14 天快照后 |

## 四、服务模块快照（每天 6 个 dashboard 截图 + API 原始 JSON）

抓取脚本：`scripts/extract_service_metrics.py`，挂在 `run_daily.sh` 后置流程。

| # | 页面 | URL | API 拦截 |
|---|---|---|---|
| 1 | 真实体验分 | https://sycm.taobao.com/qos/frame/cds/experience#/monitor | ⚠️ 数据在 iframe |
| 2 | 服务核心监控 | https://sycm.taobao.com/qos/service/core_monitor/new#/monitor | ✅ /csp/api/core/monitor/* |
| 3 | 店铺绩效 | https://sycm.taobao.com/qos/service/frame/shop/performance/new#/shop | ✅ /csp/api/shop/sale/summary/* |
| 4 | 客服绩效 | https://sycm.taobao.com/qos/service/frame/customer/performance/new#/user | ✅ /csp/api/user/sale/summary/* |
| 5 | 售后退款保障 | https://sycm.taobao.com/qos/service/after_sale/activist?activeTab=refundProtectionNew#/ | ✅ /csp/api/shop/refund/* |
| 6 | 物流洞察 | https://sycm.taobao.com/qos/frame/cds/logistics/qn | ⚠️ 数据在 iframe |

### 归档结构
```
08-公司知识库/服务报表/
├── _raw_api/YYYY-MM/YYYY-MM-DD/<店名>/<页>.jsonl    ← API 原始 JSON（每页 30-46 个响应，3-6 MB/天/店）
└── YYYY-MM/YYYY-MM-DD/<店名>/<页>.png + .txt          ← 截图 + 文本快照
```

体积：每天约 10 MB/店（截图 4 MB + API 6 MB），6 店 ≈ 60 MB/天，1 年 ≈ 22 GB。Vault 在 iCloud Sync，可控。

### 关键 API endpoint（已确认）
- `/csp/api/core/monitor/overview/list` — KPI 概览（咨询人数、响应时长、满意率、咨询率、3分钟人工响应率 等）
- `/csp/api/core/monitor/rank/list` — 客服排名
- `/csp/api/shop/sale/summary/summary.json` — 店铺销售汇总（浏览量/访客/销售额/转化率）
- `/csp/api/shop/sale/summary/chart.json` — 趋势图数据
- `/csp/api/shop/sale/summary/list.json` — 多日列表
- `/csp/api/user/sale/summary/list.json` — 客服个人绩效
- `/csp/api/user/sale/summary/summary.json` — 客服汇总
- `/csp/api/shop/refund/core/chart` — 退款趋势
- `/csp/api/shop/refund/core/summary` — 退款核心指标
- `/csp/api/shop/case/reason/list` — 退款原因明细

每个 KPI 字段格式：`{name, value, mmValue (环比%), yyValue (同行优秀)}`

## 五、技能优化 roadmap（祥书 2026-05-16 确认）

| # | 优化点 | ROI | 状态 |
|---|---|---|---|
| 1 | 拦截 sycm API 直抓 JSON 原始数据 | ⭐⭐⭐⭐⭐ | ✅ 已上线（4/6 页面覆盖核心数据） |
| 2 | 修 iframe 抓取（真实体验分 / 物流洞察）| ⭐⭐⭐⭐ | 待做：用 page.context.on 或 frame-level listener |
| 3 | KPI 时间序列索引（`_kpi_history/<店>/kpis.jsonl`，一行一天）| ⭐⭐⭐⭐ | 待做：写 kpi_extractor.py 解析 _raw_api/ → KPI 表 |
| 4 | 每日健康度报告自动化（自动出"红黄绿灯+行动建议"md）| ⭐⭐⭐⭐ | 待做：写 daily_health_report.py + 飞书同步 |
| 5 | 指标异常告警阈值（满意率<80%/退款率突涨 → 飞书私信）| ⭐⭐⭐ | 待做：方向 3 完成后定阈值 |
| 6 | 修聊天 sender 空 bug（连续消息折叠）| ⭐⭐ | 已在"已知问题"里 |
| 7 | 多店并行 wrapper（`--all` 跑所有已登录店）| ⭐⭐ | 等第 2 家店登录后做 |
| 8 | "服务核心监控" 系统给的客服质检 hint 自动派任务 | ⭐⭐ | 方向 3 完成后做 |
| 9 | Vault → git 自动备份（防 iCloud 丢失）| ⭐ | 视情况 |

### 触发条件
- 方向 2/3 任何时候有空就可做
- 方向 4 在方向 3 数据出来后立刻做（最大价值）
- 方向 5 攒 ≥ 7 天数据后定合理阈值
- 方向 8 写完方向 3、4 后顺手做

## 四、AI 维护本文件的准则

- 发现新的 bug / 数据质量问题 → 加入"已知问题"
- 跑完某个分析 → 在"待开发"对应行更新状态、记本次发现
- 祥书明确"已修复" / "不做了" → 删除对应行
- 每次更新后，更新本文件顶部的"最后维护时间"

**最后维护时间**：2026-05-22（复核"全量 tab 漏抓"实为误判：实测 tab 正常、每天数据少是真实低咨询量；倍视能单店日咨询个位数，扩数据量靠扩店而非修 bug）
