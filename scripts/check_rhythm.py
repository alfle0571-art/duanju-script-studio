#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""短剧节奏时间轴检查器。

用法:
    python check_rhythm.py <时间轴文件> [--mode full|comedy|romance|suspense|light]

输入格式（每行一个锚点）:
    00:06 | 巴掌 | 女主一句话把婆婆噎在原地

检查: 锚点齐全度、空档长度、呼吸段周期、类型单调、字面暴力、未填占位符、未知类型、
      时间轴乱序、重复锚点、单集时长上限。
退出码: 0 = 可交付（可带 WARN）；1 = 存在 ERROR（缺必需锚点、反转后缺呼吸段或无法解析）。

口径: 张力轴（冲突 / 爆点 / 巴掌位）按全局空档衡量；喜剧轴按周期；反转按 30 秒周期、
      容差 45 秒，且把「最后一个反转到片尾」计入，防止只在开头排一个反转。

这是辅助检查，不替代 `09-rhythm-grid.md` 里的创作判断。
"""

import argparse
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 竖线同时吃半角 | 与全角 ｜：中文输入法默认产出全角，旧版只认半角，
# 整份时间轴会「一个锚点都解析不到」。时间冒号同理
LINE = re.compile(r"^\s*(\d{1,2})[:：](\d{2})\s*[|｜]\s*([^|｜]+?)\s*[|｜]\s*(.+?)\s*$")
# 只写了一列分隔的「分:秒｜内容」：细纲动作节点的写法，不是三列时间轴
NEAR = re.compile(r"^\s*\d{1,2}[:：]\d{2}\s*[|｜]\s*\S")

ALIASES = {
    "钩子": "hook", "开场钩子": "hook", "反常理钩子": "hook",
    "结尾钩子": "ending",
    "冲突": "conflict", "冲突升级": "conflict",
    "爆点": "burst", "微爆点": "burst",
    "巴掌": "slap", "巴掌位": "slap", "打脸": "slap", "反击": "slap",
    "笑点": "joke",
    "包袱铺垫": "setup", "铺垫": "setup",
    "包袱": "payoff", "抖响": "payoff",
    "反转": "twist",
    "呼吸": "breath", "呼吸段": "breath", "留白": "breath",
}

LABELS = {
    "hook": "钩子", "ending": "结尾钩子", "conflict": "冲突", "burst": "爆点",
    "slap": "巴掌位", "joke": "笑点", "setup": "包袱铺垫", "payoff": "包袱",
    "twist": "反转", "breath": "呼吸段",
}

# 各类型的周期上限（秒）。检查的是「最长空档」，用 2 倍容忍持续升级的冲突。
PERIOD = {
    "conflict": 3, "burst": 5, "slap": 6, "joke": 11,
    "payoff": 15, "twist": 30,
}

# extra：喜剧轴离散点的上限（秒）覆盖值。
# full 是打脸爽剧默认档，喜剧轴按「中」密度；comedy 才是喜剧向满档，按 15s 包袱严格查。
MODES = {
    "full": {"required": ["hook", "ending", "conflict", "burst", "slap", "twist", "payoff"],
             "enabled": ["conflict", "burst", "slap", "joke", "payoff", "twist"], "factor": 1.0,
             "extra": {"joke": 33, "payoff": 45}},
    "comedy": {"required": ["hook", "ending", "conflict", "burst", "slap", "twist", "payoff", "joke", "setup"],
               "enabled": ["conflict", "burst", "slap", "joke", "payoff", "twist"], "factor": 1.0,
               "extra": {"joke": 22, "payoff": 30}},
    "romance": {"required": ["hook", "ending", "conflict", "burst", "twist"],
                "enabled": ["conflict", "burst", "slap", "twist"], "factor": 1.5, "extra": {}},
    "suspense": {"required": ["hook", "ending", "conflict", "burst", "twist"],
                 "enabled": ["conflict", "burst", "slap", "twist"], "factor": 1.0, "extra": {}},
    "light": {"required": ["hook", "ending", "conflict", "burst", "twist"],
              "enabled": ["conflict", "burst", "slap", "joke", "payoff", "twist"], "factor": 1.5,
              "extra": {"joke": 33, "payoff": 45}},
}

MODE_NOTE = {
    "romance": "虐恋档：喜剧轴关闭，巴掌位减半",
    "suspense": "悬疑档：喜剧轴关闭，反转优先",
    "light": "降档：周期放宽 1.5 倍",
}

# 用正则而非子串：「扇婆婆耳光」「抽了她一巴掌」这类插入成分，纯子串匹配会漏检
VIOLENCE = [
    r"扇.{0,4}耳光", r"扇.{0,4}巴掌", r"抽.{0,3}巴掌", r"打.{0,3}巴掌",
    r"一记耳光", r"掌掴", r"断肢", r"割喉", r"流血", r"血迹",
    r"捅进", r"刺穿", r"血肉模糊",
]


def parse(path):
    anchors, unknown, near = [], [], []
    text = Path(path).read_text(encoding="utf-8-sig")   # 吃掉 Windows 记事本的 BOM
    for idx, raw in enumerate(text.splitlines(), 1):
        m = LINE.match(raw)
        if not m:
            if NEAR.match(raw):
                near.append(idx)
            continue
        sec = int(m.group(1)) * 60 + int(m.group(2))
        kind = ALIASES.get(m.group(3).strip())
        if kind is None:
            unknown.append((idx, m.group(3).strip()))
            continue
        anchors.append((sec, kind, m.group(4).strip(), idx))
    anchors.sort(key=lambda x: (x[0], x[3]))
    return anchors, unknown, near


def main():
    ap = argparse.ArgumentParser(description="短剧节奏时间轴检查器")
    ap.add_argument("file", help="时间轴文件路径")
    ap.add_argument("--mode", choices=list(MODES), default="full", help="题材档位")
    args = ap.parse_args()
    cfg = MODES[args.mode]

    path = Path(args.file)
    if not path.is_file():
        print("文件不存在：{}".format(args.file))
        return 1
    anchors, unknown, near = parse(path)
    print("\n=== 节奏时间轴检查：{} （档位 {}）===".format(path.name, args.mode))
    if args.mode in MODE_NOTE:
        print("  " + MODE_NOTE[args.mode])
    if not anchors:
        if near:
            print("  ERROR  读到 {} 行「分:秒｜内容」式写法（首个在 L{}），缺类型列，不是三列时间轴".format(
                len(near), near[0]))
            print("         每行必须是「分:秒 | 类型 | 落点」；细纲里的动作节点另附一份时间轴，")
            print("         格式见 assets/节奏时间轴模板.md（类型可选值与同义词也在那里）")
        else:
            print("  ERROR  未解析到任何锚点，检查每行是否为「分:秒 | 类型 | 落点」")
        return 1

    errs, warns = [], []
    for ln, kind in unknown:
        warns.append("L{} 未知类型「{}」已忽略，可用类型见 assets/节奏时间轴模板.md".format(ln, kind))
    kinds = [k for _, k, _, _ in anchors]
    duration = max(s for s, _, _, _ in anchors)

    # 0. 文件序 vs 时间序：锚点会按时间排好再算，但报告里的 L 行号会跟时间顺序错位，
    #    用户按行号找会找不到。这类「文件没按时间写」必须单独提示。
    order = [ln for _, _, _, ln in anchors]
    inversions = [(a, b) for a, b in zip(order, order[1:]) if b < a]
    if inversions:
        warns.append("时间轴未按时间顺序书写（L{} 之后又回到 L{}），已按时间重排计算；"
                     "建议文件本身就按时间升序，报告里的行号才对得上".format(*inversions[0]))

    # 0b. 完全重复的锚点：复制粘贴残留会让密度虚高、并把「连续 3 个同类」误判出来
    seen = {}
    for sec, k, _, ln in anchors:
        seen.setdefault((sec, k), []).append(ln)
    dups = [((sec, k), lns) for (sec, k), lns in seen.items() if len(lns) > 1]
    for (sec, k), lns in sorted(dups)[:3]:
        warns.append("L{} 是同一秒同一类型的重复锚点（{:02d}:{:02d} {}），删掉多余行".format(
            "、".join(str(x) for x in lns[1:]), sec // 60, sec % 60, LABELS[k]))
    if len(dups) > 3:
        warns.append("另有 {} 组重复锚点未逐条列出".format(len(dups) - 3))

    # 0c. 单集时长上限 120 秒（60 / 90 / 120 三档，02 要求显式声明）
    if duration > 120:
        warns.append("时间轴末锚点在 {:02d}:{:02d}，超过单集上限 120 秒；"
                     "若这是多集合排，请拆成一集一份时间轴".format(duration // 60, duration % 60))

    # 1. 必需锚点
    for k in cfg["required"]:
        if k not in kinds:
            errs.append("缺少必需锚点「{}」".format(LABELS[k]))

    # 2. 各启用类型
    # 张力轴（冲突 / 爆点 / 巴掌位）是连续流：一个持续升级的冲突能覆盖多个 3 秒窗口，
    # 因此不按离散周期查同类间隔，改由下面的「全局空档」衡量。
    # 喜剧轴（笑点 / 包袱）与反转是离散点，才按周期检查相邻间隔。
    print("\n  --- 锚点覆盖 ---")
    continuous = {"conflict", "burst", "slap"}
    for k in cfg["enabled"]:
        pts = [s for s, kk, _, _ in anchors if kk == k]
        if not pts:
            warns.append("「{}」一次都没出现，按题材确认是否有意关闭".format(LABELS[k]))
            continue
        # 反转是离散点，周期 30 秒，容差 1.5 倍 → 45 秒；且必须算到片尾，
        # 否则「只在开头排一个反转、后面全靠对话」的稿子会漏检。
        # 张力轴（冲突 / 爆点 / 巴掌位）与喜剧轴不把片尾计入：结尾钩子本就不必再排该类型。
        if k == "twist":
            limit = PERIOD["twist"] * 1.5 * cfg["factor"]
            gaps = [pts[0]] + [b - a for a, b in zip(pts, pts[1:])] + [duration - pts[-1]]
            span = "最长空档（含片尾）"
        else:
            limit = cfg.get("extra", {}).get(k, PERIOD[k] * 2 * cfg["factor"])
            gaps = [pts[0]] + [b - a for a, b in zip(pts, pts[1:])]
            span = "最长间隔"
        longest = max(gaps) if gaps else 0
        if k in continuous:
            print("  OK   {:<6} 出现 {} 次，首次 {:02d}:{:02d}（连续流，按全局空档衡量）".format(
                LABELS[k], len(pts), pts[0] // 60, pts[0] % 60))
        else:
            flag = "OK " if longest <= limit else "超期"
            print("  {}  {:<6} 出现 {} 次，首次 {:02d}:{:02d}，{} {}s（上限 {}s）".format(
                flag, LABELS[k], len(pts), pts[0] // 60, pts[0] % 60, span, longest, int(limit)))
            if longest > limit:
                warns.append("「{}」{} {}s 超过 {}s，补一个该类型锚点".format(
                    LABELS[k], span, longest, int(limit)))
        # 首现上限与间隔上限用同一把尺，否则会出现「间隔 33s 合格、首现 12s 就报错」的自相矛盾
        first_limit = cfg.get("extra", {}).get(k, PERIOD[k] * cfg["factor"])
        if pts[0] > first_limit:
            warns.append("「{}」首次出现太晚（{:02d}:{:02d}，上限 {}s），开场密度不足".format(
                LABELS[k], pts[0] // 60, pts[0] % 60, int(first_limit)))

    # 3. 全局空档（呼吸段豁免）
    print("\n  --- 全局密度 ---")
    total = duration or 1
    print("  时长约 {}s，锚点 {} 个，平均每 10 秒 {:.1f} 个".format(
        total, len(anchors), len(anchors) * 10 / total))
    prev_sec, prev_kind = 0, None
    for sec, kind, _, ln in anchors:
        gap = sec - prev_sec
        # 呼吸段两侧豁免；反转之后的 6–12 秒是留白，观众正在消化新信息，也豁免
        if gap > 6 and prev_kind not in ("breath", "twist") and kind != "breath":
            warns.append("L{} 前后空档 {}s（{:02d}:{:02d} → {:02d}:{:02d}），超过 6 秒未见对抗升级".format(
                ln, gap, prev_sec // 60, prev_sec % 60, sec // 60, sec % 60))
        prev_sec, prev_kind = sec, kind

    # 4. 呼吸段
    breaths = [(s, k, ln) for s, k, _, ln in anchors if k == "breath"]
    print("  呼吸段 {} 个".format(len(breaths)))
    if not breaths and duration >= 60:
        warns.append("全篇没有呼吸段，每 35 秒内至少给一次 5–8 秒低密度段，反转之后必给")
    elif breaths:
        # 呼吸段周期（09 定的硬口径是「每 35 秒内至少一次」）。这里只给 WARN 不给
        # ERROR：片尾与反转留白需要人工判断，且「零呼吸段」已在上面单列。
        span = [(0, breaths[0][0])] + [(a[0], b[0]) for a, b in zip(breaths, breaths[1:])] + [(breaths[-1][0], duration)]
        gap, at = max(((b - a, a) for a, b in span), key=lambda x: x[0])
        print("  呼吸段最长空档 {}s（自 {:02d}:{:02d} 起，上限 35s）".format(gap, at // 60, at % 60))
        if gap > 35:
            warns.append("呼吸段最长空档 {}s（自 {:02d}:{:02d} 起）超过 35s，中间补一段 5–8 秒低密度戏".format(
                gap, at // 60, at % 60))
    twists = [s for s, k, _, _ in anchors if k == "twist"]
    for t in twists:
        # 反转本身就是结尾钩子时，身后没有时长可排，豁免
        if duration - t < 12:
            continue
        if not any(t < b <= t + 12 for b, _, _ in breaths):
            errs.append("{:02d}:{:02d} 的反转之后 12 秒内没有呼吸段，新信息来不及落地（09 定为硬要求）".format(
                t // 60, t % 60))

    # 5. 类型单调
    run, run_kind = 0, None
    for _, k, _, _ in anchors:
        if k == run_kind and k not in ("breath",):
            run += 1
        else:
            run, run_kind = 1, k
        if run >= 3:
            warns.append("连续 3 个「{}」，爽点类型重复，换一种落点".format(LABELS[k]))
            break

    # 6. 字面暴力与占位符
    placeholders = []
    for sec, k, text, ln in anchors:
        for pat in VIOLENCE:
            hit = re.search(pat, text)
            if hit:
                warns.append("L{} 出现字面暴力「{}」，按 05-storyboard-pipeline.md 降维为侧面暗示 + 精准音效".format(
                    ln, hit.group(0)))
                break
        if "〈" in text or "填写" in text:
            placeholders.append(ln)
    # 空白模板会整篇都是占位符，逐行报会把真正的问题淹没，压成一条汇总
    if len(placeholders) == 1:
        warns.append("L{} 落点还是占位符，未填具体内容".format(placeholders[0]))
    elif placeholders:
        head = "、".join("L{}".format(x) for x in placeholders[:3])
        warns.append("{} 等 {} 处落点还是占位符（{:.0%}），未填具体内容；照模板刚起稿时出现此提示属正常".format(
            head, len(placeholders), len(placeholders) / len(anchors)))

    # 7. 包袱结构
    if "payoff" in kinds and "setup" not in kinds and args.mode in ("full", "comedy"):
        warns.append("有包袱但没有「包袱铺垫」行，包袱需要前面埋、此处响")

    print("\n  --- 问题 ---")
    for e in errs:
        print("  ERROR  " + e)
    for w in warns:
        print("  WARN   " + w)
    if not errs and not warns:
        print("  未发现问题。")
    print("\n  汇总：ERROR {} 项 / WARN {} 项 → {}".format(
        len(errs), len(warns), "未通过，按 ERROR 修复" if errs else "可交付，按 WARN 人工判断"))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
