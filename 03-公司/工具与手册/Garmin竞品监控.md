# Garmin竞品监控脚本使用说明

> 📦 已收录为公司技能：`.claude/skills/taobao-price-monitor/SKILL.md`（v1.1+）
> 给 AI 跑直接说"跑一下淘宝比价 / 跑竞品监控"，会自动调这个 skill。

脚本路径：`~/garmin_monitor.py`
监控产品：Garmin **S70 / G82 / R50 / Z30**
数据来源：淘宝搜索（按销量排序）
输出：飞书多维表格（**只写异常价**，正常价过滤掉）

**多维表格地址**：https://xiangxingolf.feishu.cn/base/KkWWbX5goaoMKrsDcOvcb2Emn2d

---

## 一、运行命令

每次运行前**完全退出 Chrome**（`Cmd+Q`，不是只关窗口），然后：

```bash
/usr/local/bin/python3 ~/garmin_monitor.py
```

> ⚠️ 必须用 `/usr/local/bin/python3`（Python 3.15），不能用系统自带的 `python3`（缺依赖）。

---

## 二、当前配置（已写入脚本）

| 项目            | 值                             |
| ------------- | ----------------------------- |
| App ID        | `cli_a977681a7d389bc1`        |
| App 名称        | 邹祥书的飞书 CLI                    |
| Bitable Token | `KkWWbX5goaoMKrsDcOvcb2Emn2d` |
| 数据表 ID        | `tbl5JSiMcOVd2eMa`            |
| 数据表名          | Garmin竞品                      |

> 应用已被授予该 Base 的「可管理」权限，写入链路已测试通过。

---

## 三、首次设置回顾（已完成，存档备查）

1. **依赖安装**
   ```bash
   /usr/local/bin/python3 -m pip install lark-oapi
   ```
   selenium / selenium-stealth 已存在。

2. **多维表格 + 字段** 通过 lark-cli 自动建好（9 列）。

3. **应用授权**
   ```bash
   lark-cli auth login --scope "docs:permission.member:create drive:drive bitable:app"
   lark-cli api POST /open-apis/drive/v1/permissions/<base_token>/members \
     --params '{"type":"bitable","need_notification":false}' \
     --data '{"member_type":"appid","member_id":"cli_a977681a7d389bc1","perm":"full_access","perm_type":"container"}' \
     --as user
   ```

---

## 四、首次运行流程

1. 完全退出 Chrome（Cmd+Q）
2. 跑脚本：`/usr/local/bin/python3 ~/garmin_monitor.py`
3. 脚本会自动复制 Chrome 配置 → 启动浏览器 → 打开淘宝
4. 若未登录，脚本暂停，你扫码登录后回终端按回车
5. 脚本依次搜 4 个型号，每个抓前 15 条
6. 数据自动写入飞书多维表格

---

## 五、调整参数

编辑 `~/garmin_monitor.py` 顶部配置区：

| 参数        | 默认值 | 说明                       |
|-------------|--------|----------------------------|
| `KEYWORDS`  | 4 个型号 | 增删监控的关键词           |
| `TOP_N`     | 15     | 每个型号抓前几条           |
| `PAGE_WAIT` | 10     | 每页等待秒数（太快会风控） |

---

## 六、风控处理

脚本检测到 rgv587 风控时会暂停，**用淘宝 App 扫屏幕上的二维码**，完成后回终端按回车继续。

---

## 七、注意事项

- 频次：建议 **每天 1 次**，不要小时级频跑
- 到手价：依赖淘宝页面显示，没有时取原价
- 选择器失效：淘宝改版后更新 `~/garmin_monitor.py` 里的 `CARD_SELECTORS / FINAL_SEL` 等
- 测试记录：表里有一条 `model=TEST` 的测试数据，可以直接删

## 七·五、异常价过滤（v1.1）

**铁律**：大家价格都一样的就是正常价，不写入飞书。脚本会按型号分组、用中位数当基准，偏离 ≤ 3% 视为正常价丢弃，> 3% 才写入。

| 参数 | 默认 | 含义 |
|---|---|---|
| `NORMAL_PRICE_TOLERANCE` | 0.03 | 偏离中位数 ≤ 3% → 丢弃 |
| `MIN_RECORDS_FOR_FILTER` | 3 | 样本少于 3 条不过滤，全写入 |

效果：当天某型号若全网价格一致，飞书里那天该型号就是 0 条；只要有 1 家串货低价，那一条会被记下来。

---

## 八、查看历史

每次运行后所有记录会**追加**到表里，靠「采集时间」列区分批次。

在飞书多维表格里：
- 视图 → 添加分组 → 按「采集时间」分组 → 每天数据自然分组
- 视图 → 筛选 → 「型号 = S70」→ 看单一型号历史价格走势
