#!/usr/bin/env python3
"""anchor_timeline.py — 岁月锚时间线生成与缺口检查（v2）

输入出生年（可选）与若干条岁月锚，输出：
  1. 按五年分段的时间线（每段列出锚事件与当时年龄）
  2. 各锚反推出生年的一致性校验（误差 >=2 岁标【对不上】）
  3. 空段清单，16 岁后算缺口、16 岁前标可选，附出题建议

用法：
  python anchor_timeline.py --birth 1990 \
      --year "2008:高考" --age "18:高考" \
      --year "2013:入职杭州" --year "2016:搬进拱墅" \
      [--to 2026]

  # 不知道出生年也能用，只是不算年龄、不按出生年对齐分段
  python anchor_timeline.py --year "2008:高考" --year "2019:辞职"

锚的两种写法：
  --year "年份:事件"    直接给公元年
  --age  "年龄:事件"    给当时年龄，脚本反推年份（需要 --birth）
"""

import argparse
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")

SEG_WIDTH = 5          # 五年一段：25-45 岁事件最密，十年会糊成一片
AGE_TOLERANCE = 1      # 各锚反推出生年允许误差（岁），超过即标【对不上】
CHILDHOOD_MAX = 16     # 16 岁以前的空段标「可选」，不算缺口

GAP_HINTS = (
    "问四样：住在哪（城市/小区/几楼）、吃什么（常去的店、谁做饭）、"
    "每天走哪条路（通勤怎么走）、身边有谁（同事几个、谁后来失联了）。"
)


def parse_args():
    p = argparse.ArgumentParser(description="岁月锚时间线生成与缺口检查")
    p.add_argument("--birth", type=int, default=None, help="出生年（不知道可不填）")
    p.add_argument("--year", action="append", default=[],
                   metavar='"年份:事件"', help="公元年锚，可多次")
    p.add_argument("--age", action="append", default=[],
                   metavar='"年龄:事件"', help="年龄锚（当时几岁），可多次")
    p.add_argument("--to", type=int, default=None, help="截止年（默认今年）")
    return p.parse_args()


def parse_anchor(raw, kind, birth):
    """返回 (year, event, derived_birth 或 None)。"""
    try:
        num, event = raw.split(":", 1)
        num = int(num.strip())
        event = event.strip()
    except ValueError:
        sys.exit(f"锚格式错误：{raw!r}（应为 {'年份' if kind == 'year' else '年龄'}:事件）")
    if not event:
        sys.exit(f"锚缺事件：{raw!r}")
    if kind == "year":
        return num, event, None
    if birth is None:
        sys.exit(f"年龄锚 {raw!r} 需要同时给 --birth")
    return birth + num, event, birth


def main():
    args = parse_args()
    birth = args.birth
    this_year = date.today().year
    end = args.to or this_year

    anchors = []
    for raw in args.year:
        y, ev, _ = parse_anchor(raw, "year", birth)
        anchors.append((y, ev, None))
    for raw in args.age:
        y, ev, d = parse_anchor(raw, "age", birth)
        anchors.append((y, ev, d))

    if not anchors:
        sys.exit("至少给一条锚（--year 或 --age）。一条锚都没有，先去收锚。")

    # 同一年同一事件用 --year 和 --age 各报一次时去重
    seen = {}
    for y, ev, d in anchors:
        key = (y, ev)
        if key not in seen or seen[key][2] is None:
            seen[key] = (y, ev, d)
    anchors = sorted(seen.values(), key=lambda a: a[0])

    problems = []

    # ---- 校验：年龄锚反推出生年 ----
    for y, ev, d in anchors:
        if d is not None and abs(d - birth) > AGE_TOLERANCE:
            problems.append(f"  【对不上】{y}「{ev}」按年龄反推出生 {d}，与给定 {birth} 差 {abs(d - birth)} 岁")

    # ---- 校验：年份范围 ----
    for y, ev, _ in anchors:
        if y < 1900 or y > this_year:
            problems.append(f"  【对不上】{y}「{ev}」不在合理范围内（1900—{this_year}）")
        elif birth is not None and y < birth:
            problems.append(f"  【对不上】{y}「{ev}」早于出生年 {birth}")
        elif y > end:
            problems.append(f"  【提示】{y}「{ev}」晚于时间线截止年 {end}，已按截止年收口")

    # ---- 校验：同一事件钉在两个年份 ----
    by_event = {}
    for y, ev, _ in anchors:
        by_event.setdefault(ev, set()).add(y)
    for ev, years in by_event.items():
        if len(years) > 1:
            ys = "、".join(str(y) for y in sorted(years))
            problems.append(f"  【两说】「{ev}」被钉在 {ys} 两个年份——两个都留，问先后，不问哪年")

    # ---- 五年分段 ----
    years_only = [y for y, _, _ in anchors if y <= end]
    if not years_only:
        sys.exit("所有锚都晚于截止年，没法分段。")

    if birth is not None:
        seg_start = birth
    else:
        seg_start = (min(years_only) // SEG_WIDTH) * SEG_WIDTH

    buckets = {}
    for y, ev, _ in anchors:
        if y > end:
            continue
        buckets.setdefault((y - seg_start) // SEG_WIDTH, []).append((y, ev))

    print(f"讲述者：{f'{birth} 年生' if birth else '出生年未提供'}")
    print(f"时间线：{seg_start} — {end}，共 {len(anchors)} 条锚，{SEG_WIDTH} 年一段\n")
    print("=" * 60)

    gaps = []
    optional = []
    i = 0
    while True:
        lo = seg_start + i * SEG_WIDTH
        hi = lo + SEG_WIDTH - 1
        if lo > end:
            break
        hi = min(hi, end)
        items = buckets.get(i, [])
        if birth is not None:
            alo, ahi = lo - birth, hi - birth
            head = f"{lo}—{hi}（{alo}—{ahi} 岁）"
        else:
            head = f"{lo}—{hi}"

        if not items:
            print(f"\n{head}")
            if birth is not None and ahi < CHILDHOOD_MAX:
                print("  （可选：这一段没有锚，童年记忆稀薄属正常，不必强补）")
                optional.append((head, lo, hi))
            elif hi >= this_year:
                print("  （进行中：这一段还在过，没有锚属正常）")
                optional.append((head, lo, hi))
            else:
                print("  （缺口：这一段一个锚都没有）")
                gaps.append((head, lo, hi))
        else:
            print(f"\n{head}  ◆ {len(items)} 条锚")
            for y, ev in items:
                age = f"（{y - birth} 岁）" if birth is not None else ""
                print(f"    {y}  {ev}{age}")
        i += 1

    print("\n" + "=" * 60)
    if problems:
        print("校验发现问题：")
        for m in problems:
            print(m)
        print("→ 把对不上的两件事摆在一起问先后，不问年份。")
    else:
        print("校验：各锚一致，无冲突。")

    if gaps:
        print(f"\n缺口 {len(gaps)} 段（建议补）：")
        for head, _, _ in gaps:
            print(f"  · {head}")
        print(f"  {GAP_HINTS}")
    else:
        print("\n无缺口。可以进入成稿，或补薄段（只有一条锚的阶段）。")

    if optional:
        print(f"\n可选段 {len(optional)} 段（不强求，想写再写）：")
        for head, _, _ in optional:
            print(f"  · {head}")


if __name__ == "__main__":
    main()
