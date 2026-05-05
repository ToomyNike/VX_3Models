import docx
import sys
import io

def read_doc(filepath, f_out):
    try:
        doc = docx.Document(filepath)
        for p in doc.paragraphs:
            if p.text.strip():
                f_out.write(p.text + '\n')
    except Exception as e:
        f_out.write(f"Error: {e}\n")

if __name__ == "__main__":
    files = [
        "计算机设计大赛思路：基于 APSIM 机理模型与微信小程序的全栈智慧农业平台.docx",
        "MVP开发文档.docx"
    ]
    with open("docx_output_utf8.txt", "w", encoding="utf-8") as f_out:
        for f in files:
            f_out.write("======= " + f + " =======\n")
            read_doc(f, f_out)
