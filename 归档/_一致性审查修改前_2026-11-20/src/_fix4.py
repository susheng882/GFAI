# -*- coding: utf-8 -*-
"""流水线收尾：停用旧图归一化（已全部由生成器接管）+ 更新小册子要点与图名。"""
from pathlib import Path

ROOT = Path(__file__).parent

# 1) _normalize.py：旧图已全部由 _build_figs_a/c/d/e/f 重绘，重复归一化会二次缩放损伤
p = ROOT / "_normalize.py"
s = p.read_text(encoding="utf-8")
old = '''if __name__ == "__main__":
    for k, v in SPEC.items():
        if (ROOT / k).exists():
            build(k, v)
        else:
            print("  MISSING", k)'''
new = '''if __name__ == "__main__":
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
    print("  normalize: skipped (all figures owned by generators)")'''
assert old in s, "normalize main block not found"
p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("normalize.py patched")

# 2) _booklet.py：要点与图名对齐重绘后的内容结构
p = ROOT / "_booklet.py"
s = p.read_text(encoding="utf-8")
R = [
('name="系统技术架构图（七层）"', 'name="系统技术架构图（七层 · 架构评审修订版）"'),
('pts=["服务器选型卡：2 核 4G 轻量应用服务器、≥60 GB SSD、境内节点（G7 备案）、活动价 ¥188/年。",\n              "3×2 六服务卡片矩阵 + 服务依赖矩阵表，API 与 Worker 分进程，无流程箭头。",\n              "K1–K3 关键路径与贯穿运维面（CI / 备份 / 磁盘水位 / 告警 / certbot）。"]',
 'pts=["六款候选服务器全宽实证对比矩阵：腾讯云轻量 2C4G5M ★ ¥188/年 ≈¥15.7/月，另列 5 个否决 / 备选方案与理由。",\n              "3×2 六服务卡片矩阵 + 6×6 服务依赖矩阵全宽对齐，API 与 Worker 分进程，无流程箭头。",\n              "K1–K3 关键路径卡与贯穿运维面；规格、无 GPU 硬约束、磁盘治理三条注释可逐条核验。"]'),
('pts=["四泳道 + 标准流程符号（起止 / 处理 / 判定 / 数据）拆解 K2 入队与 K3 状态反馈，异常出口用朱红虚线。",',
 'pts=["四泳道 13 个标准流程符号 + 阶段带 + 7 行参数矩阵 + 设计依据三卡，全宽铺满无留白。",'),
('pts=["三步协议 + 四泳道判定：签发 presign → 浏览器直传 MinIO → confirm 以 stat 结果为准。",',
 'pts=["三步协议 + 12 个标准流程符号 + 三步阶段带 + 7 行安全边界矩阵 + 评审动机三卡。",'),
('pts=["三级取材降本链：平台字幕优先 → 音轨下载 → 本地转写，命中字幕单视频成本降一个量级。",',
 'pts=["五级管线全宽流程卡 + 三档路由实价矩阵（qwen-flash / plus / max 按量单价）+ 三级取材降本链 3 卡 + 双索引 RAG 3 卡。",'),
('pts=["三重护栏：单用户每日 token 配额、单任务 token 上限、全平台日成本阈值。",',
 'pts=["护栏判定链（起止 + 3 判定）+ 四级降级阶梯 + 三重护栏阈值表 + 可观测性表 + 理论权衡三卡。",'),
('pts=["五步链路改为标准流程图：提问 → 意图解析 → 白名单查询 → 契约校验 → 渲染，含 3 处判定与拒答 / 降级出口。",',
 'pts=["五步链路四泳道 10 个流程符号 + Step 1–5 阶段带 + 双保险约束表 + 理论依据三卡；异常汇流为朱红总线。",'),
('pts=["测试金字塔：单元 / 契约 / 集成 / 端到端 / 探索性，AI 评测集不少于 300 条。",',
 'pts=["测试金字塔五层 + 四指标闸门表 + G1–G7 七域逐域判定表 + Go/No-Go 流程 + 回滚机制三卡。",'),
('pts=["七层编号式分层 + 左侧中英对照层标签，模块网格统一、技术选型注记上墙。",',
 'pts=["七层统一网格重排：层间标注独立成行、技术选型注记移至层间行，彻底消除层内文字压盖。",'),
('pts=["全部要买的只有 3 样：服务器 ¥188/年、大模型订阅 ¥39–79/月、域名 ¥60–80/年，其余免费。",',
 'pts=["四张全宽实证矩阵：采购清单 / 五款一次付费方案对比 / 三档路由→模型池映射 / 8 个月总账。",'),
]
miss = []
for a, b in R:
    if a not in s:
        miss.append(a[:60])
    s = s.replace(a, b, 1)
p.write_text(s, encoding="utf-8")
print("booklet.py patched", len(R) - len(miss), "/", len(R), "| MISS:", miss)
