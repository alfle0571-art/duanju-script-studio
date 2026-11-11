---
name: duanju-script-studio
display_name: 短剧剧本工作台
display_name_en: Duanju Script Studio
description: "【中文短剧 / 漫剧 · 文字剧本交付件】模糊说法：「写个70集大纲」「把粗纲扩成细纲」「按细纲写第3集」「△开头那种剧本」「场1-1怎么写」「内心OS」「闪回放哪」「这段台词太AI了」。产出70-80集分集大纲、逐集细纲、标准格式分集剧本（△动作行、人物名加冒号、括号情绪、首次出场字幕、内心os、闪回、场x-x场序），并可续接AI漫剧四步分镜（情绪节奏图谱、视觉风险预控、防穿模分镜、台词纵向模板）。自带情绪微表情库、爆款五规律、去AI味文风工具箱与格式校验脚本。要画面加旁白的解说稿转写剧本；要15集竖屏短剧工业统筹转microdrama-storyforge；要漫剧全流程与视频提示词编译转manju-production-suite；要改已有本子转screenwriting-pro；只要逐镜成品表转seedance-shotlist-director。"
description_en: "A production line for Chinese paid short dramas and AI comic dramas. Turns a premise into a 70-80 episode outline, then per-episode beats, then fully formatted shooting scripts (action lines prefixed with a triangle, colon dialogue, bracketed emotion cues, on-screen character captions, inner monologue, flashback markers, numbered scene headings), and optionally an AI-friendly storyboard with compliance-safe staging. Ships an emotion micro-expression library, hook-writing rules, a de-AI voice toolkit and a format checker."
agent_created: true
metadata:
  version: "1.0.0"
  language: "zh-CN"
  audience: "中文付费短剧编剧、AI漫剧导演、短剧内容工作室"
---

# 短剧剧本工作台

## 定位

把一句话题材或一段小说原文，加工成**可直接交付的中文短剧文字剧本**，并可续接成适合 AI 视频生成的分镜表。

主生产线是一条顺序链：**大纲 → 细纲 → 分集剧本 → AI 分镜**。三套资产贯穿全程：排版规范、情绪微表情库、爆款规律。文风改写工具箱是旁支，不进主线。

本技能只负责**文字交付件**。不生成图片、不生成视频、不编译 Seedance / H3 提示词、不做镜头实测。

## 触发与转介

触发本技能：中文付费短剧、分集大纲、粗纲转细纲、按细纲写剧本、`△` 动作行、`场x-x` 场序、`内心os`、`【闪回】`、首次出场字幕、情绪微表情、漫剧防穿模分镜。

转介已有技能，不硬抢：

| 需求 | 转介 |
|---|---|
| 画面 + 旁白两行的解说稿 | `写剧本` |
| 15 集竖屏短剧的题材重构、成本控制、工业化统筹 | `microdrama-storyforge` |
| 漫剧四阶段全流程、角色卡、视频提示词编译 | `manju-production-suite` |
| 修改 / 续写 / 诊断已有剧本 | `screenwriting-pro` |
| 小说改剧集圣经、提案、treatment | `novel-to-screenplay` |
| 只要成品逐镜表 | `seedance-shotlist-director` |
| 打斗分镜专项 | `seedance-fight-sequence` |

## 入口路由

先判断用户手里的素材停在哪一级，再从对应工位起，不倒回去重做上游。

| 用户给的 | 进入 | 必读参考 |
|---|---|---|
| 一个题材、一句话点子、类型与受众 | 工位 1 · 大纲 | `01-outline-agent.md`、`07-hit-rules.md` |
| 全书粗纲、分集梗概、某集一句话概要 | 工位 2 · 细纲 | `02-beat-agent.md`、`07-hit-rules.md` |
| 完整细纲、"按细纲写第 N 集" | 工位 3 · 分集剧本 | `03-script-agent.md`、`04-format-spec.md`、`06-emotion-library.md` |
| 小说原文、"做成漫剧 / 分镜 / 视觉素材" | 工位 4 · 分镜四步 | `05-storyboard-pipeline.md`、`06-emotion-library.md` |
| "台词太 AI 了"、"改口语一点" | 支线 · 文风 A 区 | `08-voice-toolkit.md` |
| "改成公众号 / 小红书文案" | 支线 · 文风 B 区 | `08-voice-toolkit.md` |
| "学术化 / 论文润色 / 引用格式" | 支线 · 文风 C 区 | `08-voice-toolkit.md` |

上游设定缺失时，只补**最小必要设定**（时代、人物关系、核心钩子、主角欲求），不擅自扩写整部大纲，不替用户决定题材与结局。

## 五条硬规则

1. **先定级再动笔。** 明确本次交付物是哪一级（大纲 / 细纲 / 剧本 / 分镜），一次只交付一级。用户要"一条龙"时按工位顺序逐级确认，禁止跳级把大纲直接扩成剧本。

2. **排版是交付件，不是风格建议。** 分集剧本一律遵循 `04-format-spec.md`：每集场景不超过 5 个、`场x-y` 场序连续、动作行以 `△` 起始、对话用「人物名：」、说话状态写在括号内、人物首次或第二次出场给【字幕】、内心活动写「人物名内心os：」、闪回用 `【闪回】` / `【闪回结束】` 成对包裹。成稿后运行 `scripts/check_format.py` 校验。

3. **文风隔离，最易翻车的一条。** `08-voice-toolkit.md` 的 **B 区（28 岁博主闲聊体）与 C 区（学术 / 论文 / 商务润色）禁止进入**剧本的台词、动作行、OS、字幕。短剧台词标准是：短句、当代口语、带情绪钩子、可直接念出来。禁止出现"哈哈""emmm""说实话""以我的经验""欢迎在评论区分享"、禁止排比与"赋能 / 闭环 / 全链路"式黑话、禁止书面长句与论文腔。只有用户明确要求改写文案、公众号稿或论文时，才启用 B / C 区。

4. **情绪必须落到可见的脸上和身上。** 写动作行与表演提示时，从 `06-emotion-library.md` 取具体可见描述（牙关紧咬、咬肌紧绷、眼底泛红、鼻翼微缩、肩膀微颤），不写"她很悲伤""他愤怒了""气氛压抑"这类抽象判断。抽象词只可用于细纲的节奏标注，不可用于剧本正文。

5. **分镜支线守住物理与合规。** 进入工位 4 时严格执行四原则：禁止复杂多人肢体接触（拆成单人特写 / 正反打 / 主观局部特写）；暴力与亲密内容降维为侧面暗示并用精准音效代偿；关键动作注明首帧起始态与尾帧结束态；普通文戏 2–5 秒、情绪爆发 5–8 秒。详见 `05-storyboard-pipeline.md`。

## 主流程要点

### 工位 1 · 大纲（70–80 集）

读取 `01-outline-agent.md`。产出总纲 + 分集大纲，默认 70–80 集规模。每集须有一个可复述的钩子句、一个明确的爽点或泪点，并在全季标出主线反转节点与人物弧光转折集。文字简练明快，不写散文式铺陈。

### 工位 2 · 细纲

读取 `02-beat-agent.md`。把粗纲的一行扩成可执行的一集：谁在哪、做了什么、被谁打断、情绪怎么翻、结尾留什么钩子。情节之间因果连续，不新增与粗纲冲突的人物或设定。标注爽点 / 泪点 / 燃点位置。

### 工位 3 · 分集剧本

读取 `03-script-agent.md`、`04-format-spec.md`、`06-emotion-library.md`。用 `assets/剧本空白模板.md` 起稿。台词语气贴合人物，动作行带画面感与具体特效说明；场景数压到最少；写完跑格式校验。

### 工位 4 · AI 分镜四步

读取 `05-storyboard-pipeline.md`，严格按 step.01 → 02 → 03 → 04 顺序：情绪节奏图谱与连续动作拆解 → 视觉元素与四类风险预控清单 → AI 适配型分镜初稿 → 台词精炼与纵向模板输出。用 `assets/分镜纵向模板.md` 交付 step.04。前一步的结论必须被后一步显式引用，不另起炉灶。

## 交付前自检

- [ ] 交付物层级与用户请求一致，没有夹带上一级或下一级内容
- [ ] 分集剧本通过 `scripts/check_format.py`，无场序断号、无未闭合闪回、场景数 ≤ 5
- [ ] 每个有台词的角色首次或第二次出场带【字幕】
- [ ] 台词里没有博主腔、学术腔、排比句和互联网黑话
- [ ] 动作行写的是看得见的动作与微表情，不是情绪形容词
- [ ] 每集结尾留钩子；全季反转节点不集中在前 10 集
- [ ] 分镜稿已注明首尾帧承接状态，暴力 / 亲密内容已降维并配好音效

## 资源清单

| 文件 | 用途 | 何时读取 |
|---|---|---|
| `references/01-outline-agent.md` | 大纲智能体人设、约束、70–80 集规格 | 工位 1 |
| `references/02-beat-agent.md` | 细纲智能体人设、约束、颗粒度标准 | 工位 2 |
| `references/03-script-agent.md` | 剧本生成智能体人设、约束、示例 | 工位 3 |
| `references/04-format-spec.md` | 中文短剧排版硬规范 + 完整剧本范例 | 工位 3 必读 |
| `references/05-storyboard-pipeline.md` | 漫剧四步分镜法 + 纵向输出模板 | 工位 4 |
| `references/06-emotion-library.md` | 哀 / 怒 / 喜 / 惊微表情词库 | 写动作行、表演提示时 |
| `references/07-hit-rules.md` | 爆款五规律与钩子公式 | 定大纲、定每集开头结尾时 |
| `references/08-voice-toolkit.md` | 去 AI 味与文风改写工具箱（A/B/C 三区隔离） | 仅文风支线 |
| `assets/剧本空白模板.md` | 可直接复制的分集剧本骨架 | 起稿 |
| `assets/分镜纵向模板.md` | step.04 逐镜纵向模板空白版 | 分镜交付 |
| `scripts/check_format.py` | 剧本格式校验 | 成稿后 |
