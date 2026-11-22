# -*- coding: utf-8 -*-
"""D 组：图 2-2 / 2-3 / 3-3 流程图拆解重绘（632 全宽铺满、固定字号、节点密集、无压盖）。"""
from pathlib import Path
from _figlib import INK, GREY, RED, t, r, ln, save
from _figlib2 import (X0, CW, frame2, sect, grid, band, cards, notebox,
                      nd, lane, legend_flow, arrow, elbow)

ROOT = Path(__file__).parent
COL = [110, 218, 326, 434, 542]          # 5 列 × 100 宽，间隔 8
LY = [88, 176, 264, 352]                 # 4 泳道 × 88 高
NW, NH = 100, 44


def N(col, li, title, sub="", kind="proc", fill="#FFFFFF"):
    return nd(COL[col], LY[li] + 22, NW, NH, title, sub, kind, fill)


# ---------------------------------------------------------------- 图 2-2
def fig_2_2():
    b = [sect(78, "A　四泳道标准流程图：长任务从提交到产物落库（◆ 架构评审拍板）")]
    for i, (lab, sub) in enumerate([("① 浏览器", "React SPA"),
                                    ("② API", "FastAPI"),
                                    ("③ Redis", "List / 状态"),
                                    ("④ Worker", "独立进程 + PG")]):
        b.append(lane(LY[i], 88, lab, sub))
    # 节点
    for spec in [
        (0, 0, "提交任务", "POST /tasks", "term"),
        (0, 1, "鉴权 + 配额", "生成 task_id", "proc"),
        (1, 1, "体积判定", "> 阈值？", "dec"),
        (1, 2, "LPUSH", "载荷 ≤4 KB", "data"),
        (2, 1, "返回 202", "task_id / 轮询串", "term"),
        (0, 3, "BRPOPLPUSH", "取任务 + 心跳", "proc"),
        (1, 3, "执行管线", "checkpoint 分段", "proc"),
        (2, 3, "段失败？", "重试 ≤3", "dec"),
        (3, 3, "产物写 PG", "缓存 + 版本", "data"),
        (3, 2, "状态回写", "done / failed", "data"),
        (3, 0, "拿到产物", "渲染 / 导出", "term"),
        (4, 0, "轮询 GET", "3→15 s 退避", "proc"),
        (4, 3, "死信队列", "人工排查", "data", "#F4F4F4"),
    ]:
        b.append(N(*spec[:2], spec[2], spec[3], spec[4], spec[5] if len(spec) > 5 else "#FFFFFF"))
    # 连线（全部走节点间空隙，不穿过任何文字）
    b.append(arrow(160, 154, 160, 198))
    b.append(arrow(210, 220, 218, 220))
    b.append(arrow(268, 242, 268, 286))
    b.append(arrow(318, 220, 326, 220))
    b.append(arrow(268, 330, 268, 374))
    b.append(arrow(210, 396, 218, 396))
    b.append(arrow(318, 396, 326, 396))
    b.append(arrow(426, 396, 434, 396))
    b.append(arrow(484, 374, 484, 330))
    b.append(elbow("M 484,286 L 484,154"))
    b.append(arrow(534, 132, 542, 132))
    b.append(elbow("M 592,154 L 592,308 L 534,308", dash="4 3"))
    b.append(t(596, 240, "状态查询", 8.4, fill=GREY))
    b.append(elbow("M 376,418 L 376,430 L 592,430 L 592,418", color=RED, dash="4 3"))
    b.append(t(386, 426, "重试耗尽 → 死信（不无限重试）", 8.4, fill=RED))
    b.append(t(332, 278, "K1 大文件走图 2-3", 8.4, fill=RED))
    b.append(t(438, 278, "K2 入队 · K3 反馈", 8.4, fill=GREY))
    b.append(band(446, ["阶段 1　提交与鉴权", "阶段 2　入队与返回", "阶段 3　异步执行", "阶段 4　轮询与交付"]))

    b.append(sect(484, "B　关键参数与失败分支（逐项可核验）"))
    rows = [
        ["队列原语", "Redis List · BRPOPLPUSH", "取出即进 processing 备份队列，Worker 崩溃可由定时任务回收"],
        ["载荷上限", "≤4 KB（仅 ID / key / 参数）", "大对象一律走 MinIO，不把视频字节塞进 Redis"],
        ["硬超时", "GFLC_TASK_TIMEOUT_MIN = 60 min", "超时置 failed 并保留已完成段，不整单丢弃"],
        ["断点续传", "按段 checkpoint 写 PG", "失败重跑只补未完成段（吸收 BiliNote 模式）"],
        ["并发隔离", "WORKER_CONCURRENCY = 4", "API 进程不跑 CPU 密集管线；超长视频 P1 分片"],
        ["前端轮询", "3 s→15 s 退避，上限 5 min", "不引入 WebSocket 长连接，G2 P95 ≤3 s 不被拖垮"],
        ["异常出口", "重试耗尽 → 独立死信 List", "人工排查后清理；不自动无限重试，避免成本失控"],
    ]
    s, _ = grid(492, [96, 200, 336], ["项目", "拍板值", "理由与落点"], rows,
                header_h=26, row_h=30, font=9.0)
    b.append(s)
    b.append(sect(738, "C　设计依据、状态机与跨图锚定"))
    b.append(cards(744, 66, [
        ("进程隔离依据", ["40 min 视频 faster-whisper 转写占满 2 核", "十余分钟；与 G2「P95 ≤3 s」天然互斥，", "故 API / Worker 必须分进程部署"], "gear"),
        ("任务状态机", ["queued → processing → done；异常转 failed", "→ dead_letter；每次迁移双写 PG 与 Redis，", "前端只读状态快照，不订阅长连接"], "flow"),
        ("跨图锚定", ["K1 大文件直传见图 2-3；K2 入队、", "K3 任务态反馈见本图；与图 5-1、", "图 5-2、图 2-1 的编号一一对应"], "layers"),
    ], lsize=8.5))
    nb, _ = notebox(818, [
        "注 1：本链路为架构评审拍板项——API 只做鉴权与入队，所有 CPU 密集管线在 Worker 独立进程执行。",
        "注 2：数据源为技术方案 2.5 / 2.7 节与产品报告第五章（六）架构评审修订；◆ 表示 2026-11 评审新增。",
    ], h=40, fs=8.8)
    b.append(nb)
    return frame2("长任务异步执行链路流程图拆解",
                  "第二章 · 四泳道 + 标准流程符号 + 阶段带 + 参数矩阵 · 技术方案 2.5",
                  "\n".join(b),
                  "圆角＝起止　矩形＝处理　菱形＝判定　平行四边形＝数据　虚线＝异步　朱红＝异常出口　◆ 评审拍板",
                  "图 2-2　长任务异步执行链路流程图拆解",
                  "Fig. 2-2　Flowchart decomposition of the long-running asynchronous task pipeline")


# ---------------------------------------------------------------- 图 2-3
def fig_2_3():
    b = [sect(78, "A　四泳道标准流程图：大文件预签名直传三步协议（◆ 架构评审拍板）")]
    for i, (lab, sub) in enumerate([("① 浏览器", "React SPA"),
                                    ("② API", "FastAPI"),
                                    ("③ MinIO", "对象存储"),
                                    ("④ PG", "业务库")]):
        b.append(lane(LY[i], 88, lab, sub))
    for spec in [
        (0, 0, "选择文件", "视频 / PDF", "term"),
        (0, 1, "签发请求", "name / size / type", "proc"),
        (1, 1, "合规判定", "配额 / 水位？", "dec"),
        (2, 1, "生成预签名", "PUT URL + key", "proc"),
        (3, 1, "返回 URL", "有效期 15 min", "term"),
        (3, 2, "PUT 直传", "字节流不进 API", "data"),
        (3, 0, "上传进度", "XHR / 分片", "proc"),
        (4, 0, "confirm", "POST /uploads", "proc"),
        (4, 2, "HEAD / stat", "实际大小 / ETag", "data"),
        (4, 3, "写 materials", "建解析任务", "data"),
        (2, 3, "stat 一致？", "以 stat 为准", "dec"),
        (0, 3, "拒绝 / 清理", "超配额或残留", "term", "#F4F4F4"),
    ]:
        b.append(N(*spec[:2], spec[2], spec[3], spec[4], spec[5] if len(spec) > 5 else "#FFFFFF"))
    b.append(arrow(160, 154, 160, 198))
    b.append(arrow(210, 220, 218, 220))
    b.append(arrow(318, 220, 326, 220))
    b.append(arrow(426, 220, 434, 220))
    b.append(arrow(484, 242, 484, 286))
    b.append(arrow(484, 330, 484, 374))
    b.append(arrow(534, 308, 542, 308))
    b.append(elbow("M 592,154 L 592,286"))
    b.append(arrow(534, 132, 542, 132))
    b.append(elbow("M 592,330 L 592,352 L 376,352 L 376,374"))
    b.append(arrow(426, 396, 542, 396))
    b.append(arrow(326, 396, 210, 396))
    b.append(t(224, 390, "否 → 拒绝并清理残留", 8.4, fill=RED))
    b.append(t(452, 390, "是 → 落库", 8.4, fill=GREY))
    b.append(t(494, 176, "进度回传不经过 API 业务层", 8.4, fill=GREY))
    b.append(t(546, 262, "K1 直传", 8.4, fill=RED))
    b.append(band(446, ["第 1 步　签发 presign", "第 2 步　浏览器直传 MinIO",
                        "第 3 步　confirm 以 stat 为准", "异常　拒绝 / 清理残留"]))

    b.append(sect(484, "B　协议约束、安全边界与失败分支"))
    rows = [
        ["签发入参", "文件名 / 大小 / MIME / 用户配额", "服务端按白名单 MIME 与 UPLOAD_MAX 校验，不信任客户端声明"],
        ["预签名 URL", "PUT 限定 object_key，15 min 有效", "最小权限：只能写这一个 key，不能列举 / 删除桶内对象"],
        ["直传通道", "浏览器 → MinIO（Nginx 反代）", "字节流不进 API 进程，两个并发 1 GB 上传不打爆 4 GB 内存"],
        ["confirm 校验", "以 MinIO HEAD/stat 的 size / ETag 为准", "防「客户端声称成功但对象不完整」；不一致标记失败并清理"],
        ["磁盘治理", "水位 ≥80% 冻结；单任务 ≤5 GB", "与 5.7 节磁盘水位告警、临时文件清理联动"],
        ["幂等与版本", "object_key = task_id + 内容哈希", "重复 confirm 不产生第二条 materials；开启桶版本控制"],
        ["失败分支", "超配额 / 水位冻结 / stat 不符 / 过期", "统一返回明确错误码，前端展示「部分成功」而非静默吞掉"],
    ]
    s, _ = grid(492, [96, 200, 336], ["项目", "协议约定", "理由与落点"], rows,
                header_h=26, row_h=30, font=9.0)
    b.append(s)
    b.append(sect(738, "C　评审动机、信任边界与链路衔接"))
    b.append(cards(744, 66, [
        ("评审动机", ["隐含的 Nginx → FastAPI 上传路径会让", "1 GB 视频流经 API 进程；而「上传文件", "优先」是核心入口策略，必须绕开"], "warn"),
        ("信任边界", ["客户端不可信：大小、类型、成功状态", "一律以服务端校验与对象存储 stat 为准；", "预签名 URL 限定单 key 与短时效"], "shield"),
        ("链路衔接", ["materials 落库后与图 2-2 的 K2 入队", "链路衔接；K1 / K2 / K3 编号与图 5-1、", "图 5-2 互相锚定，可跨图引用"], "flow"),
    ], lsize=8.5))
    nb, _ = notebox(818, [
        "注 1：三步协议（签发 → 直传 → confirm）源自技术方案 2.6 节；磁盘水位与配额治理见 5.7 节。",
        "注 2：数据源另见产品报告第五章（六）架构评审修订；◆ 表示 2026-11 评审新增项。",
    ], h=40, fs=8.8)
    b.append(nb)
    return frame2("大文件预签名直传协议流程图拆解",
                  "第二章 · 三步协议 + 四泳道 + 判定分支 + 安全边界矩阵 · 技术方案 2.6 / 5.6 / 5.7",
                  "\n".join(b),
                  "圆角＝起止　矩形＝处理　菱形＝判定　平行四边形＝数据　虚线＝旁路　朱红＝异常出口　◆ 评审拍板",
                  "图 2-3　大文件预签名直传协议流程图拆解",
                  "Fig. 2-3　Flowchart decomposition of the presigned direct-upload protocol")


# ---------------------------------------------------------------- 图 3-3
def fig_3_3():
    b = [sect(78, "A　五步链路标准流程图：NL 问数仪表盘（P2 增强，双保险约束）")]
    LY3 = [88, 174, 260, 346]
    for i, (lab, sub) in enumerate([("① 交互层", "输入 / 渲染"),
                                    ("② 模型层", "轻档 LLM"),
                                    ("③ 数据层", "白名单模板"),
                                    ("④ 契约层", "Schema 校验")]):
        b.append(lane(LY3[i], 86, lab, sub))
    COL3 = [110, 218, 326, 434, 542]
    def N3(c, li, title, sub="", kind="proc", fill="#FFFFFF"):
        return nd(COL3[c], LY3[li] + 21, 100, 44, title, sub, kind, fill)
    for spec in [
        (0, 0, "自然语言提问", "本周掌握度趋势？", "term"),
        (0, 1, "意图解析", "轻档 · <0.001 元/次", "proc"),
        (1, 1, "命中模板？", "白名单枚举", "dec"),
        (2, 2, "模板 + 参数", "后端生成只读 SQL", "proc"),
        (3, 2, "结果合理？", "空集 / 超阈 / 越权", "dec"),
        (3, 3, "图表契约校验", "JSON Schema", "proc"),
        (2, 3, "通过？", "自修复 ≤2 次", "dec"),
        (1, 3, "渲染图表", "附口径与时间窗", "term"),
        (0, 3, "拒答 / 改写", "不编造查询", "term", "#F4F4F4"),
        (4, 0, "图表展示", "ECharts + 口径注释", "term"),
    ]:
        b.append(N3(*spec[:2], spec[2], spec[3], spec[4], spec[5] if len(spec) > 5 else "#FFFFFF"))
    A = lambda x1, y1, x2, y2, dash="": ln(x1, y1, x2, y2, INK, 1, dash, True)
    A(160, 151, 160, 195)
    A(210, 217, 218, 217)
    b.append(elbow("M 268,239 L 268,251 L 376,251 L 376,281"))
    A(426, 303, 434, 303)
    A(484, 325, 484, 367)
    A(434, 389, 426, 389)
    A(326, 389, 318, 389)
    b.append(elbow("M 268,411 L 268,436 L 620,436 L 620,153", dash="4 3"))
    b.append(t(300, 430, "渲染结果回传交互层展示（附口径与时间窗）", 8.4, fill=GREY))
    b.append(arrow(268, 239, 268, 340, dash="4 3", color=RED))
    b.append(t(196, 258, "否 → 拒答", 8.4, fill=RED))
    b.append(elbow("M 484,325 L 484,340 L 104,340 L 104,389 L 110,389", color=RED, dash="4 3"))
    b.append(t(240, 360, "空集 / 越权 / 契约失败 → 降级提示（不编造数据）", 8.4, fill=RED))
    b.append(band(446, ["Step 1　提问", "Step 2　意图解析", "Step 3　白名单查询",
                        "Step 4　契约校验", "Step 5　渲染"], fs=8.8))

    b.append(sect(484, "B　双保险设计与成本 / 边界（收编为 P2 增强）"))
    rows = [
        ["保险一：查询白名单", "模型只输出模板 ID 与参数", "SQL 由后端白名单生成，杜绝自然语言直转 SQL 的越权与注入"],
        ["保险二：图表契约", "输出走 JSON Schema 全字段校验", "校验失败触发自修复 ≤2 次，仍失败降级为表格或提示"],
        ["模型档位", "意图解析走轻档 qwen-flash", "单次成本 <0.001 元量级；聚合步骤零模型成本"],
        ["复用设施", "与 RAG 问答共用意图解析与校验", "边际开发约 1 周，不新增独立服务"],
        ["明确不做", "自由 SQL / 跨用户聚合 / 自造指标", "口径不可核验的数字不进仪表盘（对齐可解释原则）"],
        ["验收口径", "模板命中率、拒答正确率、一次通过率", "与 G4 数据一致性门禁、图 4-1 测试体系共用评测集"],
    ]
    s, _ = grid(492, [132, 200, 300], ["约束", "设计", "原因与验收"], rows,
                header_h=26, row_h=32, font=9.0)
    b.append(s)
    b.append(sect(726, "C　理论依据与展示规范"))
    b.append(cards(732, 70, [
        ("认知负荷理论", ["白名单模板把无限查询空间收敛为", "有限枚举，降低外在负荷（Sweller", "1988）；先判定后生成避免无效推理"], "brain"),
        ("可解释 AI 原则", ["每张图强制附数据口径、时间窗与", "样本量；拒答优于编造，保证任何", "数字可回指只读视图"], "eye"),
        ("复用与成本", ["与图 3-2 成本护栏共用轻档路由", "与降级设施；与图 5-2 仪表盘模块、", "图 4-3 理论矩阵一一对应"], "coin"),
    ], lsize=8.5))
    nb, _ = notebox(810, [
        "注 1：NL 问数不是「让大模型查数据库」，而是把自然语言收敛到有限模板；展示层必须附数据口径与时间窗。",
        "注 2：理论映射对应技术方案 3.9 节（认知负荷、元认知反馈、可验证性优先），图 4-3 给出全功能理论矩阵。",
    ], h=44, fs=8.8)
    b.append(nb)
    return frame2("NL 问数仪表盘五步链路流程图拆解",
                  "第三章 · 判定分支 + 双保险约束 + 异常降级 + 理论依据 · 技术方案 3.8 / 3.9（P2）",
                  "\n".join(b),
                  "圆角＝起止　矩形＝处理　菱形＝判定　平行四边形＝数据　虚线朱红＝拒答 / 降级出口",
                  "图 3-3　NL 问数仪表盘五步链路流程图拆解",
                  "Fig. 3-3　Flowchart decomposition of the NL-to-dashboard query pipeline")


if __name__ == "__main__":
    save("图2-2_长任务异步执行链路时序图", fig_2_2(), ROOT)
    save("图2-3_大文件预签名直传协议时序图", fig_2_3(), ROOT)
    save("图3-3_NL问数仪表盘五步链路图", fig_3_3(), ROOT)
