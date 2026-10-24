#!/usr/bin/env python3
"""tone_scan.py — 人生记录成稿腔调病扫描（v2）

扫描四种普通人自传常见腔调病：
  标签腔  「社畜」「小镇做题家」「躺平」……（用标签代替具体）
  概括腔  「就这样吧」「都差不多」「一言难尽」……（拒绝落到场景）
  表演腔  「成年人的崩溃」「后来才明白」「熠熠生辉」……（写给别人看）
  教训腔  「人要……」「吃亏是福」「知足常乐」……（全书超过三处即提示）

词表命中是**提示**，不是判决。引用原话里出现这些词是正常的，
判断标准见 references/tone-rules.md，最终以读出声那一步为准。

用法：
  python tone_scan.py 稿子.md [更多稿子.md ...]
"""

import glob
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

# (病名, 正则)
DISEASES = [
    ("标签腔", r"社畜|打工人|躺平|摆烂|小镇做题家|牛马|韭菜|工具人|佛系|内卷|纯路人|天选"),
    ("概括腔", r"就这样吧|都差不多|没啥特别|没什么特别|挺平常|反正就那样|一言难尽|"
               r"没啥好说|没什么好说|平平淡淡|普通的很|普通得很|记不清了"),
    ("表演腔", r"成年人的崩溃|后来才明白|后来才知道|才懂得|你要相信|愿你|生活不会|"
               r"终将|热爱可抵|人间清醒|情绪价值|松弛感|自洽|熠熠生辉|"
               r"泪目|破防|传奇|伟大的一生|奋斗的一生|平凡而伟大|所有的[^。]{0,8}都是"),
    ("教训腔", r"人要[^。，]{0,8}|人得[^。，]{0,8}|要懂得|要记住|吃亏是福|知足常乐|"
               r"做人要|所以说[^。]{0,10}要|人这一辈子|人这辈子|人活着[^。，]{0,8}|"
               r"还是得[^。，]{0,6}"),
]

LIMIT_NOTE = {"教训腔": 3}
MAX_SHOW = 12


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)

    paths = []
    for arg in sys.argv[1:]:
        hit = glob.glob(arg)
        paths.extend(hit if hit else [arg])

    total = {name: 0 for name, _ in DISEASES}
    findings = {name: [] for name, _ in DISEASES}
    read_ok = 0

    for path in paths:
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            print(f"跳过 {path}: {e}")
            continue
        read_ok += 1
        lines = text.splitlines()
        for name, pattern in DISEASES:
            rx = re.compile(pattern)
            for no, line in enumerate(lines, 1):
                last_end = -1
                for m in rx.finditer(line):
                    if m.start() < last_end:   # 同一句里重叠命中只算一次
                        continue
                    last_end = m.end()
                    total[name] += 1
                    findings[name].append((path, no, m.group(0), line.strip()[:60]))

    if not read_ok:
        sys.exit("没有可读的文件。")

    print("腔调病扫描报告")
    print("=" * 60)
    ok = True
    for name, _ in DISEASES:
        n = total[name]
        cap = LIMIT_NOTE.get(name)
        if n == 0:
            print(f"[ OK ] {name}：0 处")
            continue
        over = cap is None or n > cap
        if over:
            ok = False
        mark = "[ !! ]" if over else "[提醒]"
        suffix = f"（上限 {cap} 处）" if cap else ""
        print(f"{mark} {name}：{n} 处{suffix}")
        for path, no, word, line in findings[name][:MAX_SHOW]:
            print(f"       {path}:{no}  「{word}」  {line}")
        if len(findings[name]) > MAX_SHOW:
            print(f"       …另有 {len(findings[name]) - MAX_SHOW} 处")

    print("=" * 60)
    if ok:
        print("通过。")
        print("还要过两步：1) 读出声，念着别扭的地方就是假话；2) 逐句问「写给别人看还是给自己留的」。")
    else:
        print("未通过。处理建议：")
        print("  标签腔 → 问「哪个瞬间让你这么觉得」，换成具体动作")
        print("  概括腔 → 追一个场景：那天几点起、走的哪条路、吃的什么")
        print("  表演腔 → 删掉形容词和金句，看剩下的是不是事实")
        print("  教训腔 → 找这条道理的出处，还原成故事，道理只留一句原话")
        print("改完重扫。命中不等于错——引用原话里出现这些词是正常的。")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
