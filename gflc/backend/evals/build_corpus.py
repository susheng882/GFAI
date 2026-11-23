# -*- coding: utf-8 -*-
"""生成 V3/N5 离线评测集（一次性脚本，可重复运行覆盖）。

产出：
  evals/corpus/<id>.json   32 份中文标注资料（pdf / video / note / question_bank 四类）
  evals/questions.json     24 条标注问题（含 4 条无答案诱饵、3 条语义问法）
  evals/VERSION            基线版本号

说明：
  - 每份资料按 chunk 切分，chunk 带 chunk_id / page / ts_start，便于离线检索与溯源校验。
  - 标注问题逐条写明 expected_chunk_ids（命中依据）、expected_chunk_keywords（应命中关键词）、
    expected_answer_points（应有答案要点），供 quality_eval.py --offline 计算六项指标。
  - 本脚本不联网、不调用任何 LLM；内容均为人工撰写的可检索中文语料。
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "corpus"


def doc(did, source_type, title, chunks):
    return {"id": did, "source_type": source_type, "title": title, "chunks": chunks}


def chunk(cid, text, page=None, ts_start=None):
    c = {"chunk_id": cid, "text": text}
    if page is not None:
        c["page"] = page
    if ts_start is not None:
        c["ts_start"] = ts_start
    return c


DOCS = [
    # ---------------- PDF（10 份）----------------
    doc("pdf-01", "pdf", "一元二次方程与求根公式", [
        chunk("pdf-01-c1", "一元二次方程的标准形式是 ax²+bx+c=0（a≠0）。求根公式为 x=(-b±√(b²-4ac))/(2a)。判别式 Δ=b²-4ac 决定根的情况：Δ>0 有两个不等实根，Δ=0 有两个相等实根，Δ<0 没有实根。理解推导过程比死记硬背更牢。", page=3),
        chunk("pdf-01-c2", "例题：解方程 x²-5x+6=0。代入 a=1、b=-5、c=6，判别式 Δ=25-24=1>0，x=(5±1)/2，得到 x₁=3、x₂=2。也可因式分解为 (x-2)(x-3)=0，结论一致。", page=4),
    ]),
    doc("pdf-02", "pdf", "导数与函数极值", [
        chunk("pdf-02-c1", "函数 f(x) 的导数 f'(x) 表示瞬时变化率。求极值步骤：先求导并令 f'(x)=0 得到驻点，再判断驻点两侧导数符号；导数由正变负是极大值点，由负变正是极小值点。幂函数求导法则 (xⁿ)'=n·xⁿ⁻¹。", page=12),
        chunk("pdf-02-c2", "例题 f(x)=x³-3x：f'(x)=3x²-3=3(x-1)(x+1)，驻点为 x=1 与 x=-1。x=-1 处导数由正变负，是极大值点；x=1 处导数由负变正，是极小值点。", page=13),
    ]),
    doc("pdf-03", "pdf", "函数单调性与奇偶性", [
        chunk("pdf-03-c1", "判断函数单调性可用定义法或导数法。导数法：区间内 f'(x)>0 则单调递增，f'(x)<0 则单调递减。奇偶性：f(-x)=f(x) 为偶函数，图像关于 y 轴对称；f(-x)=-f(x) 为奇函数，图像关于原点对称。", page=5),
    ]),
    doc("pdf-04", "pdf", "等差数列与等比数列", [
        chunk("pdf-04-c1", "等差数列通项 aₙ=a₁+(n-1)d，前 n 项和 Sₙ=n(a₁+aₙ)/2。推导方法：把数列正序与倒序相加，每一对的和都是 a₁+aₙ，共 n 对，所以 Sₙ=n(a₁+aₙ)/2。这个推导过程说明了公式的来源。", page=8),
        chunk("pdf-04-c2", "等比数列通项 aₙ=a₁·qⁿ⁻¹，前 n 项和 Sₙ=a₁(1-qⁿ)/(1-q)（q≠1）。", page=9),
    ]),
    doc("pdf-05", "pdf", "英语易混词 affect 与 effect", [
        chunk("pdf-05-c1", "affect 通常作动词，意为影响；effect 通常作名词，意为效果、结果。例：The rain affected our plans.（雨影响了我们的计划）；The effect was immediate.（效果立竿见影）。记忆口诀：affect 是动作（Action），effect 是结果（End）。", page=2),
    ]),
    doc("pdf-06", "pdf", "现在完成时与一般过去时", [
        chunk("pdf-06-c1", "现在完成时 have/has done 强调过去动作对现在的影响，常与 already、yet、since、for 连用；一般过去时 did 只描述过去某个时间点的事实，与现在没有关联。例：I have lost my key.（现在还没找到）；I lost my key yesterday.（只陈述昨天的事）。", page=7),
    ]),
    doc("pdf-07", "pdf", "牛顿第二定律", [
        chunk("pdf-07-c1", "牛顿第二定律：物体的加速度与所受合外力成正比，与质量成反比，方向与合外力相同，公式 F=ma。单位：力为牛顿 N，质量为 kg，加速度为 m/s²。解题时先做受力分析求出合力，再代入 F=ma。", page=4),
    ]),
    doc("pdf-08", "pdf", "物质的量与摩尔质量", [
        chunk("pdf-08-c1", "物质的量 n 的单位是摩尔（mol），1 mol 所含粒子数约为 6.02×10²³。摩尔质量 M 单位是 g/mol，数值上等于相对分子质量。三者关系：n=m/M。例：18 g 水的物质的量为 1 mol。", page=6),
    ]),
    doc("pdf-09", "pdf", "细胞结构：线粒体与叶绿体", [
        chunk("pdf-09-c1", "线粒体是细胞有氧呼吸的主要场所，被称为动力车间；叶绿体是植物进行光合作用的场所，把光能转化为化学能。两者都含有 DNA 和双层膜，但叶绿体含叶绿素，线粒体不含叶绿素。", page=3),
    ]),
    doc("pdf-10", "pdf", "气候类型判断方法", [
        chunk("pdf-10-c1", "气候类型判断：先看纬度位置区分热带、温带、寒带，再看海陆位置与降水季节分配。地中海气候夏季炎热干燥、冬季温和多雨；温带季风气候夏季高温多雨、冬季寒冷干燥。", page=2),
    ]),

    # ---------------- 视频（8 份）----------------
    doc("video-01", "video", "间隔重复与遗忘曲线", [
        chunk("video-01-c1", "间隔重复来自艾宾浩斯遗忘曲线：遗忘在学习后最初最快，随后逐渐变慢。要在快要忘记的时候复习，而不是每天重复同样的内容。推荐节奏为第 1 天、第 2 天、第 4 天、第 7 天、第 15 天逐步拉长间隔。", ts_start=45.0),
        chunk("video-01-c2", "一周复习计划示例：周一学新内容，周二复习周一的，周四再复习一次，周日做一次总回顾。每次复习只花几分钟主动回忆，而不是通读笔记。", ts_start=180.0),
    ]),
    doc("video-02", "video", "检索练习：主动回忆为什么有效", [
        chunk("video-02-c1", "检索练习也叫主动回忆，指合上书后自己把知识说出来或写出来。研究显示，同样的时间投入，主动回忆比反复阅读的记忆保持率高得多，因为提取过程本身会强化记忆通路。", ts_start=30.0),
        chunk("video-02-c2", "具体做法：读完一节后合上资料，写下能记住的要点；卡住的地方再回去看，并标记为待巩固。", ts_start=120.0),
    ]),
    doc("video-03", "video", "费曼学习法：加深理解", [
        chunk("video-03-c1", "费曼学习法四步：第一步选一个概念；第二步假装讲给完全不懂的人听；第三步卡壳时回到资料重新理解；第四步简化语言并用类比表达。核心是以教促学，用输出倒逼真正理解。", ts_start=60.0),
        chunk("video-03-c2", "加深理解的关键不是重复看，而是能否用自己的话解释清楚，并回答别人的追问。", ts_start=200.0),
    ]),
    doc("video-04", "video", "为什么要理解推导过程", [
        chunk("video-04-c1", "公式记不牢，往往是因为只背结论、不理解推导过程。数学公式几乎都能从更基本的原理推出来：求根公式来自配方，等差数列求和来自倒序相加。理解了推导过程，即使忘记结论也能现场推出来。", ts_start=90.0),
        chunk("video-04-c2", "建议每个重要公式都亲手推导一遍，写下每一步的依据，这就是理解记忆，比死记硬背牢得多。", ts_start=240.0),
    ]),
    doc("video-05", "video", "勾股定理及其证明", [
        chunk("video-05-c1", "勾股定理：直角三角形两条直角边 a、b 的平方和等于斜边 c 的平方，即 a²+b²=c²。赵爽弦图用四个全等直角三角形拼成正方形，通过面积相等给出证明。", ts_start=20.0),
        chunk("video-05-c2", "例题：两条直角边分别是 3 和 4，则斜边 c=√(9+16)=5。", ts_start=150.0),
    ]),
    doc("video-06", "video", "英语听力精听方法", [
        chunk("video-06-c1", "精听方法：选一段 1 到 2 分钟的材料，先盲听记大意，再逐句听写，对照原文标出生词和连读，最后跟读模仿。泛听重在培养语感，不追求每句都听懂。", ts_start=50.0),
    ]),
    doc("video-07", "video", "酸碱中和滴定", [
        chunk("video-07-c1", "酸碱中和滴定用已知浓度的标准液滴定待测液，以酚酞作指示剂，终点颜色为浅红色且 30 秒不褪色。计算公式 c(待测)=c(标准)·V(标准)/V(待测)。", ts_start=70.0),
    ]),
    doc("video-08", "video", "平抛运动的分解", [
        chunk("video-08-c1", "平抛运动可分解为水平方向的匀速直线运动与竖直方向的自由落体运动。水平位移 x=v₀t，竖直位移 y=½gt²。飞行时间只由高度决定，与初速度无关。", ts_start=40.0),
    ]),

    # ---------------- 笔记（8 份）----------------
    doc("note-01", "note", "常用数学公式卡", [
        chunk("note-01-c1", "# 常用数学公式\n- 一元二次方程求根公式：x=(-b±√(b²-4ac))/(2a)\n- 幂函数导数：(xⁿ)'=n·xⁿ⁻¹\n- 等差数列求和：Sₙ=n(a₁+aₙ)/2\n每个公式都要理解推导过程，不要死记硬背。"),
    ]),
    doc("note-02", "note", "英语易混词笔记", [
        chunk("note-02-c1", "# 易混词辨析\n- affect 是动词，意为影响；effect 是名词，意为效果。\n- 例句：The weather affected the effect of the plan.\n- 现在完成时 have done 强调对现在的影响；一般过去时 did 只陈述过去事实。"),
    ]),
    doc("note-03", "note", "一周复习计划笔记", [
        chunk("note-03-c1", "# 一周复习计划\n周一学新概念；周二主动回忆周一的内容；周四用间隔重复再测一次；周日用费曼法讲解本周内容。重点是合上资料自己复述，卡住时再翻书。"),
    ]),
    doc("note-04", "note", "错题本：函数极值", [
        chunk("note-04-c1", "# 错题：f(x)=x³-3x 求极值点\n错因：只求导，没有判断驻点两侧导数符号的变化。\n正解：f'(x)=3(x²-1)，驻点 x=±1；x=-1 处导数由正变负是极大值点，x=1 处是极小值点。"),
    ]),
    doc("note-05", "note", "导数视频大纲笔记", [
        chunk("note-05-c1", "# 导数视频大纲\n00:00 导数定义；05:00 求导法则；12:00 极值判定：导数由正变负为极大值点、由负变正为极小值点；18:00 例题 f(x)=x³-3x。"),
    ]),
    doc("note-06", "note", "复习卡片制作规范", [
        chunk("note-06-c1", "# 卡片制作要点\n一张卡片只问一个知识点；问题要具体，答案要简短可验证；正面写问题，背面写答案要点；加上来源页码或时间戳方便溯源；定期用检索练习做主动回忆自测。"),
    ]),
    doc("note-07", "note", "阅读笔记：如何抓重点", [
        chunk("note-07-c1", "# 如何抓重点\n先读标题和小标题建立框架；每段找主题句；用自己的话写摘要；把关键术语做成卡片；读完合上书复述一遍，检查理解漏洞。"),
    ]),
    doc("note-08", "note", "考前冲刺清单", [
        chunk("note-08-c1", "# 考前冲刺清单\n1. 用卡片做一轮主动回忆；2. 重做错题本里的错题；3. 亲手推导核心公式；4. 按间隔重复节奏复习薄弱点；5. 保证睡眠，不要通读全书。"),
    ]),

    # ---------------- 题库（6 份）----------------
    doc("qbank-01", "question_bank", "函数极值选择题", [
        chunk("qbank-01-c1", "题目：函数 f(x)=x³-3x 的极大值点是多少？A. x=-1　B. x=0　C. x=1　D. x=3。解析：求导得 f'(x)=3x²-3，令其为零得 x=±1；x=-1 处导数由正变负，是极大值点，故选 A。答案：A。"),
    ]),
    doc("qbank-02", "question_bank", "等差数列填空题", [
        chunk("qbank-02-c1", "题目：等差数列 a₁=1，d=2，求前 10 项和 S₁₀。解析：Sₙ=n(a₁+aₙ)/2，a₁₀=1+9×2=19，S₁₀=10×(1+19)/2=100。答案：100。"),
    ]),
    doc("qbank-03", "question_bank", "英语语法选择题", [
        chunk("qbank-03-c1", "题目：The new policy ___ our lives significantly. A. affect　B. affects　C. effect　D. effects。解析：主语 policy 是第三人称单数，空格需填及物动词作谓语，故选 affects。答案：B。"),
    ]),
    doc("qbank-04", "question_bank", "牛顿第二定律选择题", [
        chunk("qbank-04-c1", "题目：质量 2 kg 的物体受合力 10 N，加速度是多少？A. 2 m/s²　B. 5 m/s²　C. 10 m/s²　D. 20 m/s²。解析：由 F=ma 得 a=F/m=10/2=5 m/s²，故选 B。答案：B。"),
    ]),
    doc("qbank-05", "question_bank", "摩尔质量填空题", [
        chunk("qbank-05-c1", "题目：18 g 水的物质的量是多少 mol？解析：水的摩尔质量 M=18 g/mol，n=m/M=18/18=1 mol。答案：1 mol。"),
    ]),
    doc("qbank-06", "question_bank", "细胞结构判断题", [
        chunk("qbank-06-c1", "题目：线粒体是光合作用的场所。（判断对错）解析：错误。光合作用在叶绿体中进行，线粒体是有氧呼吸的主要场所。答案：错。"),
    ]),
]


def q(qid, question, kind, expected_chunk_ids, expected_chunk_keywords,
      expected_answer_points, is_decoy=False, semantic=False):
    return {
        "id": qid,
        "question": question,
        "kind": kind,
        "is_decoy": is_decoy,
        "is_semantic": semantic,
        "expected_chunk_ids": expected_chunk_ids,
        "expected_chunk_keywords": expected_chunk_keywords,
        "expected_answer_points": expected_answer_points,
    }


QUESTIONS = [
    q("q-01", "解一元二次方程 x²-5x+6=0，并写出求根过程。", "math",
      ["pdf-01-c1", "pdf-01-c2", "note-01-c1"],
      ["求根公式", "判别式", "x₁=3", "x₂=2"],
      ["a=1、b=-5、c=6", "Δ=1>0", "x₁=3、x₂=2", "求根公式"]),
    q("q-02", "直角三角形两条直角边分别是 3 和 4，求斜边长，并说明用的是哪个定理。", "math",
      ["video-05-c1", "video-05-c2"],
      ["勾股定理", "a²+b²=c²", "√(9+16)=5"],
      ["勾股定理", "a²+b²=c²", "斜边 c=5"]),
    q("q-03", "函数 f(x)=x³-3x 的极大值点和极小值点分别在 x 等于多少？给出求导过程。", "math",
      ["pdf-02-c1", "pdf-02-c2", "note-04-c1", "qbank-01-c1"],
      ["f'(x)=3x²-3", "x=-1", "x=1", "极大值点", "极小值点"],
      ["f'(x)=3(x²-1)", "驻点 x=±1", "x=-1 极大值点", "x=1 极小值点"]),
    q("q-04", "等差数列前 n 项和公式是什么？它是怎么推导出来的？", "math",
      ["pdf-04-c1", "note-01-c1"],
      ["Sₙ=n(a₁+aₙ)/2", "倒序相加", "推导过程"],
      ["Sₙ=n(a₁+aₙ)/2", "正序与倒序相加", "每对和为 a₁+aₙ"]),
    q("q-05", "affect 和 effect 的用法有什么区别？请各举一个例句。", "english",
      ["pdf-05-c1", "note-02-c1"],
      ["affect", "effect", "动词", "名词"],
      ["affect 作动词意为影响", "effect 作名词意为效果", "动词与名词的区分"]),
    q("q-06", "现在完成时和一般过去时有什么区别？请举例说明。", "english",
      ["pdf-06-c1", "note-02-c1"],
      ["现在完成时", "一般过去时", "have/has done", "对现在的影响"],
      ["现在完成时强调对现在的影响", "一般过去时只陈述过去事实", "常与 already/yet/since/for 连用"]),
    q("q-07", "英语里想表达“影响”这个动作时该用 affect 还是 effect？", "english",
      ["pdf-05-c1", "note-02-c1", "qbank-03-c1"],
      ["affect", "动词", "影响"],
      ["affect 是动词", "表示影响的动作用 affect"]),
    q("q-08", "如何用间隔重复的方法安排一周的复习计划？请给出具体到天的安排。", "study",
      ["video-01-c1", "video-01-c2", "note-03-c1"],
      ["间隔重复", "遗忘曲线", "周一", "周二", "周四", "周日"],
      ["第 1/2/4/7/15 天逐步拉长间隔", "周一学新、周二复习、周四再测、周日总回顾", "在快要忘记时复习"]),
    q("q-09", "检索练习为什么比反复阅读更有助于记忆？", "study",
      ["video-02-c1", "video-02-c2", "note-06-c1"],
      ["检索练习", "主动回忆", "记忆保持率", "提取"],
      ["主动回忆比反复阅读保持率高", "提取过程强化记忆通路", "合上资料自己复述"]),
    q("q-10", "费曼学习法的具体步骤有哪些？", "study",
      ["video-03-c1", "video-03-c2", "note-03-c1"],
      ["费曼学习法", "以教促学", "讲给不懂的人听", "卡壳"],
      ["选概念、讲给外行、卡壳回炉、简化类比四步", "核心是以教促学", "用自己的话解释"]),
    q("q-11", "牛顿第二定律的公式是什么，它说明了力、质量和加速度的什么关系？", "physics",
      ["pdf-07-c1", "qbank-04-c1"],
      ["F=ma", "合外力", "质量", "加速度"],
      ["公式 F=ma", "加速度与合外力成正比", "加速度与质量成反比"]),
    q("q-12", "物质的量、质量和摩尔质量之间怎么换算？18 克水是多少摩尔？", "chemistry",
      ["pdf-08-c1", "qbank-05-c1"],
      ["n=m/M", "摩尔质量", "1 mol"],
      ["n=m/M", "水的摩尔质量 18 g/mol", "18 g 水是 1 mol"]),
    q("q-13", "线粒体和叶绿体在功能上有什么区别？", "biology",
      ["pdf-09-c1", "qbank-06-c1"],
      ["线粒体", "叶绿体", "有氧呼吸", "光合作用"],
      ["线粒体是有氧呼吸主要场所", "叶绿体是光合作用场所", "叶绿体含叶绿素"]),
    q("q-14", "公式总是记不牢，不想死记硬背，应该怎么真正记住一个公式？", "study",
      ["video-04-c1", "video-04-c2", "pdf-01-c1", "note-01-c1"],
      ["推导过程", "理解记忆", "死记硬背", "求根公式来自配方"],
      ["理解推导过程而不是背结论", "每个公式亲手推导一遍", "忘记结论也能现场推出来"],
      semantic=True),
    q("q-15", "学完很快就忘了，有什么办法能加深理解而不是反复看？", "study",
      ["video-03-c1", "video-03-c2", "video-02-c1", "note-07-c1"],
      ["加深理解", "以教促学", "主动回忆", "复述"],
      ["用自己的话讲给不懂的人", "主动回忆与复述", "卡壳时回到资料重新理解"],
      semantic=True),
    q("q-16", "求根公式记不住，怎么才能理解它而不是硬背？", "math",
      ["pdf-01-c1", "video-04-c1", "pdf-04-c1"],
      ["推导", "配方", "判别式", "求根公式"],
      ["求根公式来自配方", "判别式决定根的情况", "理解推导后能现场推出来"],
      semantic=True),
    q("q-17", "制作复习卡片有哪些要点，才能让卡片真正可用？", "study",
      ["note-06-c1", "note-07-c1"],
      ["一张卡片只问一个知识点", "来源", "主动回忆", "答案要点"],
      ["一卡一知识点", "答案简短可验证并带来源", "定期用检索练习自测"]),
    q("q-18", "怎么判断一个函数是单调递增还是单调递减？", "math",
      ["pdf-03-c1", "note-05-c1"],
      ["f'(x)>0", "f'(x)<0", "单调递增", "单调递减"],
      ["导数大于零则单调递增", "导数小于零则单调递减", "也可用定义法判断"]),
    q("q-19", "等差数列已知首项 a₁=1、公差 d=2，前 10 项和怎么算？", "math",
      ["qbank-02-c1", "pdf-04-c1"],
      ["S₁₀=100", "Sₙ=n(a₁+aₙ)/2", "a₁₀=19"],
      ["a₁₀=19", "S₁₀=10×(1+19)/2=100", "用等差数列求和公式"]),
    q("q-20", "语法题 The new policy ___ our lives 应该填 affect 还是 effect，为什么？", "english",
      ["qbank-03-c1", "pdf-05-c1"],
      ["affects", "第三人称单数", "动词"],
      ["需要动词作谓语", "主语第三人称单数用 affects", "effect 是名词不合适"]),

    # ---- 无答案诱饵（4 条）----
    q("d-01", "今天天气怎么样？适合出门跑步吗？", "decoy", [], [], [], is_decoy=True),
    q("d-02", "帮我推荐几首适合跑步时听的流行歌曲。", "decoy", [], [], [], is_decoy=True),
    q("d-03", "现在沪深 300 指数是多少点？", "decoy", [], [], [], is_decoy=True),
    q("d-04", "帮我订一张明天去上海的高铁票。", "decoy", [], [], [], is_decoy=True),
]


def main():
    CORPUS.mkdir(parents=True, exist_ok=True)
    for d in DOCS:
        (CORPUS / f"{d['id']}.json").write_text(
            json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    (HERE / "questions.json").write_text(
        json.dumps(QUESTIONS, ensure_ascii=False, indent=2), encoding="utf-8")
    if not (HERE / "VERSION").exists():
        (HERE / "VERSION").write_text("v1.0\n", encoding="utf-8")
    types = {}
    for d in DOCS:
        types[d["source_type"]] = types.get(d["source_type"], 0) + 1
    print(f"已生成 {len(DOCS)} 份资料：{types}")
    print(f"已生成 {len(QUESTIONS)} 条问题（诱饵 {sum(1 for x in QUESTIONS if x['is_decoy'])}，"
          f"语义问法 {sum(1 for x in QUESTIONS if x['is_semantic'])}）")


if __name__ == "__main__":
    main()
