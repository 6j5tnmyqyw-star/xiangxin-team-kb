---
name: xiangxin-replenish-advisor
version: 1.0.0
employee: kg
description: "祥新公司专用·补货建议：基于吉客云库存快照，算出该补哪些货、补多少、找谁拿。按动销速度分级（超卖急补/7天内断货/提醒/备货），并把『可用为负但不动销』的对账问题单独挑出来给库管核对。当祥书或库管说『该补什么货』『有哪些要断货了』『生成补货建议/补货清单』『哪些 SKU 要补货』『跑一下补货』时使用。"
metadata:
  requires:
    bins: ["python3"]
  python: "/usr/bin/python3"
  optional_skills: ["xiangxin-supplier-finder", "jackyun-inventory-weekly", "jackyun-api"]
---

# 库管·补货建议（replenish-advisor）

> 库存周报看"现在有多少、占了多少钱"；本 skill 进一步回答"**该补哪些、补多少、找谁拿**"。

## 一、什么时候用

- 「该补什么货 / 哪些要断货了 / 生成补货建议 / 补货清单 / 跑一下补货」
- 库存周报跑完后想接着出补货动作

**不适用**：
- 只想看库存现状/资金占用/滞销 → [[jackyun-inventory-weekly]]（库存周报）
- 单 SKU 实时库存/销量 → [[jackyun-api]]

## 二、前置：要有两份库存快照

补货建议靠**两份快照的净出库**估算动销，所以 `99-附件/吉客云导出/` 里至少要有 2 份 `YYYY-MM-DD-总库存查询.xlsx`。
- 没有 / 只有一份 → 先跑 [[jackyun-inventory-weekly]] 导一份（或用 [[jackyun-api]] 拉库存）。
- 两份间隔越规整越准（理想 7 天一份）。

## 三、运行

```bash
VAULT="/Users/mac/obsidian/祥子AI"
/usr/bin/python3 "$VAULT/07-AI协作/skills/xiangxin-replenish-advisor/advise.py"
# 默认自动取最新两份快照。也可指定：advise.py 本期.xlsx 上期.xlsx
```

输出：`_待整理/YYYY-MM-DD-补货建议.md`（归档进程会移到 `03-公司/库存分析/补货建议/`）。
跑完把摘要 + 🔴急补表念给祥书，完整报告给链接。

## 四、报告分档（怎么读）

| 档 | 含义 | 动作 |
|---|---|---|
| 🔴 超卖急补 | 可用为负**且**仍在动销 | 立刻补，先补平超卖 |
| 🔴 紧急 | 7 天内可能断货 | 尽快下单 |
| 🟡 提醒 | 7–14 天可售 | 本周安排 |
| 🟢 备货 | 14–21 天可售（列占款 Top 20） | 计划内备货 |
| ⚠️ 负库存待核 | 可用为负**但近期不动销** | **不是补货** → 多为对账/盘点问题，交库管去吉客云核对 |

每行给「建议补货量」「预估占款」「找谁拿」（主力供应商；多家比价用 [[xiangxin-supplier-finder]]）。

## 五、口径与可调参数

- **动销估算**：`期间净出库 = 上期库存数量 - 本期库存数量`（>0 部分），日均 = 净出库 / 间隔天数。
  - ⚠️ 吉客云导出的「支撑天数」字段公司基本没维护（2 万 SKU 里只有 ~200 个非空），所以**不用它**，自己算。
  - 窗口短（如 6 天）时单件波动就会放大，结果**仅供参考**；积累更多快照后更稳。
- **排除**：货品名含「二手球」（回收货）、「清仓」（正在清）的不进补货。
- 脚本顶部 CONFIG 可调：
  - `TARGET_COVER_DAYS=30`：补到能卖多少天
  - `T_URGENT=7 / T_WARN=14 / T_WATCH=21`：分档阈值
  - 改完直接重跑即可。

## 六、升级路径（更准的动销）

当前用快照差估动销，窗口短。要更准：用 [[jackyun-api]] 拉近 30 天**真实销售订单**算日均销量，替换脚本里的「期间净出库」估算。届时单份快照（看可用库存）+ API 销量就够，不必依赖两份快照。

## 七、文件位置

| 内容 | 位置 |
|---|---|
| 本 skill | `07-AI协作/skills/xiangxin-replenish-advisor/SKILL.md` |
| 脚本 | 同目录 `advise.py` |
| 库存快照源 | `99-附件/吉客云导出/*-总库存查询.xlsx` |
| 输出 | `_待整理/YYYY-MM-DD-补货建议.md` → `03-公司/库存分析/补货建议/` |
| 供应商对应 | [[xiangxin-supplier-finder]] / `03-公司/供应商/00-供应商信息汇总.md` |

## 八、维护

- 新品牌主力供应商：改 `advise.py` 的 `PRIMARY_SUPPLIER` 字典。
- 品牌识别规则：改 `BRAND_PATTERNS`（与 jackyun-inventory-weekly 保持一致）。
