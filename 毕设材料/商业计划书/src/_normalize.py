# -*- coding: utf-8 -*-
"""把未重绘的旧图统一到标准 680×960 画布：删原图题/外框/背景，等比嵌入统一内容区，留白补「设计依据」栏。"""
import re
from pathlib import Path
from lxml import etree

from _figlib import W, H, INK, GREY, RED, r, t, ln, icon, frame

ROOT = Path(__file__).parent
SVGNS = "http://www.w3.org/2000/svg"
Q = "{" + SVGNS + "}"

CONTENT_TOP, CONTENT_BOT, CW = 76, 852, 632
OLD_TOP, OLD_BOT_PAD = 66, 66

# 旧图 -> (标题, 副标题, 图例, 中文图题, 英文图题, 补充要点)
SPEC = {
    "图2-1_部署拓扑与服务编排.svg": (
        "服务器选型与六服务矩阵部署架构", "第二章 · 服务器规格卡 · 3×2 服务矩阵 · 依赖矩阵 · 技术方案 2.3 / 5.3 / 5.8",
        "◆ 架构评审新增　·　六服务矩阵无流程箭头　·　数据出处：技术方案 2.3 / 5.8",
        "图 2-1　服务器选型与六服务矩阵部署架构", "Fig. 2-1　Server selection and six-service deployment matrix",
        ["选型：2C / 4G / ≥60 GB SSD 轻量应用服务器，境内节点满足 G7 备案，活动价 ¥188/年 ≈¥15.7/月。",
         "无 GPU 为硬约束：LLM 全走云 API，ASR / OCR / Embedding 在服务器 CPU 本地跑。",
         "六服务矩阵：nginx / api / worker（profile 隔离）/ db / redis / minio；左下 6×5 依赖矩阵表。",
         "K1 大文件直传、K2 长任务入队、K3 任务态反馈与图 5-1、5-2 编号一致。",
         "磁盘水位 80% 冻结、单任务 5 GB 配额、certbot 自动续期构成贯穿运维面。"],
    ),
    "图3-1_AI内容处理管线与三档模型路由.svg": (
        "AI 内容处理管线与三档模型路由", "第三章 · 三级取材降本链 · 分块与契约 · 双索引 RAG · 技术方案 3.1 / 3.2",
        "◆ 吸收自 BiliNote　·　三档路由　·　数据出处：技术方案 3.1 / 3.2 / 3.6",
        "图 3-1　AI 内容处理管线与三档模型路由", "Fig. 3-1　AI content pipeline and three-tier model routing",
        ["三级取材：平台字幕优先 → 音轨下载 → 本地 faster-whisper 转写，命中字幕单视频成本降一个量级。",
         "按请求体积预算二分切块，多轮归并；输出走 JSON Schema 契约，失败触发自修复重试。",
         "轻 / 中 / 强三档按任务难度路由；Chroma 双索引（笔记 H2/H3 块 + 转写 15 段滑窗）。",
         "RAG 限 50 段，回答必带来源时间戳；溯源跳转为 P0 硬字段。"],
    ),
    "图3-2_成本护栏判定与四级降级流程图.svg": (
        "成本护栏判定与四级降级流程图", "第三章 · 三重护栏 · 决策判定 · 四级降级 · 技术方案 3.3 / 3.4",
        "菱形＝判定　实线＝主路径　虚线＝降级路径　·　数据出处：技术方案 3.3 / 3.4",
        "图 3-2　成本护栏判定与四级降级流程图", "Fig. 3-2　Cost guardrail decision and four-level degradation flow",
        ["三重护栏：单用户每日 token 配额、单任务 token 上限、全平台日成本阈值。",
         "四级降级：强档换中档 → 长上下文改分段 → 缓存命中复用 → 本地模型兜底。",
         "触发上限时自动降档而非失败，用户感知是「慢一点」而不是「用不了」。",
         "阈值按 §5.8 真实报价设初值；任何降级都写入结构化日志与成本看板。"],
    ),
    "图4-1_测试体系分层与G1-G7上线门禁.svg": (
        "测试体系分层与 G1–G7 上线门禁", "第四章 · 测试金字塔 · 四指标闸门 · 七域上线标准 · 技术方案 4.1–4.4",
        "◆ 企业级上线标准　·　任一指标较上版下降 >3 pp 即回滚　·　数据出处：技术方案 4.3",
        "图 4-1　测试体系分层与 G1–G7 上线门禁", "Fig. 4-1　Testing pyramid and G1–G7 release gates",
        ["金字塔五层：单元 / 契约 / 集成 / 端到端 / 探索性；AI 评测集不少于 300 条固定样本。",
         "四指标：字段完整率、知识点召回率、幻觉率、人工可用率；Prompt 或模型变更前后各跑一遍。",
         "G1–G7 覆盖技术验证、性能、合规、数据一致性、存储、观测、备案七个域。",
         "发布前 48 小时执行 Go/No-Go 逐域核验；本机已执行验证见 §4.4。"],
    ),
    "图5-1_系统技术架构图.svg": (
        "系统技术架构图（七层 · 架构评审修订版）", "第五章 · 编号式分层 · 中英对照层标签 · K1–K3 关键链路 · 技术方案 2 / 5",
        "◆ 评审新增　·　K1 直传 / K2 入队 / K3 反馈　·　（P2）二期规划　·　数据出处：技术方案 2",
        "图 5-1　系统技术架构图（七层 · 架构评审修订版）", "Fig. 5-1　Seven-layer system architecture (review revision)",
        ["七层：① 接入 → ② 网关 → ③ 应用 → ④ 异步 Worker → ⑤ AI 管线 → ⑥ 持久层 → ⑦ 基础设施通栏。",
         "每层右上角标注技术选型；模块盒尺寸按统一网格三档排布，杜绝大小不一。",
         "◆ 标记 2026-11-14 架构评审新增：Worker 容器、预签名直传、轮询回路、Alembic、磁盘治理、告警、certbot。",
         "K1–K3 编号与图 2-1、2-2、2-3、5-2 互相锚定，论文可跨图引用。"],
    ),
    "图5-2_功能全景流程图.svg": (
        "功能全景流程图（38 项功能五阶段）", "第五章 · 素材接入 → 调度 → AI 管线 → 知识产品 → 学习闭环 · 产品报告第四章",
        "实线＝同步　虚线＝闭环回授　◆ 新增　·　数据出处：产品报告第四章（八）",
        "图 5-2　功能全景流程图（38 项功能五阶段）", "Fig. 5-2　End-to-end functional flow of 38 features",
        ["五阶段严格对齐：素材接入 → 入口与调度 → AI 处理管线 → 知识产品层 → 学习闭环层。",
         "38 项功能清单映射：主线 27 项 / V1.5 8 项 / 规划池 3 项。",
         "错题回炉以虚线回授箭头从学习闭环回到向量化索引，形成可演示的闭环证据。",
         "每步箭头带动作标注（统一提交、异步下发、结构化产物落库等），读图即读流程。"],
    ),
    "图5-4_采购清单与一次付费多模型方案.svg": (
        "采购清单与一次付费多模型方案", "第五章 · 三样必买 · Token Plan 对比 · 毕设 8 个月总账 · 技术方案 5.8",
        "★ 推荐方案　·　⚠ 落地前核对项　·　数据出处：技术方案 5.8 · 2026-11-14 实采",
        "图 5-4　采购清单与一次付费多模型方案", "Fig. 5-4　Procurement list and one-payment multi-model plan",
        ["必买仅 3 样：服务器 ¥188/年、大模型订阅 ¥39–79/月、域名 ¥60–80/年；SSL / 备案 / 自建存储 / 本地 ASR 全为 ¥0。",
         "阿里云百炼 Token Plan 个人版 Lite ¥39/月（新客 ¥19.5），池内 150+ 模型共享额度。",
         "池内覆盖 Qwen 全系、DeepSeek-V4-Pro、GLM、Kimi、Fun-ASR，三档路由与 ASR 兜底一订阅解决。",
         "毕设 8 个月总账 ¥560–880；叠加阿里云学生 ¥300 抵扣金，实付可低至 ¥260 量级。",
         "⚠ 核对：个人订阅的商用条款、API 程序化调用是否走 Credits 抵扣；任一不满足即回退按量付费。"],
    ),
    "图6-1_16周工程里程碑与排期映射甘特图.svg": (
        "16 周工程里程碑与排期映射甘特图", "第六章 · 四阶段 P1–P4 · 周刻度对齐 · 依赖箭头与出口条件 · 技术方案 6",
        "■ 阶段条　→ 依赖　◆ 技术验证门　·　数据出处：技术方案 6",
        "图 6-1　16 周工程里程碑与排期映射甘特图", "Fig. 6-1　16-week milestone and schedule Gantt chart",
        ["四阶段 P1–P4 与周刻度严格对齐，阶段间依赖箭头标明前后置关系。",
         "G1 技术验证门（第 3 周末）：三条解析链路各跑通 10 个真实样本、成本基线可测。",
         "P2 出口：40 份评测集字段完整率 ≥95%；Worker 队列 + 预签名上传 + Alembic 全部就位。",
         "可牺牲项（视频时间戳溯源增强）在第 11 周未达标即降 V1.5，避免范围膨胀拖垮主线。"],
    ),
    "图7-1_数据模型与知识产物关系图.svg": (
        "数据模型与知识产物关系图（ER）", "第七章 · 九类实体 · 1:N 关系 · 四存储职责边界 · 技术方案 2.1 / 2.5 / 2.7",
        "矩形＝实体　连线＝1:N　◆ 硬字段　·　数据出处：技术方案 2.1",
        "图 7-1　数据模型与知识产物关系图（ER）", "Fig. 7-1　Entity-relationship model of data and knowledge artifacts",
        ["九类实体：users / materials / tasks / knowledge_units / notes / cards / review_logs / plans / usage。",
         "pgvector vector(1024) 与业务表同库，JOIN 即可完成溯源，无需跨库二次查询。",
         "时间戳为 P0 硬字段：每个知识单元必须可回指原始视频秒数或 PDF 页码。",
         "职责边界：PG 存业务与产物、Redis 只存小状态、MinIO 存对象、/data/tmp 存中间产物。"],
    ),
    "图9-1_盈利模式四层结构与单位经济模型.svg": (
        "盈利模式四层结构与单位经济模型", "第九章 · 免费额度 → 个人订阅 → 团体授权 → 增值服务 · 产品报告第九章",
        "◆ 2026-11-14 实价校准　·　数据出处：产品报告第九章 · 技术方案 5.8",
        "图 9-1　盈利模式四层结构与单位经济模型", "Fig. 9-1　Four-layer revenue model and unit economics",
        ["四层按启动顺序排列，逐层以前一层积累的数据为开通条件，不一次性铺开。",
         "单用户月成本 1.5–2.5 元 vs 客单价 10–12 元，毛利约八成；约 11 个付费用户覆盖平台固定支出。",
         "第九章成本表已按实价校准：云服务器 15.7 元/月、对象存储 0 元、LLM 60 元，合计约 82 元/月。",
         "订阅制（Token Plan ¥39–79/月）可锁定多模型能力，替代按量付费的成本浮动。"],
    ),
}


def strip_old(svg_text: str, H_old: int):
    root = etree.fromstring(svg_text.encode("utf-8"))
    # 删除：背景 / 外框 / 原主副标题 / 原图题 / 原图例行 / defs（引用改指向统一 marker）
    for el in list(root):
        if not isinstance(el.tag, str):   # 跳过 XML 注释 / 处理指令
            continue
        tag = etree.QName(el).localname
        if tag == "defs":
            root.remove(el)
            continue
        if tag == "rect":
            x = float(el.get("x", 0)); y = float(el.get("y", 0))
            w = float(el.get("width", 0)); h = float(el.get("height", 0))
            if (x == 0 and y == 0 and w >= 680) or (x == 8 and y == 8 and w >= 660):
                root.remove(el); continue
        if tag == "text":
            yv = el.get("y", "")
            s = "".join(el.itertext()).strip()
            try:
                yf = float(yv)
            except ValueError:
                yf = -1
            if yf in (40.0, 58.0) or re.match(r"^图\s*\d+[-–]\d+", s) or s.startswith("Fig."):
                root.remove(el); continue
            if yf > H_old - 105 and ("●" in s or "数据出处" in s or "实线" in s or "图例" in s):
                root.remove(el); continue
        if tag == "line":
            # 原图标题下的横线（y≈66）与图例分隔线
            try:
                if abs(float(el.get("y1", -1)) - 66) < 1 and abs(float(el.get("y2", -1)) - 66) < 1:
                    root.remove(el); continue
            except ValueError:
                pass
    inner = "".join(etree.tostring(c, encoding="unicode") for c in root)
    # 统一 marker 引用
    inner = re.sub(r'url\(#([A-Za-z0-9_-]+)\)', 'url(#ar)', inner)
    return inner


def build(fname, spec):
    p = ROOT / fname
    s = p.read_text(encoding="utf-8")
    m = re.search(r'viewBox="0 0 680 ([\d.]+)"', s)
    H_old = float(m.group(1))
    title, sub, legend, cap_cn, cap_en, pts = spec
    inner = strip_old(s, H_old)

    ch = H_old - OLD_TOP - OLD_BOT_PAD
    scale = min(CW / 680, (CONTENT_BOT - CONTENT_TOP) / ch)
    dx = 24 + (CW - 680 * scale) / 2
    dy = CONTENT_TOP - OLD_TOP * scale
    body = [f'<g transform="translate({dx:.2f},{dy:.2f}) scale({scale:.5f})">{inner}</g>']

    used = ch * scale
    box_y = CONTENT_TOP + used + 8
    box_h = CONTENT_BOT - box_y
    if box_h >= 42:
        body.append(r(24, box_y, CW, box_h, "#FCFCFC", "#999999", 0.8, "5 3"))
        body.append(icon("book", 32, box_y + 7, 0.66))
        body.append(t(54, box_y + 18, "设计依据与关键参数（统一补充栏）", 8.6, weight="bold"))
        n = max(1, min(len(pts), int((box_h - 30) / 18)))
        for i, s2 in enumerate(pts[:n]):
            body.append(t(36, box_y + 34 + i * 18, f"{i+1}. {s2}", 7.8, fill="#333333"))
    else:
        body.append(t(24, CONTENT_BOT + 2, "", 7))
    # 内容区细框（严格对齐）
    body.append(r(24, CONTENT_TOP - 2, CW, CONTENT_BOT - CONTENT_TOP + 4, "none", "#DDDDDD", 0.5))
    svg = frame(title, sub, "\n".join(body), legend, cap_cn, cap_en, tag="GFLC · 2026")
    p.write_text(svg, encoding="utf-8")
    print(f"  normalized {fname}: {H_old:.0f} -> 960, scale {scale:.3f}, extra {box_h:.0f}px")


if __name__ == "__main__":
    # 2026-11-15：全部 18 张图已由 _build_figs_a/c/d/e/f 生成或已归一化完成。
    # 本脚本仅作历史保留，默认不再执行——重复归一化会二次缩放并放大字号，造成文字压盖。
    KEEP = set()   # 如需单独重跑某张旧图，把文件名加入此集合
    for k, v in SPEC.items():
        if k not in KEEP:
            continue
        if (ROOT / k).exists():
            build(k, v)
        else:
            print("  MISSING", k)
    print("  normalize: skipped (all figures owned by generators)")
