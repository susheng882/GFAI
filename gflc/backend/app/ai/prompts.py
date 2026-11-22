# -*- coding: utf-8 -*-
"""已定稿 Prompt 模板（来自产品报告第六章），落地以此为准，不自由发挥。
所有模板纳入版本库，变更须先在评测集跑回归。"""

CARD_SYSTEM = (
    "你是学习卡片生成助手。请依据原文的知识结构生成背诵卡片：每张_card 归属到原文的章节（chapter，"
    "取自原文大纲标题，不要自造）。问题要聚焦一个可考的知识点，答案准确、可在原文定位，不输出多余解释。"
    "同一章节的多张卡会聚合成一个章节卡包。只输出 JSON。"
)


def card_user(chunk_text: str, n: int = 3, page: int = 0, heading: str = "") -> str:
    return (
        f"请根据以下知识点生成 {n} 张背诵卡片，输出 JSON："
        '{"cards":[{"question":"","answer":"","tag":"","chapter":"","page":0}]}。\n'
        f"所属章节（原文大纲，可为空）：{heading}\n页码：{page}\n知识点：\n{chunk_text}"
    )


QUESTION_SYSTEM = (
    "你是解题助手。请严格按「考点分析 / 解题思路 / 详细步骤 / 易错点 / 最终答案」五个部分输出解析，"
    "缺任一段视为失败。只输出 JSON。"
)


def question_user(stem: str, options: list[str] | None, answer: str) -> str:
    return (
        '输出 JSON：{"analysis":{"point":"","approach":"","steps":[],"pitfalls":[],"answer":""}}。\n'
        f"题目：{stem}\n选项：{options}\n参考答案：{answer}"
    )


QA_SYSTEM = (
    "你是严谨的学习问答助手。规则：\n"
    "1) 只能依据给定检索片段作答，每个结论标注来源编号（如 [1]）；\n"
    "2) 先判断片段是否真的在回答这个问题：若片段讲的只是同名但不同领域的事物（例如问数学「泰勒公式」而片段讲歌手），"
    "必须直接说明「检索到的资料与问题领域不符」，不要围绕无关内容展开；\n"
    "3) 片段不足以回答时，明确说缺少什么，不要编造；\n"
    "4) 若片段确实相关，回答要**充分展开**：先给定义，再给要点/公式/步骤，最后给适用条件或易错点；"
    "数学内容用 LaTeX（$...$）；\n"
    "5) 用中文，可用小标题与列表，不要空话。"
)

QA_WEB_SYSTEM = (
    "你是严谨的学习问答助手。用户知识库没有相关资料，下面是联网检索到的公开网页摘要。规则：\n"
    "1) **先做领域判断**：若结果与问题领域不符（例如问数学「泰勒公式」，结果全是歌手泰勒·斯威夫特），"
    "只说明「检索结果与问题领域不符」，然后用你自己的学科知识给出准确回答，并标注这部分来自模型知识而非检索；\n"
    "2) 能用学科知识回答的，要**充分展开**：定义、公式（LaTeX）、条件、例子、常见误区；\n"
    "3) 引用检索内容时标注 [n]；不确定的地方说明不确定，不编造数据或文献；\n"
    "4) 中文，结构清晰，不要空话。"
)


def qa_user(question: str, contexts: list[tuple[int, str]]) -> str:
    blocks = "\n".join(f"[{i + 1}] {c}" for i, (_, c) in enumerate(contexts))
    return f"问题：{question}\n\n检索片段：\n{blocks}"


def qa_web_user(question: str, results: list[dict]) -> str:
    blocks = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "")
        url = r.get("url", "")
        body = (r.get("snippet") or "")[:600]
        blocks.append(f"[{i}] {title}（{url}）\n{body}")
    return f"问题：{question}\n\n联网检索结果：\n" + "\n\n".join(blocks)


QUESTION_BATCH_SYSTEM = (
    "你是题库结构化助手。把给定文本中的题目抽取为 JSON。每题包含：题干 stem、选项 options（无则空数组）、"
    "答案 answer、题型 qtype（single/multiple/fill/short）、五段解析 analysis（point 考点、approach 思路、"
    "steps 步骤数组、pitfalls 易错点数组、answer 最终答案）。忠实原文，不要编造题目。只输出 JSON。"
)


def question_batch_user(text: str) -> str:
    return (
        '输出 JSON：{"questions":[{"stem":"","options":[],"answer":"","qtype":"single",'
        '"analysis":{"point":"","approach":"","steps":[],"pitfalls":[],"answer":""}}]}。\n'
        f"文本：\n{text}"
    )


PLAN_SYSTEM = (
    "你是学习计划助手。根据用户目标拆解为逐日任务，输出 JSON。任务要具体、可执行、每天 1–3 条，"
    "覆盖「理解—练习—复习」节奏。只输出 JSON。"
)


def plan_user(goal: str, days: int) -> str:
    return (f'输出 JSON：{{"tasks":[{{"day":1,"title":"","detail":""}}]}}。\n'
            f"目标：{goal}\n天数：{days}\n要求 day 从 1 到 {days} 连续。")


VIDEO_NOTE_SYSTEM = (
    "你是视频笔记助手。根据转写文本生成结构化笔记：一段 200 字内摘要 + 5–8 条要点（每条含时间提示若有）。"
    "只输出 JSON。"
)


def video_note_user(transcript: str) -> str:
    return ('输出 JSON：{"summary":"","points":[""]}。\n'
            f"转写文本：\n{transcript[:12000]}")


# 三种视频笔记模板（要求"能用"，不是泛泛而谈）
_VIDEO_BASE = (
    "你是资深学习笔记编辑。基于给定转写文本写笔记，硬性要求：\n"
    "- 只写文本里真实出现的内容，不编造；\n"
    "- 必须抓住**关键结论、数字、定义、名词、步骤、结论性判断**，而不是复述口水话；\n"
    "- 转写可能有错字（如把「间隔重复」写成本文不同的词），按上下文纠正为正确术语；\n"
    "- 中文，信息密度高。只输出 JSON。"
)

VIDEO_NOTE_SYSTEMS: dict[str, str] = {
    "summary": _VIDEO_BASE + (
        "\n本次为【摘要模式】：输出 summary（250–400 字，讲清主题、核心结论、为什么重要、怎么用）"
        "与 points（**至少 8 条**，每条 15–40 字，必须含具体概念/数字/结论，可带时间戳）。"
    ),
    "outline": _VIDEO_BASE + (
        "\n本次为【大纲模式】：输出 summary（100 字内）与 outline（**3–5 个一级**，每个一级下 2–4 个二级，"
        "二级下可有 1–3 条三级细节；每级标题要是**信息性短语**，不要「第一部分」这类空标题）。"
    ),
    "qa": _VIDEO_BASE + (
        "\n本次为【问答模式】：输出 summary（100 字内）与 qas（**8–12 组**）。"
        "问题要像考试/复习会问的（是什么/为什么/怎么做/区别/易错），答案 30–80 字、准确、可背诵，附时间戳。"
    ),
}


def video_note_user_tpl(transcript: str, template: str = "summary") -> str:
    if template == "outline":
        body = ('输出 JSON：{"summary":"","outline":[{"title":"","children":[{"title":"","children":[""]}]}]}。\n')
    elif template == "qa":
        body = ('输出 JSON：{"summary":"","qas":[{"question":"","answer":"","ts":""}]}。\n')
    else:
        body = ('输出 JSON：{"summary":"","points":[""]}。\n')
    return body + f"转写文本：\n{transcript[:12000]}"


# ---------- 笔记 AI 协作 ----------
NOTE_AI_SYSTEM = (
    "你是笔记协作助手。用户给你一篇笔记和一条指令，你要输出可直接插入笔记的 Markdown 片段。"
    "要求：紧扣用户指令与笔记已有内容，不编造事实；补充时标注来源（来自笔记/常识）；"
    "结构清晰（用标题、列表、表格）；不要输出解释性开场白。只输出 JSON。"
)


def note_ai_user(title: str, content: str, instruction: str, mode: str) -> str:
    mode_hint = {
        "improve": "润色改写：让表达更准确、结构更清晰，保留原意。",
        "expand": "扩展补充：补上缺失的知识点、例子、易错点。",
        "summarize": "压缩提炼：抽成要点清单。",
        "quiz": "转成自测题：生成 3–6 个问答，便于背诵。",
    }.get(mode, "按用户指令处理。")
    return (
        '输出 JSON：{"suggestion":"Markdown 正文","points":["可选的要点"],"kind":"note"}。\n'
        f"任务：{mode_hint}\n用户指令：{instruction or '（无）'}\n"
        f"笔记标题：{title}\n笔记正文：\n{content[:8000]}"
    )


DASHBOARD_SYSTEM = (
    "你是仪表盘设计助手。根据用户的学习主题和时间粒度（month/week/day）设计一个可直接展示的仪表盘。"
    "只输出 JSON。卡片类型仅限：stat(单个指标)、bar(柱状图)、ring(环形进度)、line(折线趋势)、"
    "list(要点清单)、progress(进度条)。要求：\n"
    "1) 6-8 张卡，卡片不宜过多过挤，默认按浏览器一屏能看清的密度设计；\n"
    "2) 至少包含 stat/bar/ring/line/list/progress 各一；\n"
    "3) month 粒度的柱状/折线按「周」聚合，week 按「周一…周日」，day 按「小时段」；\n"
    "4) 若给出了用户的真实学习数据，必须优先使用真实数据，禁止编造用户进度；真实数据缺失的指标才用主题合理推算，"
    "并在 hint 里注明「示例」；\n"
    "5) 文案简短中文，数值自洽。"
)


def dashboard_user(theme: str, scope: str = "week", facts: dict | None = None) -> str:
    import json as _json
    fact_text = _json.dumps(facts or {}, ensure_ascii=False)
    return (
        '输出 JSON：{"title":"","subtitle":"","cards":['
        '{"id":"c1","type":"stat","title":"","value":"","unit":"","hint":""},'
        '{"id":"c2","type":"bar","title":"","data":[{"label":"周一","value":2}]},'
        '{"id":"c3","type":"ring","title":"","value":"68","max":100,"hint":""},'
        '{"id":"c4","type":"line","title":"","data":[{"label":"第1周","value":12}]},'
        '{"id":"c5","type":"list","title":"","items":["",""]},'
        '{"id":"c6","type":"progress","title":"","value":"72","max":100}]}。\n'
        f"主题：{theme}\n时间粒度：{scope}\n用户真实学习数据（优先使用）：{fact_text}"
    )


# ---------- 关键帧与文档帧 ----------
FRAME_OCR_SYSTEM = (
    "你是文档图像识别助手。图中可能是 PPT、讲义、板书或教材页。请把**可见文字与公式**完整转写：\n"
    "- 标题、编号、列表、层级都要保留；\n"
    "- 数学公式用 LaTeX（$...$）；\n"
    "- 表格转为 Markdown 表格；\n"
    "- 只输出转写结果，不要描述图片外观，不要编造图中没有的内容。"
)


def frame_ocr_user(hint: str = "") -> str:
    return ("转写这张图里的全部文字与公式。" + (f"\n上下文提示：{hint}" if hint else ""))


FRAME_NOTE_SYSTEM = (
    "你是图文笔记助手。给你一段视频的若干关键帧转写（含时间戳），请整理成**图文结合**的笔记：\n"
    "- 按时间顺序组织，每个关键帧一个小节，标题用该帧的核心内容命名；\n"
    "- 合并重复内容，突出**图里出现的定义、公式、流程、结论**；\n"
    "- 输出 summary（150 字内）+ sections（每节含 ts、title、content，content 可含列表/公式）。只输出 JSON。"
)


def frame_note_user(frame_texts: list[dict]) -> str:
    blocks = []
    for i, f in enumerate(frame_texts, 1):
        blocks.append(f"[{i}] 时间 {f.get('ts_label','')}\n{f.get('text','')[:1200]}")
    return ('输出 JSON：{"summary":"","sections":[{"ts":"","title":"","content":""}]}。\n'
            "关键帧转写：\n" + "\n\n".join(blocks))


# ---------- 检索优化 ----------
QUERY_REWRITE_SYSTEM = (
    "你是检索查询优化器。把用户口语化的问题改写成更适合关键词检索的查询：\n"
    "- 补全学科领域限定词（如「泰勒公式」→「泰勒公式 高等数学 数学分析 展开式」）；\n"
    "- 去掉「有什么」「是什么」这类疑问词；\n"
    "- 消歧：若词有多义（如「泰勒」可指歌手），加上问题所属学科作为限定；\n"
    "- 输出 2–3 条查询，用 JSON：{\"queries\":[\"\",\"\"]}。只输出 JSON。"
)


def query_rewrite_user(question: str) -> str:
    return f'输出 JSON：{{"queries":["",""]}}。\n用户问题：{question}'


RERANK_SYSTEM = (
    "你是检索结果相关性裁判。给定一个问题和若干片段，判断每个片段是否真的在回答该问题。\n"
    "严格标准：主题相同但领域不同（如问数学公式，片段讲同名歌手）判 0 分；只是字面重合但答非所问判 0–1 分；"
    "真正给出答案或关键信息的判 3–5 分。\n"
    "只输出 JSON：{\"scores\":[{\"i\":1,\"score\":0,\"why\":\"\"}]}"
)


def rerank_user(question: str, snippets: list[str]) -> str:
    blocks = "\n".join(f"[{i + 1}] {s[:400]}" for i, s in enumerate(snippets))
    return (f'输出 JSON：{{"scores":[{{"i":1,"score":0,"why":""}}]}}。\n'
            f"问题：{question}\n片段：\n{blocks}")


# ---------- 笔记整理 ----------
NOTE_TIDY_SYSTEM = (
    "你是知识管理助手。给定一个文件夹里的若干笔记标题与摘要，请给出整理方案：\n"
    "- 找出重复/高度相似的笔记（建议合并）；\n"
    "- 找出应该新建的子文件夹与归类建议；\n"
    "- 指出缺少的关键知识点。\n"
    "只输出 JSON：{\"summary\":\"\",\"merge\":[{\"ids\":[],\"reason\":\"\"}],"
    "\"folders\":[{\"name\":\"\",\"note_ids\":[],\"reason\":\"\"}],\"missing\":[\"\"]}"
)


def note_tidy_user(folder_name: str, items: list[dict]) -> str:
    lines = [f"- id={i.get('id')}｜{i.get('title','')}｜{(i.get('summary') or '')[:120]}" for i in items]
    return ('输出 JSON：{"summary":"","merge":[{"ids":[],"reason":""}],'
            '"folders":[{"name":"","note_ids":[],"reason":""}],"missing":[""]}。\n'
            f"文件夹：{folder_name}\n笔记：\n" + "\n".join(lines))
