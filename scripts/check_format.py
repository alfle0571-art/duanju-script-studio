#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中文短剧剧本格式校验器。

用法:
    python check_format.py <剧本文件路径> [更多路径...]

检查项: 场序格式与连续性、每集场景数 <= 5、动作行、对话行、说话状态位置、
        内心os 写法、闪回成对、首次出场字幕覆盖（群演可声明豁免）、文风禁用词。

退出码: 0 = 无 ERROR（可交付）；1 = 存在 ERROR；2 = 入参或文件错误。
仅做结构校验，不判断文笔；文笔与情绪按 SKILL.md 自检清单人工复核。

口径说明: 字幕按「全篇首次出场」计，群演声明按「全篇生效」——同一个群演角色
          不会因为换集又变回需要挂字幕。若某角色中途升格为主要人物（开始有姓名
          与独立戏份），给他补一条【字幕：姓名，身份】即可，无需删旧声明。

编码: 按 utf-8-sig 读，Windows 记事本另存的 UTF-8（带 BOM）也能正常解析。
"""

import re
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCENE_HEAD = re.compile(r"^场(\d+)-(\d+)\s+(.*)$")
DIALOG = re.compile(r"^([^△\s【】（）()：:]+?)(?:[（(][^）)]*[）)])?[：:]\s*(.*)$")
OS_LINE = re.compile(r"^(.+?)内心\s*os\s*[：:]\s*(.*)$", re.IGNORECASE)
CAPTION = re.compile(r"【字幕[：:]\s*([^，,、】]+)[，,]?([^】]*)】")
# 群演 / 功能性角色豁免：文件里写一行「（本集群演：司仪、宾客甲、路人甲）」即可不挂字幕
EXTRA = re.compile(r"[（(]?\s*(?:本集)?群演\s*[：:]\s*([^）)】\n]+)")
FLASH_START = "【闪回】"
FLASH_END = "【闪回结束】"

# B 区博主腔 / C 区学术腔 / 互联网黑话（对应 SKILL.md 硬规则 4）
BANNED = [
    "哈哈", "emmm", "说实话", "以我的经验", "个人觉得", "我之前试过",
    "欢迎在评论区", "有没有遇到过这种情况", "说到这个", "对了，还有",
    "星巴克", "赋能", "闭环", "全链路", "多维度", "底座", "体系化",
    "发挥了关键作用", "提供了坚实基础", "全方位强化", "综上所述", "由此可见",
]
# 动作行里不该出现的抽象情绪判断（对应硬规则 5）
ABSTRACT = [
    "很悲伤", "很愤怒", "气氛压抑", "气氛凝固", "内心悲痛", "心情复杂",
    "情绪崩溃", "感到绝望", "十分震惊", "非常难过", "特别生气",
]
# 括号里只写抽象情绪标签，没给可演的动作
VAGUE_CUE = re.compile(r"[（(](悲伤|愤怒|开心|难过|生气|震惊|害怕|激动|痛苦|绝望)[）)]")

SKIP_PREFIX = ("△", "【", "（", "(", "#", ">", "|", "-", "---", "第", "*", ">")
# 说话状态必须写在人物名后、冒号前；紧跟冒号的括号属于排版错误
PAREN_OPEN = ("（", "(")
# 这些是版面标签而非角色，不能算进「有台词角色」的字幕覆盖
NON_SPEAKER = {"字幕", "人物", "主要人物", "时间", "地点", "备注", "场次", "集数", "片名", "标题", "类型"}


def check(path):
    try:
        # utf-8-sig：Windows 记事本另存的 UTF-8 带 BOM，
        # 用 utf-8 读会让首行粘上 \ufeff，整场静默失检（旧版漏洞）
        text = Path(path).read_text(encoding="utf-8-sig")
    except Exception as exc:
        return None, [("ERROR", 0, "无法读取文件：{}".format(exc))]

    issues = []
    lines = text.splitlines()
    scenes = []                 # (行号, 集号, 场号, 整行)
    speakers = set()            # 有台词的角色
    captions = set()            # 挂过字幕的角色
    extras = set()              # 声明为群演、不需要字幕的角色
    flash_depth = 0
    scene_count_by_ep = {}
    has_action = False
    has_dialog = False

    for idx, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line:
            continue

        # 文风禁用词：台词、动作行、OS、场序、字幕一律检查。
        # 必须放在各条 continue 之前，否则动作行与 OS 会整体绕过（旧版漏洞）。
        for word in BANNED:
            if word in line:
                issues.append(("ERROR", idx, "出现禁用词「{}」：博主腔 / 学术腔 / 黑话不得进入剧本（SKILL.md 硬规则 4）".format(word)))

        # 字幕：可在任意行尾，先全局收集
        for m in CAPTION.finditer(line):
            cap = m.group(1).strip()
            captions.add(cap)
            # 年代 / 地点被写成人物字幕，会被当成一个叫「1987 年」的角色（04 第 4 条）
            if re.search(r"\d{2,4}\s*年|年代|世纪", cap):
                issues.append(("WARN", idx, "【字幕：{}】是年代 / 时间信息，应写成（时间字幕：{}）".format(cap, cap)))

        # 群演豁免声明
        for m in EXTRA.finditer(line):
            for part in re.split(r"[、，,／/；;]", m.group(1)):
                if part.strip():
                    extras.add(part.strip())

        # 闪回配对
        if FLASH_START in line:
            flash_depth += 1
        if FLASH_END in line:
            flash_depth -= 1
            if flash_depth < 0:
                issues.append(("ERROR", idx, "【闪回结束】多于【闪回】，没有对应的开始标记"))
                flash_depth = 0

        # 场序
        m = SCENE_HEAD.match(line)
        if m:
            ep, no, rest = int(m.group(1)), int(m.group(2)), m.group(3)
            scenes.append((idx, ep, no, line))
            scene_count_by_ep[ep] = scene_count_by_ep.get(ep, 0) + 1
            if "/" not in rest:
                issues.append(("ERROR", idx, "场序缺「天气/场景」，应写作 日/内、日/外、夜/内 等"))
            if "主要人物" not in rest:
                issues.append(("ERROR", idx, "场序缺「主要人物：」字段"))
            continue

        # 疑似场序但写错前缀
        if re.match(r"^\d+-\d+\s", line):
            issues.append(("ERROR", idx, "场序缺少「场」前缀，应写作 场x-y …"))
            continue

        # 「场1-1日内灵堂」这类缺空格的场序，SCENE_HEAD 匹配不到，
        # 旧版会被下面的「以场开头就跳过」静默吃掉，等于整场失检。
        if re.match(r"^场\s*\d+\s*-\s*\d+\s*\S", line):
            issues.append(("ERROR", idx, "场序格式错误：场号和「天气/场景」之间缺空格，应写作 场1-1 日/内 灵堂 主要人物：…"))
            continue

        # 动作行
        if line.startswith("△"):
            has_action = True
            for word in ABSTRACT:
                if word in line:
                    issues.append(("WARN", idx, "动作行含抽象情绪词「{}」，换成可见微表情（06-emotion-library.md）".format(word)))
            if len(line) < 4:
                issues.append(("WARN", idx, "动作行内容过短，可能不是可拍摄的动作"))
            continue

        # 内心 OS
        m = OS_LINE.match(line)
        if m:
            if not m.group(2).strip():
                issues.append(("WARN", idx, "内心os 为空"))
            if len(m.group(2)) > 80:
                issues.append(("WARN", idx, "内心os 过长（>80字），压成短句，其余交给动作与台词"))
            continue

        # 闪回标记行、提示行、表格行等跳过
        if line.startswith(SKIP_PREFIX) or line.startswith("场") or line.startswith("|"):
            continue

        # 对话行
        m = DIALOG.match(line)
        if m:
            name, speech = m.group(1).strip(), m.group(2).strip()
            if name and name not in NON_SPEAKER and len(name) <= 12 and not name.startswith("填写"):
                has_dialog = True
                speakers.add(name)
                if not speech:
                    issues.append(("WARN", idx, "「{}」这句台词为空".format(name)))
                if line.find("：") == -1:
                    issues.append(("WARN", idx, "对话用了半角冒号，规范用全角「：」"))
                vm = VAGUE_CUE.search(line)
                if vm:
                    issues.append(("WARN", idx, "括号里只写了「{}」，换成具体动作或语气".format(vm.group(1))))
                if speech.startswith(PAREN_OPEN):
                    issues.append(("ERROR", idx, "「{}」的说话状态写在了冒号后，规范是 人物名（动作）：台词".format(name)))

    if flash_depth > 0:
        issues.append(("ERROR", len(lines), "有 {} 处【闪回】未用【闪回结束】闭合".format(flash_depth)))

    if not scenes:
        issues.append(("ERROR", 0, "未找到任何场序行（场x-x 天气/场景 地点 主要人物：…）"))
    else:
        # 按集检查场号从 1 连续递增
        by_ep = {}
        for ln, ep, no, _ in scenes:
            by_ep.setdefault(ep, []).append((no, ln))
        for ep in sorted(by_ep):
            seq = by_ep[ep]
            expected = 1
            for no, ln in seq:
                if no != expected:
                    issues.append(("ERROR", ln, "第{}集场序断号或重复：期望 场{}-{}，实际 场{}-{}".format(ep, ep, expected, ep, no)))
                    expected = no
                expected += 1
        for ep, count in sorted(scene_count_by_ep.items()):
            if count > 5:
                issues.append(("ERROR", 0, "第{}集有 {} 个场景，超过每集上限 5 个".format(ep, count)))

    if not has_action:
        issues.append(("WARN", 0, "全篇没有 △ 动作行"))
    if not has_dialog:
        issues.append(("WARN", 0, "全篇没有识别到对话行"))

    missing = sorted(speakers - captions - extras)
    if missing:
        issues.append(("ERROR", 0, "以下有台词的角色未挂【字幕】：{}（群演请先声明「（本集群演：…）」）".format("、".join(missing))))

    return {
        "scenes": len(scenes),
        "by_ep": scene_count_by_ep,
        "speakers": len(speakers),
        "captions": len(captions),
        "extras": len(speakers & extras),
    }, issues


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    total_err = total_warn = 0
    failed = False
    for arg in sys.argv[1:]:
        path = Path(arg)
        if not path.is_file():
            print("文件不存在：{}".format(arg))
            failed = True
            continue
        stat, issues = check(path)
        print("\n=== 短剧剧本格式校验：{} ===".format(path.name))
        errs = [i for i in issues if i[0] == "ERROR"]
        warns = [i for i in issues if i[0] == "WARN"]
        for level, ln, msg in errs:
            print("  ERROR  L{:<4} {}".format(ln, msg))
        for level, ln, msg in warns:
            print("  WARN   L{:<4} {}".format(ln, msg))
        if not issues:
            print("  未发现问题。")
        if stat:
            detail = " / ".join("第{}集 {} 场".format(ep, n) for ep, n in sorted(stat["by_ep"].items()))
            print("  --- 汇总 ---")
            print("  场景：{}（共 {} 场）".format(detail or "无", stat["scenes"]))
            print("  有台词角色 {} 个，字幕覆盖 {} 个，群演豁免 {} 个".format(
                stat["speakers"], stat["captions"], stat["extras"]))
        print("  ERROR {} 项 / WARN {} 项 → {}".format(len(errs), len(warns), "未通过，需修复 ERROR" if errs else "通过，可交付"))
        total_err += len(errs)
        total_warn += len(warns)
        if errs:
            failed = True

    print("\n合计：ERROR {} 项 / WARN {} 项".format(total_err, total_warn))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
