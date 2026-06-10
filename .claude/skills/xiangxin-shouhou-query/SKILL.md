---
name: xiangxin-shouhou-query
description: 祥新公司专用·网店售后单查询——查某商品/品牌/店铺最近的售后单(退款/退货/换货)：多少单、什么原因、哪个店、退了多少钱，给客服(迎客)和运营自助查，辅助售后话术与选品。数据来自吉客云「网店售后单查询」。当祥书或客服说『查下XX的售后』『FIT39手套有哪些退货/退款』『这个品牌/商品售后多吗』『最近售后啥情况』『XX店退款多少』『某单号的售后』时使用。
---

# 网店售后单查询（xiangxin-shouhou-query）

给客服(迎客)/运营自助查某商品·品牌·店铺的售后情况——多少单、什么原因、退多少钱——辅助售后话术和选品决策。数据源 = 吉客云「网店售后单查询」。

## 一、快速查（数据已导出时，最常用）

```bash
cd 07-AI协作/skills/xiangxin-shouhou-query
python3 query_aftersale.py --keyword FIT39                 # 查某品牌/商品
python3 query_aftersale.py --keyword 手套 --type 退货 --days 30
python3 query_aftersale.py --shop 京东FIT39 --reason 质量    # 某店、某原因
python3 query_aftersale.py --order 51164177XXXXXXXXXXX     # 按单号查
```

参数：`--keyword`(商品/品牌，逗号分隔多个)｜`--shop`(店铺)｜`--type`(退款/退货/换货/维修/补寄)｜`--reason`(退款原因)｜`--order`(网店订单号)｜`--days`(近N天)｜`--limit`(明细条数，默认50)
不带参数 = 看全表概览。默认自动读 `~/Downloads` 或归档目录里最新的「网店售后单*.xlsx」。

输出：命中明细(按单号去重) + 洞察(售后类型分布 / 退款原因Top5 / 店铺分布 / 处理状态 / 退款金额合计)。

### 归因分析·哪些是「我们的问题」（analyze_problems.py）
```bash
python3 analyze_problems.py                     # 全表
python3 analyze_problems.py --from 2026-01-01    # 今年至今
python3 analyze_problems.py --shop 京东祥新       # 限某店
```
把售后按退款原因归四类：**我们的问题**(质量/发错漏发/缺货/发货超时/描述不符)、**尺码引导**(半我们)、**买家主观**(不想要/拍错/7天无理由)、**中性/财务**(赠品/协商/价保)。输出：四类占比 → 我们的问题子类明细(单数/金额/店铺/典型商品) → 尺码问题涉及品牌 → 各店铺「我们的问题」排行。归因规则在脚本顶部 `RULES`，可改。

### 售后率对比·卖 vs 退（compare_sales.py）
```bash
python3 compare_sales.py --keyword FIT39,手套,GFORE        # 多个分别对比
python3 compare_sales.py --keyword 手套 --from 2026-01-01 --to 2026-05-21
```
同期「卖多少单 vs 退几单」算售后率。销量来自 `03-公司/财务数据/吉客云销售/原始明细/jky_销售明细_*.csv`(按货品摘要匹配、订单去重)。⚠️ 销量 csv 更新可能滞后，看输出「实际覆盖到」提示、对齐 `--to` 更准。

## 二、数据怎么来（两条路）

### 路1 · 手动导出（当前可用）
1. 吉客云顶部搜索框搜「网店售后单查询」打开页面，时间筛选确认是「近一个月」（或你要的范围）
2. 点 **【导出 → 导出所有页 → 合并导出(主表和明细在同一行)】** — 共三下
3. 文件**即时**下载到 `~/Downloads/网店售后单.xlsx`（不是异步下载中心）
4. 跑 `query_aftersale.py` 查询

> ⚠️ **为什么这一步要手动**：实测确认，吉客云导出按钮只认**真实硬件点击**，browser-harness/CDP 的合成鼠标事件点不开这个 mini 菜单（hover 子菜单可合成、但顶层按钮的 click 不行）。所以「点导出」得人来点，其余(解析/查询/归档)全自动。
> `export_aftersale.py` 跑起来会帮你：聚焦售后页 + 关掉吉客云的业务提醒弹窗 + 导出后自动把文件归档到 vault；它会停在「请手动点导出」处等你点完三下，再自动接管归档。

### 路2 · jky-cli API（无人值守正解，★推荐升级，待配凭证）
接口 **`omsapi-business.refund.listRefund`（分页查询网店售后单）** 已确认存在，配好凭证即可无人值守定时拉，不用开浏览器、不用手点。
- **前置**：祥书先在终端 `jky-cli configure`，填吉客云开放平台的 AppKey/AppSecret（目前未配，所以暂走路1）
- 配好后告诉我，我补 `refund_api.py`：
  - 入参：`createTimeBegin/createTimeEnd`(退款申请时间)、`refundType`(0退款/1退货/2换货/3补寄)、`shopId`(渠道)、`platOrderNo`(订单号)、`refundNo`(售后单号)、`pageInfo`(分页)
  - ⚠️ 接口**没有商品名/品牌查询参数**，品牌(如 FIT39)只能在返回结果里客户端过滤
  - 返回剥 `result.data.data`

## 三、数据坑（改脚本前必读）
- 吉客云导出的 xlsx，**dimension 标签不准**：openpyxl 必须用**完整模式**(`load_workbook(path)`，不能 `read_only=True`)，否则只读到 1 行表头。
- 「合并导出(主表和明细在同一行)」= 23列，每行是**一个货品明细**+所属售后单的主表字段；**一个售后单可能多行**(多货品)，query 已按「网店订单号」去重。
- 日期范围偶尔**混入个别历史脏数据**(如某条 2021 的退款最近才有动作)，看输出「数据覆盖」行判断，主体是近一个月。
- 用**脱敏版**(就是「合并导出(主表和明细在同一行)」，非「明文」版)，不含买家姓名/手机/地址；输出里的订单号是内部核对用(符合隐私铁律——隐私只指人事，订单号/商品/金额不算)。

## 四、关联
- **客服售后话术起草** → [[xiangxin-yingke-kefu]]（迎客副驾：处理售后问题时，先用本 skill 查该商品的历史售后情况——主因是质量还是尺码/不想要——再据此起草话术）
- 吉客云其他 API/数据 → [[jackyun-api]]
