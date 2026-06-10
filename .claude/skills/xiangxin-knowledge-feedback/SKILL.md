---
name: xiangxin-knowledge-feedback
version: 1.0.0
description: "祥新公司专用：同事发现好的运营方法/客服话术/工具技巧，让 AI 回传给阿祥的总库（团队知识库升级）。当同事说『回传总库』『这个方法好用，交上去』『这个话术效果好，给阿祥那边也加上』时使用。⚠️ 报错/问题用 xiangxin-problem-report，这里只收『好东西』。"
metadata:
  requires:
    bins: ["lark-cli"]
---

# 知识回传（团队版）

> 你（同事的 AI）把"好东西"整理成结构化记录登记到公司 Base，阿祥侧每周扫描、拍板合并进团队知识库，下次 `git pull` 全团队就都有了。贡献人会署名进 CHANGELOG。

## Step 1：收集信息（缺什么问什么，一次问完）

1. **这是什么**：一句话标题（如"淘宝主图带价签点击率高 1 倍"）
2. **怎么用**：场景 + 具体步骤/话术原文
3. **效果**：最好带数据（转化/点击/省时间），没有就写主观感受
4. **建议放哪**：团队库哪份文档（不知道就让 AI 自己判，写进 AI处理建议）
5. 🔴 **隐私红线**：话术/截图里的客户姓名、手机号、地址、订单号，先删掉或打码再登记

## Step 2：写入 Base

| 项 | 值 |
|---|---|
| base_token | `CWuIblgzqaW7lUsivCBccKSmnqf` |
| table_id | `tblfZ9iO2sqYEWTy` |

```bash
lark-cli base +record-upsert \
  --base-token CWuIblgzqaW7lUsivCBccKSmnqf \
  --table-id tblfZ9iO2sqYEWTy \
  --as user \
  --json '{
    "错误问题场景": "【回传】<一句话标题>",
    "问题具体情况": "<场景 + 步骤/话术原文 + 效果数据>",
    "分类": "知识回传",
    "发现日期": "<今天 YYYY/MM/DD>",
    "发现人": [{"id": "<本人 open_id，见 xiangxin-problem-report 的速查表>"}],
    "优先级": "<高=全团队马上能用 / 中=本岗位通用 / 低=偶尔用得上>",
    "AI处理建议": "<建议合进团队库哪份文档哪一节，怎么改>"
  }'
```

**坑**：参数是 `--json`；upsert 不带 record_id 每次都新建——同一条只跑一次，立刻记下返回的 record_id。

## Step 3：有截图/文件就传附件

```bash
lark-cli base +record-upload-attachment \
  --base-token CWuIblgzqaW7lUsivCBccKSmnqf \
  --table-id tblfZ9iO2sqYEWTy \
  --record-id <Step 2 的 record_id> \
  --field-id fldJGEEUox \
  --file <文件路径>
```

## Step 4：回报同事

给出 record_id + 一句"已回传，阿祥那边每周五统一过，采纳后会署你的名合进团队库"。

## 不要做

- 不要自己改团队知识库的文档（合并是阿祥侧拍板后统一做的，避免总库分裂）
- 不要勾「已入规则」（那是合并完成的标记）
- 客户隐私绝不进表
