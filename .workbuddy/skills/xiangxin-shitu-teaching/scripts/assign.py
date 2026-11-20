#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
师徒教学·派学一键脚本
给某个【师傅→徒弟】派一个「学会某个 AI 技能/操作」的教学任务：
  ① 建飞书任务（assignee=徒弟，follower=师傅，挂【祥新任务】清单）
  ② 在「师徒教学台账」Base 写一条记录（含交付方式/验收标准/任务链接）
交付方式按【类型】自动定：操作类→截图，方法类→文档。

用法:
  python3 assign.py --shifu 娜娜 --tudi 嘉欣 --content "用迎客客服副驾起草询单回复" \
      --type 操作类 --days 3 [--note "..."] [--dry-run]
"""
import argparse, json, subprocess, sys, datetime, hashlib

BASE_TOKEN = "EZjsb727JaMQklshxFdcUzC7nNd"
TABLE_ID   = "tblsKb81VpiyNHl3"
TASKLIST   = "a1b4297b-0a7a-4b0e-8748-e0b75ae15485"  # 【祥新任务】

# 别名/真名 -> open_id（2026-05-25 核对）
PEOPLE = {
    "祥书":"ou_ed1dba4721b4aae7f7f0a96ebf37b63c","阿祥":"ou_ed1dba4721b4aae7f7f0a96ebf37b63c","邹祥书":"ou_ed1dba4721b4aae7f7f0a96ebf37b63c",
    "荔枝":"ou_14bf1279a6115f36cf5e98746e138f8a","何小琴":"ou_14bf1279a6115f36cf5e98746e138f8a",
    "娜娜":"ou_f4d78367e15db6628b2a5ff71218bfc7","王娜":"ou_f4d78367e15db6628b2a5ff71218bfc7",
    "红红":"ou_655d3dd4590eb9baa9415596bba31ce3","洪洪":"ou_655d3dd4590eb9baa9415596bba31ce3","洪丽华":"ou_655d3dd4590eb9baa9415596bba31ce3",
    "嘉欣":"ou_ab49258dc68e351d1bf1cbdf24b0c622","于嘉欣":"ou_ab49258dc68e351d1bf1cbdf24b0c622",
    "老孙":"ou_047bb1745d4d61c3430023d8eb545e5c","孙庆弘":"ou_047bb1745d4d61c3430023d8eb545e5c","庆弘":"ou_047bb1745d4d61c3430023d8eb545e5c",
    "凌晨":"ou_f942122bf5205126653f41e4ebec4cb5","朱凌晨":"ou_f942122bf5205126653f41e4ebec4cb5",
    "王珊":"ou_7d255dd02750fd6f78d5a990549ed8a6","珊珊":"ou_7d255dd02750fd6f78d5a990549ed8a6",
    "罗舒怡":"ou_a4623a2063aba67870735f004eaa06e6","舒怡":"ou_a4623a2063aba67870735f004eaa06e6","罗淑怡":"ou_a4623a2063aba67870735f004eaa06e6",
    "罗姣阳":"ou_bf5633d19f4f6a21aa17ba707384e56c","阳阳":"ou_bf5633d19f4f6a21aa17ba707384e56c","罗骄阳":"ou_bf5633d19f4f6a21aa17ba707384e56c",
    "华华":"ou_acf3f337f4aa9b143e7fcf85e57d4b08","许建华":"ou_acf3f337f4aa9b143e7fcf85e57d4b08",
    "海英":"ou_221a1f81dc2e230fe73b2556185c7156","姜海英":"ou_221a1f81dc2e230fe73b2556185c7156",
    "月月":"ou_a0aaf562b5da54ae4dde72b516ad0068","兰月":"ou_a0aaf562b5da54ae4dde72b516ad0068",
    "月阳":"ou_8d94d080d69538216ce3b7f9b5ad7faa","王月阳":"ou_8d94d080d69538216ce3b7f9b5ad7faa","月牙":"ou_8d94d080d69538216ce3b7f9b5ad7faa",
}
# 规范名（写台账时显示用）
CANON = {
    "阿祥":"祥书","邹祥书":"祥书","何小琴":"荔枝","王娜":"娜娜","红红":"洪洪","洪丽华":"洪洪",
    "于嘉欣":"嘉欣","孙庆弘":"老孙","庆弘":"老孙","朱凌晨":"凌晨","珊珊":"王珊",
    "舒怡":"罗舒怡","罗淑怡":"罗舒怡","阳阳":"罗姣阳","罗骄阳":"罗姣阳","许建华":"华华","姜海英":"海英",
    "兰月":"月月","王月阳":"月阳","月牙":"月阳",
}
# 师傅 -> [徒弟]（规范名，用于校验师徒关系）
# 2026-06-03 调整：荔枝直接带嘉欣+洪洪（嘉欣从娜娜名下上移）；娜娜名下留老孙
TREE = {
    "祥书":["荔枝"], "荔枝":["嘉欣","洪洪","娜娜"], "娜娜":["老孙"],
    "洪洪":["凌晨","王珊"], "嘉欣":["罗舒怡","罗姣阳"], "老孙":["华华","海英"],
    "王珊":["月月","月阳"],
}

def canon(name): return CANON.get(name, name)
def oid(name):
    if name not in PEOPLE:
        sys.exit(f"[错] 不认识的人名「{name}」，请用花名册里的名字，或先把人加进 PEOPLE 表。")
    return PEOPLE[name]

def run(cmd, stdin=None):
    r = subprocess.run(cmd, input=stdin, capture_output=True, text=True)
    if r.returncode != 0 and not r.stdout.strip():
        sys.exit(f"[错] 命令失败: {' '.join(cmd)}\n{r.stderr}")
    # 剥掉 lark-cli 的 proxy WARN 行，取 JSON
    out = "\n".join(l for l in r.stdout.splitlines() if not l.startswith("[lark-cli]"))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shifu", required=True, help="师傅（花名/真名）")
    ap.add_argument("--tudi",  required=True, help="徒弟（花名/真名）")
    ap.add_argument("--content", required=True, help="学什么 AI 技能/操作")
    ap.add_argument("--type", required=True, choices=["操作类","方法类"], help="操作类→截图交付 / 方法类→文档交付")
    ap.add_argument("--days", type=int, default=3, help="期望几天内学会，默认3")
    ap.add_argument("--note", default="", help="备注")
    ap.add_argument("--force", action="store_true", help="师徒关系不在标准树里时也强制派")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    shifu, tudi = canon(a.shifu), canon(a.tudi)
    deliver = "截图" if a.type == "操作类" else "文档"
    rubric = ("操作截图：把整个操作过程+最终结果截图发上来，证明你独立做对了一遍。"
              if a.type=="操作类" else
              "总结文档：用自己的话写清这套打法的步骤/要点/坑，证明你不仅会用、还能教下一个人。")
    # 校验师徒关系
    if not a.force and tudi not in TREE.get(shifu, []):
        print(f"[提醒] 标准师徒树里『{shifu}』不带『{tudi}』。当前 {shifu} 的徒弟={TREE.get(shifu,[])}。"
              f"确认无误请加 --force。", file=sys.stderr)
        sys.exit(2)

    today = datetime.date.today()
    due   = today + datetime.timedelta(days=a.days)
    due_str = f"{due.isoformat()} 18:00:00"

    summary = f"【师徒教学】学会：{a.content}"
    desc = (f"师傅：{shifu}　徒弟：{tudi}\n"
            f"学习内容：{a.content}\n"
            f"类型：{a.type}　交付方式：{deliver}\n"
            f"期望完成：{due.isoformat()} 前\n\n"
            f"【交付标准】{rubric}\n"
            f"流程：师傅教+带 → 你自己练 → 按上面方式交付凭证 → 师傅验收。师傅只带不替你做，交付必须你本人完成。")

    ctok = "shitu-" + hashlib.md5(f"{shifu}-{tudi}-{a.content}-{today}".encode()).hexdigest()[:16]
    task_json = json.dumps({
        "summary": summary, "description": desc, "mode": 1,
        "members": [{"id": oid(tudi), "role":"assignee"}, {"id": oid(shifu), "role":"follower"}],
        "tasklists": [{"tasklist_guid": TASKLIST}],
        "client_token": ctok,
    }, ensure_ascii=False)

    if a.dry_run:
        print("=== DRY RUN ===")
        print("飞书任务 payload:\n", task_json)
        print(f"\n台账记录: 学习内容={a.content} 师傅={shifu} 徒弟={tudi} 类型={a.type} 交付方式={deliver} 状态=待学 派学日期={today} 期望完成={due}")
        return

    # ① 建飞书任务
    out = run(["lark-cli","task","tasks","create","--as","user","--data","-"], stdin=task_json)
    try:
        task = json.loads(out)["data"]["task"]
        guid, url = task["guid"], task.get("url","")
    except Exception:
        sys.exit(f"[错] 建任务返回解析失败:\n{out}")
    print(f"✅ 飞书任务已建: {guid}\n{url}")

    # ② 写台账 Base
    rec = {
        "学习内容": a.content,
        "师傅": [{"id": oid(shifu)}],
        "徒弟": [{"id": oid(tudi)}],
        "类型": a.type,
        "交付方式": deliver,
        "状态": "待学",
        "派学日期": f"{today.isoformat()} 00:00:00",
        "期望完成": due_str,
        "飞书任务": url,
    }
    if a.note: rec["备注"] = a.note
    out2 = run(["lark-cli","base","+record-upsert","--as","user",
                "--base-token",BASE_TOKEN,"--table-id",TABLE_ID,
                "--json", json.dumps(rec, ensure_ascii=False)])
    ok = '"ok": true' in out2 or '"created"' in out2
    print("✅ 台账已登记" if ok else f"⚠️ 台账写入存疑:\n{out2}")
    print(f"\n师傅 {shifu} → 徒弟 {tudi}｜{a.content}｜{a.type}/{deliver}｜{a.days}天内（{due}）")

if __name__ == "__main__":
    main()
