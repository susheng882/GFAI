# -*- coding: utf-8 -*-
"""为图表册 PDF 补全文档元数据（幂等，可在每次重建 PDF 后运行）。
Playwright page.pdf() 产出的 PDF 无 Title/Author，答辩时属性栏空白，
这里用 pypdf 写回与旧版一致的规范元数据。
"""
from pathlib import Path
from pypdf import PdfReader, PdfWriter

BASE = Path(r'F:\GrowthForward_AI学习伴侣\毕设材料\商业计划书')
JOBS = [
    (BASE / '统一版式' / 'GrowthForward_商业计划书册.pdf',
     'GrowthForward 商业计划书 · 学术图表册（40 张图 / 54 页 A4）',
     '毕业设计商业计划书配套学术图表册：卷首品牌篇 + 九章 BP 逻辑，统一 A4 竖版版式'),
]

for pdf, title, subject in JOBS:
    if not pdf.exists():
        print('SKIP 不存在', pdf.name)
        continue
    r = PdfReader(str(pdf))
    w = PdfWriter()
    for page in r.pages:
        w.add_page(page)
    w.add_metadata({
        '/Title': title,
        '/Author': 'GrowthForward 项目组',
        '/Subject': subject,
        '/Keywords': 'GrowthForward,AI 学习伴侣,商业计划书,学术图表册,毕业设计,BP',
        '/Creator': 'Chromium',
        '/Producer': 'Skia/PDF (Playwright)',
    })
    tmp = pdf.with_suffix('.tmp.pdf')
    with open(tmp, 'wb') as f:
        w.write(f)
    tmp.replace(pdf)
    print('OK', pdf.name, '| 页数', len(r.pages), '|', pdf.stat().st_size, 'B')
