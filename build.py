# -*- coding: utf-8 -*-
"""把 books.json + borrowed.json 内嵌进 template.html，生成单文件 index.html（在线/离线均可用）。
借出状态唯一可变来源是 borrowed.json；本脚本只读取 books.json，不改写它。
"""
import os
from builder import render_index

HERE = os.path.dirname(os.path.abspath(__file__))
out, marked = render_index(
    os.path.join(HERE, 'books.json'),
    os.path.join(HERE, 'borrowed.json'),
    os.path.join(HERE, 'template.html'))
dst = os.path.join(HERE, 'index.html')
with open(dst, 'w', encoding='utf-8') as f:
    f.write(out)
print(f'已生成 {dst} ({os.path.getsize(dst)//1024} KB)，标记已外借 {marked} 本')
