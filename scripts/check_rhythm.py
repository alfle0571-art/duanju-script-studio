#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""短剧节奏时间轴检查器。

用法:
    python check_rhythm.py <时间轴文件> [--mode full|comedy|romance|suspense|light]

输入格式（每行一个锚点）:
    00:06 | 巴掌 | 女主一句话把婆婆噎在原地

检查: 锚点齐全度、任意空档长度、呼吸段、类型单调、字面暴力、未填占位符。
退出码: 0 = 可交付（可带 WARN）；1 = 存在 ERROR（缺必需锚点或无法解析）。

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

LINE = re.compile(r"^\s*(\d{1,2}):(\d{2})\s*\|\s*([^|]+?)\s*\|\s*(.+?)\s*$")

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

VIOLENCE = ["扇耳光", "掌掴", "打了一巴掌", "一记耳光", "抽了一巴掌"]


def parse(path):
    anchors = []
    for idx, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        m = LINE.match(raw)
        if not m:
            continue
        sec = int(m.group(1)) * 60 + int(m.group(2))
        kind = ALIASES.get(m.group(3).strip())
        if kind is None:
            print("  WARN   L{:<4} 未知类型「{}」，已忽略（可用类型见时间轴模板）".format(idx, m.group(3).strip()))
            continue
        anchors.append((sec, kind, m.group(4).strip(), idx))
    anchors.sort(key=lambda x: (x[0], x[3]))
    return anchors


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
    anchors = parse(path)
    print("\n=== 节奏时间轴检查：{} （档位 {}）===".format(path.name, args.mode))
    if args.mode in MODE_NOTE:
        print("  " + MODE_NOTE[args.mode])
    if not anchors:
        print("  ERROR  未解析到任何锚点，检查每行是否为「分:秒 | 类型 | 落点」")
        return 1

    errs, warns = [], []
    kinds = [k for _, k, _, _ in anchors]
    duration = max(s for s, _, _, _ in anchors)

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
        limit = cfg.get("extra", {}).get(k, PERIOD[k] * 2 * cfg["factor"])
        # 不含「末尾到片尾」：结尾钩子本就不必再排该类型，计入会产生假超期
        gaps = [pts[0]] + [b - a for a, b in zip(pts, pts[1:])]
        longest = max(gaps) if gaps else 0
        if k in continuous:
            print("  OK   {:<6} 出现 {} 次，首次 {:02d}:{:02d}（连续流，按全局空档衡量）".format(
                LABELS[k], len(pts), pts[0] // 60, pts[0] % 60))
        else:
            flag = "OK " if longest <= limit else "超期"
            print("  {}  {:<6} 出现 {} 次，首次 {:02d}:{:02d}，最长间隔 {}s（上限 {}s）".format(
                flag, LABELS[k], len(pts), pts[0] // 60, pts[0] % 60, longest, int(limit)))
            if longest > limit:
                warns.append("「{}」相邻间隔最长 {}s 超过 {}s，补一个该类型锚点".format(
                    LABELS[k], longest, int(limit)))
        if pts[0] > PERIOD[k] * cfg["factor"]:
            warns.append("「{}」首次出现太晚（{:02d}:{:02d}），开场密度不足".format(
                LABELS[k], pts[0] // 60, pts[0] % 60))

    # 3. 全局空档（呼吸段豁免）
    print("\n  --- 全局密度 ---")
    total = duration or 1
    print("  时长约 {}s，锚点 {} 个，平均每 10 秒 {:.1f} 个".format(
        total, len(anchors), len(anchors) * 10 / total))
    prev_sec, prev_kind = 0, None
    for sec, kind, _, ln in anchors:
        gap = sec - prev_sec
        if gap > 6 and prev_kind != "breath" and kind != "breath":
            warns.append("L{} 前后空档 {}s（{:02d}:{:02d} → {:02d}:{:02d}），超过 6 秒未见对抗升级".format(
                ln, gap, prev_sec // 60, prev_sec % 60, sec // 60, sec % 60))
        prev_sec, prev_kind = sec, kind

    # 4. 呼吸段
    breaths = [(s, k, ln) for s, k, _, ln in anchors if k == "breath"]
    print("  呼吸段 {} 个".format(len(breaths)))
    if not breaths and duration >= 60:
        warns.append("全篇没有呼吸段，每 25–35 秒应给 5–8 秒低密度段，反转之后必给")
    twists = [s for s, k, _, _ in anchors if k == "twist"]
    for t in twists:
        if not any(t < b <= t + 12 for b, _, _ in breaths):
            warns.append("{:02d}:{:02d} 的反转之后 12 秒内没有呼吸段，新信息来不及落地".format(t // 60, t % 60))

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
    for sec, k, text, ln in anchors:
        for w in VIOLENCE:
            if w in text:
                warns.append("L{} 出现字面暴力「{}」，按 05-storyboard-pipeline.md 降维为侧面暗示 + 精准音效".format(ln, w))
                break
        if "〈" in text or "填写" in text:
            warns.append("L{} 落点还是占位符，未填具体内容".format(ln))

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
    print("\n  ERROR {} 项 / WARN {} 项 → {}".format(
        len(errs), len(warns), "未通过，补齐必需锚点" if errs else "可交付，按 WARN 人工判断"))
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
