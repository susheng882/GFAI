# -*- coding: utf-8 -*-
"""重绘生成器的坐标自检修正（一次性，源码级替换）。"""
from pathlib import Path

ROOT = Path(__file__).parent
F = ROOT / "_build_figs_f.py"
D = ROOT / "_build_figs_d.py"

R_F = [
# --- 5-1：技术选型注记移出层框，改放层间行（原位置会压住模块盒） ---
('''    if tech:
        o.append(t(X0 + 84, y + 11, tech, 8.2, fill=GREY))
    for m in mods:''',
 '''    for m in mods:'''),
('b.append(inter(y, "HTTPS / TLS（certbot 自动续期 ◆）", "接入")); y += 14',
 'b.append(inter(y, "HTTPS / TLS（certbot 自动续期 ◆）", "L1  React 19 · AntD 5 · Vite")); y += 14'),
('"接入 → 应用"', '"L2  Nginx · HttpOnly Cookie · Argon2id"'),
('"应用 → 异步"', '"L3  FastAPI · Uvicorn｜同步边界仅短查询"'),
('"异步 → AI 管线"', '"L4  独立进程 profile: worker"'),
('"AI 管线 → 持久层"', '"L5  三级取材链 · 三档路由 · JSON Schema"'),
('"持久层 → 基础设施"', '"L6  四存储职责单一化 · 时间戳 P0"'),
# --- 5-1：过长副标题收紧，避免 130/176 px 模块盒溢出 ---
('"BRPOPLPUSH · 超时回收 · maxmemory 256 MB ◆"', '"BRPOPLPUSH · 超时回收 ◆"'),
('"并发 4 · 超时 1800 s · checkpoint 断点续传"', '"并发 4 · checkpoint 断点续传"'),
('"进度 · 状态写入 PG；产物落 MinIO / 缓存落 PG ◆"', '"状态写 PG · 产物落 MinIO ◆"'),
('"业务库 · 产物缓存 · pgvector；Alembic 版本化迁移 ◆"', '"业务库 · pgvector · Alembic ◆"'),
('"任务队列 · 会话 · 小状态；maxmemory 256 MB"', '"队列 · 会话 · 小状态"'),
('"音视频原始对象 · 产物对象存储；桶版本控制"', '"原始对象 · 产物对象存储"'),
# --- 3-1：A 区五卡文案收紧（卡宽仅 118 px） ---
('''        ("① 统一取材", ["视频链接 / 本地文件 / PDF", "三级降本链：平台字幕 → 音轨", "→ 本地 faster-whisper 转写"], "video"),
        ("② 分块归一", ["按请求体积预算二分切块", "多轮归并，单次 LLM 输入", "控制在契约上限内"], "doc"),
        ("③ 三档路由", ["LIGHT / MID / HEAVY", "按任务难度与体积分档", "超额自动降档而非失败"], "gear"),
        ("④ 生成校验", ["JSON Schema 输出契约", "字段 / 类型 / 枚举全校验", "失败触发自修复重试 ≤2 次"], "check"),
        ("⑤ 索引与溯源", ["ChromaDB 双索引入库", "笔记 H2/H3 块 + 转写滑窗", "时间戳写入 P0 硬字段"], "db"),
    ], gap=10, lsize=8.4, tsize=9.4))''',
 '''        ("① 统一取材", ["视频 / PDF / 链接", "三级链：字幕→音轨", "→本地转写"], "video"),
        ("② 分块归一", ["体积预算二分切块", "多轮归并", "控制单次输入上限"], "doc"),
        ("③ 三档路由", ["LIGHT/MID/HEAVY", "按难度与体积分档", "超额自动降档"], "gear"),
        ("④ 生成校验", ["JSON Schema 契约", "字段/类型全校验", "失败自修复 ≤2 次"], "check"),
        ("⑤ 索引溯源", ["Chroma 双索引", "笔记块+转写滑窗", "时间戳 P0 硬字段"], "db"),
    ], gap=10, lsize=8.0, tsize=9.2))'''),
# --- 4-1：右侧表宽度原先 364 px 会越出画布（可用仅 326） ---
('s, _ = grid(88, [92, 62, 210], ["指标", "阈值", "判定方式"], rows_a,',
 's, _ = grid(88, [80, 56, 190], ["指标", "阈值", "判定方式"], rows_a,'),
('b.append(r(330, 264, 302, 34, "#FAFAFA", "#999999", 0.8, "5 3"))',
 'b.append(r(330, 264, 326, 34, "#FAFAFA", "#999999", 0.8, "5 3"))'),
('("单元测试", "解析 / 分块 / 路由 / 调度纯函数", 136)',
 '("单元测试", "解析 / 分块 / 路由纯函数", 136)'),
# --- 4-1：C 区四节点原 x 最右到 678，越出画布；改为严格 632 分布 ---
('''    b.append(sect(590, "C　Go / No-Go 判定流程与回滚机制"))
    xs = [X0 + 6, 172, 338, 504]''',
 '''    b.append(sect(590, "C　Go / No-Go 判定流程与回滚机制"))
    xs = [X0 + i * 160.67 for i in range(4)]'''),
]

R_D = [
# --- 2-3：confirm→stat 垂直线原插进节点文字；进度旁路原穿过返回 URL 框 ---
('''    b.append(arrow(534, 308, 542, 308))
    b.append(elbow("M 592,154 L 592,308"))
    b.append(elbow("M 592,330 L 592,352 L 376,352 L 376,374"))
    b.append(arrow(326, 396, 210, 396))
    b.append(t(224, 390, "否 → 拒绝并清理残留", 8.4, fill=RED))
    b.append(t(440, 390, "是 → 落库", 8.4, fill=GREY))
    b.append(elbow("M 484,264 L 510,264 L 510,132 L 534,132", dash="4 3"))
    b.append(t(494, 176, "进度回传不经过 API 业务层", 8.4, fill=GREY))''',
 '''    b.append(arrow(534, 308, 542, 308))
    b.append(elbow("M 592,154 L 592,286"))
    b.append(arrow(534, 132, 542, 132))
    b.append(elbow("M 592,330 L 592,352 L 376,352 L 376,374"))
    b.append(arrow(426, 396, 542, 396))
    b.append(arrow(326, 396, 210, 396))
    b.append(t(224, 390, "否 → 拒绝并清理残留", 8.4, fill=RED))
    b.append(t(452, 390, "是 → 落库", 8.4, fill=GREY))
    b.append(t(494, 176, "进度回传不经过 API 业务层", 8.4, fill=GREY))'''),
# --- 3-3：展示节点移到交互层右列；两条异常改为汇流总线，避免与展示回授线交叉 ---
('(2, 0, "前端展示", "ECharts + 口径注释", "data"),',
 '(4, 0, "图表展示", "ECharts + 口径注释", "term"),'),
('''    A(268, 367, 268, 151)
    A(376, 129, 376, 129)
    A(376, 129, 434, 129)
    b.append(elbow("M 268,239 L 268,340 L 160,340 L 160,367", color=RED, dash="4 3"))
    b.append(t(238, 334, "否 → 拒答", 8.4, fill=RED))
    b.append(elbow("M 484,325 L 600,325 L 600,434 L 160,434 L 160,411", color=RED, dash="4 3"))
    b.append(t(300, 428, "空集 / 越权 / 契约自修复失败 → 降级提示（不返回编造数据）", 8.4, fill=RED))''',
 '''    b.append(elbow("M 268,411 L 268,428 L 620,428 L 620,153", dash="4 3"))
    b.append(t(300, 424, "渲染结果回传交互层展示（附口径与时间窗）", 8.4, fill=GREY))
    b.append(arrow(268, 239, 268, 340, dash="4 3", color=RED))
    b.append(t(196, 258, "否 → 拒答", 8.4, fill=RED))
    b.append(elbow("M 484,325 L 484,340 L 104,340 L 104,389 L 110,389", color=RED, dash="4 3"))
    b.append(t(240, 336, "空集 / 越权 / 契约自修复失败 → 降级提示", 8.4, fill=RED))'''),
]

for path, rules in [(F, R_F), (D, R_D)]:
    s = path.read_text(encoding="utf-8")
    miss = []
    for a, b in rules:
        if a not in s:
            miss.append(a[:70].replace("\n", " / "))
        s = s.replace(a, b, 1)
    path.write_text(s, encoding="utf-8")
    print(path.name, "replacements", len(rules) - len(miss), "/", len(rules), "| MISS:", miss)
