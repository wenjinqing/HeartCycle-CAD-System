"""把 V5 docx 同步导出一份 PDF 供快速浏览。"""
import os
import win32com.client as wc

SRC = r"c:\Users\ylq06\Desktop\毕业设计\论文\毕业设计论文 - V5.0_完整版.docx"
DST = r"c:\Users\ylq06\Desktop\毕业设计\论文\毕业设计论文 - V5.0_完整版.pdf"

word = wc.Dispatch("Word.Application")
word.Visible = False
doc = word.Documents.Open(SRC, ReadOnly=True)

# 触发分页 / 更新页码 / 更新目录之类的域；TOC 会被刷新到当前实际页码
try:
    doc.Fields.Update()
    doc.Repaginate()
except Exception:
    pass

doc.SaveAs(DST, FileFormat=17)  # 17 = wdFormatPDF
doc.Close(SaveChanges=False)
word.Quit()
print(f"OK PDF 大小: {os.path.getsize(DST)/1024:.1f} KB -> {DST}")
