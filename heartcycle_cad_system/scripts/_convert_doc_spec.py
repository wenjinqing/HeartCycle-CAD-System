"""一次性脚本：把学院规范 .doc 转 .txt + .docx 以便阅读引用。"""
import os
import win32com.client as wc

SRC = r"c:\Users\ylq06\Desktop\毕业设计\校 教〔2021〕38 号阳光学院本科生毕业论文（设计）存档要求与撰写规范 (1) (1) (1).doc"
DST_TXT = r"D:\Graduate Work\heartcycle_cad_system\docs\thesis_format_spec.txt"
DST_DOCX = r"D:\Graduate Work\heartcycle_cad_system\docs\thesis_format_spec.docx"

os.makedirs(os.path.dirname(DST_TXT), exist_ok=True)
word = wc.Dispatch("Word.Application")
word.Visible = False
doc = word.Documents.Open(SRC, ReadOnly=True)
doc.SaveAs(DST_TXT, FileFormat=2)        # wdFormatText
doc.SaveAs(DST_DOCX, FileFormat=16)      # wdFormatDocumentDefault (.docx)
doc.Close(SaveChanges=False)
word.Quit()
print("OK txt=", os.path.getsize(DST_TXT), "docx=", os.path.getsize(DST_DOCX))
