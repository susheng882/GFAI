# -*- coding: utf-8 -*-
"""BP 图号重编后同步两份文档中的图号引用（只改 w:t 文本，不动结构与书签）。"""
import re
import shutil
import zipfile
from pathlib import Path
from lxml import etree

BASE = Path(r"F:\GrowthForward_AI学习伴侣")
MD = BASE / "技术方案_GrowthForward.md"
DOCX = BASE / "产品报告_GrowthForward_AI学习伴侣_V2完整版.docx"
BAK = BASE / "归档" / "_backup_report_before_bp_renumber.docx"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

NO = {"1-1": "2-4", "1-2": "2-5", "2-1": "6-1", "4-2": "3-10",
      "4-3": "3-3", "5-3": "7-2", "5-4": "7-3"}


def _repl(m):
    k = m.group(1) + "-" + m.group(2)
    return "图 " + NO.get(k, k)


def patch(s):
    s = s.replace("图 5-3 / 5-4", "图 7-2 / 图 7-3")
    return re.sub(r"图 (\d)-(\d)(?!\d)", _repl, s)


NOTE_MD = ("> **图号口径**：本文与《产品报告》中引用的「图 X-Y」均指 "
           "《GrowthForward 商业计划书学术图表册》"
           "（`毕设材料/学术图表/统一版式/GrowthForward_学术图表册.pdf`）中的图号，"
           "按商业计划书九章体系重编（卷首品牌 → ① 执行摘要 → ② 市场 → ③ 产品 → ④ 架构 → "
           "⑤ AI 治理 → ⑥ 工程 → ⑦ 财务 → ⑧ 团队 → ⑨ 进度与风险）；"
           "本文自身章节号（§1.4 / §3.9 / §5.8 等）保持不变。\n\n")


def main():
    # --- 技术方案 md ---
    s = MD.read_text(encoding="utf-8")
    s2 = patch(s)
    if "图号口径" not in s2:
        lines = s2.splitlines(keepends=True)
        # 插在第一个二级标题（## 0. 结论）之前
        for i, l in enumerate(lines):
            if l.startswith("## "):
                lines.insert(i, NOTE_MD)
                break
        s2 = "".join(lines)
    MD.write_text(s2, encoding="utf-8")
    print("MD refs remaining(old):", re.findall(r"图 (?:1-1|1-2|2-1|4-2|4-3|5-3|5-4)", s2))
    print("MD note inserted:", "图号口径" in s2, "| lines", len(s2.splitlines()))

    # --- 产品报告 docx（保留命名空间前缀） ---
    shutil.copy2(DOCX, BAK)
    z = zipfile.ZipFile(DOCX)
    items = [(i, z.read(i.filename)) for i in z.infolist()]
    z.close()
    doc = [b for n, b in items if n.filename == "word/document.xml"][0]
    root = etree.fromstring(doc)
    cnt = 0
    for t in root.iter(W + "t"):
        if not t.text:
            continue
        new = patch(t.text)
        if "逐项报价细目见技术方案 5.8 节" in new and "图号按商业计划书" not in new:
            new = new.replace(
                "实际采购以厂商当期活动页为准。",
                "实际采购以厂商当期活动页为准；图号按商业计划书学术图表册九章体系重编。")
        if new != t.text:
            t.text = new
            cnt += 1
    new_doc = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    with zipfile.ZipFile(DOCX, "w", zipfile.ZIP_DEFLATED) as out:
        for info, data in items:
            out.writestr(info, new_doc if info.filename == "word/document.xml" else data)
    z2 = zipfile.ZipFile(DOCX)
    r2 = etree.fromstring(z2.read("word/document.xml"))
    print("DOCX patched nodes:", cnt)
    print("  bookmarks", len(list(r2.iter(W + "bookmarkStart"))), "/", len(list(r2.iter(W + "bookmarkEnd"))),
          "tables", len(list(r2.iter(W + "tbl"))), "fldChar", len(list(r2.iter(W + "fldChar"))))
    print("  mc:Ignorable", r2.get("{http://schemas.openxmlformats.org/markup-compatibility/2006}Ignorable"),
          "| w14 in nsmap", "w14" in r2.nsmap)
    txt = "".join(n.text or "" for n in r2.iter(W + "t"))
    print("  old refs left:", re.findall(r"图 (?:1-1|1-2|2-1|4-2|4-3|5-3|5-4)", txt))
    print("  new refs:", re.findall(r"图 (?:2-4|2-5|3-3|3-10|6-1|7-2|7-3)", txt))
    print("  backup:", BAK.name)


if __name__ == "__main__":
    main()
