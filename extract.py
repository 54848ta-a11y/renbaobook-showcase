# -*- coding: utf-8 -*-
"""从馆藏 Excel 提取全部图书为 books.json（供展示网页内嵌使用）。"""
import openpyxl, json, os, collections

SRC = r"C:/Users/Haonch/WorkBuddy/Claw/attachments/1787454777016-5fcba4/20260706-人保研修院借阅室现有馆藏（5002册）.xlsx"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "books.json")

# 中图分类法（索书号首字母 -> 类目名）
CLC = {
    "A": "马克思主义、列宁主义、毛泽东思想、邓小平理论",
    "B": "哲学、宗教", "C": "社会科学总论", "D": "政治、法律", "E": "军事",
    "F": "经济", "G": "文化、科学、教育、体育", "H": "语言、文字", "I": "文学",
    "J": "艺术", "K": "历史、地理", "N": "自然科学总论", "O": "数理科学和化学",
    "P": "天文学、地球科学", "Q": "生物科学", "R": "医药、卫生", "S": "农业科学",
    "T": "工业技术", "U": "交通运输", "V": "航空、航天", "X": "环境科学、安全科学",
    "Z": "综合性图书",
}

def cat_of(callno):
    c = (callno or "").strip().upper()
    for ch in c:
        if ch.isalpha():
            return ch if ch in CLC else "其他"
    return "其他"

def s(v):
    return (str(v).strip() if v is not None else "")

def main():
    wb = openpyxl.load_workbook(SRC, read_only=True, data_only=True)
    ws = wb["馆藏分布清单"]
    rows = ws.iter_rows(values_only=True)
    next(rows)  # 大标题行
    header = [s(x) for x in next(rows)]
    print("表头:", header)
    books = []
    miss_isbn = miss_title = 0
    for i, r in enumerate(rows):
        if all(v is None or str(v).strip() == "" for v in r):
            continue
        barcode, title, isbn, author, callno, publisher, status, price, location = (list(r) + [None] * 9)[:9]
        title, isbn = s(title), s(isbn)
        if not title:
            miss_title += 1
        if not isbn:
            miss_isbn += 1
        cat = cat_of(s(callno))
        books.append({
            "i": len(books),                    # 序号
            "b": s(barcode),                    # 条码号
            "t": title,                         # 题名
            "isbn": isbn,
            "a": s(author),                     # 作者
            "c": s(callno),                     # 索书号
            "p": s(publisher),                  # 出版社
            "st": s(status),                    # 馆藏状态
            "pr": s(price),                     # 单价
            "cat": cat,                         # 中图分类字母
        })
    wb.close()

    cats = collections.Counter(b["cat"] for b in books)
    titles = collections.Counter(b["t"] for b in books)
    dup_titles = sum(1 for t, n in titles.items() if n > 1)
    print(f"总册数: {len(books)} | 种数(不同题名): {len(titles)} | 重复题名的种数: {dup_titles}")
    print(f"缺 ISBN: {miss_isbn} | 缺题名: {miss_title}")
    print("分类分布:", dict(sorted(cats.items(), key=lambda x: -x[1])))

    payload = {
        "clc": CLC,
        "books": books,
        "meta": {"total": len(books), "species": len(titles)},
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    print(f"已写出 {OUT} ({os.path.getsize(OUT)//1024} KB)")

if __name__ == "__main__":
    main()
