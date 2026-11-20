---
name: xiangxin-problem-report
version: 1.0.0
description: "祥新公司专用：同事把工作中的报错/问题（通常带截图）告诉 AI，AI 登记到公司【纠错日志 Base】并 @ 处理人。当同事说『登记一下这个问题』『这个报错帮我记到纠错日志』『截图你看下，记一条』时使用。⚠️ 只登记新问题；处理已有记录的交付走 xiangxin-problem-delivery。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# 纠错日志登记（团队版）

> 对应公司规则 005「错误登记流程」。你（AI）替同事把表填全，别让同事手动进 Base 一格一格填。

## Step 0：先分流，别什么都进表

- **❌ 紧急/有时效**（今天不解决就影响出单、发货、客诉、上下架）→ 不进表，提醒同事直接飞书 @ 对应人现场处理。
- **✅ 进表**：没时效性 / 一下子不好处理 / 需多方协调的流程性问题，以及 AI 错答、重复性失误。

## Step 1：收集信息

向同事确认（缺什么问什么，一次问完）：

1. **发生了什么**（一句话）+ 背景细节
2. **截图**：⚠️ 必须以**文件**形式给——拖文件进对话框，或告知文件路径。纯粘贴的图 AI 看得见但拿不到文件、传不上 Base。
3. 🔴 **隐私红线**：截图/描述里有客户姓名、手机号、地址、订单号的，先裁掉或打码再登记。

## Step 2：写入 Base（一次填全）

| 项 | 值 |
|---|---|
| base_token | `CWuIblgzqaW7lUsivCBccKSmnqf` |
| table_id | `tblfZ9iO2sqYEWTy` |

AI 自己先判好：**分类**（9 选 1：订单物流/客服售后/商品价格/成本采购/内容创作/AI工具/团队管理/流程规则/规则建议修改）、**优先级**（高=立即/中=本周/低=有空）、**评分**（1-10）、**期望交付时间**（高=当天 / 中=本周末 / 低=两周内）、**AI处理建议**（给处理人的解题思路）。

> 对现有规则/SOP 提修改建议的，分类选「**规则建议修改**」——阿祥每周五会专门扫这一类来更新规则。

```bash
lark-cli base +record-upsert \
  --base-token CWuIblgzqaW7lUsivCBccKSmnqf \
  --table-id tblfZ9iO2sqYEWTy \
  --as user \
  --json '{
    "错误问题场景": "<一句话标题>",
    "问题具体情况": "<背景/细节/原话>",
    "分类": "<9选1>",
    "发现日期": "<今天 YYYY/MM/DD>",
    "发现人": [{"id": "<本人 open_id，见下表>"}],
    "处理人": [{"id": "ou_xxx"}],
    "优先级": "中",
    "评分": 6,
    "期望交付时间": "<YYYY/MM/DD HH:mm>",
    "AI处理建议": "<解题思路/规则化建议>"
  }'
```

**坑（都踩过，别再踩）**：
- 参数是 `--json` 不是 `--fields`；没有 `+record-create`，新建就走 `+record-upsert`
- 不带 record_id 的 upsert **每次都新建、不去重**——同一条只跑一次，立刻抓 `.data.record.record_id_list[0]` 记下 record_id，别因为没看到输出就重跑
- 新记录索引有几秒延迟，刚写完 `+record-search` 可能搜不到，不代表没写进去

**处理人怎么填**：同事描述里 @ 谁 / 说"该谁管"就填谁（可多选）；不知道派给谁就不填，Step 4 评论里 @ 阿祥定。阿祥本人不加进处理人。

**open_id 速查**：

| 人 | open_id |
|---|---|
| 邹祥书（阿祥） | `ou_ed1dba4721b4aae7f7f0a96ebf37b63c` |
| 何小琴（荔枝） | `ou_14bf1279a6115f36cf5e98746e138f8a` |
| 王娜（娜娜） | `ou_f4d78367e15db6628b2a5ff71218bfc7` |
| 洪丽华（洪洪） | `ou_655d3dd4590eb9baa9415596bba31ce3` |
| 于嘉欣（嘉欣） | `ou_ab49258dc68e351d1bf1cbdf24b0c622` |
| 孙庆弘（老孙） | `ou_047bb1745d4d61c3430023d8eb545e5c` |
| 朱凌晨 | `ou_f942122bf5205126653f41e4ebec4cb5` |
| 王珊（珊珊） | `ou_7d255dd02750fd6f78d5a990549ed8a6` |
| 王月阳（月阳） | `ou_8d94d080d69538216ce3b7f9b5ad7faa` |
| 兰月（月月） | `ou_a0aaf562b5da54ae4dde72b516ad0068` |
| 罗舒怡（舒怡） | `ou_a4623a2063aba67870735f004eaa06e6` |
| 罗姣阳（阳阳） | `ou_bf5633d19f4f6a21aa17ba707384e56c` |
| 袁桂平（九一） | `ou_e81614cb874657f1ab61ad147c244717` |
| 赵素青（彭彭） | `ou_82b5f1d92081eabb41f84fd639e7eee0` |
| 张桐（同同） | `ou_91a16b28f0e5bb91c07d93061099f587` |
| 徐鹤（鹤子） | `ou_f972473873fc9088193de4ed88eabfed` |
| 许建华（华华） | `ou_acf3f337f4aa9b143e7fcf85e57d4b08` |
| 李秀娟（阿娟） | `ou_60ef4fee66aca6a594337ad58db27773` |

不在表里的人：`lark-cli contact +search-user --query "<名字>" --as user`

## Step 3：传截图

```bash
lark-cli base +record-upload-attachment \
  --base-token CWuIblgzqaW7lUsivCBccKSmnqf \
  --table-id tblfZ9iO2sqYEWTy \
  --record-id <Step 2 返回的 record_id> \
  --field-id fldCUzhQM2 \
  --file <截图文件路径>
```

（`截图附件`=`fldCUzhQM2`；交付物附件用 `附件交付`=`fldJGEEUox`）

## Step 4：评论 @ 处理人（必须，公司规则 003）

只填字段不算登记完成。在该 record 下发评论 @ 处理人，一句话写清"请 TA 做什么 / 期望什么时候反馈"。不知道派给谁就评论 @ 阿祥（邹祥书）让他定。

## Step 5：回报同事

给出 record_id + 摘要（分类/优先级/处理人），并提醒：优先级"高"的问题要当天另行告知阿祥。

## 不要做

- 不要勾「已入规则」（阿祥周五汇总的活）
- 不要拉全表"看看以前有没有"
- 不要把临时讨论当问题记；只记会重复、需约束、需交付的
- 客户隐私（姓名/手机号/地址/订单号）绝不进表
