# -*- coding: utf-8 -*-
"""生成重点学术图 B 组：图 2-2 / 2-3 / 3-3（泳道 + 标准流程图符号拆解，统一 680×960 画布）。"""
from pathlib import Path
from _figlib import *

ROOT = Path(__file__).parent
X0, CW = 24, 632


def node(x, y, w, h, title, sub="", kind="proc", fill="#FFFFFF"):
    """标准流程图符号：proc 矩形 / term 圆角起止 / dec 菱形 / data 平行四边形。"""
    o = []
    if kind == "term":
        o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h/2}" fill="{fill}" stroke="{INK}" stroke-width="1.2"/>')
    elif kind == "dec":
        o.append(f'<path d="M {x+w/2},{y} L {x+w},{y+h/2} L {x+w/2},{y+h} L {x},{y+h/2} Z" fill="{fill}" stroke="{INK}" stroke-width="1.1"/>')
    elif kind == "data":
        o.append(f'<path d="M {x+10},{y} L {x+w},{y} L {x+w-10},{y+h} L {x},{y+h} Z" fill="{fill}" stroke="{INK}" stroke-width="1.1"/>')
    else:
        o.append(r(x, y, w, h, fill, INK, 1.1))
    lines = [title] + ([sub] if sub else [])
    for i, s in enumerate(lines):
        yy = y + h / 2 + 3 - (len(lines) - 1) * 5.5 + i * 11
        o.append(t(x + w / 2, yy, s, 7.8 if i == 0 else 7.0, "middle", "bold" if i == 0 else "", INK if i == 0 else "#555555"))
    return "\n".join(o)


def swimlane(x, y, w, h, label, sub="", fill="#FFFFFF"):
    o = [r(x, y, w, h, fill, "#BBBBBB", 0.7), r(x, y, 78, h, "#F0F0F0", "#BBBBBB", 0.7)]
    o.append(t(x + 6, y + 18, label, 8.2, weight="bold"))
    if sub:
        o.append(t(x + 6, y + 32, sub, 7.0, fill=GREY))
    return "\n".join(o)


def legend_flow(y):
    return "\n".join([
        r(X0, y, CW, 56, "#FAFAFA", "#999999", 0.8),
        node(X0 + 12, y + 14, 62, 26, "处理", kind="proc"),
        t(X0 + 82, y + 31, "处理步骤", 7.6),
        f'<path d="M {X0+152},{y+14} L {X0+186},{y+27} L {X0+152},{y+40} L {X0+118},{y+27} Z" fill="#FFFFFF" stroke="{INK}" stroke-width="1"/>',
        t(X0 + 194, y + 31, "判定分支", 7.6),
        f'<rect x="{X0+262}" y="{y+14}" width="62" height="26" rx="13" fill="#FFFFFF" stroke="{INK}" stroke-width="1"/>',
        t(X0 + 332, y + 31, "起止", 7.6),
        t(X0 + 382, y + 31, "实线＝同步调用　虚线＝异步 / 落库　朱红＝异常分支", 7.6, fill="#444444"),
    ])


def fig_2_2():
    b = []
    b.append(t(X0, 78, "A　四泳道流程图：长任务从提交到产物落库（◆ 架构评审拍板）", 9, weight="bold"))
    lanes = [("① 浏览器", "React SPA"), ("② API", "FastAPI"), ("③ Redis", "List / 状态"), ("④ Worker", "独立进程 + PG")]
    ly = [88, 182, 276, 370]
    for i, (lab, sub) in enumerate(lanes):
        b.append(swimlane(X0, ly[i], CW, 90, lab, sub))
    # 节点（x 从 112 起，每格 106）
    b.append(node(112, 106, 88, 44, "提交任务", "POST /api/v1/tasks", "term"))
    b.append(node(112, 200, 88, 44, "鉴权 + 配额", "生成 task_id", "proc"))
    b.append(node(218, 200, 88, 44, "体积判定", "> 阈值？", "dec"))
    b.append(node(218, 294, 88, 44, "LPUSH", "载荷 ≤4 KB", "data"))
    b.append(node(324, 200, 88, 44, "返回 202", "task_id / 轮询串", "term"))
    b.append(node(112, 388, 88, 44, "BRPOPLPUSH", "取任务 + 心跳", "proc"))
    b.append(node(218, 388, 88, 44, "执行管线", "checkpoint 分段", "proc"))
    b.append(node(324, 388, 88, 44, "段失败？", "重试 ≤3", "dec"))
    b.append(node(430, 388, 88, 44, "产物写 PG", "缓存 + 版本", "data"))
    b.append(node(430, 294, 88, 44, "状态回写", "done / failed", "data"))
    b.append(node(536, 106, 88, 44, "轮询 GET", "3 s → 15 s 退避", "proc"))
    b.append(node(536, 200, 88, 44, "拿到产物", "渲染 / 导出", "term"))
    b.append(node(536, 388, 88, 44, "死信队列", "人工排查", "data", "#F7F7F7"))
    # 连线
    A = lambda x1, y1, x2, y2, dash="", arrow=True: ln(x1, y1, x2, y2, INK, 1, dash, arrow)
    A(200, 128, 156, 200)
    A(200, 222, 216, 222)
    A(262, 244, 262, 294)
    A(306, 316, 368, 244)
    A(412, 222, 534, 222)
    b.append(path("M 156,200 L 156,388 L 110,388", dash="4 3", arrow=True))
    A(306, 316, 262, 316)
    A(200, 410, 216, 410)
    A(306, 410, 322, 410)
    A(412, 410, 428, 410)
    A(474, 388, 474, 338)
    A(474, 294, 580, 294)
    A(580, 294, 580, 150)
    b.append(t(586, 240, "状态查询", 7.0, fill=GREY))
    A(580, 200, 536, 200)
    A(580, 128, 580, 200)
    b.append(path("M 362,432 L 362,452 L 580,452 L 580,434", stroke=RED, dash="4 3", arrow=True))
    b.append(t(386, 446, "重试耗尽 → 死信（不无限重试）", 7.2, fill=RED))
    b.append(t(328, 268, "K1 大文件走图 2-3", 7.0, fill=RED))
    # 阶段带
    b.append(r(X0, 468, CW, 26, INK, INK, 0.6))
    for i, s in enumerate(["阶段 1　提交与入队", "阶段 2　异步执行", "阶段 3　状态与产物", "阶段 4　轮询与交付"]):
        b.append(t(X0 + 10 + i * 158, 485, s, 7.8, weight="bold", fill="#FFFFFF"))

    b.append(t(X0, 508, "B　关键参数与失败分支（逐项可核验）", 9, weight="bold"))
    rows = [
        ["队列原语", "Redis List · BRPOPLPUSH + 心跳回收", "取出即进 processing 备份队列，Worker 崩溃可由定时任务回收"],
        ["载荷上限", "≤4 KB，仅存 task_id / object_key / 参数", "大对象一律走 MinIO，不把视频字节塞进 Redis"],
        ["硬超时", "GFLC_TASK_TIMEOUT_MIN = 60 min", "超时未心跳 → failed，保留已完成段，不整单丢弃"],
        ["断点续传", "按段 checkpoint 写 PG", "失败重跑只补未完成段（吸收 BiliNote 模式）"],
        ["并发与降级", "WORKER_CONCURRENCY = 4", "超长视频 P1 分片；API 进程不跑任何 CPU 密集管线"],
        ["前端轮询", "3 s → 15 s 指数退避，上限 5 min", "不依赖 WebSocket / 长连接，G2 P95 ≤3 s 不被拖垮"],
        ["异常出口", "重试耗尽 → 死信 List（独立）", "人工排查后清理；不自动无限重试，避免成本失控"],
    ]
    tb, hh = table(X0, 518, [92, 216, 324], ["项目", "拍板值", "理由与落点"], rows,
                   header_h=24, row_h=32, font=7.6, aligns=["start", "start", "start"])
    b.append(tb)
    y = 518 + hh + 8
    b.append(legend_flow(y))
    b.append(t(X0, y + 62, "注 1：40 分钟视频用 faster-whisper 转写可占满 2 核十余分钟，与 G2「P95 ≤3 s」天然互斥，故 API / Worker 必须分进程。", 7.8, fill="#444444"))
    b.append(t(X0, y + 78, "注 2：K1 / K2 / K3 编号与图 5-1、图 5-2、图 2-1 一致；本图对应 K2 长任务入队与 K3 任务态反馈。", 7.8, fill="#444444"))
    return frame("长任务异步执行链路流程图拆解",
                 "第二章 · 四泳道 + 标准流程符号（起止 / 处理 / 判定 / 数据）· 技术方案 2.5",
                 "\n".join(b),
                 "圆角＝起止　矩形＝处理　菱形＝判定　平行四边形＝数据 / 存储　虚线＝异步　朱红＝异常出口",
                 "图 2-2　长任务异步执行链路流程图拆解",
                 "Fig. 2-2　Flowchart decomposition of the long-running asynchronous task pipeline",
                 tag="GFLC · 2026")


def fig_2_3():
    b = []
    b.append(t(X0, 78, "A　四泳道流程图：大文件预签名直传三步协议（◆ 架构评审拍板）", 9, weight="bold"))
    lanes = [("① 浏览器", "React SPA"), ("② API", "FastAPI"), ("③ MinIO", "对象存储"), ("④ PG", "业务库")]
    ly = [88, 182, 276, 370]
    for i, (lab, sub) in enumerate(lanes):
        b.append(swimlane(X0, ly[i], CW, 90, lab, sub))
    b.append(node(112, 106, 88, 44, "选择文件", "视频 / PDF", "term"))
    b.append(node(112, 200, 88, 44, "签发请求", "name/size/type", "proc"))
    b.append(node(218, 200, 88, 44, "合规判定", "配额 / 水位？", "dec"))
    b.append(node(324, 200, 88, 44, "生成预签名", "PUT URL + key", "proc"))
    b.append(node(430, 200, 88, 44, "返回 URL", "有效期 15 min", "term"))
    b.append(node(430, 294, 88, 44, "PUT 直传", "字节流不进 API", "data"))
    b.append(node(430, 106, 88, 44, "上传进度", "XHR / 分片", "proc"))
    b.append(node(536, 106, 88, 44, "confirm", "POST /uploads", "proc"))
    b.append(node(536, 294, 88, 44, "HEAD/stat", "实际大小 / ETag", "data"))
    b.append(node(536, 388, 88, 44, "写 materials", "建解析任务", "data"))
    b.append(node(324, 388, 88, 44, "stat 一致？", "以 stat 为准", "dec"))
    b.append(node(112, 388, 88, 44, "拒绝 / 清理", "超配额或残留", "term", "#F7F7F7"))
    A = lambda x1, y1, x2, y2, dash="": ln(x1, y1, x2, y2, INK, 1, dash, True)
    A(200, 128, 156, 200)
    A(200, 222, 216, 222)
    A(306, 222, 322, 222)
    A(412, 222, 428, 222)
    A(474, 244, 474, 294)
    A(474, 338, 474, 388)
    A(474, 294, 534, 294)
    A(474, 150, 580, 150)
    A(580, 150, 580, 200)
    b.append(path("M 580,200 L 580,268 L 534,268 L 534,294", arrow=True))
    b.append(path("M 580,338 L 580,360 L 368,360 L 368,388", arrow=True))
    A(324, 410, 200, 410)
    b.append(t(212, 402, "否", 7.2, fill=RED))
    b.append(t(416, 402, "是", 7.2, fill=GREY))
    b.append(path("M 474,244 L 508,244 L 508,128 L 518,128", dash="4 3", arrow=True))
    b.append(t(486, 176, "进度回传（不经过 API 业务层）", 7.0, fill=GREY))
    b.append(r(X0, 468, CW, 26, INK, INK, 0.6))
    for i, s in enumerate(["第 1 步　签发 presign", "第 2 步　浏览器直传 MinIO", "第 3 步　confirm 以 stat 为准", "异常　拒绝 / 清理残留"]):
        b.append(t(X0 + 10 + i * 158, 485, s, 7.8, weight="bold", fill="#FFFFFF"))

    b.append(t(X0, 508, "B　协议约束、安全边界与失败分支", 9, weight="bold"))
    rows = [
        ["签发入参", "文件名 / 大小 / MIME / 用户配额", "服务端按白名单 MIME 与 UPLOAD_MAX 校验，不信任客户端声明"],
        ["预签名 URL", "PUT 限定 object_key，有效期 15 min", "最小权限：只能写这一个 key，不能列举 / 删除桶内对象"],
        ["直传通道", "浏览器 → MinIO（Nginx 反代或直连）", "字节流不进 API 进程，两个并发 1 GB 上传不打爆 4 GB 内存"],
        ["confirm 校验", "以 MinIO HEAD/stat 的 size / ETag 为准", "防止「客户端声称成功但对象不完整」；不一致标记失败并清理"],
        ["磁盘治理", "水位 ≥80% 冻结上传；单任务 ≤5 GB 配额", "与 5.7 节磁盘水位告警、临时文件清理联动"],
        ["幂等与版本", "object_key 由 task_id + 内容哈希生成", "重复 confirm 不产生第二条 materials 记录，开启桶版本控制"],
        ["失败分支", "超配额 / 水位冻结 / stat 不一致 / URL 过期", "统一返回明确错误码，前端展示「部分成功」而非静默吞掉"],
    ]
    tb, hh = table(X0, 518, [92, 216, 324], ["项目", "协议约定", "理由与落点"], rows,
                   header_h=24, row_h=32, font=7.6, aligns=["start", "start", "start"])
    b.append(tb)
    y = 518 + hh + 8
    b.append(legend_flow(y))
    b.append(t(X0, y + 62, "注 1：评审动机——隐含的「Nginx → FastAPI」上传路径会让 1 GB 视频流经 API 进程，而「上传文件优先」是核心入口策略。", 7.8, fill="#444444"))
    b.append(t(X0, y + 78, "注 2：本图对应 K1 大文件直传；与图 2-2 的 K2 入队链路在 materials 落库处衔接。", 7.8, fill="#444444"))
    return frame("大文件预签名直传协议流程图拆解",
                 "第二章 · 三步协议 + 四泳道 + 判定分支 · 技术方案 2.6 / 5.6 / 5.7",
                 "\n".join(b),
                 "圆角＝起止　矩形＝处理　菱形＝判定　平行四边形＝数据 / 存储　虚线＝旁路　朱红＝异常出口",
                 "图 2-3　大文件预签名直传协议流程图拆解",
                 "Fig. 2-3　Flowchart decomposition of the presigned direct-upload protocol",
                 tag="GFLC · 2026")


def fig_3_3():
    b = []
    b.append(t(X0, 78, "A　五步链路流程图：NL 问数仪表盘（P2 增强，双保险约束）", 9, weight="bold"))
    b.append(swimlane(X0, 88, CW, 78, "① 交互层", "用户输入 / 图表渲染"))
    b.append(swimlane(X0, 166, CW, 78, "② 模型层", "轻档 LLM · 意图解析"))
    b.append(swimlane(X0, 244, CW, 78, "③ 数据层", "白名单模板 · PG 聚合"))
    b.append(swimlane(X0, 322, CW, 78, "④ 契约层", "Schema 校验 · 渲染"))
    b.append(node(112, 104, 94, 44, "自然语言提问", "例：本周掌握度趋势", "term"))
    b.append(node(112, 182, 94, 44, "意图解析", "轻档 · <0.001 元/次", "proc"))
    b.append(node(230, 182, 94, 44, "命中模板？", "白名单枚举", "dec"))
    b.append(node(348, 260, 94, 44, "参数填充 + SQL", "后端生成 · 只读视图", "proc"))
    b.append(node(466, 260, 94, 44, "结果合理？", "空集 / 超阈 / 越权", "dec"))
    b.append(node(466, 338, 94, 44, "图表契约校验", "JSON Schema", "proc"))
    b.append(node(348, 338, 94, 44, "通过？", "自修复 ≤2 次", "dec"))
    b.append(node(230, 338, 94, 44, "渲染图表", "附数据口径与时间窗", "term"))
    b.append(node(112, 338, 94, 44, "拒答 / 引导改写", "不编造查询", "term", "#F7F7F7"))
    b.append(node(348, 104, 94, 44, "前端展示", "ECharts + 口径注释", "data"))
    A = lambda x1, y1, x2, y2, dash="": ln(x1, y1, x2, y2, INK, 1, dash, True)
    A(206, 126, 159, 182)
    A(206, 204, 228, 204)
    b.append(path("M 277,226 L 277,246 L 395,246 L 395,260", arrow=True))
    A(442, 282, 464, 282)
    A(513, 304, 513, 338)
    A(466, 360, 442, 360)
    A(348, 360, 324, 360)
    A(230, 338, 230, 148)
    A(277, 126, 348, 126)
    b.append(path("M 230,204 L 230,316 L 159,316 L 159,338", stroke=RED, dash="4 3", arrow=True))
    b.append(t(238, 310, "否 → 拒答", 7.0, fill=RED))
    b.append(path("M 513,282 L 590,282 L 590,436 L 159,436 L 159,382", stroke=RED, dash="4 3", arrow=True))
    b.append(t(330, 428, "空集 / 越权 / 契约自修复失败 → 降级提示（不返回编造数据）", 7.2, fill=RED))
    b.append(r(X0, 440, CW, 26, INK, INK, 0.6))
    for i, s in enumerate(["Step 1　提问", "Step 2　意图解析", "Step 3　白名单查询", "Step 4　契约校验", "Step 5　渲染"]):
        b.append(t(X0 + 8 + i * 126, 457, s, 7.8, weight="bold", fill="#FFFFFF"))

    b.append(t(X0, 480, "B　双保险设计与成本 / 边界（收编为 P2 增强）", 9, weight="bold"))
    rows = [
        ["保险一：查询白名单", "模型只输出模板 ID 与参数，SQL 由后端白名单生成", "杜绝自然语言直转 SQL 带来的越权与注入；只读视图 + 用户 ID 强制过滤"],
        ["保险二：图表契约", "输出走 JSON Schema，字段 / 类型 / 枚举全校验", "校验失败触发自修复重试 ≤2 次，仍失败则降级为表格或提示"],
        ["模型档位", "意图解析走轻档（qwen-flash）", "单次成本 <0.001 元量级；聚合步骤零模型成本"],
        ["复用设施", "与 RAG 问答共用意图解析与契约校验", "边际开发约 1 周，不新增独立服务"],
        ["明确不做", "自由 SQL、跨用户聚合、模型自造指标", "口径不可核验的数字不进仪表盘（对齐产品报告可解释原则）"],
        ["验收口径", "模板命中率、拒答正确率、契约一次通过率", "与 G4 数据一致性门禁、图 4-1 测试体系共用评测集"],
    ]
    tb, hh = table(X0, 490, [116, 212, 304], ["约束", "设计", "原因与验收"], rows,
                   header_h=24, row_h=32, font=7.6, aligns=["start", "start", "start"])
    b.append(tb)
    y = 490 + hh + 8
    b.append(legend_flow(y))
    b.append(t(X0, y + 62, "注 1：NL 问数不是「让大模型查数据库」，而是把自然语言收敛到有限模板；展示层必须附数据口径与时间窗。", 7.8, fill="#444444"))
    b.append(t(X0, y + 78, "注 2：本图与图 3-2 成本护栏共用轻档路由与降级设施；与图 5-2 仪表盘模块对应。", 7.8, fill="#444444"))
    y4 = y + 88
    b.append(r(X0, y4, CW, 46, "#FAFAFA", INK, 0.8))
    b.append(icon("brain", X0 + 10, y4 + 8, 0.66))
    b.append(t(X0 + 34, y4 + 21, "理论映射：白名单模板＝降低外在负荷；先判定后生成＝可解释 AI；拒答优于编造＝可验证性优先", 8.0))
    b.append(t(X0 + 34, y4 + 37, "（对应技术方案 3.9 的认知负荷理论与元认知反馈，见图 4-3）", 7.6, fill=GREY))
    return frame("NL 问数仪表盘五步链路流程图拆解",
                 "第三章 · 判定分支 + 双保险约束 + 异常降级 · 技术方案 3.8（P2）",
                 "\n".join(b),
                 "圆角＝起止　矩形＝处理　菱形＝判定　平行四边形＝数据　虚线朱红＝拒答 / 降级出口",
                 "图 3-3　NL 问数仪表盘五步链路流程图拆解",
                 "Fig. 3-3　Flowchart decomposition of the NL-to-dashboard query pipeline",
                 tag="GFLC · 2026")


if __name__ == "__main__":
    save("图2-2_长任务异步执行链路时序图", fig_2_2(), ROOT)
    save("图2-3_大文件预签名直传协议时序图", fig_2_3(), ROOT)
    save("图3-3_NL问数仪表盘五步链路图", fig_3_3(), ROOT)
