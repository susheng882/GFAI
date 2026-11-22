# -*- coding: utf-8 -*-
"""2026-11-15：产品报告补充市场数据来源链接，并修正与实采报价冲突的旧口径。

只改 word/document.xml 的文本节点与末尾追加段落，不动样式、书签、域与目录结构。
"""
from zipfile import ZipFile, ZIP_DEFLATED
from pathlib import Path
from lxml import etree
import shutil

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
XML = '{http://www.w3.org/XML/1998/namespace}'
ROOT = Path(r'F:\GrowthForward_AI学习伴侣')
DOC = ROOT / '产品报告_GrowthForward_AI学习伴侣_V2完整版.docx'
ARCH = ROOT / '归档' / '_产品报告_补充来源前_2026-11-15.docx'
ARCH.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(DOC, ARCH)

with ZipFile(DOC) as z:
    names = z.namelist()
    data = {n: z.read(n) for n in names}
root = etree.fromstring(data['word/document.xml'])
body = root.find(W + 'body')

# 1) 修正「成本均为经验估算」这一与 2026-11-14 官网实采冲突的旧表述
NEW_EST = ('已实采事实（2026-11-14 复核）：服务器、对象存储、域名、模型订阅与按量单价均按厂商官网当日报价采集，'
           '逐项列于第九章成本表、《技术方案》§5.8 与图 7-2 / 7-3，含活动价、学生优惠与次年续费价，'
           '并标注采集日期与来源链接；仍属估算的仅工作量人日与部分指标阈值。价格随供应商调整会变化，执行前需重新询价。')
hit = 0
for p in body.findall(W + 'p'):
    if ''.join(p.itertext()).startswith('估算值：全部成本'):
        ts = p.findall('.//' + W + 't')
        ts[0].text = NEW_EST
        for x in ts[1:]:
            x.text = ''
        hit += 1
assert hit == 1, f'估算值段落命中 {hit} 次，已中止'

# 2) 在附录末尾、sectPr 之前追加来源核验段（不用 heading 样式，避免影响活目录）
def para(txt, bold=False):
    p = etree.Element(W + 'p')
    pPr = etree.SubElement(p, W + 'pPr')
    sp = etree.SubElement(pPr, W + 'spacing')
    sp.set(W + 'before', '100'); sp.set(W + 'after', '60')
    sp.set(W + 'line', '320'); sp.set(W + 'lineRule', 'auto')
    r = etree.SubElement(p, W + 'r')
    rPr = etree.SubElement(r, W + 'rPr')
    if bold:
        etree.SubElement(rPr, W + 'b')
    rf = etree.SubElement(rPr, W + 'rFonts')
    rf.set(W + 'ascii', 'SimSun'); rf.set(W + 'eastAsia', 'SimSun')
    sz = etree.SubElement(rPr, W + 'sz')
    sz.set(W + 'val', '22' if bold else '20')
    t = etree.SubElement(r, W + 't')
    t.set(XML + 'space', 'preserve')
    t.text = txt
    return p

ADDS = [
    ('市场数据来源与口径核验（2026-11-15 补充）', True),
    ('在线教育用户 3.27 亿人：CNNIC 第 57 次《中国互联网络发展状况统计报告》（2026-02-05 发布，'
     '数据截至 2025-12，同比 −7.89%），https://www.cnnic.cn/ ；报道见 '
     'https://www.cnr.cn/jy/gc/20260209/t20260209_527520725.shtml 。'
     '早期材料中的「突破 3.5 亿」为 2024 年高点，已弃用。', False),
    ('2027 研考报名人数：截至 2026-11-15 教育部尚未公布最终数据；报名 2026-10-15～24、'
     '初试 2026-12-19～20 见《2027 年全国硕士研究生招生工作管理规定》教学〔2026〕2号 '
     'http://www.moe.gov.cn/srcsite/A15/moe_778/s3261/202609/t20260923_1451734.html 。'
     '机构测算 315–335 万（中枢约 320 万）为非官方值，仅作敏感性区间，不进入 TAM/SAM 计算，'
     'https://www.mbachina.com/html/xw/202610/663518.html 。', False),
    ('2026 研考报名 343 万人为教育部 2025-11-24 公布的最近一期官方值，仅作历史锚点：'
     'https://www.eol.cn/news/yaowen/202511/t20251124_2702608.shtml 。'
     '答辩前须复查研招网 / 教育部是否发布 2027 年最终数据；若已发布，以官方值替换「尚未公布」，'
     '不得用机构预测覆盖官方值。完整口径对照表见《技术方案_GrowthForward.md》§1.5 与图 2-3。', False),
]
sect = body.find(W + 'sectPr')
idx = list(body).index(sect)
for k, (txt, b) in enumerate(ADDS):
    body.insert(idx + k, para(txt, b))

data['word/document.xml'] = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)
with ZipFile(DOC, 'w', ZIP_DEFLATED) as z:
    for n in names:
        z.writestr(n, data[n])

# 3) 结构校验：书签 / 表格 / 域 / 活目录均须保持
with ZipFile(DOC) as z:
    x = z.read('word/document.xml').decode('utf-8')
print('bookmarkStart / End:', x.count('<w:bookmarkStart'), '/', x.count('<w:bookmarkEnd'))
print('w:tbl 表格:', x.count('<w:tbl'), '| fldChar 域:', x.count('w:fldCharType'))
print('活 TOC 域仍在:', 'TOC ' in x)
print('命名空间 w14 前缀保留:', 'w14' in x[:1200] or 'w14:' in x)
print('来源链接写入:', all(s in x for s in ['moe.gov.cn', 'cnnic.cn', 'eol.cn', 'mbachina.com']))
print('实采口径已修正:', '已实采事实' in x and '经验值估算' not in x)
print('修订前备份:', ARCH.name)
