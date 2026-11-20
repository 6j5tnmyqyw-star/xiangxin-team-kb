#!/usr/local/bin/python3
# -*- coding: utf-8 -*-
"""查库 —— 输入一个问题，秒返客服知识库里最相关的现成 QA。

跟 kefu_draft.py 的区别：这个【不起草、不调 AI】，纯检索，毫秒级返回库里
现成答案，给销售/客服自己查「这个怎么答」，避免一个个私下重复问。

用法：
  python3 kb_query.py "GFORE的球包有没有送罩子"
  python3 kb_query.py 中秋礼盒 闪送
  echo "客户问的问题" | python3 kb_query.py
"""
import sys

from kefu_draft import retrieve_kb  # 复用同目录副驾的全库检索


def main():
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    elif not sys.stdin.isatty():
        query = sys.stdin.read()
    else:
        print('用法：python3 kb_query.py "客户的问题"', file=sys.stderr)
        sys.exit(2)

    query = query.strip()
    if not query:
        print("✗ 没给问题", file=sys.stderr)
        sys.exit(2)

    hits = retrieve_kb(query, k=5, max_chars=1200, min_score=3.0)
    if not hits:
        print(f"🔎 「{query}」—— 库里没搜到相关内容，换个说法或关键词再试。")
        print("（也可能这条确实没沉淀，问采购/助理后建议补进知识库）")
        return

    print(f"🔎 「{query}」库里最相关的 {len(hits)} 条：")
    for i, (name, txt) in enumerate(hits, 1):
        print("─" * 46)
        print(f"#{i}  〔{name}〕")
        print(txt.strip())
    print("─" * 46)
    print("提示：[配图] 处原文有图，去对应文件/飞书知识库取；要直接起草发客户的话术用 kefu_draft.py")


if __name__ == "__main__":
    main()
