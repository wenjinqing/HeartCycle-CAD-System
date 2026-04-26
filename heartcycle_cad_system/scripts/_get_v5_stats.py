"""用 Word COM 拿到论文的精确页数 / 字数。"""
import win32com.client as wc

SRC = r"c:\Users\ylq06\Desktop\毕业设计\论文\毕业设计论文 - V5.0_完整版.docx"

word = wc.Dispatch("Word.Application")
word.Visible = False
doc = word.Documents.Open(SRC, ReadOnly=True)
try:
    pages = doc.ComputeStatistics(2)        # wdStatisticPages
    words = doc.ComputeStatistics(0)        # wdStatisticWords
    chars_no_space = doc.ComputeStatistics(3)
    chars_with_space = doc.ComputeStatistics(5)
    paras = doc.ComputeStatistics(4)
    print(f"页数               : {pages}")
    print(f"Word 字数(中英混合) : {words:,}")
    print(f"字符数(不含空格)    : {chars_no_space:,}")
    print(f"字符数(含空格)      : {chars_with_space:,}")
    print(f"段落数              : {paras}")
finally:
    doc.Close(SaveChanges=False)
    word.Quit()
